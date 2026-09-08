#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec "$HOME/.venvs/traffic-conflict-pilot/bin/python" "$@"
