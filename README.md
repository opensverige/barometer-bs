# Accountability Radar

OpenSverige — *ord mot handling*.

Mäter avståndet mellan vad riksdagspartier **säger** och vad de **gör**. Inte opinion. Inte röstmaskin.

| Dokument | Vad det styr |
|----------|----------------|
| [docs/SPEC.md](docs/SPEC.md) | beteende: hierarki, claims, conflicts, ingest, gates |
| [docs/PRD.md](docs/PRD.md) | produkt: mål, scope-lager, metrics, feature-livscykel |
| [docs/SCORING.md](docs/SCORING.md) | `evidence_score`-formeln (byte = major) |

L1 (riksdagen) vinner vid konflikt. Första topic är `ai` — motorn är issue-agnostisk.

## Kör

```bash
pip install -e ".[dev]"
pytest
python -m radar validate tests/fixtures/golden.json
python -m radar detect tests/fixtures/golden.json
```

```
schema/                 JSON Schema v0.1
config/                 8 partier, topics, regering, L3-whitelist
radar/                  validate · score · detect · adapters · cli
tests/fixtures/golden.json   alla fem conflict-typer
```

Bidrag via pull request. Inget direkt till `main`. Se [CONTRIBUTING.md](CONTRIBUTING.md).
