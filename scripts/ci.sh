#!/usr/bin/env bash
set -euo pipefail
python -m pip install -e ".[dev]"
pytest
python -m radar validate tests/fixtures/golden.json
python -m radar detect tests/fixtures/golden.json
