#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODE="${1:-curated}"

TYPECHECK_GROUPS=(
  "src/rps/agents"
  "src/rps/core/logging.py"
  "src/rps/data_pipeline/intervals_data.py"
  "src/rps/openai"
  "src/rps/orchestrator"
  "src/rps/rendering/renderer.py"
  "src/rps/ui/intervals_refresh.py"
  "src/rps/ui/rps_chatbot.py"
  "src/rps/ui/shared.py"
  "src/rps/ui/pages/athlete_profile/about_you.py"
  "src/rps/ui/pages/athlete_profile/availability.py"
  "src/rps/ui/pages/athlete_profile/events.py"
  "src/rps/ui/pages/athlete_profile/logistics.py"
  "src/rps/ui/pages/coach.py"
  "src/rps/ui/pages/plan/hub.py"
  "src/rps/ui/pages/plan/season.py"
)

run_curated() {
  echo "Running mypy on curated commit gate scope..."
  for target in "${TYPECHECK_GROUPS[@]}"; do
    echo "  - $target"
    PYTHONPATH=src python3 -m mypy "$target"
  done
}

run_full() {
  echo "Running mypy on full repo scope..."
  python3 -m mypy --explicit-package-bases src tests scripts
}

case "$MODE" in
  curated)
    run_curated
    ;;
  --full|full)
    run_full
    ;;
  *)
    echo "Usage: ./scripts/run_typecheck.sh [--full]" >&2
    exit 2
    ;;
esac
