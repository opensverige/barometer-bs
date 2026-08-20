# Accountability Radar

OpenSverige — *ord mot handling*. Tema: **VALET**.

Inte opinion. Inte röstmaskin. Sade / skrev / röstade — med länk.

## Deploy (Vercel)

Root Directory: `web`. Inget build command. Merge PR → Import GitHub repo → Done.

Lokalt:

```
python -m http.server 8765 --directory web
```

## Motor

```
pip install -e ".[dev]"
pytest
python -m radar ingest riksdagen --topic ai
```

L1 = Sveriges riksdag. Tom cell i UI = inget i urvalet, inte frikänd.
