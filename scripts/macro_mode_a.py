#!/usr/bin/env python3
"""Mode A helper for Macro-Planner: scenarios + macro overview."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SYS_PATH = str(ROOT / "src")
if SYS_PATH not in sys.path:
    # Allow running this script directly without installing the package.
    sys.path.insert(0, SYS_PATH)

from app.agents.multi_output_runner import AgentRuntime, run_agent_multi_output  # noqa: E402
from app.agents.registry import AGENTS  # noqa: E402
from app.agents.tasks import AgentTask  # noqa: E402
from app.core.config import load_app_settings, load_env_file  # noqa: E402
from app.openai.client import get_client  # noqa: E402
from app.openai.vectorstore_state import VectorStoreResolver  # noqa: E402
from app.prompts.loader import PromptLoader  # noqa: E402


def _runtime() -> tuple[AgentRuntime, str]:
    load_env_file(ROOT / ".env")
    settings = load_app_settings()
    runtime = AgentRuntime(
        client=get_client(),
        model=settings.openai_model,
        prompt_loader=PromptLoader(settings.prompts_dir),
        vs_resolver=VectorStoreResolver(settings.vs_state_path),
        shared_vs_name=settings.shared_vs_name,
        schema_dir=settings.schema_dir,
        workspace_root=settings.workspace_root,
    )
    return runtime, settings.openai_model


def _default_athlete() -> str | None:
    load_env_file(ROOT / ".env")
    from os import getenv

    return getenv("ATHLETE_ID")


def run_scenarios(args: argparse.Namespace) -> int:
    runtime, _ = _runtime()
    spec = AGENTS["macro_planner"]
    user_input = (
        "Mode A. Generate the pre-decision scenarios. "
        "Use workspace_get_input to load season_brief. "
        f"Target ISO week: {args.year}-{args.week:02d}."
    )

    result = run_agent_multi_output(
        runtime,
        agent_name=spec.name,
        agent_vs_name=spec.vector_store_name,
        athlete_id=args.athlete,
        tasks=[],
        user_input=user_input,
        run_id=args.run_id,
        model_override=args.model,
        force_file_search=not args.no_file_search,
        max_num_results=args.max_num_results,
    )

    text = result.get("final_text") or ""
    if args.out:
        out_path = Path(args.out)
    else:
        out_dir = ROOT / ".cache" / "macro_scenarios"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{args.run_id}.md"
    if text:
        out_path.write_text(text, encoding="utf-8")
        print(text)
        print(f"[saved] {out_path}")
    else:
        print(result)
    return 0


def run_overview(args: argparse.Namespace) -> int:
    runtime, _ = _runtime()
    spec = AGENTS["macro_planner"]

    scenario = args.scenario.upper()
    if scenario not in {"A", "B", "C"}:
        raise SystemExit("Scenario must be A, B, or C.")

    trace_line = ""
    if args.scenario_run_id:
        trace_line = (
            f"Set meta.trace_upstream to include '{args.scenario_run_id}'. "
        )

    events_line = ""
    if args.allow_missing_events:
        events_line = "If events input is missing, set events_constraints to an empty array and proceed. "

    user_input = (
        f"Scenario {scenario}. Mode A. Output the MACRO_OVERVIEW JSON now. "
        "Set meta.schema_id exactly to MacroOverviewInterface, "
        "meta.schema_version to 1.0, authority to Binding, owner_agent to Macro-Planner. "
        "Use workspace_get_input for season brief. "
        "Use workspace_get_latest with artifact_type KPI_PROFILE (not a filename). "
        f"{events_line}"
        f"{trace_line}"
        "Call store_macro_overview with schema-compliant JSON only."
    )

    result = run_agent_multi_output(
        runtime,
        agent_name=spec.name,
        agent_vs_name=spec.vector_store_name,
        athlete_id=args.athlete,
        tasks=[AgentTask.CREATE_MACRO_OVERVIEW],
        user_input=user_input,
        run_id=args.run_id,
        model_override=args.model,
        force_file_search=not args.no_file_search,
        max_num_results=args.max_num_results,
    )
    print(result)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    base = argparse.ArgumentParser(add_help=False)
    base.add_argument("--athlete", default=_default_athlete())
    base.add_argument("--year", type=int, required=True)
    base.add_argument("--week", type=int, required=True)
    base.add_argument("--run-id", required=True)
    base.add_argument("--model")
    base.add_argument("--max-num-results", type=int, default=1)
    base.add_argument("--no-file-search", action="store_true")

    scen = subparsers.add_parser("scenarios", parents=[base])
    scen.add_argument("--out", help="Optional path to write the scenario output.")
    scen.set_defaults(func=run_scenarios)

    overview = subparsers.add_parser("overview", parents=[base])
    overview.add_argument("--scenario", required=True, help="A, B, or C.")
    overview.add_argument("--scenario-run-id", help="Optional run id from scenarios step.")
    overview.add_argument("--allow-missing-events", action="store_true")
    overview.set_defaults(func=run_overview)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.athlete:
        raise SystemExit("Missing athlete id. Set ATHLETE_ID in .env or pass --athlete.")

    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
