# Bidra till Accountability Radar

Diskussion i Discord. Spårbara beslut i GitHub Issues + PR. Inget direkt till `main`.

## Vad du kan göra

| Du vill … | Gör … |
|-----------|--------|
| Ändra beteende (hierarki, score, invariants) | Issue `spec-change` + PR mot `docs/SPEC.md` **först** |
| Ny/borttagen yta | Issue `feature` / `remove` enligt [PRD §7](docs/PRD.md) |
| Nytt topic | Issue `topic` + rad i `config/topics.json` |
| Källa / fixture | PR mot `tests/fixtures/` eller `config/` |
| Adapter | Samma kontrakt: `fetch` → `normalize` → `extract` |

## Lokalt

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
python -m radar validate tests/fixtures/golden.json
python -m radar detect tests/fixtures/golden.json
```

Live-ingest (valfritt, nätverk):

```bash
pip install -e ".[ingest]"
python -m radar ingest riksdagen --rm 2024/25 --rm 2025/26 --topic ai --out data/raw/riksdagen.json
```

Inga nycklar i repo. Riksdagens API är nyckelfritt; ange alltid Sveriges riksdag som källa.

## Grind

CI ska köra schema + semantiska invariants + golden conflicts (alla fem typer). Agent får kommentera PR, inte mergea.
