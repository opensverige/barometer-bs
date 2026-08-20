import json
from pathlib import Path

PACK = Path(__file__).resolve().parents[1] / "web" / "quotes.json"


def test_sauron_quotes_fit_the_bubble():
    pack = json.loads(PACK.read_text(encoding="utf-8"))
    assert 20 <= len(pack["quotes"]) <= 50
    for q in pack["quotes"]:
        assert 1 <= len(q["text"].split()) <= 12
