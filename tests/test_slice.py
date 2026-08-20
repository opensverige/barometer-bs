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
    assert metadata_freeze_match_ratio([{"snapshot": blob, "content_hash": stored}]) == 1.0
    assert metadata_freeze_match_ratio([{"snapshot": blob, "content_hash": snapshot_hash(blob + "x")}]) == 0.0
    freeze = load_freeze(FREEZE)
    assert metadata_freeze_match_ratio(freeze["records"]) is None
    assert metadata_freeze_match_ratio(_seal(freeze["records"])) == 1.0


def test_unsealed_source_content_hash_is_empty():
    sources = records_to_sources(load_freeze(FREEZE))
    assert sources
    assert all(s.content_hash == "" for s in sources)


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


def test_acclamation_lives_only_in_decisions_never_votes():
    ui = build_ui(load_freeze(FREEZE))
    for party in ui["parties"]:
        assert all(v.get("vote_method") != "acclamation" for v in party["votes"])
        for decision in party["decisions"]:
            assert decision["vote_method"] == "acclamation"
            assert decision["party_vote"] == "unknown"
            assert decision["decision_result"] == "known"
            assert decision["role"] == "beslutades"
    sd = next(p for p in ui["parties"] if p["actor_id"] == "sd")
    assert sd["votes"] == []
    assert sd["decisions"]
    assert sd["decisions"][0]["dok_id"] == "HD01TU8"
    assert ui["then_vs_now"] == []


def test_party_can_have_recorded_vote_and_acclamation_decision():
    freeze = load_freeze(FREEZE)
    freeze = json.loads(json.dumps(freeze))
    freeze["records"].append({
        "kind": "votering",
        "actor_id": "sd",
        "rm": "2025/26",
        "dok_id": "HAE123",
        "title": "Votering AI punkt 1",
        "published_at": "2026-02-18",
        "url": "https://data.riksdagen.se/votering/HAE123",
        "punkt": "1",
        "party_vote": "support",
        "vote_method": "recorded",
        "snapshot": "HAE123|2025/26|Votering AI punkt 1|2026-02-18",
    })
    ui = build_ui(freeze)
    sd = next(p for p in ui["parties"] if p["actor_id"] == "sd")
    assert len(sd["votes"]) == 1
    assert sd["votes"][0]["party_vote"] == "support"
    assert sd["votes"][0]["vote_method"] == "recorded"
    assert len(sd["decisions"]) == 1
    assert sd["decisions"][0]["vote_method"] == "acclamation"
    assert all(v.get("vote_method") != "acclamation" for v in sd["votes"])
    assert all(d.get("kind") != "votering" or d.get("vote_method") == "acclamation" for d in sd["decisions"])


def test_then_vs_now_hidden_without_two_comparable_votes():
    ui = build_ui(load_freeze(FREEZE))
    assert ui["then_vs_now"] == []
    sd = next(p for p in ui["parties"] if p["actor_id"] == "sd")
    assert sd["actions"][0]["dok_id"] == "HD02311"
    assert sd["decisions"][0]["dok_id"] == "HD01TU8"


def test_upsert_idempotent():
    sources = records_to_sources(load_freeze(FREEZE))
    again = upsert_sources(sources, sources)
    assert [s.source_id for s in again] == [s.source_id for s in sources]
