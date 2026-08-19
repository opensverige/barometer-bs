from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

from radar.models import (
    PARTY_FROM_RIKSDAGEN,
    Claim,
    DerivedFrom,
    Locator,
    Source,
)
from radar.adapters.base import Adapter
from radar.scoring import score_claim

BASE = "https://data.riksdagen.se"
ATTRIBUTION = "Sveriges riksdag"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _get(client: Any, url: str) -> dict[str, Any]:
    response = client.get(url, timeout=30.0)
    response.raise_for_status()
    return response.json()


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


def votering_url(rm: str, page: int = 1) -> str:
    params = {"rm": rm, "utformat": "json", "p": str(page)}
    return f"{BASE}/voteringlista/?{urlencode(params)}"


def anforande_url(rm: str, query: str, page: int = 1) -> str:
    params = {
        "rm": rm,
        "anftyp": "Nej",
        "utformat": "json",
        "p": str(page),
        "sok": query,
    }
    return f"{BASE}/anforandelista/?{urlencode(params)}"


class RiksdagenAdapter(Adapter):
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
        query = " OR ".join(self.aliases[:3])
        raw: dict[str, Any] = {"dokument": [], "votering": [], "anforande": []}
        for rm in window:
            try:
                raw["dokument"].extend(self._pages(client, lambda p: dokument_url(rm, query, p), "dokumentlista", "dokument"))
            except Exception as exc:
                self.errors.append({"at": _now(), "adapter": self.name, "message": f"dokument {rm}: {exc}"})
            try:
                raw["anforande"].extend(self._pages(client, lambda p: anforande_url(rm, query, p), "anforandelista", "anforande"))
            except Exception as exc:
                self.errors.append({"at": _now(), "adapter": self.name, "message": f"anforande {rm}: {exc}"})
            # voteringlista is huge; do not full-scan in v0 fetch without a dok filter
        return raw

    def _pages(self, client: Any, url_for: Any, wrapper: str, item: str, cap: int = 5) -> list[dict[str, Any]]:
        collected: list[dict[str, Any]] = []
        page = 1
        while page <= cap:
            payload = _get(client, url_for(page))
            block = payload.get(wrapper) or {}
            rows = block.get(item) or []
            if isinstance(rows, dict):
                rows = [rows]
            collected.extend(rows)
            try:
                total = int(block.get("@sidor") or 1)
            except ValueError:
                total = 1
            if page >= total:
                break
            page += 1
        return collected

    def normalize(self, raw: Any) -> list[Source]:
        sources: list[Source] = []
        retrieved = _now()
        for doc in raw.get("dokument") or []:
            dok_id = str(doc.get("dok_id") or doc.get("id") or "")
            if not dok_id:
                self.errors.append({"at": retrieved, "adapter": self.name, "message": "dokument without dok_id"})
                continue
            url = doc.get("dokument_url_html") or f"https://www.riksdagen.se/sv/dokument-och-lagar/dokument/{dok_id}/"
            blob = f"{dok_id}|{doc.get('titel')}|{doc.get('organ')}"
            sources.append(
                Source(
                    source_id=f"l1:dok:{dok_id}",
                    layer="L1",
                    kind="motion" if str(doc.get("typ") or doc.get("doktyp") or "mot").lower().startswith("mot") else "beslut",
                    locator=Locator(url=url, official_id=dok_id, official_id_kind="dok_id"),
                    retrieved_at=retrieved,
                    published_at=str(doc.get("datum") or "") or None,
                    content_hash=_hash(blob),
                    attribution=ATTRIBUTION,
                )
            )
        for speech in raw.get("anforande") or []:
            aid = str(speech.get("anforande_id") or speech.get("dok_id") or "")
            if not aid:
                self.errors.append({"at": retrieved, "adapter": self.name, "message": "anforande without id"})
                continue
            url = speech.get("protokoll_url_www") or f"https://data.riksdagen.se/anforande/{aid}"
            blob = f"{aid}|{speech.get('anforandetext') or speech.get('avsnittsrubrik')}"
            sources.append(
                Source(
                    source_id=f"l1:anf:{aid}",
                    layer="L1",
                    kind="anforande",
                    locator=Locator(url=url, official_id=aid, official_id_kind="anforande_id"),
                    retrieved_at=retrieved,
                    published_at=str(speech.get("dok_datum") or speech.get("rel_dok_id") or "") or None,
                    content_hash=_hash(blob),
                    attribution=ATTRIBUTION,
                )
            )
        for vote in raw.get("votering") or []:
            vid = str(vote.get("votering_id") or "")
            punkt = str(vote.get("punkt") or "")
            if not vid:
                self.errors.append({"at": retrieved, "adapter": self.name, "message": "votering without id"})
                continue
            url = f"https://data.riksdagen.se/votering/{vid}"
            sources.append(
                Source(
                    source_id=f"l1:vot:{vid}:{punkt}:{vote.get('parti')}",
                    layer="L1",
                    kind="votering",
                    locator=Locator(url=url, official_id=vid, official_id_kind="votering_id"),
                    retrieved_at=retrieved,
                    content_hash=_hash(f"{vid}|{punkt}|{vote.get('parti')}|{vote.get('rost')}"),
                    attribution=ATTRIBUTION,
                    vote_data="recorded" if vote.get("rost") else "none",
                    punkt=punkt or None,
                )
            )
        return sources

    def extract(self, sources: list[Source], topic_id: str, raw: dict[str, Any] | None = None) -> list[Claim]:
        raw = raw or {}
        claims: list[Claim] = []
        source_idx = {s.source_id: s for s in sources}
        for doc in raw.get("dokument") or []:
            dok_id = str(doc.get("dok_id") or doc.get("id") or "")
            sid = f"l1:dok:{dok_id}"
            if sid not in source_idx:
                continue
            organ = str(doc.get("organ") or "").upper()
            actor = PARTY_FROM_RIKSDAGEN.get(organ)
            if not actor:
                continue
            claim = Claim(
                claim_id=f"cl:mot:{dok_id}",
                actor_id=actor,
                topic_id=topic_id,
                statement=str(doc.get("titel") or dok_id),
                stance="support",
                claim_role="action",
                derived_from=(DerivedFrom(sid),),
                evidence_score=0.0,
                polarity_notes="authored/signed motion; stance=support for own proposal",
                time_start=str(doc.get("datum") or "") or None,
            )
            claim = Claim(
                **{**claim.__dict__, "evidence_score": score_claim(claim, source_idx)}
            )
            claims.append(claim)
        rost_map = {"Ja": "support", "Nej": "oppose", "Avstår": "mixed"}
        for vote in raw.get("votering") or []:
            vid = str(vote.get("votering_id") or "")
            punkt = str(vote.get("punkt") or "")
            parti = str(vote.get("parti") or "").upper()
            sid = f"l1:vot:{vid}:{punkt}:{vote.get('parti')}"
            if sid not in source_idx:
                continue
            src = source_idx[sid]
            if src.vote_data == "none":
                continue
            actor = PARTY_FROM_RIKSDAGEN.get(parti)
            rost = rost_map.get(str(vote.get("rost") or ""))
            if not actor or not rost:
                continue
            claim = Claim(
                claim_id=f"cl:vot:{vid}:{punkt}:{actor}",
                actor_id=actor,
                topic_id=topic_id,
                statement=f"votering {vid} punkt {punkt}: {vote.get('rost')}",
                stance=rost,  # type: ignore[arg-type]
                claim_role="action",
                derived_from=(DerivedFrom(sid),),
                evidence_score=0.0,
            )
            claim = Claim(
                **{**claim.__dict__, "evidence_score": score_claim(claim, source_idx)}
            )
            claims.append(claim)
        return claims
