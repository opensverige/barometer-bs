from __future__ import annotations

import hashlib
from typing import Iterable

from radar.models import Claim, Source


def snapshot_blob(official_id: str, title: str, rm: str, published_at: str) -> str:
    return "|".join([official_id, rm, title, published_at])


def snapshot_hash(blob: str) -> str:
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def freeze_match(stored_hash: str, blob: str) -> bool:
    return bool(stored_hash) and stored_hash == snapshot_hash(blob)


def freeze_match_ratio(rows: Iterable[dict]) -> float | None:
    rows = list(rows)
    if not rows:
        return None
    ok = sum(1 for r in rows if freeze_match(r.get("content_hash") or "", r.get("snapshot") or ""))
    return ok / len(rows)


def locator_ok(source: Source) -> bool:
    loc = source.locator
    return bool(loc.official_id and loc.url and str(loc.url).startswith("https://"))


def locator_kpi(claims: list[Claim], sources: dict[str, Source]) -> float | None:
    if not claims:
        return None
    hits = 0
    for claim in claims:
        if any(locator_ok(sources[d.source_id]) for d in claim.derived_from if d.source_id in sources):
            hits += 1
    return hits / len(claims)
