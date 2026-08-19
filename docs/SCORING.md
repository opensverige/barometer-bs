# evidence_score v0.1

Byte av denna formel = **major** (SPEC §7 / §14).

Score ∈ [0, 1]. Enbart funktion av källor — inte politikens innehåll.

## Formel

```
layer_w = max(w(layer(s)) for s in claim.sources)
  w(L1) = 0.70
  w(L2) = 0.40
  w(L3) = 0.15

extra_l1 = 0.10 * max(0, distinct_l1_locators - 1)

score = min(1.0, layer_w + extra_l1)

om endast L3-källor:
  score = min(score, 0.25)
  claim_role måste vara words
```

Saknad locator → claim ogiltig, ingen public score.

## Inte

- partiskhet
- “hur AI-positiv”
- kvalitet på förslaget
