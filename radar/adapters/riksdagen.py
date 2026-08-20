from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

from radar.adapters.base import Adapter
from radar.models import PARTY_FROM_RIKSDAGEN, Claim, DerivedFrom, Locator, Source
from radar.scoring import score_claim

BASE = "https://data.riksdagen.se"
ATTRIBUTION = "Sveriges riksdag"
ROST_TO_STANCE = {"Ja": "support", "Nej": "oppose", "Avstår": "mixed"}


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


def _rows(block: dict[str, Any], key: str) -> list[dict[str, Any]]:
    rows = block.get(key) or []
    if isinstance(rows, dict):
        return [rows]
    return list(rows)


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
    return f"{BASE}/dokumentlista/?{urlencode(params)}"


def anforande_url(rm: str, query: str, page: int = 1) -> str:
    params = {
        "sok": query,
        "rm": rm,
        "anftyp": "Nej",
        "utformat": "json",
        "p": str(page),
    }
    return f"{BASE}/anforandelista/?{urlencode(params)}"


def votering_url(rm: str, query: str, page: int = 1) -> str:
    params = {
        "sok": query,
        "rm": rm,
        "utformat": "json",
        "p": str(page),
    }
    return f"{BASE}/voteringlista/?{urlencode(params)}"


def rows_from_dokumentlista(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return _rows(payload.get("dokumentlista") or {}, "dokument")


def rows_from_anforandelista(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return _rows(payload.get("anforandelista") or {}, "anforande")


def rows_from_voteringlista(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return _rows(payload.get("voteringlista") or {}, "votering")


def official_dok_id(doc: dict[str, Any]) -> str:
    return str(doc.get("dok_id") or "").strip()


def official_anforande_id(row: dict[str, Any]) -> str:
    aid = str(row.get("anforande_id") or "").strip()
    if aid:
        return aid
    dok = official_dok_id(row)
    nr = str(row.get("anforande_nummer") or row.get("nummer") or "").strip()
    if dok and nr:
        return f"{dok}:{nr}"
    return ""


def official_votering_id(row: dict[str, Any]) -> str:
    return str(row.get("votering_id") or "").strip()


class RiksdagenAdapter(Adapter):
    """L1: motioner + anföranden + voteringar. Extract bara från registrerad rost."""

    name = "riksdagen"

    def __init__(
        self,
        client: Any | None = None,
        aliases: list[str] | None = None,
        *,
        include_votes: bool = True,
        page_cap: int = 5,
    ):
        self.client = client
        self.aliases = aliases or ["AI"]
        self.include_votes = include_votes
        self.page_cap = page_cap
        self.errors: list[dict[str, Any]] = []
        self._vote_rows: list[dict[str, Any]] = []

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
        raw: dict[str, Any] = {"dokument": [], "anforande": [], "votering": [], "meta": []}
        for rm in window:
            for kind, url_fn, unwrap, bucket in (
                ("dokument", dokument_url, rows_from_dokumentlista, "dokument"),
                ("anforande", anforande_url, rows_from_anforandelista, "anforande"),
            ):
                try:
                    rows, meta = self._pages(client, url_fn, unwrap, rm, query)
                    raw[bucket].extend(rows)
                    raw["meta"].append({"kind": kind, **meta})
                except Exception as exc:
                    self.errors.append(
                        {"at": _now(), "adapter": self.name, "message": f"{kind} {rm}: {exc}"}
                    )
            if self.include_votes:
                try:
                    rows, meta = self._pages(
                        client, votering_url, rows_from_voteringlista, rm, query, cap=min(2, self.page_cap)
                    )
                    raw["votering"].extend(rows)
                    raw["meta"].append({"kind": "votering", **meta})
                except Exception as exc:
                    self.errors.append(
                        {"at": _now(), "adapter": self.name, "message": f"votering {rm}: {exc}"}
                    )
        return raw

    def _pages(
        self,
        client: Any,
        url_fn: Any,
        unwrap: Any,
        rm: str,
        query: str,
        cap: int | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        collected: list[dict[str, Any]] = []
        meta: dict[str, Any] = {"rm": rm, "pages": 0}
        limit = cap or self.page_cap
        page = 1
        while page <= limit:
            response = client.get(url_fn(rm, query, page), timeout=30.0)
            response.raise_for_status()
            payload = response.json()
            collected.extend(unwrap(payload))
            wrapper = next(iter(payload.values())) if payload else {}
            if not isinstance(wrapper, dict):
                wrapper = {}
            meta["pages"] = page
            try:
                total = int(wrapper.get("@sidor") or 1)
            except (TypeError, ValueError):
                total = 1
            if page >= total:
                break
            page += 1
        return collected, meta

    def normalize(self, raw: Any) -> list[Source]:
        retrieved = _now()
        sources: list[Source] = []
        sources.extend(self._norm_docs(raw.get("dokument") or [], retrieved))
        sources.extend(self._norm_speeches(raw.get("anforande") or [], retrieved))
        vote_sources, vote_rows = self._norm_votes(raw.get("votering") or [], retrieved)
        sources.extend(vote_sources)
        self._vote_rows = vote_rows
        return sources

    def _norm_docs(self, docs: list[dict[str, Any]], retrieved: str) -> list[Source]:
        out: list[Source] = []
        seen: set[str] = set()
        for doc in docs:
            dok_id = official_dok_id(doc)
            if not dok_id:
                self.errors.append({"at": retrieved, "adapter": self.name, "message": "dokument without dok_id"})
                continue
            if dok_id in seen:
                continue
            seen.add(dok_id)
            html = _https(doc.get("dokument_url_html")) or f"{BASE}/dokument/{dok_id}.html"
            blob = "|".join([dok_id, str(doc.get("titel") or ""), str(doc.get("rm") or ""), str(doc.get("datum") or "")])
            out.append(
                Source(
                    source_id=f"l1:dok:{dok_id}",
                    layer="L1",
                    kind="motion",
                    locator=Locator(url=html, official_id=dok_id, official_id_kind="dok_id"),
                    retrieved_at=retrieved,
                    published_at=str(doc.get("datum") or "") or None,
                    content_hash=_hash(blob),
                    attribution=ATTRIBUTION,
                )
            )
        return out

    def _norm_speeches(self, rows: list[dict[str, Any]], retrieved: str) -> list[Source]:
        out: list[Source] = []
        seen: set[str] = set()
        for row in rows:
            aid = official_anforande_id(row)
            if not aid:
                self.errors.append({"at": retrieved, "adapter": self.name, "message": "anforande without id"})
                continue
            if aid in seen:
                continue
            seen.add(aid)
            url = _https(row.get("protokoll_url_www")) or f"{BASE}/anforande/{aid}"
            blob = "|".join([aid, str(row.get("avsnittsrubrik") or row.get("dok_titel") or ""), str(row.get("parti") or "")])
            out.append(
                Source(
                    source_id=f"l1:anf:{aid}",
                    layer="L1",
                    kind="anforande",
                    locator=Locator(url=url, official_id=aid, official_id_kind="anforande_id"),
                    retrieved_at=retrieved,
                    published_at=str(row.get("dok_datum") or row.get("datum") or "") or None,
                    content_hash=_hash(blob),
                    attribution=ATTRIBUTION,
                )
            )
        return out

    def _norm_votes(self, rows: list[dict[str, Any]], retrieved: str) -> tuple[list[Source], list[dict[str, Any]]]:
        kept: list[dict[str, Any]] = []
        out: list[Source] = []
        seen: set[str] = set()
        for row in rows:
            vid = official_votering_id(row)
            punkt = str(row.get("punkt") or "").strip()
            parti = str(row.get("parti") or "").strip().upper()
            if not vid:
                self.errors.append({"at": retrieved, "adapter": self.name, "message": "votering without votering_id"})
                continue
            rost = str(row.get("rost") or "").strip()
            if rost in {"", "Frånvarande"}:
                continue
            kept.append(row)
            sid = f"l1:vot:{vid}:{punkt}:{parti}"
            if sid in seen:
                continue
            seen.add(sid)
            url = f"{BASE}/votering/{vid}"
            out.append(
                Source(
                    source_id=sid,
                    layer="L1",
                    kind="votering",
                    locator=Locator(url=url, official_id=vid, official_id_kind="votering_id"),
                    retrieved_at=retrieved,
                    content_hash=_hash(f"{vid}|{punkt}|{parti}"),
                    attribution=ATTRIBUTION,
                    vote_data="recorded",
                    punkt=punkt or None,
                )
            )
        return out, kept

    def extract(self, sources: list[Source], topic_id: str, raw: dict[str, Any] | None = None) -> list[Claim]:
        """No LLM. Motions/anföranden → inga claims. Votering → stance från registrerad rost."""
        del raw
        index = {s.source_id: s for s in sources}
        groups: dict[tuple[str, str, str], set[str]] = defaultdict(set)
        for row in self._vote_rows:
            vid = official_votering_id(row)
            punkt = str(row.get("punkt") or "").strip()
            parti = str(row.get("parti") or "").strip().upper()
            rost = str(row.get("rost") or "").strip()
            if rost in ROST_TO_STANCE:
                groups[(vid, punkt, parti)].add(rost)

        claims: list[Claim] = []
        for (vid, punkt, parti), rost_set in groups.items():
            actor = PARTY_FROM_RIKSDAGEN.get(parti)
            sid = f"l1:vot:{vid}:{punkt}:{parti}"
            src = index.get(sid)
            if not actor or src is None or src.vote_data == "none":
                continue
            if rost_set == {"Ja"}:
                stance = "support"
            elif rost_set == {"Nej"}:
                stance = "oppose"
            else:
                stance = "mixed"
            claim = Claim(
                claim_id=f"cl:vot:{vid}:{punkt}:{actor}",
                actor_id=actor,
                topic_id=topic_id,
                statement=f"votering {vid} punkt {punkt}: {','.join(sorted(rost_set))}",
                stance=stance,  # type: ignore[arg-type]
                claim_role="action",
                derived_from=(DerivedFrom(sid),),
                evidence_score=0.0,
                polarity_notes="partiaggregat av registrerad rost; ingen LLM",
            )
            claim = Claim(**{**claim.__dict__, "evidence_score": score_claim(claim, index)})
            claims.append(claim)
        return claims
