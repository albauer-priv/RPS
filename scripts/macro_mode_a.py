#!/usr/bin/env python3
"""Mode A helper for Macro planning: scenarios, selection, and season plan."""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    # Allow running the script directly without installing the package.
    sys.path.insert(0, str(ROOT))

from rps.agents.multi_output_runner import AgentRuntime, run_agent_multi_output  # noqa: E402
from rps.agents.registry import AGENTS  # noqa: E402
from rps.agents.tasks import AgentTask  # noqa: E402
from rps.core.config import load_app_settings, load_env_file  # noqa: E402
from rps.openai.client import get_client  # noqa: E402
from rps.openai.vectorstore_state import VectorStoreResolver  # noqa: E402
from rps.orchestrator.plan_week import _build_injection_block  # noqa: E402
from rps.prompts.loader import PromptLoader  # noqa: E402
from rps.workspace.local_store import LocalArtifactStore  # noqa: E402
from rps.workspace.types import ArtifactType  # noqa: E402
from scripts.script_logging import configure_logging  # noqa: E402

@dataclass(frozen=True)
class ScriptConfig:
    athlete_id: str
    year: int
    week: int
    run_id_prefix: str


def _default_athlete() -> str | None:
    load_env_file(ROOT / ".env")
    from os import getenv

    return getenv("ATHLETE_ID")


def _runtime() -> tuple[AgentRuntime, object]:
    load_env_file(ROOT / ".env")
    settings = load_app_settings()
    runtime = AgentRuntime(
        client=get_client(),
        model=settings.openai_model,
        temperature=settings.openai_temperature,
        reasoning_effort=settings.openai_reasoning_effort,
        reasoning_summary=settings.openai_reasoning_summary,
        prompt_loader=PromptLoader(settings.prompts_dir),
        vs_resolver=VectorStoreResolver(settings.vs_state_path),
        schema_dir=settings.schema_dir,
        workspace_root=settings.workspace_root,
    )
    return runtime, settings


def _make_run_id(prefix: str, suffix: str) -> str:
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return f"{prefix}_{suffix}_{stamp}"


def _ensure_selection_exists(store: LocalArtifactStore, athlete_id: str) -> None:
    if not store.latest_exists(athlete_id, ArtifactType.SEASON_SCENARIO_SELECTION):
        raise SystemExit("No SEASON_SCENARIO_SELECTION found. Run --select first.")


def _run_scenarios(cfg: ScriptConfig, runtime: AgentRuntime, settings: object) -> None:
    spec = AGENTS["season_scenario"]
    injected_block = _build_injection_block("season_scenario", mode="scenario")
    user_input = (
        "Mode A. Generate the pre-decision scenarios. "
        f"Target ISO week: {cfg.year}-{cfg.week:02d}. "
        "Use workspace_get_input for Season Brief and Events. "
        f"{injected_block}"
        "Follow the Mandatory Output Chapter for SEASON_SCENARIOS."
    )
    run_id = _make_run_id(cfg.run_id_prefix, f"season_scenarios_{cfg.year}_{cfg.week:02d}")
    run_agent_multi_output(
        runtime,
        agent_name=spec.name,
        agent_vs_name=spec.vector_store_name,
        athlete_id=cfg.athlete_id,
        tasks=[AgentTask.CREATE_SEASON_SCENARIOS],
        user_input=user_input,
        run_id=run_id,
        model_override=settings.model_for_agent(spec.name),
        temperature_override=settings.temperature_for_agent(spec.name),
        force_file_search=True,
        max_num_results=settings.file_search_max_results,
    )


