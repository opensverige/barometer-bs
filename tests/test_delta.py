from pathlib import Path

from radar.delta import snapshot
from radar.models import Dataset
from radar.validate import load_dataset

FIXTURE = Path(__file__).parent / "fixtures" / "valet.json"


def test_valet_fixture_validates():
    _, errors = load_dataset(FIXTURE)
    assert errors == []


def test_s_has_election_delta_and_live_words():
    payload, errors = load_dataset(FIXTURE)
    assert errors == []
    ds = Dataset.from_dict(payload)
    deltas, _ = snapshot(ds.claims, ds.source_index())
    s = next(d for d in deltas if d.actor_id == "s")
    assert s.said_then
    assert s.did
    assert s.says_now
    assert "then_vs_now" in s.conflict_types
    assert "say_vs_write" in s.conflict_types
    assert "action_without_words" not in s.conflict_types


def test_sd_action_without_campaign_or_today_words():
    payload, _ = load_dataset(FIXTURE)
    ds = Dataset.from_dict(payload)
    deltas, _ = snapshot(ds.claims, ds.source_index())
    sd = next(d for d in deltas if d.actor_id == "sd")
    assert sd.did
    assert sd.said_then == []
    assert sd.says_now == []
    assert "action_without_words" in sd.conflict_types
