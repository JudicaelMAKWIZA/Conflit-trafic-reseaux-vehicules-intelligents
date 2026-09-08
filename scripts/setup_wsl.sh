#!/usr/bin/env bash
# Local Linux runtime for hosts where native SUMO binaries cannot execute.
set -euo pipefail
cd "$(dirname "$0")/.."
pilot_venv="$HOME/.venvs/traffic-conflict-pilot"
python3 -m venv "$pilot_venv"
"$pilot_venv/bin/python" -m pip install --index-url https://pypi.org/simple --progress-bar off -r requirements.txt
"$pilot_venv/bin/python" -m pip install --no-deps -e .
"$pilot_venv/bin/python" scripts/doctor.py
