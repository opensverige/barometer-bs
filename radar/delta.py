from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from radar.conflicts import OPPOSING, detect
from radar.models import Claim, Conflict, Source

CONFIG = Path(__file__).resolve().parents[1] / "config" / "windows.json"


def load_windows(path: Path | None = None) -> dict[str, Any]:
    return json.loads((path or CONFIG).read_text(encoding="utf-8"))


def _in_window(claim: Claim, start: str, end: str | None) -> bool:
    c0 = claim.time_start or claim.time_end
    c1 = claim.time_end or claim.time_start
    if not c0:
        return False
    c1 = c1 or c0
    w1 = end or "9999-12-31"
    return c0 <= w1 and start <= c1


def _opposes(a: Claim, b: Claim) -> bool:
    return (a.stance, b.stance) in OPPOSING


@dataclass
class ActorDelta:
    actor_id: str
    topic_id: str
    said_then: list[str]
    did: list[str]
    says_now: list[str]
    conflict_types: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "topic_id": self.topic_id,
            "said_then": self.said_then,
            "did": self.did,
            "says_now": self.says_now,
            "conflict_types": self.conflict_types,
        }


def _pick(claims: list[Claim], window: dict[str, Any], role: str) -> list[Claim]:
    start = window["start"]
    end = window.get("end")
    return [
        c
        for c in claims
        if c.claim_role == role and _in_window(c, start, end)
    ]


def _election_types(then: list[Claim], did: list[Claim], now: list[Claim]) -> list[str]:
    types: set[str] = set()
    if any(_opposes(t, d) for t in then for d in did):
        types.add("then_vs_now")
    if any(_opposes(n, d) for n in now for d in did):
        types.add("say_vs_write")
    if then and not did:
        types.add("words_without_action")
    if did and not now:
        types.add("action_without_words")
    return sorted(types)


def snapshot(
    claims: list[Claim],
    sources: dict[str, Source],
    *,
    topic_id: str | None = None,
    windows: dict[str, Any] | None = None,
    detected_at: str = "2026-08-19T00:00:00Z",
) -> tuple[list[ActorDelta], list[Conflict]]:
    cfg = windows or load_windows()
    by_id = {w["window_id"]: w for w in cfg["windows"]}
    val = by_id["valrorelse_2022"]
    mandat = by_id["mandat_2022_2026"]
    idag = by_id["idag"]

    scoped = [c for c in claims if topic_id is None or c.topic_id == topic_id]
    actors = sorted({c.actor_id for c in scoped})
    topics = sorted({c.topic_id for c in scoped})

    deltas: list[ActorDelta] = []
    windowed: list[Claim] = []

    for actor in actors:
        for topic in topics:
            group = [c for c in scoped if c.actor_id == actor and c.topic_id == topic]
            then = _pick(group, val, "words")
            did = _pick(group, mandat, "action")
            now = _pick(group, idag, "words")
            deltas.append(
                ActorDelta(
                    actor_id=actor,
                    topic_id=topic,
                    said_then=[c.statement for c in then],
                    did=[c.statement for c in did],
                    says_now=[c.statement for c in now],
                    conflict_types=_election_types(then, did, now),
                )
            )
            windowed.extend(then + did + now)

    conflicts = detect(windowed, sources, detected_at=detected_at)
    return deltas, conflicts
