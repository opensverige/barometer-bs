from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from radar.models import Claim, Dataset, Source
from radar.scoring import score_claim

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schema" / "radar.schema.json"


def load_schema() -> dict[str, Any]:
    root = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    dataset = {**root["$defs"]["dataset"]}
    dataset["$schema"] = root["$schema"]
    dataset["$defs"] = root["$defs"]
    return dataset


def schema_errors(payload: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(load_schema())
    return sorted(
        f"{list(e.path)}: {e.message}" for e in validator.iter_errors(payload)
    )


def semantic_errors(ds: Dataset) -> list[str]:
    errors: list[str] = []
    sources = ds.source_index()
    actor_ids = {a["actor_id"] for a in ds.actors}
    topic_ids = {t["topic_id"] for t in ds.topics}

    for src in ds.sources:
        if not src.locator.present():
            errors.append(f"source {src.source_id}: missing locator")

    claim_ids: set[str] = set()
    for claim in ds.claims:
        if claim.claim_id in claim_ids:
            errors.append(f"duplicate claim_id {claim.claim_id}")
        claim_ids.add(claim.claim_id)
        if claim.actor_id not in actor_ids:
            errors.append(f"{claim.claim_id}: unknown actor {claim.actor_id}")
        if claim.topic_id not in topic_ids:
            errors.append(f"{claim.claim_id}: unknown topic {claim.topic_id}")
        if not claim.derived_from:
            errors.append(f"{claim.claim_id}: no sources")
            continue
        missing = [sid for sid in claim.source_ids() if sid not in sources]
        if missing:
            errors.append(f"{claim.claim_id}: missing sources {missing}")
            continue
        resolved = [sources[sid] for sid in claim.source_ids()]
        if any(not s.locator.present() for s in resolved):
            errors.append(f"{claim.claim_id}: source without locator")
        layers = {s.layer for s in resolved}
        if layers <= {"L3"} and claim.claim_role != "words":
            errors.append(f"{claim.claim_id}: L3-only must be words")
        try:
            expected = score_claim(claim, sources)
        except ValueError as exc:
            errors.append(str(exc))
        else:
            if abs(expected - claim.evidence_score) > 0.001:
                errors.append(
                    f"{claim.claim_id}: score {claim.evidence_score} != {expected}"
                )

    for conflict in ds.conflicts:
        ids = conflict.get("claim_ids") or []
        if not ids:
            errors.append(f"{conflict.get('conflict_id')}: no claim refs")
        unknown = [i for i in ids if i not in claim_ids]
        if unknown:
            errors.append(
                f"{conflict.get('conflict_id')}: unknown claims {unknown}"
            )
        if len(ids) < 2 and not conflict.get("documented_absence"):
            errors.append(
                f"{conflict.get('conflict_id')}: need 2 claims or documented_absence"
            )
        for cid in ids:
            claim = next((c for c in ds.claims if c.claim_id == cid), None)
            if claim is None:
                continue
            for sid in claim.source_ids():
                src = sources.get(sid)
                if src and not src.locator.present():
                    errors.append(
                        f"{conflict.get('conflict_id')}: claim {cid} has sourceless locator"
                    )
    return errors


def validate_payload(payload: dict[str, Any]) -> list[str]:
    errors = schema_errors(payload)
    if errors:
        return errors
    return semantic_errors(Dataset.from_dict(payload))


def load_dataset(path: Path) -> tuple[dict[str, Any], list[str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload, validate_payload(payload)
