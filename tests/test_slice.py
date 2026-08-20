from pathlib import Path
import json

from radar.kpis import freeze_match, snapshot_blob, snapshot_hash
from radar.slice import build_ui, load_freeze, records_to_sources
from radar.store import upsert_sources
from radar.title_gate import title_is_on_topic

FREEZE = Path(__file__).resolve().parents[1] / "data" / "freeze" / "ai_3rm.json"


def test_title_gate_drops_export_control_and_keeps_ai_title():
    assert not title_is_on_topic(
        "med anledning av skr. 2025/26:114 Strategisk exportkontroll 2025"
    )
    assert title_is_on_topic("För en säker och hållbar AI")
    assert title_is_on_topic("Risker och möjligheter med artificiell intelligens (AI)")


def test_freeze_match_and_locator_kpi():
    freeze = load_freeze(FREEZE)
    ui = build_ui(freeze)
    assert ui["kpis"]["freeze_match"] == 1.0
    assert ui["kpis"]["locator"] == 1.0
    blob = snapshot_blob("HD02311", "En tillförlitlig, konkurrenskraftig och hållbar svensk AI-politik", "2025/26", "2025-10-03")
    assert freeze_match(snapshot_hash(blob), blob)
    assert not freeze_match(snapshot_hash(blob), blob + "x")


def test_sd_has_clickable_chain_over_two_dates():
    ui = build_ui(load_freeze(FREEZE))
    sd = next(p for p in ui["parties"] if p["actor_id"] == "sd")
    assert sd["actions"] and sd["votes"]
    assert sd["actions"][0]["url"].startswith("https://www.riksdagen.se")
    assert sd["votes"][0]["vote_data"] == "none"
    dates = [x["date"] for x in sd["timeline"]]
    assert dates == sorted(dates) and len(dates) >= 2
    tvn = next(x for x in ui["then_vs_now"] if x["actor_id"] == "sd")
    assert tvn["status"] == "underlag_saknas"
    assert "acklamation" in tvn["summary"].lower()


def test_banned_and_empty_windows_are_honest():
    freeze = load_freeze(FREEZE)
    ids = {r["dok_id"] for r in freeze["records"]}
    assert "HD024115" not in ids
    ui = build_ui(freeze)
    assert ui["coverage"]["motions_title_gated_by_rm"]["2023/24"] == 0
    assert ui["coverage"]["motions_title_gated_by_rm"]["2024/25"] == 0
    assert ui["coverage"]["recorded_party_votes"] == 0


def test_upsert_idempotent():
    sources = records_to_sources(load_freeze(FREEZE))
    again = upsert_sources(sources, sources)
    assert [s.source_id for s in again] == [s.source_id for s in sources]
