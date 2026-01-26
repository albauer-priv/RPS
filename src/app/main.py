"""CLI entry point for running agents."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import sys
import time

from app.agents.multi_output_runner import AgentRuntime as MultiRuntime, run_agent_multi_output
from app.agents.runner import AgentRuntime, run_agent
from app.agents.registry import AGENTS
from app.agents.tasks import AgentTask
from app.core.config import load_app_settings, load_env_file
from app.core.logging import setup_logging
from app.openai.client import get_client
from app.openai.vectorstore_state import VectorStoreResolver
from app.orchestrator.plan_week import plan_week
from app.prompts.loader import PromptLoader


def main() -> None:
    """Entry point for CLI commands."""
    load_env_file(Path(".env"))
    settings = load_app_settings()
    default_athlete = os.getenv("ATHLETE_ID")
    default_log_level = os.getenv("APP_LOG_LEVEL", "INFO")
    default_log_file = os.getenv("APP_LOG_FILE")
    default_max_results = settings.file_search_max_results

    strict_only_agents = {
        "season_scenario",
        "macro_planner",
        "meso_architect",
        "micro_planner",
        "workout_builder",
        "performance_analysis",
    }

    def add_logging_args(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--log-level", default=default_log_level)
        parser.add_argument("--log-file", default=default_log_file)
        parser.add_argument(
            "--log-stdout",
            action="store_true",
            help="Mirror logs to stdout (in addition to log file).",
        )

    base_runtime = AgentRuntime(
        client=get_client(),
        model=settings.openai_model,
        temperature=settings.openai_temperature,
        reasoning_effort=settings.openai_reasoning_effort,
        reasoning_summary=settings.openai_reasoning_summary,
        prompt_loader=PromptLoader(settings.prompts_dir),
        vs_resolver=VectorStoreResolver(settings.vs_state_path),
    )

    def runtime_for_agent(agent_name: str) -> AgentRuntime:
        return AgentRuntime(
            client=base_runtime.client,
            model=base_runtime.model,
            temperature=base_runtime.temperature,
            reasoning_effort=settings.reasoning_effort_for_agent(agent_name),
            reasoning_summary=settings.reasoning_summary_for_agent(agent_name),
            prompt_loader=base_runtime.prompt_loader,
            vs_resolver=base_runtime.vs_resolver,
        )

    def multi_runtime_for_agent(agent_name: str) -> MultiRuntime:
        return MultiRuntime(
            client=base_runtime.client,
            model=base_runtime.model,
            temperature=base_runtime.temperature,
            reasoning_effort=settings.reasoning_effort_for_agent(agent_name),
            reasoning_summary=settings.reasoning_summary_for_agent(agent_name),
            prompt_loader=base_runtime.prompt_loader,
            vs_resolver=base_runtime.vs_resolver,
            schema_dir=settings.schema_dir,
            workspace_root=settings.workspace_root,
        )

    if len(sys.argv) > 1 and sys.argv[1] in {"plan-week", "run-agent", "run-task"}:
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="cmd", required=True)

        plan_parser = subparsers.add_parser("plan-week")
        plan_parser.add_argument("--athlete", default=default_athlete)
        plan_parser.add_argument("--year", type=int, required=True)
        plan_parser.add_argument("--week", type=int, required=True)
        plan_parser.add_argument("--run-id", default="run_plan_week")
        plan_parser.add_argument("--no-file-search", action="store_true")
        add_logging_args(plan_parser)

        run_parser = subparsers.add_parser("run-agent")
        run_parser.add_argument("--agent", required=True, choices=AGENTS.keys())
        run_parser.add_argument("--athlete", default=default_athlete)
        run_parser.add_argument("--text", required=True)
        run_parser.add_argument("--debug-file-search", action="store_true")
        run_parser.add_argument("--no-file-search", action="store_true")
        run_parser.add_argument("--task", nargs="+", choices=[task.value for task in AgentTask])
        run_parser.add_argument("--run-id")
        run_parser.add_argument("--max-results", type=int, default=default_max_results)
        run_parser.add_argument("--strict", action="store_true")
        run_parser.add_argument("--non-strict", action="store_true")
        add_logging_args(run_parser)

        task_parser = subparsers.add_parser("run-task")
        task_parser.add_argument("--agent", required=True, choices=AGENTS.keys())
        task_parser.add_argument("--athlete", default=default_athlete)
        task_parser.add_argument("--text", required=True)
        task_parser.add_argument(
            "--task",
            required=True,
            nargs="+",
            choices=[task.value for task in AgentTask],
        )
        task_parser.add_argument("--run-id", default="run_task")
        task_parser.add_argument("--debug-file-search", action="store_true")
        task_parser.add_argument("--no-file-search", action="store_true")
        task_parser.add_argument("--max-results", type=int, default=default_max_results)
        add_logging_args(task_parser)

        args = parser.parse_args()

        if not args.athlete:
            raise SystemExit("Missing athlete id. Set ATHLETE_ID in .env or pass --athlete.")

        if not args.log_file:
            timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
            log_filename = {
                "plan-week": f"plan_week_{timestamp}.log",
                "run-agent": f"agent_run_{timestamp}.log",
                "run-task": f"task_run_{timestamp}.log",
            }.get(args.cmd, f"app_{timestamp}.log")
            args.log_file = str(settings.workspace_root / args.athlete / "logs" / log_filename)

        setup_logging(args.log_level, args.log_file, log_stdout=args.log_stdout)

        if args.cmd == "plan-week":
            result = plan_week(
                multi_runtime_for_agent("macro_planner"),
                athlete_id=args.athlete,
                year=args.year,
                week=args.week,
                run_id=args.run_id,
                model_resolver=settings.model_for_agent,
                temperature_resolver=settings.temperature_for_agent,
                reasoning_effort_resolver=settings.reasoning_effort_for_agent,
                reasoning_summary_resolver=settings.reasoning_summary_for_agent,
                force_file_search=not args.no_file_search,
                max_num_results=settings.file_search_max_results,
            )
            print({"ok": result.ok, "steps": result.steps})
            return

        if args.cmd == "run-task":
            tasks = [AgentTask(value) for value in args.task]
            spec = AGENTS[args.agent]
            result = run_agent_multi_output(
                multi_runtime_for_agent(spec.name),
                agent_name=spec.name,
                agent_vs_name=spec.vector_store_name,
                athlete_id=args.athlete,
                tasks=tasks,
                user_input=args.text,
                run_id=args.run_id,
                model_override=settings.model_for_agent(spec.name),
                temperature_override=settings.temperature_for_agent(spec.name),
                include_debug_file_search=args.debug_file_search,
                force_file_search=not args.no_file_search,
                max_num_results=args.max_results,
            )
            print(result)
            return

        spec = AGENTS[args.agent]
        strict = args.strict or bool(args.task)
        if args.non_strict:
            strict = False
        elif not args.strict and not args.non_strict and args.agent in strict_only_agents:
            strict = True

        if strict:
            if not args.task:
                raise SystemExit(
                    "Strict mode requires --task. "
                    "Use run-task or pass --non-strict for non-JSON outputs."
                )
            run_id = args.run_id or f"{args.agent}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
            tasks = [AgentTask(value) for value in args.task]
            result = run_agent_multi_output(
                multi_runtime_for_agent(spec.name),
                agent_name=spec.name,
                agent_vs_name=spec.vector_store_name,
                athlete_id=args.athlete,
                tasks=tasks,
                user_input=args.text,
                run_id=run_id,
                model_override=settings.model_for_agent(spec.name),
                temperature_override=settings.temperature_for_agent(spec.name),
                include_debug_file_search=args.debug_file_search,
                force_file_search=not args.no_file_search,
                max_num_results=args.max_results,
            )
            print(result)
            return

        output = run_agent(
            runtime_for_agent(spec.name),
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
            max_num_results=args.max_results,
            run_id=args.run_id,
        )
        print(output)
        return

    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", required=True, choices=AGENTS.keys())
    parser.add_argument("--athlete", default=default_athlete)
    parser.add_argument("--text", required=True)
    parser.add_argument("--debug-file-search", action="store_true")
    parser.add_argument("--no-file-search", action="store_true")
    parser.add_argument("--task", nargs="+", choices=[task.value for task in AgentTask])
    parser.add_argument("--run-id")
    parser.add_argument("--max-results", type=int, default=default_max_results)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--non-strict", action="store_true")
    add_logging_args(parser)
    args = parser.parse_args()
    setup_logging(args.log_level, args.log_file, log_stdout=args.log_stdout)

    if not args.athlete:
        raise SystemExit("Missing athlete id. Set ATHLETE_ID in .env or pass --athlete.")

    spec = AGENTS[args.agent]

    strict = args.strict or bool(args.task)
    if args.non_strict:
        strict = False
    elif not args.strict and not args.non_strict and args.agent in strict_only_agents:
        strict = True

    if strict:
        if not args.task:
            raise SystemExit(
                "Strict mode requires --task. "
                "Use run-task or pass --non-strict for non-JSON outputs."
            )
        run_id = args.run_id or f"{args.agent}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        tasks = [AgentTask(value) for value in args.task]
        result = run_agent_multi_output(
            multi_runtime_for_agent(spec.name),
            agent_name=spec.name,
            agent_vs_name=spec.vector_store_name,
            athlete_id=args.athlete,
            tasks=tasks,
            user_input=args.text,
            run_id=run_id,
            model_override=settings.model_for_agent(spec.name),
            temperature_override=settings.temperature_for_agent(spec.name),
            include_debug_file_search=args.debug_file_search,
            force_file_search=not args.no_file_search,
            max_num_results=args.max_results,
        )
        print(result)
        return

    output = run_agent(
        runtime_for_agent(spec.name),
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
        max_num_results=args.max_results,
        run_id=args.run_id,
    )
    print(output)


if __name__ == "__main__":
    main()
