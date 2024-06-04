import time
import uuid
from typing import Union

from django.conf import settings
from redis import Redis


def get_redis_interface(
    db_name: str,
    decode_responses: bool = True,
) -> Redis:
    """Pick an existing redis connection from the global object.

    :param db_name: The name of the database to use, as defined in our settings
    :param decode_responses: Whether to decode responses with utf-8. If you're
    putting binary data (like a picked object) into redis, don't try to decode
    it.
    :return Redis interface using django settings
    """
    return settings.REDIS_CLIENTS[f"{db_name}-{decode_responses}"]


def create_redis_semaphore(r: Union[str, Redis], key: str, ttl: int) -> bool:
    """Use a redis key to create a semaphore with a specified TTL

    Note that this function has a very small race condition between when it
    checks for the key, discovers it doesn't exist, and then creates it. This
    race condition is unfortunate. It can be fixed in one of two ways. A Lua
    script could be set up in the Redis server as described here:

      https://stackoverflow.com/a/36645586/64911

    Or Redis can be upgraded to a version where the SET command has a KEEPTTL
    parameter. Using that, you can set the value while keeping the TTL it might
    already have. In #1675 we learned that the obvious way of doing this, using
    getset, deletes the TTL from a key, making that approach untenable. So,
    instead of using that approach, or using a Lua script, we just accept the
    possibility of a race condition.

    :param r: The Redis DB to connect to as a connection interface or str that
    can be handed off to get_redis_interface.
    :param key: The key to create
    :param ttl: How long the key should live
    :return: True if the key was created else False
    """
    if isinstance(r, str):
        r = get_redis_interface(r)

    currently_enqueued = bool(r.get(key))
    if currently_enqueued:
        # We've got the semaphore already
        return False

    # We don't have a key for this yet. Set a new expiring key. Normally, the
    # semaphores created by this function would be manually cleaned up by your
    # code, but if you fail to do so, the expiration gives a safety so that the
    # semaphore *will* eventually go away even if our task, server, whatever
    # crashes.
    # Redis doesn't do bools anymore, so use 1 as True.
    r.set(key, 1, ex=ttl)
    return True


def delete_redis_semaphore(r: Union[str, Redis], key: str) -> None:
    """Delete a redis key

    :param r: The Redis DB to connect to as a connection interface or str that
    can be handed off to get_redis_interface.
    :param key: The key to delete
    :return: None
    """
    if isinstance(r, str):
        r = get_redis_interface(r)
    r.delete(key)


def acquire_atomic_redis_lock(r: Redis, key, ttl: int) -> str:
    """Acquires an atomic lock in Redis.

    This method attempts to acquire a lock with the given key and TTL in Redis.
    It uses a Lua script to ensure the lock is set atomically.
    If the lock is already in use by another process, it retries until the
    lock is acquired.

    :param r: The Redis DB to connect to as a connection interface.
    :param key: The key for the lock in Redis.
    :param ttl: Time-to-live for the lock in milliseconds.
    :return: A unique identifier for the lock.
    """

    # Lua script to acquire lock
    lua_script = """
    local lock_key = KEYS[1]
    local lock_value = ARGV[1]
    local ttl = ARGV[2]

    if redis.call("SET", lock_key, lock_value, "NX", "PX", ttl) then
        return 1
    else
        return 0
    end
    """
    identifier = str(uuid.uuid4())
    while True:
        if r.eval(lua_script, 1, key, identifier, ttl) == 1:
            return identifier
        time.sleep(0.1)


def release_atomic_redis_lock(r: Redis, key, identifier: str) -> int:
    """Releases an atomic lock in Redis.

    This method releases the lock with the given key and identifier in Redis.
    It uses a Lua script to ensure the lock is only released if the identifier
    matches the current lock value. This prevents other processes from
    mistakenly releasing the lock.

    :param r: The Redis DB to connect to as a connection interface.
    :param key: The key for the lock in Redis.
    :param identifier: The unique identifier for the lock.
    :return: None
    """
    # Lua script to release lock
    lua_script = """
    local lock_key = KEYS[1]
    local lock_value = ARGV[1]

    if redis.call("GET", lock_key) == lock_value then
        return redis.call("DEL", lock_key)
    else
        return 0
    end
    """
    return r.eval(lua_script, 1, key, identifier)
