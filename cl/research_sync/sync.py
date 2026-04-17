"""Core sync logic: fetch remote API, upsert LocalHit, optional PDF download."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import parse_qsl

import requests
from django.core.files.base import ContentFile
from django.utils import timezone

from cl.research_sync.models import LocalHit, SyncRun, SyncTarget
from cl.research_sync.remote_client import CourtListenerRemoteClient

logger = logging.getLogger(__name__)


def _cluster_absolute_url(client: CourtListenerRemoteClient, cluster_id: int) -> str:
    base = client.base_url.rstrip("/")
    return f"{base}/opinion/{cluster_id}/"


def _docket_absolute_url(client: CourtListenerRemoteClient, docket_id: int) -> str:
    base = client.base_url.rstrip("/")
    return f"{base}/docket/{docket_id}/"


def sync_search_target(
    target: SyncTarget,
    run: SyncRun,
    client: CourtListenerRemoteClient,
    download_pdfs: bool,
    max_pages: int,
) -> tuple[int, int]:
    """Paginate v4 search for target.query_string. Returns (hits, files)."""
    qd = dict(parse_qsl(target.query_string, keep_blank_values=True))
    if "type" not in qd:
        qd["type"] = "o"

    hits = 0
    files = 0
    cursor: str | None = None
    pages = 0

    while pages < max_pages:
        pages += 1
        data = client.search_v4_page(qd, cursor=cursor)
        results = data.get("results") or []
        for row in results:
            h, f = _upsert_opinion_cluster_row(
                target, run, row, client, download_pdfs
            )
            hits += h
            files += f
        cursor = _extract_cursor_from_next(data.get("next"))
        if not cursor or not results:
            break

    return hits, files


def _extract_cursor_from_next(next_url: str | None) -> str | None:
    if not next_url or "cursor=" not in next_url:
        return None
    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(next_url)
    qs = parse_qs(parsed.query)
    c = qs.get("cursor", [None])[0]
    return c


def _upsert_opinion_cluster_row(
    target: SyncTarget,
    run: SyncRun,
    row: dict[str, Any],
    client: CourtListenerRemoteClient,
    download_pdfs: bool,
) -> tuple[int, int]:
    """Process one OpinionCluster-shaped search result. Returns (hits, files)."""
    # v4 serializer uses cluster_id; some environments may expose id
    cluster_id = row.get("cluster_id") or row.get("id")
    if cluster_id is None:
        return 0, 0
    try:
        cluster_id = int(cluster_id)
    except (TypeError, ValueError):
        return 0, 0

    title = ""
    case_name = row.get("caseName")
    if isinstance(case_name, str):
        title = case_name
    elif isinstance(case_name, dict) and case_name:
        title = str(next(iter(case_name.values())))

    court = row.get("court_id") or row.get("court_citation_string") or ""
    if isinstance(court, dict) and court:
        court = str(next(iter(court.values())))
    court_id = str(court)[:15] if court else ""

    docket_number = row.get("docketNumber") or ""
    if isinstance(docket_number, dict) and docket_number:
        docket_number = str(next(iter(docket_number.values())))
    docket_number = str(docket_number)[:100]

    au = row.get("absolute_url")
    if isinstance(au, str) and au.startswith("/"):
        detail_url = client.base_url.rstrip("/") + au
    else:
        detail_url = _cluster_absolute_url(client, cluster_id)
    dedupe_key = f"cluster-{cluster_id}"

    opinions = row.get("opinions") or []
    first_pdf_url: str | None = None
    first_opinion_id: int | None = None
    for op in opinions:
        if not isinstance(op, dict):
            continue
        oid = op.get("id")
        lp = op.get("local_path")
        url = client.pdf_url_from_local_path(lp) if lp else op.get("download_url")
        if url and not first_pdf_url:
            first_pdf_url = url
            try:
                first_opinion_id = int(oid) if oid is not None else None
            except (TypeError, ValueError):
                first_opinion_id = None
            break

    snapshot = {
        "cluster_id": cluster_id,
        "docket_id": row.get("docket_id"),
        "caseName": row.get("caseName"),
        "dateFiled": row.get("dateFiled"),
        "citation": row.get("citation"),
        "docketNumber": row.get("docketNumber"),
        "absolute_url": row.get("absolute_url"),
    }

    remote_docket_id = row.get("docket_id")
    try:
        remote_docket_id = int(remote_docket_id) if remote_docket_id is not None else None
    except (TypeError, ValueError):
        remote_docket_id = None

    obj, _created = LocalHit.objects.update_or_create(
        target=target,
        dedupe_key=dedupe_key,
        defaults={
            "run": run,
            "resource_type": LocalHit.ResourceType.OPINION_CLUSTER,
            "remote_cluster_id": cluster_id,
            "remote_docket_id": remote_docket_id,
            "remote_opinion_id": first_opinion_id,
            "title": title[:500],
            "court_id": court_id,
            "docket_number": docket_number,
            "remote_detail_url": detail_url,
            "remote_pdf_url": first_pdf_url or "",
            "snapshot": snapshot,
        },
    )

    file_count = 0
    if download_pdfs and first_pdf_url and not obj.local_file:
        if _try_download_pdf(obj, first_pdf_url):
            obj.save(update_fields=["local_file"])
            file_count = 1

    return 1, file_count


def _try_download_pdf(hit: LocalHit, url: str) -> bool:
    try:
        r = requests.get(url, timeout=120, stream=True)
        r.raise_for_status()
        content = r.content
        if len(content) < 100:
            return False
        name = f"opinion-{hit.remote_opinion_id or hit.remote_cluster_id}.pdf"
        hit.local_file.save(name, ContentFile(content), save=False)
        return True
    except OSError as exc:
        logger.warning("PDF save failed for hit %s: %s", hit.pk, exc)
        return False
    except requests.RequestException as exc:
        logger.warning("PDF download failed for hit %s: %s", hit.pk, exc)
        return False


def sync_docket_target(
    target: SyncTarget,
    run: SyncRun,
    client: CourtListenerRemoteClient,
    download_pdfs: bool,
) -> tuple[int, int]:
    """Fetch docket JSON and record one LocalHit for context."""
    if not target.remote_docket_id:
        raise ValueError("Docket target requires remote_docket_id")

    data = client.get_docket(target.remote_docket_id)
    did = int(data.get("id") or target.remote_docket_id)
    case_name = (data.get("case_name") or data.get("caseName") or "")[:500]
    court_id = str(data.get("court") or "").split("/")[-2][:15] if data.get("court") else ""
    if not court_id and data.get("court_id"):
        court_id = str(data.get("court_id"))[:15]

    detail_url = _docket_absolute_url(client, did)
    dedupe_key = f"docket-{did}"

    LocalHit.objects.update_or_create(
        target=target,
        dedupe_key=dedupe_key,
        defaults={
            "run": run,
            "resource_type": LocalHit.ResourceType.DOCKET,
            "remote_docket_id": did,
            "title": case_name,
            "court_id": court_id,
            "docket_number": str(data.get("docket_number", ""))[:100],
            "remote_detail_url": detail_url,
            "snapshot": {"docket": data.get("resource_uri"), "raw_keys": list(data.keys())[:40]},
        },
    )

    # Optionally pull first page of docket entries if nested (API shape varies)
    hits = 1
    files = 0
    if download_pdfs:
        # RECAP PDFs need authenticated API user; skip bulk here
        pass
    return hits, files


def run_sync_for_target(
    target: SyncTarget,
    *,
    download_pdfs: bool = False,
    max_search_pages: int = 3,
) -> SyncRun:
    client = CourtListenerRemoteClient()
    run = SyncRun.objects.create(target=target, status=SyncRun.Status.STARTED)
    hits = 0
    files = 0
    try:
        if target.kind == SyncTarget.Kind.SEARCH:
            hits, files = sync_search_target(
                target, run, client, download_pdfs, max_search_pages
            )
        elif target.kind == SyncTarget.Kind.DOCKET:
            hits, files = sync_docket_target(target, run, client, download_pdfs)
        else:
            raise ValueError(f"Unknown kind {target.kind}")

        run.hits_fetched = hits
        run.files_downloaded = files
        run.status = SyncRun.Status.OK
        run.message = "OK"
    except Exception as exc:  # noqa: BLE001 — surface to admin / CLI
        logger.exception("Sync failed for target %s", target.pk)
        run.status = SyncRun.Status.ERROR
        run.message = str(exc)[:4000]
    finally:
        run.finished_at = timezone.now()
        run.save()
    return run
