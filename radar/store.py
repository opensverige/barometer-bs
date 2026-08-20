from __future__ import annotations

from radar.models import Claim, Source


def upsert_sources(existing: list[Source], incoming: list[Source]) -> list[Source]:
    by_id = {s.source_id: s for s in existing}
    for src in incoming:
        by_id[src.source_id] = src
    return [by_id[k] for k in sorted(by_id)]


def upsert_claims(existing: list[Claim], incoming: list[Claim]) -> list[Claim]:
    by_id = {c.claim_id: c for c in existing}
    for claim in incoming:
        by_id[claim.claim_id] = claim
    return [by_id[k] for k in sorted(by_id)]
