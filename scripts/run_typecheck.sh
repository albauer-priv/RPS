#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TYPECHECK_TARGETS=(
  "src/rps/agents/knowledge_injection.py"
  "src/rps/agents/multi_output_runner.py"
  "src/rps/orchestrator/plan_week.py"
  "src/rps/orchestrator/season_flow.py"
  "src/rps/orchestrator/week_revision.py"
)

echo "Running mypy on curated commit gate scope..."
for target in "${TYPECHECK_TARGETS[@]}"; do
  echo "  - $target"
  PYTHONPATH=src python3 -m mypy "$target"
done
