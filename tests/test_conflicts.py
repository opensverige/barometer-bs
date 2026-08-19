from pathlib import Path

from radar.conflicts import detect
from radar.models import Dataset
from radar.validate import load_dataset

FIXTURE = Path(__file__).parent / "fixtures" / "golden.json"

REQUIRED = {
    "say_vs_write",
    "write_vs_vote",
    "then_vs_now",
    "words_without_action",
    "action_without_words",
}


def test_golden_validates():
    _, errors = load_dataset(FIXTURE)
    assert errors == []


def test_all_conflict_types_detected():
    payload, errors = load_dataset(FIXTURE)
    assert errors == []
    ds = Dataset.from_dict(payload)
    found = detect(ds.claims, ds.source_index(), detected_at="2026-08-19T00:00:00Z")
    types = {c.type for c in found}
    assert REQUIRED <= types
    pairs = {(c.type, c.actor_id) for c in found}
    assert ("say_vs_write", "s") in pairs
    assert ("write_vs_vote", "m") in pairs
    assert ("then_vs_now", "v") in pairs
    assert ("words_without_action", "c") in pairs
    assert ("action_without_words", "sd") in pairs
    for conflict in found:
        assert conflict.summary
        assert "svek" not in conflict.summary.lower()
        assert conflict.claim_ids


def test_acklamation_does_not_invent_vote():
    payload, _ = load_dataset(FIXTURE)
    ds = Dataset.from_dict(payload)
    found = detect(ds.claims, ds.source_index(), detected_at="2026-08-19T00:00:00Z")
    assert not any(c.actor_id == "kd" for c in found)
