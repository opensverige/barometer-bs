import json
from pathlib import Path

from radar.adapters.riksdagen import (
    RiksdagenAdapter,
    dokument_url,
    official_dok_id,
    rows_from_dokumentlista,
)
from radar.validate import validate_payload

FIXTURE = Path(__file__).parent / "fixtures" / "riksdagen_dokumentlista_mot_2025_26.json"
ACTORS = Path(__file__).resolve().parents[1] / "config" / "actors.json"
TOPICS = Path(__file__).resolve().parents[1] / "config" / "topics.json"


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, payload):
        self.payload = payload
        self.urls: list[str] = []

    def get(self, url, timeout=None):
        del timeout
        self.urls.append(url)
        return FakeResponse(self.payload)


def _recorded():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_dokument_url_hits_open_dokumentlista():
    url = dokument_url("2025/26", "AI", 1)
    assert url.startswith("https://data.riksdagen.se/dokumentlista/")
    assert "doktyp=mot" in url
    assert "utformat=json" in url
    assert "rm=2025%2F26" in url or "rm=2025/26" in url


def test_fetch_unwraps_real_dokumentlista_shape():
    recorded = _recorded()
    client = FakeClient(recorded)
    adapter = RiksdagenAdapter(client=client, aliases=["AI"])
    raw = adapter.fetch(["2025/26"])
    assert client.urls
    assert "dokumentlista" in client.urls[0]
    assert "voteringlista" not in client.urls[0]
    assert official_dok_id(raw["dokument"][0]) == "HD024156"
    assert len(raw["dokument"]) == 3


def test_normalize_keeps_official_dok_id_and_https_locator():
    recorded = _recorded()
    adapter = RiksdagenAdapter()
    sources = adapter.normalize({"dokument": rows_from_dokumentlista(recorded)})
    by_id = {s.locator.official_id: s for s in sources}
    assert set(by_id) == {"HD024156", "HD024122", "HD024115"}
    src = by_id["HD024156"]
    assert src.layer == "L1"
    assert src.kind == "motion"
    assert src.locator.official_id_kind == "dok_id"
    assert src.locator.url == "https://data.riksdagen.se/dokument/HD024156.html"
    assert src.attribution == "Sveriges riksdag"
    assert src.published_at == "2026-05-13"
    # organ is committee (UbU), must not leak into locator id
    assert src.locator.official_id != "UbU"
    assert src.source_id == "l1:dok:HD024156"


def test_missing_dok_id_is_logged_not_silenced():
    adapter = RiksdagenAdapter()
    sources = adapter.normalize({"dokument": [{"titel": "saknar id", "organ": "S"}]})
    assert sources == []
    assert any("dok_id" in e["message"] for e in adapter.errors)


def test_extract_does_not_invent_claims():
    recorded = _recorded()
    adapter = RiksdagenAdapter()
    sources = adapter.normalize({"dokument": rows_from_dokumentlista(recorded)})
    assert adapter.extract(sources, "ai") == []


def test_normalized_sources_are_schema_valid():
    recorded = _recorded()
    adapter = RiksdagenAdapter()
    sources = adapter.normalize({"dokument": rows_from_dokumentlista(recorded)})
    payload = {
        "as_of": "2026-08-20",
        "run_id": "fixture-dokumentlista",
        "spec_version": "0.1.0",
        "actors": json.loads(ACTORS.read_text(encoding="utf-8")),
        "topics": json.loads(TOPICS.read_text(encoding="utf-8")),
        "sources": [
            {
                "source_id": s.source_id,
                "layer": s.layer,
                "kind": s.kind,
                "locator": {
                    "url": s.locator.url,
                    "official_id": s.locator.official_id,
                    "official_id_kind": s.locator.official_id_kind,
                },
                "retrieved_at": s.retrieved_at,
                "published_at": s.published_at,
                "content_hash": s.content_hash,
                "attribution": s.attribution,
            }
            for s in sources
        ],
        "claims": [],
        "conflicts": [],
    }
    assert validate_payload(payload) == []