def _run_selection(
    cfg: ScriptConfig,
    runtime: AgentRuntime,
    settings: object,
    selected: str,
    rationale: str | None,
) -> None:
    spec = AGENTS["season_scenario"]
    injected_block = _build_injection_block("season_scenario", mode="scenario")
    rationale_line = f"Rationale: {rationale.strip()}. " if rationale else ""
    user_input = (
        f"Select Scenario {selected.upper()} for ISO week {cfg.year}-{cfg.week:02d}. "
        "Use the latest SEASON_SCENARIOS as context. "
        f"{rationale_line}"
        f"{injected_block}"
        "Follow the Mandatory Output Chapter for SEASON_SCENARIO_SELECTION."
    )
    run_id = _make_run_id(cfg.run_id_prefix, f"season_scenario_selection_{cfg.year}_{cfg.week:02d}")
    run_agent_multi_output(
        runtime,
        agent_name=spec.name,
        agent_vs_name=spec.vector_store_name,
        athlete_id=cfg.athlete_id,
        tasks=[AgentTask.CREATE_SEASON_SCENARIO_SELECTION],
        user_input=user_input,
        run_id=run_id,
        model_override=settings.model_for_agent(spec.name),
        temperature_override=settings.temperature_for_agent(spec.name),
        force_file_search=True,
        max_num_results=settings.file_search_max_results,
    )


def _run_season_plan(cfg: ScriptConfig, runtime: AgentRuntime, settings: object) -> None:
    spec = AGENTS["season_planner"]
    injected_block = _build_injection_block("season_planner", mode="season")
    user_input = (
        "Mode A. Create SEASON_PLAN for the selected scenario. "
        f"Target ISO week: {cfg.year}-{cfg.week:02d}. "
        "Use the latest SEASON_SCENARIO_SELECTION as input. "
        "Use workspace_get_input for Season Brief and Events. "
        f"{injected_block}"
        "Follow the Mandatory Output Chapter for SEASON_PLAN."
    )
    run_id = _make_run_id(cfg.run_id_prefix, f"season_plan_{cfg.year}_{cfg.week:02d}")
    run_agent_multi_output(
        runtime,
        agent_name=spec.name,
        agent_vs_name=spec.vector_store_name,
        athlete_id=cfg.athlete_id,
        tasks=[AgentTask.CREATE_SEASON_PLAN],
        user_input=user_input,
        run_id=run_id,
        model_override=settings.model_for_agent(spec.name),
        temperature_override=settings.temperature_for_agent(spec.name),
        force_file_search=True,
        max_num_results=settings.file_search_max_results,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mode A helper for Macro planning: scenarios + selection + season plan."
    )
    parser.add_argument("--athlete", default=_default_athlete())
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--week", type=int, required=True)
    parser.add_argument("--run-id-prefix", default="macro_mode_a")
    parser.add_argument("--scenarios", action="store_true", help="Generate season scenarios.")
    parser.add_argument("--select", help="Select scenario id (A/B/C).")
    parser.add_argument("--rationale", help="Optional rationale for selection.")
    parser.add_argument("--season-plan", action="store_true", help="Create season plan.")
    parser.add_argument("--all", action="store_true", help="Run scenarios, selection, and season plan.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.athlete:
        raise SystemExit("Missing athlete id. Set ATHLETE_ID in .env or pass --athlete.")

    if not any([args.scenarios, args.select, args.season_plan, args.all]):
        raise SystemExit("Select at least one action: --scenarios, --select, --season-plan, or --all.")

    logger = configure_logging(ROOT, Path(__file__).stem)
    runtime, settings = _runtime()
    cfg = ScriptConfig(
        athlete_id=args.athlete,
        year=args.year,
        week=args.week,
        run_id_prefix=args.run_id_prefix,
    )
    store = LocalArtifactStore(root=settings.workspace_root)

    if args.all or args.scenarios:
        logger.info("Running season scenarios (Mode A).")
        _run_scenarios(cfg, runtime, settings)

    if args.all or args.select:
        if not args.select:
            raise SystemExit("--select is required for scenario selection.")
        logger.info("Selecting scenario %s.", args.select)
        _run_selection(cfg, runtime, settings, args.select, args.rationale)

    if args.all or args.season_plan:
        _ensure_selection_exists(store, cfg.athlete_id)
        logger.info("Creating season plan (Mode A).")
        _run_season_plan(cfg, runtime, settings)

    logger.info("Macro Mode A flow complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
