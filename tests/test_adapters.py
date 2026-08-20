from radar.adapters.riksdagen import RiksdagenAdapter, dokument_url
from radar.models import PARTY_FROM_RIKSDAGEN


def test_dokument_url_is_stable():
    url = dokument_url("2025/26", "AI", 1)
    assert "dokumentlista" in url
    assert "utformat=json" in url
    assert "rm=2025%2F26" in url or "rm=2025/26" in url


def test_normalize_drops_nothing_silently():
    adapter = RiksdagenAdapter()
    sources = adapter.normalize({
        "dokument": [{"titel": "saknar id", "organ": "S"}, {"dok_id": "H1", "titel": "AI", "organ": "S", "typ": "mot", "datum": "2026-01-01"}],
        "anforande": [{}],
        "votering": [{"votering_id": "V1", "punkt": "1", "parti": "M", "rost": "Ja"}],
    })
    ids = {s.source_id for s in sources}
    assert "l1:dok:H1" in ids
    assert "l1:vot:V1:1:M" in ids
    assert any("dok_id" in e["message"] for e in adapter.errors)
    assert any("anforande" in e["message"] for e in adapter.errors)


def test_extract_motion_is_action_support():
    adapter = RiksdagenAdapter()
    raw = {"dokument": [{"dok_id": "H1", "titel": "Nationell AI-plan", "organ": "SD", "typ": "mot", "datum": "2025-11-01"}]}
    sources = adapter.normalize(raw)
    claims = adapter.extract(sources, "ai", raw=raw)
    assert len(claims) == 1
    assert claims[0].actor_id == PARTY_FROM_RIKSDAGEN["SD"]
    assert claims[0].claim_role == "action"
    assert claims[0].stance == "support"
    assert claims[0].evidence_score == 0.7
