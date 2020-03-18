#!/usr/bin/env bash
set -e

export PYTHONDONTWRITEBYTECODE=1

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
. .venv/bin/activate
pip install -r tests/requirements.txt
pip install -e .

python3 -m pytest --cov-report html "$@"
