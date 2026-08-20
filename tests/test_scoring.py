import json
from copy import deepcopy
from pathlib import Path

from radar.models import Claim, DerivedFrom, Locator, Source
from radar.scoring import score_claim
from radar.validate import validate_payload

FIXTURE = Path(__file__).parent / "fixtures" / "golden.json"


def _src(layer: str, sid: str = "s1") -> Source:
    return Source(
        source_id=sid,
        layer=layer,  # type: ignore[arg-type]
        kind="motion" if layer != "L3" else "party_page",
        locator=Locator(url=f"https://example.test/{sid}"),
        retrieved_at="2026-08-19T00:00:00Z",
        content_hash="abcdabcd",
        attribution="t",
    )


def _claim(sources: list[str], score: float = 0.0) -> Claim:
    return Claim(
        claim_id="c1",
        actor_id="s",
        topic_id="ai",
        statement="x",
        stance="support",
        claim_role="action",
        derived_from=tuple(DerivedFrom(s) for s in sources),
        evidence_score=score,
    )


def test_l1_beats_l3():
    sources = {"a": _src("L1", "a"), "b": _src("L3", "b")}
    assert score_claim(_claim(["a", "b"]), sources) == 0.7


def test_l3_only_capped():
    sources = {"b": _src("L3", "b")}
    assert score_claim(_claim(["b"]), sources) == 0.15


def test_extra_l1_locator_raises():
    sources = {"a": _src("L1", "a"), "c": _src("L1", "c")}
    assert score_claim(_claim(["a", "c"]), sources) == 0.8


def test_l3_action_rejected():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    bad = deepcopy(payload)
    bad["claims"] = [
        {
            "claim_id": "bad",
            "actor_id": "s",
            "topic_id": "ai",
            "statement": "x",
            "stance": "support",
            "claim_role": "action",
            "derived_from": [{"source_id": "src-s-web"}],
            "evidence_score": 0.15,
        }
    ]
    bad["conflicts"] = []
    errors = validate_payload(bad)
    assert any("L3-only must be words" in e for e in errors)
