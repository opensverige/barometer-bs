# Deploy (senare)

Ingest är Python. Vercel hostar statiska filer. Supabase lagrar dataset.

```
radar ingest (CI/cron) → data/export/dataset.json → Supabase tables
                       → web/ (Vercel)
```

Tabeller speglar `schema/radar.schema.json`: actors, topics, sources, claims, conflicts.

Inte nu: inga nycklar i repo, ingen Next-app, ingen auto-push till produktion.
