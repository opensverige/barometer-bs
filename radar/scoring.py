from __future__ import annotations

from radar.models import Claim, Source

LAYER_W = {"L1": 0.70, "L2": 0.40, "L3": 0.15}
L3_CAP = 0.25
EXTRA_L1 = 0.10


def score_claim(claim: Claim, sources: dict[str, Source]) -> float:
    resolved = [sources[sid] for sid in claim.source_ids() if sid in sources]
    if not resolved:
        raise ValueError(f"{claim.claim_id}: no resolvable sources")
    if any(not s.locator.present() for s in resolved):
        raise ValueError(f"{claim.claim_id}: source without locator")

    layers = [s.layer for s in resolved]
    layer_w = max(LAYER_W[layer] for layer in layers)
    l1_ids = {
        (s.locator.official_id or s.locator.url)
        for s in resolved
        if s.layer == "L1"
    }
    extra = EXTRA_L1 * max(0, len(l1_ids) - 1)
    value = min(1.0, layer_w + extra)
    if all(layer == "L3" for layer in layers):
        value = min(value, L3_CAP)
    return round(value, 4)
