"""HTTP client for the public CourtListener REST API."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlencode, urljoin

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def get_research_sync_settings() -> dict[str, Any]:
    """Return dict with base_url, token, timeout from Django settings."""
    rs = getattr(settings, "RESEARCH_SYNC", {})
    return {
        "base_url": rs.get("REMOTE_API_BASE_URL", "https://www.courtlistener.com"),
        "token": rs.get("REMOTE_API_TOKEN", ""),
        "timeout": int(rs.get("REMOTE_API_TIMEOUT", 60)),
        "storage_prefix": rs.get(
            "REMOTE_STORAGE_URL_PREFIX", "https://storage.courtlistener.com/"
        ),
    }


class CourtListenerRemoteClient:
    """Minimal read-only client for v4 search and docket detail."""

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        timeout: int | None = None,
    ) -> None:
        cfg = get_research_sync_settings()
        self.base_url = (base_url or cfg["base_url"]).rstrip("/") + "/"
        self.token = token if token is not None else cfg["token"]
        self.timeout = timeout if timeout is not None else cfg["timeout"]
        self.storage_prefix = cfg["storage_prefix"].rstrip("/") + "/"

    def _headers(self) -> dict[str, str]:
        h = {"Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Token {self.token}"
        return h

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = urljoin(self.base_url, path.lstrip("/"))
        r = requests.get(
            url,
            params=params or {},
            headers=self._headers(),
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    def search_v4_page(
        self, query_dict: dict[str, str], cursor: str | None = None
    ) -> dict[str, Any]:
        params = {k: v for k, v in query_dict.items() if v is not None}
        if cursor:
            params["cursor"] = cursor
        return self.get_json("api/rest/v4/search/", params=params)

    def get_docket(self, docket_id: int) -> dict[str, Any]:
        return self.get_json(f"api/rest/v4/dockets/{docket_id}/")

    def pdf_url_from_local_path(self, local_path: str | None) -> str | None:
        if not local_path:
            return None
        path = local_path.lstrip("/")
        return f"{self.storage_prefix}{path}"
