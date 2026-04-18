from django.contrib import admin

from cl.research_sync.models import LocalHit, SyncRun, SyncTarget


class SyncRunInline(admin.TabularInline):
    model = SyncRun
    extra = 0
    readonly_fields = (
        "started_at",
        "finished_at",
        "status",
        "message",
        "hits_fetched",
        "files_downloaded",
    )
    can_delete = False


@admin.register(SyncTarget)
class SyncTargetAdmin(admin.ModelAdmin):
    inlines = [SyncRunInline]
    list_display = ("name", "kind", "enabled", "updated_at")
    list_filter = ("kind", "enabled")
    search_fields = ("name", "query_string")


@admin.register(SyncRun)
class SyncRunAdmin(admin.ModelAdmin):
    list_display = (
        "target",
        "status",
        "hits_fetched",
        "files_downloaded",
        "started_at",
    )
    list_filter = ("status",)
    readonly_fields = (
        "target",
        "started_at",
        "finished_at",
        "status",
        "message",
        "hits_fetched",
        "files_downloaded",
    )


@admin.register(LocalHit)
class LocalHitAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "target",
        "resource_type",
        "remote_cluster_id",
        "is_read",
        "discovered_at",
    )
    list_filter = ("resource_type", "is_read", "target")
    search_fields = ("title", "court_id", "docket_number")
    readonly_fields = ("snapshot", "discovered_at", "last_seen_at")
