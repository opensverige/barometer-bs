from pathlib import Path
import json

from radar.kpis import freeze_match, locator_kpi, metadata_freeze_match_ratio, snapshot_hash
from radar.slice import build_ui, load_freeze, records_to_sources
from radar.store import upsert_sources
from radar.title_gate import title_is_on_topic

FREEZE = Path(__file__).resolve().parents[1] / "data" / "freeze" / "ai_3rm.json"


def _seal(records):
    out = []
    for rec in records:
        row = dict(rec)
        row["content_hash"] = snapshot_hash(row["snapshot"])
        out.append(row)
    return out


def test_title_gate_drops_export_control():
    assert not title_is_on_topic(
        "med anledning av skr. 2025/26:114 Strategisk exportkontroll 2025"
    )
    assert title_is_on_topic("För en säker och hållbar AI")


def test_metadata_freeze_match_uses_stored_hash():
    blob = "HD02311|2025/26|titel|2025-10-03"
    stored = snapshot_hash(blob)
    assert freeze_match(stored, blob)
    assert not freeze_match(stored, blob + "x")
    sealed = [{"snapshot": blob, "content_hash": stored}]
    assert metadata_freeze_match_ratio(sealed) == 1.0
    sealed[0]["content_hash"] = snapshot_hash(blob + "x")
    assert metadata_freeze_match_ratio(sealed) == 0.0
    freeze = load_freeze(FREEZE)
    assert metadata_freeze_match_ratio(freeze["records"]) is None
    assert metadata_freeze_match_ratio(_seal(freeze["records"])) == 1.0


def test_locator_rejects_party_page_ids_requires_dok_id_and_punkt():
    freeze = load_freeze(FREEZE)
    assert locator_kpi(freeze["records"]) == 1.0
    fake = {
        "kind": "motion",
        "dok_id": "L3-S-AI",
        "url": "https://www.socialdemokraterna.se/x",
        "actor_id": "s",
    }
    assert locator_kpi([fake]) == 0.0
    beslut = next(r for r in freeze["records"] if r["kind"] == "beslut")
    broken = dict(beslut)
    broken["punkt"] = None
    assert locator_kpi([broken]) == 0.0
    page = next(r for r in freeze["records"] if r["kind"] == "party_page")
    assert "dok_id" not in page


def test_acclamation_never_presented_as_party_vote():
    ui = build_ui(load_freeze(FREEZE))
    dumped = json.dumps(ui, ensure_ascii=False)
    sd = next(p for p in ui["parties"] if p["actor_id"] == "sd")
    assert sd["votes"]
    for vote in sd["votes"]:
        assert vote["decision_result"] == "known"
        assert vote["vote_method"] == "acclamation"
        assert vote["party_vote"] == "unknown"
        assert vote["role"] == "beslutades"
        assert "Röstade" not in vote["label"]
        assert vote.get("stance") not in {"support", "oppose"}
    assert "Röstade" not in dumped
    assert ui["then_vs_now"] == []


def test_then_vs_now_hidden_without_two_comparable_votes():
    ui = build_ui(load_freeze(FREEZE))
    assert ui["then_vs_now"] == []
    sd = next(p for p in ui["parties"] if p["actor_id"] == "sd")
    assert len(sd["timeline"]) >= 2
    assert sd["actions"][0]["dok_id"] == "HD02311"
    assert sd["votes"][0]["dok_id"] == "HD01TU8"


def test_no_hardcoded_claim_actor_on_every_source():
    src = Path(__file__).resolve().parents[1] / "radar" / "slice.py"
    text = src.read_text(encoding="utf-8")
    assert 'actor_id="sd"' not in text
    assert 'actor_id="s"' not in text.replace('("s", "Socialdemokraterna")', "")


def test_upsert_idempotent():
    sources = records_to_sources(load_freeze(FREEZE))
    again = upsert_sources(sources, sources)
    assert [s.source_id for s in again] == [s.source_id for s in sources]
