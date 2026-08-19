from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def test_eight_parties_and_ai_topic():
    actors = json.loads((ROOT / "config" / "actors.json").read_text(encoding="utf-8"))
    topics = json.loads((ROOT / "config" / "topics.json").read_text(encoding="utf-8"))
    ids = {a["actor_id"] for a in actors}
    assert ids == {"s", "m", "sd", "v", "mp", "c", "kd", "l"}
    assert all(a["type"] == "party" for a in actors)
    assert {t["topic_id"] for t in topics} == {"ai"}
