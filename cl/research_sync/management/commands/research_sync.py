"""Run research sync against remote CourtListener API."""

from django.core.management.base import BaseCommand

from cl.research_sync.models import SyncTarget
from cl.research_sync.sync import run_sync_for_target


class Command(BaseCommand):
    help = (
        "Sync enabled SyncTarget rows against the remote CourtListener API. "
        "Set RESEARCH_SYNC['REMOTE_API_TOKEN'] for authenticated requests."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--target-id",
            type=int,
            help="Only sync this SyncTarget primary key.",
        )
        parser.add_argument(
            "--download-pdfs",
            action="store_true",
            help="Download first PDF per opinion cluster hit (uses public storage URLs).",
        )
        parser.add_argument(
            "--max-search-pages",
            type=int,
            default=3,
            help="Max cursor pages per search target (default 3).",
        )

    def handle(self, *args, **options):
        qs = SyncTarget.objects.filter(enabled=True)
        tid = options.get("target_id")
        if tid:
            qs = qs.filter(pk=tid)
        targets = list(qs)
        if not targets:
            self.stdout.write(self.style.WARNING("No enabled sync targets found."))
            return

        for target in targets:
            self.stdout.write(f"Syncing target {target.pk}: {target.name} …")
            run = run_sync_for_target(
                target,
                download_pdfs=options["download_pdfs"],
                max_search_pages=options["max_search_pages"],
            )
            if run.status == run.Status.OK:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  OK — hits={run.hits_fetched}, files={run.files_downloaded}"
                    )
                )
            else:
                self.stdout.write(self.style.ERROR(f"  FAILED — {run.message[:500]}"))
