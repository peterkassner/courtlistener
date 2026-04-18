from __future__ import annotations

from django.db import models


class SyncTarget(models.Model):
    """A saved query or docket to track against the remote CourtListener API."""

    class Kind(models.TextChoices):
        SEARCH = "search", "Saved search (API v4)"
        DOCKET = "docket", "Docket by ID"

    name = models.CharField(max_length=200, help_text="Label for this target.")
    kind = models.CharField(
        max_length=16,
        choices=Kind.choices,
        default=Kind.SEARCH,
    )
    # For SEARCH: same shape as site search URL, e.g. type=o&q=first+amendment
    query_string = models.TextField(
        blank=True,
        help_text="For searches: URL query string (e.g. type=o&q=...). Ignored for docket kind.",
    )
    # For DOCKET: numeric OpinionCluster / docket routing uses docket id on API
    remote_docket_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="For docket kind: CourtListener docket primary key.",
    )
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_kind_display()})"


class SyncRun(models.Model):
    """One execution of the sync command for a target."""

    class Status(models.TextChoices):
        STARTED = "started", "Started"
        OK = "ok", "Completed"
        ERROR = "error", "Failed"

    target = models.ForeignKey(
        SyncTarget,
        on_delete=models.CASCADE,
        related_name="runs",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.STARTED,
    )
    message = models.TextField(blank=True)
    hits_fetched = models.PositiveIntegerField(default=0)
    files_downloaded = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"SyncRun {self.pk} for {self.target_id} ({self.status})"


class LocalHit(models.Model):
    """A document or cluster discovered via sync, with enough context to reopen on CL."""

    class ResourceType(models.TextChoices):
        OPINION_CLUSTER = "cluster", "Opinion cluster"
        OPINION = "opinion", "Opinion"
        DOCKET = "docket", "Docket"
        OTHER = "other", "Other"

    target = models.ForeignKey(
        SyncTarget,
        on_delete=models.CASCADE,
        related_name="hits",
    )
    run = models.ForeignKey(
        SyncRun,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hits",
    )
    resource_type = models.CharField(
        max_length=16,
        choices=ResourceType.choices,
        default=ResourceType.OPINION_CLUSTER,
    )
    remote_cluster_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
    )
    remote_opinion_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
    )
    remote_docket_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
    )
    title = models.CharField(max_length=500, blank=True)
    court_id = models.CharField(max_length=15, blank=True)
    docket_number = models.CharField(max_length=100, blank=True)
    remote_detail_url = models.URLField(
        max_length=800,
        blank=True,
        help_text="Best-effort link to the resource on CourtListener.",
    )
    remote_pdf_url = models.URLField(max_length=800, blank=True)
    local_file = models.FileField(
        upload_to="research_sync/pdfs/%Y/%m/",
        max_length=500,
        blank=True,
        help_text="Optional downloaded PDF on this machine.",
    )
    snapshot = models.JSONField(
        default=dict,
        blank=True,
        help_text="Subset of API response for offline context.",
    )
    discovered_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    is_read = models.BooleanField(default=False)
    dedupe_key = models.CharField(
        max_length=120,
        db_index=True,
        help_text="Stable id for upserts, e.g. cluster-123 or opinion-456.",
    )

    class Meta:
        ordering = ["-discovered_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["target", "dedupe_key"],
                name="research_sync_localhit_target_dedupe",
            ),
        ]
        indexes = [
            models.Index(fields=["target", "is_read"]),
        ]

    def __str__(self) -> str:
        return self.title or f"Hit {self.pk}"

    def mark_read(self) -> None:
        self.is_read = True
        self.save(update_fields=["is_read"])
