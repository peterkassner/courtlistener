# AGENTS.md

**Open issue — [local storage layout, search history, and sync artifact organization](ISSUES-LIST.md#open-local-storage-layout-and-search-history-undetermined):** where relational data vs files should live long-term is [not fully decided](ISSUES-LIST.md); see [ISSUES-LIST.md](ISSUES-LIST.md) for backlog items (0–4).

## Cursor Cloud specific instructions

### Overview

CourtListener is a Django 5.1 legal research platform (Python 3.12) with React/webpack frontend assets. See `README.md` for general context.

### Research sync (current local layout)

- **Relational:** `cl.research_sync` tables in PostgreSQL — `SyncTarget`, `SyncRun`, `LocalHit` (includes `snapshot` JSON per hit). There is no separate “search history” table yet; runs are logged on `SyncRun`.
- **PDFs (optional):** `LocalHit.local_file` → under **`MEDIA_ROOT`**, default **`cl/assets/media/research_sync/pdfs/<year>/<month>/`** (override with env `MEDIA_ROOT`).
- **Broader layout** (registries, digests, mail/RSS): tracked in [ISSUES-LIST.md](ISSUES-LIST.md).

### Architecture

- **Backend**: Django app in `cl/`, settings split across `cl/settings/` (uses `django-environ` `FileAwareEnv` — reads from shell env vars, NOT `.env` files)
- **Frontend**: React/webpack in `cl/` (see `cl/package.json`), built with `npx webpack`
- **Task queue**: Celery with Redis broker (set to `CELERY_TASK_ALWAYS_EAGER=True` in dev mode)
- **Dependencies**: Poetry (`pyproject.toml` / `poetry.lock`) for Python; npm (`cl/package.json`) for JS

### Backing Services (Docker)

Three Docker containers are required. Start them before running Django:

```bash
# Network (create once)
docker network create cl_net_overlay 2>/dev/null || true

# Redis
docker start cl-redis 2>/dev/null || docker run -d --name cl-redis --network cl_net_overlay -p 6379:6379 redis:latest

# PostgreSQL (uses SSL certs from docker/postgresql/)
docker start cl-postgres 2>/dev/null || docker run -d --name cl-postgres --network cl_net_overlay -p 5432:5432 \
  -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=courtlistener \
  cl-postgres postgres -c ssl=on -c ssl_cert_file=/etc/ssl/private/cl-postgres.crt -c ssl_key_file=/etc/ssl/private/cl-postgres.key

# Elasticsearch 8.8.1 (uses SSL certs from docker/elastic/)
docker start cl-es 2>/dev/null || docker run -d --name cl-es --network cl_net_overlay -p 9200:9200 \
  -e discovery.type=single-node -e cluster.name=courtlistener-cluster \
  -e cluster.routing.allocation.disk.threshold_enabled=false \
  -e xpack.security.enabled=true -e xpack.security.http.ssl.enabled=true \
  -e xpack.security.http.ssl.key=certs/cl-es.key -e xpack.security.http.ssl.certificate=certs/cl-es.crt \
  -e xpack.security.http.ssl.certificate_authorities=certs/ca.crt \
  -e xpack.security.transport.ssl.enabled=true -e xpack.security.transport.ssl.key=certs/cl-es.key \
  -e xpack.security.transport.ssl.certificate=certs/cl-es.crt -e xpack.security.transport.ssl.certificate_authorities=certs/ca.crt \
  -e xpack.security.transport.ssl.verification_mode=certificate \
  -e ELASTIC_PASSWORD=password -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" \
  --ulimit memlock=500:600 \
  -v /workspace/docker/elastic/cl-es.crt:/usr/share/elasticsearch/config/certs/cl-es.crt \
  -v /workspace/docker/elastic/cl-es.key:/usr/share/elasticsearch/config/certs/cl-es.key \
  -v /workspace/docker/elastic/ca.crt:/usr/share/elasticsearch/config/certs/ca.crt \
  -v /workspace/cl/search/elasticsearch_files/synonyms_en.txt:/usr/share/elasticsearch/config/dictionaries/synonyms_en.txt \
  -v /workspace/cl/search/elasticsearch_files/stopwords_en.txt:/usr/share/elasticsearch/config/dictionaries/stopwords_en.txt \
  elasticsearch:8.8.1
```

### Environment Variables

Django uses `django-environ`'s `FileAwareEnv`, which reads from **shell environment variables** (not from `.env` files automatically). Export these before running Django:

```bash
export DEBUG=on DEVELOPMENT=on SECRET_KEY=dev-secret-key-for-local-development
export DB_HOST=localhost DB_NAME=courtlistener DB_USER=postgres DB_PASSWORD=postgres DB_SSL_MODE=require
export REDIS_HOST=localhost
export ELASTICSEARCH_DSL_HOST=https://localhost:9200 ELASTICSEARCH_CA_CERT=/workspace/docker/elastic/ca.crt
export ALLOWED_HOSTS="*"
export PYTHONPATH="/workspace:$PYTHONPATH"
export PGSSLCERT=/tmp/postgresql.crt
export PATH="/workspace/.venv/bin:$HOME/.local/bin:$PATH"
```

### Running Django

```bash
python manage.py migrate
python manage.py createcachetable
python manage.py runserver 0.0.0.0:8000
```

### Key Gotchas

- **ALLOWED_HOSTS**: Defaults to `["www.courtlistener.com"]`. Must set `ALLOWED_HOSTS="*"` for local dev or requests return HTTP 400.
- **PGSSLCERT**: Must be set to a dummy path (`/tmp/postgresql.crt`) to avoid SSL cert errors when connecting to PostgreSQL.
- **PostgreSQL image**: Must be built locally first — `docker build -t cl-postgres -f docker/postgresql/Dockerfile --build-arg POSTGRES_VERSION=15.2-alpine docker/postgresql/`
- **Parallel tests**: Running `manage.py test` with multiple test classes can fail with "database being accessed" errors due to parallel test DB cloning. Use `--parallel=1` for reliable local test runs.
- **Log directories**: Create `/var/log/courtlistener` and `/var/log/juriscraper` before running Django to suppress warnings.
- **Solr/Doctor/Disclosures**: These microservices are optional for basic dev. Solr is legacy search, Doctor handles doc extraction, Disclosures handles financial disclosures. Tests that need them will fail gracefully.

### Lint & Test Commands

```bash
# Lint (pre-existing issues exist in repo)
python -m black --check cl/
python -m isort --check-only cl/
python -m flake8 cl/ --select=E9,F63,F7,F82

# Tests (single test class, serial)
python manage.py test cl.lib.tests.TestStringUtils --verbosity=2

# Webpack (frontend assets)
cd cl && npx webpack --mode=development
```
