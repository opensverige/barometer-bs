import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "web" / "dataset.json"
IDS = {"s", "m", "sd", "v", "mp", "c", "kd", "l"}


def test_mvp_has_eight_parties_and_real_locators():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    actors = {p["actor_id"] for p in data["parties"]}
    assert actors == IDS
    for party in data["parties"]:
        for item in party["words"] + party["actions"] + party["votes"]:
            assert item["url"].startswith("https://")
        for item in party["actions"]:
            assert item["dok_id"]
            assert "riksdagen.se" in item["url"]
            assert "stance" not in item


def test_flags_are_absence_only():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    allowed = {None, "words_without_action", "action_without_words"}
    for party in data["parties"]:
        assert party["flag"] in allowed
