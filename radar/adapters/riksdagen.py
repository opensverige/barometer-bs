from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

from radar.adapters.base import Adapter
from radar.models import Claim, Locator, Source

BASE = "https://data.riksdagen.se"
ATTRIBUTION = "Sveriges riksdag"
DOKUMENTLISTA = f"{BASE}/dokumentlista/"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _https(url: str | None) -> str | None:
    if not url:
        return None
    if url.startswith("//"):
        return "https:" + url
    return url


def dokument_url(rm: str, query: str, page: int = 1) -> str:
    params = {
        "sok": query,
        "doktyp": "mot",
        "rm": rm,
        "utformat": "json",
        "sort": "datum",
        "sortorder": "desc",
        "p": str(page),
    }
    return f"{DOKUMENTLISTA}?{urlencode(params)}"


def rows_from_dokumentlista(payload: dict[str, Any]) -> list[dict[str, Any]]:
    block = payload.get("dokumentlista") or {}
    rows = block.get("dokument") or []
    if isinstance(rows, dict):
        return [rows]
    return list(rows)


def official_dok_id(doc: dict[str, Any]) -> str:
    return str(doc.get("dok_id") or "").strip()


class RiksdagenAdapter(Adapter):
    """L1 motioner via data.riksdagen.se/dokumentlista. Iteration 1: fetch → Source[]."""

    name = "riksdagen"

    def __init__(self, client: Any | None = None, aliases: list[str] | None = None):
        self.client = client
        self.aliases = aliases or ["AI"]
        self.errors: list[dict[str, Any]] = []

    def _client(self) -> Any:
        if self.client is not None:
            return self.client
        try:
            import httpx
        except ImportError as exc:
            raise RuntimeError("install extra ingest: pip install .[ingest]") from exc
        return httpx.Client(headers={"User-Agent": "opensverige-radar/0.1"})

    def fetch(self, window: list[str]) -> dict[str, Any]:
        client = self._client()
        query = self.aliases[0] if self.aliases else "AI"
        raw: dict[str, Any] = {"dokument": [], "meta": []}
        for rm in window:
            try:
                docs, meta = self._pages(client, rm, query)
                raw["dokument"].extend(docs)
                raw["meta"].append(meta)
            except Exception as exc:
                self.errors.append(
                    {"at": _now(), "adapter": self.name, "message": f"dokument {rm}: {exc}"}
                )
        return raw

    def _pages(self, client: Any, rm: str, query: str, cap: int = 5) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        collected: list[dict[str, Any]] = []
        meta: dict[str, Any] = {"rm": rm, "pages": 0, "traffar": None}
        page = 1
        while page <= cap:
            url = dokument_url(rm, query, page)
            response = client.get(url, timeout=30.0)
            response.raise_for_status()
            payload = response.json()
            block = payload.get("dokumentlista") or {}
            collected.extend(rows_from_dokumentlista(payload))
            meta["pages"] = page
            meta["traffar"] = block.get("@traffar")
            try:
                total = int(block.get("@sidor") or 1)
            except ValueError:
                total = 1
            if page >= total:
                break
            page += 1
        return collected, meta

    def normalize(self, raw: Any) -> list[Source]:
        sources: list[Source] = []
        retrieved = _now()
        seen: set[str] = set()
        for doc in raw.get("dokument") or []:
            dok_id = official_dok_id(doc)
            if not dok_id:
                self.errors.append(
                    {"at": retrieved, "adapter": self.name, "message": "dokument without dok_id"}
                )
                continue
            if dok_id in seen:
                continue
            seen.add(dok_id)
            html = _https(doc.get("dokument_url_html")) or f"{BASE}/dokument/{dok_id}.html"
            text_url = _https(doc.get("dokument_url_text"))
            blob = "|".join(
                [
                    dok_id,
                    str(doc.get("titel") or ""),
                    str(doc.get("rm") or ""),
                    str(doc.get("doktyp") or doc.get("typ") or ""),
                    str(doc.get("datum") or ""),
                ]
            )
            loc = Locator(url=html, official_id=dok_id, official_id_kind="dok_id")
            sources.append(
                Source(
                    source_id=f"l1:dok:{dok_id}",
                    layer="L1",
                    kind="motion",
                    locator=loc,
                    retrieved_at=retrieved,
                    published_at=str(doc.get("datum") or "") or None,
                    content_hash=_hash(blob),
                    attribution=ATTRIBUTION,
                )
            )
            if text_url is None:
                pass
        return sources

    def extract(self, sources: list[Source], topic_id: str) -> list[Claim]:
        """Iteration 1: no claims. Title/party mapping is not stance. No LLM."""
        del sources, topic_id
        return []
