#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! python3 -m ruff --version >/dev/null 2>&1; then
  echo "ruff is required for this repository. Install dev dependencies or run: python3 -m pip install ruff" >&2
  exit 1
fi

if (($# > 0)); then
  TARGETS=("$@")
else
  TARGETS=(src tests scripts)
fi

echo "Running ruff on: ${TARGETS[*]}"
PYTHONPATH=src python3 -m ruff check "${TARGETS[@]}"
