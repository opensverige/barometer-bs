from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Layer = Literal["L1", "L2", "L3"]
Stance = Literal["support", "oppose", "mixed", "conditional", "silent"]
ClaimRole = Literal["words", "action", "unclear"]
ConflictType = Literal[
    "say_vs_write",
    "write_vs_vote",
    "then_vs_now",
    "words_without_action",
    "action_without_words",
]

DOCUMENT_KINDS = {"motion", "reservation", "prop", "beslut", "strategy"}
VOTE_KINDS = {"votering"}
WORDS_KINDS = {"party_page", "press", "anforande"}

PARTY_FROM_RIKSDAGEN = {
    "S": "s",
    "M": "m",
    "SD": "sd",
    "V": "v",
    "MP": "mp",
    "C": "c",
    "KD": "kd",
    "L": "l",
}


@dataclass(frozen=True)
class Locator:
    url: str | None = None
    official_id: str | None = None
    official_id_kind: str | None = None

    def present(self) -> bool:
        return bool(self.url or self.official_id)


@dataclass(frozen=True)
class Source:
    source_id: str
    layer: Layer
    kind: str
    locator: Locator
    retrieved_at: str
    content_hash: str
    attribution: str
    published_at: str | None = None
    vote_data: str | None = None
    punkt: str | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Source:
        loc = d["locator"]
        return cls(
            source_id=d["source_id"],
            layer=d["layer"],
            kind=d["kind"],
            locator=Locator(
                url=loc.get("url"),
                official_id=loc.get("official_id"),
                official_id_kind=loc.get("official_id_kind"),
            ),
            retrieved_at=d["retrieved_at"],
            content_hash=d["content_hash"],
            attribution=d["attribution"],
            published_at=d.get("published_at"),
            vote_data=d.get("vote_data"),
            punkt=d.get("punkt"),
        )


@dataclass(frozen=True)
class DerivedFrom:
    source_id: str
    quote: str | None = None


@dataclass(frozen=True)
class Claim:
    claim_id: str
    actor_id: str
    topic_id: str
    statement: str
    stance: Stance
    claim_role: ClaimRole
    derived_from: tuple[DerivedFrom, ...]
    evidence_score: float
    polarity_notes: str | None = None
    time_start: str | None = None
    time_end: str | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Claim:
        return cls(
            claim_id=d["claim_id"],
            actor_id=d["actor_id"],
            topic_id=d["topic_id"],
            statement=d["statement"],
            stance=d["stance"],
            claim_role=d["claim_role"],
            derived_from=tuple(
                DerivedFrom(x["source_id"], x.get("quote")) for x in d["derived_from"]
            ),
            evidence_score=float(d["evidence_score"]),
            polarity_notes=d.get("polarity_notes"),
            time_start=d.get("time_start"),
            time_end=d.get("time_end"),
        )

    def source_ids(self) -> tuple[str, ...]:
        return tuple(d.source_id for d in self.derived_from)


@dataclass
class Conflict:
    conflict_id: str
    actor_id: str
    topic_id: str
    type: ConflictType
    claim_ids: list[str]
    summary: str
    detected_at: str
    status: str = "open"
    documented_absence: bool = False
    resolution_note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "conflict_id": self.conflict_id,
            "actor_id": self.actor_id,
            "topic_id": self.topic_id,
            "type": self.type,
            "claim_ids": self.claim_ids,
            "summary": self.summary,
            "detected_at": self.detected_at,
            "status": self.status,
        }
        if self.documented_absence:
            d["documented_absence"] = True
        if self.resolution_note:
            d["resolution_note"] = self.resolution_note
        return d


@dataclass
class Dataset:
    as_of: str
    run_id: str
    actors: list[dict[str, Any]]
    topics: list[dict[str, Any]]
    sources: list[Source]
    claims: list[Claim]
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    spec_version: str = "0.1.0"
    ingest_errors: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Dataset:
        return cls(
            as_of=d["as_of"],
            run_id=d["run_id"],
            actors=list(d.get("actors", [])),
            topics=list(d.get("topics", [])),
            sources=[Source.from_dict(s) for s in d.get("sources", [])],
            claims=[Claim.from_dict(c) for c in d.get("claims", [])],
            conflicts=list(d.get("conflicts", [])),
            spec_version=d.get("spec_version", "0.1.0"),
            ingest_errors=list(d.get("ingest_errors", [])),
        )

    def source_index(self) -> dict[str, Source]:
        return {s.source_id: s for s in self.sources}
