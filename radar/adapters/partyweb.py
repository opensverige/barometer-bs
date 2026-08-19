from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from radar.adapters.base import Adapter
from radar.models import Claim, Locator, Source


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class PartywebAdapter(Adapter):
    """L3 whitelist only. Produces sources, not auto-stances from prose."""

    name = "partyweb"

    def __init__(self, pages: list[dict[str, str]], client: Any | None = None):
        self.pages = pages
        self.client = client
        self.errors: list[dict[str, Any]] = []

    def fetch(self, window: list[str]) -> list[dict[str, Any]]:
        del window
        client = self.client
        if client is None:
            try:
                import httpx
            except ImportError as exc:
                raise RuntimeError("install extra ingest: pip install .[ingest]") from exc
            client = httpx.Client(headers={"User-Agent": "opensverige-radar/0.1"}, follow_redirects=True)
        rows: list[dict[str, Any]] = []
        for page in self.pages:
            url = page["url"]
            try:
                response = client.get(url, timeout=30.0)
                rows.append({
                    **page,
                    "status": response.status_code,
                    "body": response.text if response.status_code == 200 else "",
                })
            except Exception as exc:
                self.errors.append({"at": _now(), "adapter": self.name, "message": str(exc), "locator": url})
                rows.append({**page, "status": 0, "body": ""})
        return rows

    def normalize(self, raw: Any) -> list[Source]:
        sources: list[Source] = []
        retrieved = _now()
        for row in raw or []:
            url = row.get("url") or ""
            if not url:
                self.errors.append({"at": retrieved, "adapter": self.name, "message": "page without url"})
                continue
            body = row.get("body") or ""
            sources.append(
                Source(
                    source_id=f"l3:web:{row.get('actor_id')}:{row.get('topic_id')}",
                    layer="L3",
                    kind="party_page",
                    locator=Locator(url=url),
                    retrieved_at=retrieved,
                    content_hash=hashlib.sha256(body.encode("utf-8", errors="replace")).hexdigest(),
                    attribution=str(row.get("actor_id") or "party"),
                )
            )
        return sources

    def extract(self, sources: list[Source], topic_id: str) -> list[Claim]:
        del sources, topic_id
        return []
