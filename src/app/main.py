"""CLI entry point for running agents."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from app.agents.multi_output_runner import AgentRuntime as MultiRuntime
from app.agents.runner import AgentRuntime, run_agent
from app.agents.registry import AGENTS
from app.core.config import load_app_settings, load_env_file
from app.openai.client import get_client
from app.openai.vectorstore_state import VectorStoreResolver
from app.orchestrator.plan_week import plan_week
from app.prompts.loader import PromptLoader


def main() -> None:
    """Entry point for CLI commands."""
    load_env_file(Path(".env"))
    settings = load_app_settings()
    default_athlete = os.getenv("ATHLETE_ID")

    runtime = AgentRuntime(
        client=get_client(),
        model=settings.openai_model,
        temperature=settings.openai_temperature,
        prompt_loader=PromptLoader(settings.prompts_dir),
        vs_resolver=VectorStoreResolver(settings.vs_state_path),
        shared_vs_name=settings.shared_vs_name,
    )

    if len(sys.argv) > 1 and sys.argv[1] in {"plan-week", "run-agent"}:
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="cmd", required=True)

        plan_parser = subparsers.add_parser("plan-week")
        plan_parser.add_argument("--athlete", default=default_athlete)
        plan_parser.add_argument("--year", type=int, required=True)
        plan_parser.add_argument("--week", type=int, required=True)
        plan_parser.add_argument("--run-id", default="run_plan_week")

        run_parser = subparsers.add_parser("run-agent")
        run_parser.add_argument("--agent", required=True, choices=AGENTS.keys())
        run_parser.add_argument("--athlete", default=default_athlete)
        run_parser.add_argument("--text", required=True)
        run_parser.add_argument("--debug-file-search", action="store_true")
        run_parser.add_argument("--no-file-search", action="store_true")

        args = parser.parse_args()

        if not args.athlete:
            raise SystemExit("Missing athlete id. Set ATHLETE_ID in .env or pass --athlete.")

        if args.cmd == "plan-week":
            multi_runtime = MultiRuntime(
                client=runtime.client,
                model=runtime.model,
                temperature=runtime.temperature,
                prompt_loader=runtime.prompt_loader,
                vs_resolver=runtime.vs_resolver,
                shared_vs_name=runtime.shared_vs_name,
                schema_dir=settings.schema_dir,
                workspace_root=settings.workspace_root,
            )
            result = plan_week(
                multi_runtime,
                athlete_id=args.athlete,
                year=args.year,
                week=args.week,
                run_id=args.run_id,
                model_resolver=settings.model_for_agent,
                temperature_resolver=settings.temperature_for_agent,
                force_file_search=not args.no_file_search,
            )
            print({"ok": result.ok, "steps": result.steps})
            return

        spec = AGENTS[args.agent]
        output = run_agent(
            runtime,
            agent_name=spec.name,
            agent_vs_name=spec.vector_store_name,
            athlete_id=args.athlete,
            user_input=args.text,
            workspace_root=settings.workspace_root,
            schema_dir=settings.schema_dir,
            model_override=settings.model_for_agent(spec.name),
            temperature_override=settings.temperature_for_agent(spec.name),
            include_debug_file_search=args.debug_file_search,
            force_file_search=not args.no_file_search,
        )
        print(output)
        return

    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", required=True, choices=AGENTS.keys())
    parser.add_argument("--athlete", default=default_athlete)
    parser.add_argument("--text", required=True)
    parser.add_argument("--debug-file-search", action="store_true")
    parser.add_argument("--no-file-search", action="store_true")
    args = parser.parse_args()

    if not args.athlete:
        raise SystemExit("Missing athlete id. Set ATHLETE_ID in .env or pass --athlete.")

    spec = AGENTS[args.agent]

    output = run_agent(
        runtime,
        agent_name=spec.name,
        agent_vs_name=spec.vector_store_name,
        athlete_id=args.athlete,
        user_input=args.text,
        workspace_root=settings.workspace_root,
        schema_dir=settings.schema_dir,
        model_override=settings.model_for_agent(spec.name),
        temperature_override=settings.temperature_for_agent(spec.name),
        include_debug_file_search=args.debug_file_search,
        force_file_search=not args.no_file_search,
    )
    print(output)


if __name__ == "__main__":
    main()
