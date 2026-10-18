#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$repo_root"
if ! command -v uv >/dev/null 2>&1; then
  printf '%s\n' 'uv is required. See docs/operations/LOCAL.md.' >&2
  exit 127
fi
export ASTANA_MODE="${ASTANA_MODE:-fixture}"
export LLM_PROVIDER="${LLM_PROVIDER:-none}"
uv sync --locked --all-packages
exec uv run --locked uvicorn astana_api.app:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log "$@"
