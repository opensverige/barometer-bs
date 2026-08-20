# GitHub Actions drop-in

Tokenet som skriver hit saknar `workflow`-scope, så filen kan inte landa i `.github/workflows/`.

Kopiera till `.github/workflows/validate.yml`:

```yaml
name: validate

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - run: pytest
      - run: python -m radar validate tests/fixtures/golden.json
      - run: python -m radar detect tests/fixtures/golden.json
```

Lokalt: `bash scripts/ci.sh`
