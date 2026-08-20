import json
from pathlib import Path

from radar.adapters.riksdagen import (
    RiksdagenAdapter,
    anforande_url,
    rows_from_anforandelista,
    rows_from_voteringlista,
    votering_url,
)
from radar.store import upsert_claims, upsert_sources
from radar.models import Claim, DerivedFrom, Locator, Source

ANF = Path(__file__).parent / "fixtures" / "riksdagen_anforandelista.json"
VOT = Path(__file__).parent / "fixtures" / "riksdagen_voteringlista.json"


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class RoutedClient:
    def __init__(self, routes: dict):
        self.routes = routes
        self.urls: list[str] = []

    def get(self, url, timeout=None):
        del timeout
        self.urls.append(url)
        for needle, payload in self.routes.items():
            if needle in url:
                return FakeResponse(payload)
        return FakeResponse({})


def test_fetch_hits_all_three_open_endpoints():
    client = RoutedClient({
        "dokumentlista": {"dokumentlista": {"@sidor": "1", "dokument": []}},
        "anforandelista": json.loads(ANF.read_text(encoding="utf-8")),
        "voteringlista": json.loads(VOT.read_text(encoding="utf-8")),
    })
    adapter = RiksdagenAdapter(client=client, aliases=["AI"])
    raw = adapter.fetch(["2025/26"])
    joined = " ".join(client.urls)
    assert "dokumentlista" in joined
    assert "anforandelista" in joined
    assert "voteringlista" in joined
    assert raw["anforande"]
    assert raw["votering"]


def test_anforande_keeps_official_id():
    payload = json.loads(ANF.read_text(encoding="utf-8"))
    adapter = RiksdagenAdapter()
    sources = adapter.normalize({"anforande": rows_from_anforandelista(payload)})
    assert len(sources) == 1
    src = sources[0]
    assert src.kind == "anforande"
    assert src.locator.official_id == "H8C101-42"
    assert src.locator.official_id_kind == "anforande_id"
    assert src.locator.url.startswith("https://")
    assert adapter.extract(sources, "ai") == []


def test_vote_extract_is_party_aggregate_from_recorded_rost():
    payload = json.loads(VOT.read_text(encoding="utf-8"))
    adapter = RiksdagenAdapter()
    sources = adapter.normalize({"votering": rows_from_voteringlista(payload)})
    claims = adapter.extract(sources, "ai")
    by_actor = {c.actor_id: c for c in claims}
    assert by_actor["m"].stance == "support"
    assert by_actor["m"].claim_role == "action"
    assert by_actor["v"].stance == "oppose"
    assert "s" not in by_actor  # frånvarande är inte rost
    assert "kd" not in by_actor  # saknar votering_id → error, ingen claim
    assert any("votering_id" in e["message"] for e in adapter.errors)
    assert by_actor["m"].derived_from[0].source_id.startswith("l1:vot:AE123:1:M")
    assert by_actor["m"].evidence_score == 0.7


def test_urls_point_at_riksdagen():
    assert "anforandelista" in anforande_url("2025/26", "AI")
    assert "voteringlista" in votering_url("2025/26", "AI")


def test_upsert_is_idempotent_on_source_id():
    a = Source(
        source_id="l1:dok:A",
        layer="L1",
        kind="motion",
        locator=Locator(official_id="A", official_id_kind="dok_id", url="https://example.test/A"),
        retrieved_at="2026-08-20T00:00:00Z",
        content_hash="oldoldold",
        attribution="Sveriges riksdag",
    )
    b = Source(
        source_id="l1:dok:A",
        layer="L1",
        kind="motion",
        locator=Locator(official_id="A", official_id_kind="dok_id", url="https://example.test/A"),
        retrieved_at="2026-08-20T01:00:00Z",
        content_hash="newnewnew",
        attribution="Sveriges riksdag",
    )
    merged = upsert_sources([a], [b])
    assert len(merged) == 1
    assert merged[0].content_hash == "newnewnew"


def test_upsert_claims_does_not_duplicate():
    c = Claim(
        claim_id="cl:1",
        actor_id="m",
        topic_id="ai",
        statement="x",
        stance="support",
        claim_role="action",
        derived_from=(DerivedFrom("s1"),),
        evidence_score=0.7,
    )
    assert len(upsert_claims([c], [c])) == 1
