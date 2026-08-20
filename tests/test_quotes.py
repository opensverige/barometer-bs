import json
from pathlib import Path

PACK = Path(__file__).resolve().parents[1] / "web" / "quotes.json"


def test_quote_bank_size_and_length():
    pack = json.loads(PACK.read_text(encoding="utf-8"))
    quotes = pack["quotes"]
    assert 40 <= len(quotes) <= 50
    limit = pack["max_words"]
    for q in quotes:
        n = len(q["text"].split())
        assert n <= limit, f"{q['id']} has {n} words: {q['text']}"
        assert q["actor_id"]
        assert q["source"]
        assert pack["status"] == "fixture"
