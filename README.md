# Accountability Radar

OpenSverige — *ord mot handling*. Tema: **VALET**.

Inte opinion. Inte röstmaskin. Sade / skrev / röstade — med länk.

## Deploy på Vercel

Det här är en **statisk sajt**, inte Python-app. `pyproject.toml` är motorn — den ska inte byggas på Vercel.

1. Project → Settings → General
2. **Framework Preset: Other** (inte Python, inte Next)
3. **Root Directory:** tom (repo-roten)
4. Override **Install Command:** `true`
5. Override **Build Command:** `true`
6. **Output Directory:** `web`
7. Redeploy

`vercel.json` i roten sätter samma sak. Efter merge: Redeploy latest.

Lokalt: `python -m http.server 8765 --directory web`
