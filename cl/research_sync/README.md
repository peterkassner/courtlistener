# Research sync (local)

This Django app lives inside the CourtListener repo and **calls the public CourtListener API** to persist search hits and docket snapshots in your local database, so PDF links and case context stay attached to the query that found them.

## Configure

Environment variables (optional; defaults target production):

| Variable | Purpose |
|----------|---------|
| `RESEARCH_SYNC_REMOTE_API_BASE_URL` | Default `https://www.courtlistener.com` |
| `RESEARCH_SYNC_REMOTE_API_TOKEN` | DRF token for higher rate limits (create in your CL account) |
| `RESEARCH_SYNC_REMOTE_API_TIMEOUT` | HTTP timeout seconds (default 60) |
| `RESEARCH_SYNC_REMOTE_STORAGE_URL_PREFIX` | PDF host prefix (default `https://storage.courtlistener.com/`) |

## Usage

1. **Admin → Research sync → Sync targets**: add a row:
   - **Search**: kind `Saved search`, `query_string` like `type=o&q=your+terms` (same parameters as the site search URL after `?`).
   - **Docket**: kind `Docket by ID`, set `remote_docket_id` to the CourtListener docket PK.

2. **Run sync** (cron-friendly):

   ```bash
   python manage.py research_sync
   python manage.py research_sync --target-id 1 --max-search-pages 5
   python manage.py research_sync --download-pdfs   # optional; stores under MEDIA_ROOT
   ```

3. **Dashboard** (logged-in users): `/research-sync/`

## Models

- `SyncTarget` — what to pull from the remote API.
- `SyncRun` — one execution log per `research_sync` run.
- `LocalHit` — upserted row per cluster (search) or docket, with `snapshot` JSON, links, optional `local_file`.

Your local CourtListener checkout does not need to match production data; only this app’s tables and `MEDIA_ROOT` matter for the sync layer.
