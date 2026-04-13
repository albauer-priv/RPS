#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TYPECHECK_TARGETS=(
  "src/rps/agents/knowledge_injection.py"
  "src/rps/agents/multi_output_runner.py"
  "src/rps/agents/runner.py"
  "src/rps/core/logging.py"
  "src/rps/openai/litellm_runtime.py"
  "src/rps/openai/runtime.py"
  "src/rps/openai/streaming.py"
  "src/rps/openai/vectorstores.py"
  "src/rps/orchestrator/plan_week.py"
  "src/rps/orchestrator/season_flow.py"
  "src/rps/orchestrator/week_revision.py"
  "src/rps/rendering/renderer.py"
  "src/rps/ui/intervals_refresh.py"
  "src/rps/ui/pages/athlete_profile/about_you.py"
  "src/rps/ui/pages/athlete_profile/availability.py"
  "src/rps/ui/pages/athlete_profile/events.py"
  "src/rps/ui/pages/athlete_profile/logistics.py"
  "src/rps/ui/pages/plan/season.py"
)

echo "Running mypy on curated commit gate scope..."
for target in "${TYPECHECK_TARGETS[@]}"; do
  echo "  - $target"
  PYTHONPATH=src python3 -m mypy "$target"
done
