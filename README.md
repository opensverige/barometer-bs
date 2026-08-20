# Accountability Radar

OpenSverige — *ord mot handling*. Tema: **VALET**.

Mäter deltat: vad de sa senast valet · vad de gjort · vad de säger nu. Inte opinion. Inte röstmaskin.

| Dokument | Vad det styr |
|----------|----------------|
| [docs/SPEC.md](docs/SPEC.md) | beteende: hierarki, claims, conflicts, ingest, gates |
| [docs/PRD.md](docs/PRD.md) | produkt: mål, scope-lager, metrics, feature-livscykel |
| [docs/SCORING.md](docs/SCORING.md) | `evidence_score`-formeln (byte = major) |
| [docs/LINKS.md](docs/LINKS.md) | riksdagen, regeringen, statsbudget (ej L1) |

## Kör

```bash
pip install -e ".[dev]"
pytest
python -m radar validate tests/fixtures/valet.json
python -m radar delta tests/fixtures/valet.json --out web/delta.json
```

Statisk vy, ingen Vite:

```bash
# öppna web/index.html via valfri static server så fetch fungerar
python -m http.server 8765 --directory web
```

Sauron-bubblan shufflar 48 korta fixture-citat (≤10 ord). Byt mot L3-extract.

Bidrag via pull request. Inget direkt till `main`. Se [CONTRIBUTING.md](CONTRIBUTING.md).
