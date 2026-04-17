# Issues list

## Open: local storage layout and “search history” (undetermined)

**Question:** Where should *search history*, *sync metadata*, and *synced artifacts* (dockets, PDFs) live on disk and in the database, and what is the canonical organizational structure for a personal research layer on top of CourtListener?

**Current state (as implemented in `cl/research_sync`):**

| Layer | What lives there | Default path / notes |
|--------|------------------|----------------------|
| **PostgreSQL** | `research_sync_synctarget`, `research_sync_syncrun`, `research_sync_localhit` — targets, run logs, per-hit metadata (`snapshot` JSON, foreign keys to “remote” ids, read state) | Your configured `DB_*` / Docker Postgres |
| **Uploaded files** | Optional downloaded PDFs via `LocalHit.local_file` | Under Django **`MEDIA_ROOT`**, default **`cl/assets/media/research_sync/pdfs/%Y/%m/`** (see `cl/settings/django.py` `MEDIA_ROOT`; override with env `MEDIA_ROOT`) |
| **Not yet modeled** | A first-class **search history** table (every query executed, parameters, result counts, timing) distinct from `SyncRun` | Undetermined — today only *sync runs* and *hits* are stored |

**Gaps / decisions still needed:**

- Whether “history” should mean only `SyncRun` + `LocalHit`, or a separate append-only log aligned with CL API query shapes.
- Whether PDFs and large blobs should stay under `MEDIA_ROOT`, a dedicated volume (e.g. `references/` or `data/research_sync/`), or object storage.
- How to namespace data **per user** if multiple accounts share one local instance.
- Naming and folder conventions for **JSON registries** vs **Postgres** as source of truth (see item 0 below).

---

## (0) Registry schema: syntax reference for keys and local JSON

Define a **syntactical reference** (schema or style guide) for:

- **Registry keys** and **local JSON objects** that align with **CourtListener REST API** field names and resource types (`cluster_id`, `docket_id`, `opinions`, etc.), and  
- **User heuristics** (aliases, tags, digest slugs, cross-links to email threads / RSS items) where they improve ergonomics without fighting the upstream API.

Deliverable could live as `docs/research-sync-registry-schema.md` or similar, versioned with the sync code.

---

## (1) Export user tags and alerts to JSON registries and markdown digests

Use CourtListener APIs (and/or local DB where you self-host) to:

- Pull **user tags** (`/api/rest/v4/tags/`, `/api/rest/v4/docket-tags/`) and serialize into **JSON registries**.
- Pull **alerts** (`/api/rest/v4/alerts/`, docket alerts) and same.
- Generate **markdown digests** (human-readable summaries, chronology, links) alongside machine-readable JSON.

---

## (2) Supplement registries from email and RSS

- **`/gmail`**: discover **watched dockets** and notification threads tied to CourtListener / PACER / courts, and merge into registries (linking message ids → docket ids where inferable).
- **Fiery Feeds RSS** (and other CL-related feeds): ingest feed items into registries and digests so RSS-driven tracking sits next to API-driven data.

---

## (3) Subject areas for future ingestion

Workshop a **prioritized list of subject areas** (e.g. opinions vs RECAP vs OA vs people) that future ingestion pipelines should cover, with dependencies (auth, rate limits, indexing).

---

## (4) Cron / scheduling for ingestion pipelines

Document and implement **cron (or systemd timers, or Celery beat)** jobs for:

- `research_sync` (and successors),
- registry rebuilds,
- digest generation,
- optional RSS / mail polling.

Include idempotency, logging, and failure alerting conventions.
