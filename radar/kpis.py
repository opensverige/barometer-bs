from __future__ import annotations

import hashlib
import re
from typing import Any

_DOK = re.compile(r"^H[A-Z0-9]+$")


def snapshot_blob(official_id: str, title: str, rm: str, published_at: str) -> str:
    return "|".join([official_id, rm, title, published_at])


def snapshot_hash(blob: str) -> str:
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def freeze_match(sealed_hash: str, content_hash: str) -> bool:
    return bool(sealed_hash) and sealed_hash == content_hash


def metadata_freeze_match_ratio(records: list[dict[str, Any]]) -> float | None:
    rows = [r for r in records if r.get("sealed_hash")]
    if not rows:
        return None
    ok = 0
    for rec in rows:
        current = rec.get("content_hash") or snapshot_hash(rec.get("snapshot") or "")
        if freeze_match(rec["sealed_hash"], current):
            ok += 1
    return ok / len(rows)


def locator_record_ok(rec: dict[str, Any]) -> bool:
    if rec.get("kind") == "party_page":
        return False
    dok = rec.get("dok_id") or ""
    if dok.startswith("L3-") or not _DOK.match(dok):
        return False
    url = rec.get("url") or ""
    if not url.startswith("https://") or "riksdagen.se" not in url:
        return False
    kind = rec.get("kind")
    if kind == "motion" and not rec.get("actor_id"):
        return False
    if kind == "beslut" and not rec.get("punkt"):
        return False
    if kind == "votering" and not rec.get("actor_id"):
        return False
    return True


def locator_kpi(records: list[dict[str, Any]]) -> float | None:
    l1 = [r for r in records if r.get("kind") in {"motion", "beslut", "votering", "anforande"}]
    if not l1:
        return None
    return sum(1 for r in l1 if locator_record_ok(r)) / len(l1)
