from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import datetime, timezone
from itertools import combinations, product

from radar.models import (
    DOCUMENT_KINDS,
    VOTE_KINDS,
    Claim,
    Conflict,
    Source,
)

OPPOSING = {("support", "oppose"), ("oppose", "support")}

SUMMARIES = {
    "say_vs_write": "L3-ståndpunkt skiljer sig från L1-dokument på samma topic.",
    "write_vs_vote": "Skriftlig linje skiljer sig från voteringsutfall.",
    "then_vs_now": "Ståndpunkt ändras över tid utan överlappande giltighetsfönster.",
    "words_without_action": "Words finns i fönstret, ingen action.",
    "action_without_words": "Action finns i fönstret, L3 tyst eller saknas.",
}


def _opposes(a: str, b: str) -> bool:
    return (a, b) in OPPOSING


def _overlap(a: Claim, b: Claim) -> bool:
    a0, a1 = a.time_start or "0000", a.time_end or "9999"
    b0, b1 = b.time_start or "0000", b.time_end or "9999"
    return a0 <= b1 and b0 <= a1


def _dated_apart(a: Claim, b: Claim) -> bool:
    if not ((a.time_start or a.time_end) and (b.time_start or b.time_end)):
        return False
    return not _overlap(a, b)


def _kinds(claim: Claim, sources: dict[str, Source]) -> set[str]:
    return {sources[sid].kind for sid in claim.source_ids() if sid in sources}


def _layers(claim: Claim, sources: dict[str, Source]) -> set[str]:
    return {sources[sid].layer for sid in claim.source_ids() if sid in sources}


def _vote_recorded(claim: Claim, sources: dict[str, Source]) -> bool:
    for sid in claim.source_ids():
        src = sources.get(sid)
        if src and src.kind in VOTE_KINDS and src.vote_data == "none":
            return False
    return True


def _cid(ctype: str, actor: str, topic: str, claim_ids: list[str]) -> str:
    key = "|".join([ctype, actor, topic, *sorted(claim_ids)])
    digest = hashlib.sha256(key.encode()).hexdigest()[:12]
    return f"c_{ctype}_{actor}_{topic}_{digest}"


def _make(
    ctype: str,
    actor: str,
    topic: str,
    claim_ids: list[str],
    detected_at: str,
    *,
    absence: bool = False,
) -> Conflict:
    return Conflict(
        conflict_id=_cid(ctype, actor, topic, claim_ids),
        actor_id=actor,
        topic_id=topic,
        type=ctype,  # type: ignore[arg-type]
        claim_ids=sorted(claim_ids),
        summary=SUMMARIES[ctype],
        detected_at=detected_at,
        documented_absence=absence,
    )


def detect(
    claims: list[Claim],
    sources: dict[str, Source],
    *,
    detected_at: str | None = None,
) -> list[Conflict]:
    stamp = detected_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    groups: dict[tuple[str, str], list[Claim]] = defaultdict(list)
    for claim in claims:
        groups[(claim.actor_id, claim.topic_id)].append(claim)

    out: list[Conflict] = []
    for (actor, topic), group in groups.items():
        words = [c for c in group if c.claim_role == "words"]
        actions = [c for c in group if c.claim_role == "action"]
        spoken = [c for c in words if c.stance != "silent"]

        for w, a in product(spoken, actions):
            if not _overlap(w, a):
                continue
            if "L3" not in _layers(w, sources):
                continue
            if not (_kinds(a, sources) & DOCUMENT_KINDS):
                continue
            if _opposes(w.stance, a.stance):
                out.append(_make("say_vs_write", actor, topic, [w.claim_id, a.claim_id], stamp))

        writes = [c for c in actions if _kinds(c, sources) & {"motion", "reservation"}]
        votes = [
            c
            for c in actions
            if _kinds(c, sources) & VOTE_KINDS and _vote_recorded(c, sources)
        ]
        for wr, vt in product(writes, votes):
            if _overlap(wr, vt) and _opposes(wr.stance, vt.stance):
                out.append(
                    _make("write_vs_vote", actor, topic, [wr.claim_id, vt.claim_id], stamp)
                )

        dated = [c for c in group if c.time_start or c.time_end]
        for left, right in combinations(dated, 2):
            if _dated_apart(left, right) and _opposes(left.stance, right.stance):
                out.append(
                    _make(
                        "then_vs_now",
                        actor,
                        topic,
                        [left.claim_id, right.claim_id],
                        stamp,
                    )
                )

        if spoken and not actions:
            out.append(
                _make(
                    "words_without_action",
                    actor,
                    topic,
                    [c.claim_id for c in spoken],
                    stamp,
                    absence=True,
                )
            )
        if actions and not spoken:
            out.append(
                _make(
                    "action_without_words",
                    actor,
                    topic,
                    [c.claim_id for c in actions],
                    stamp,
                    absence=True,
                )
            )

    out.sort(key=lambda c: (c.type, c.actor_id, c.conflict_id))
    return out
