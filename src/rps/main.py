"""CLI entry point for running agents."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
import logging
import os
from pathlib import Path
import shutil
import sys
import time
import re

from rps.agents.multi_output_runner import AgentRuntime as MultiRuntime, run_agent_multi_output
from rps.agents.runner import AgentRuntime, run_agent
from rps.agents.registry import AGENTS
from rps.agents.tasks import AgentTask
from rps.core.config import load_app_settings, load_env_file
from rps.core.logging import setup_logging
from rps.data_pipeline.intervals_data import run_pipeline as run_intervals_pipeline
from rps.data_pipeline.season_brief_availability import (
    load_season_brief,
    parse_and_store_availability,
    validate_events_text,
    validate_season_brief_text,
)
from rps.workspace.schema_registry import SchemaRegistry, SchemaValidationError, validate_or_raise
from rps.openai.client import get_client
from rps.openai.vectorstore_state import VectorStoreResolver
from rps.orchestrator.plan_week import plan_week
from rps.prompts.loader import PromptLoader


def _select_kpi_profile(
    inputs_dir: Path,
    selected_name: str | None,
    logger: logging.Logger,
) -> Path | None:
    candidates = sorted(inputs_dir.glob("kpi_profile*.json"))
    if selected_name:
        selected_path = inputs_dir / selected_name
        if selected_path.exists():
            return selected_path
        matches = [path for path in candidates if path.name == selected_name]
        if matches:
            return matches[0]
        raise SystemExit(f"KPI profile not found in inputs: {selected_name}")
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) == 0:
        return None
    logger.error("Multiple KPI profiles in inputs; specify --kpi-profile or KPI_PROFILE_SELECTED.")
    raise SystemExit("Multiple KPI profiles found in inputs; selection required.")


def _find_first(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def _parse_iso_datetime(value: str) -> datetime | None:
    """Parse ISO datetime with optional Z suffix."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _parse_date_label(text: str, label: str) -> date | None:
    """Parse a YYYY-MM-DD date following a label like 'Valid-From:'."""
    pattern = rf"{re.escape(label)}\s*:\s*(\d{{4}}-\d{{2}}-\d{{2}})"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None


def _iso_week_str_from_date(day: date) -> str:
    year, week, _ = day.isocalendar()
    return f"{year:04d}-{week:02d}"


def _normalize_kpi_profile_payload(
    payload: dict,
    *,
    season_text: str,
    year: int | None,
    week: int | None,
    logger: logging.Logger,
) -> dict:
    """Leniently normalize KPI profile payload to satisfy strict schemas."""
    meta = payload.setdefault("meta", {})
    data = payload.setdefault("data", {})

    # --- Derive temporal anchors from Season Brief when possible ---
    valid_from = _parse_date_label(season_text, "Valid-From")
    valid_to = _parse_date_label(season_text, "Valid-To")
    season_year = year or (valid_from.year if valid_from else None) or datetime.now(timezone.utc).year
    if valid_from is None:
        valid_from = date(season_year, 1, 1)
    if valid_to is None:
        valid_to = date(season_year, 12, 31)

    iso_start = _iso_week_str_from_date(valid_from)
    iso_end = _iso_week_str_from_date(valid_to)
    iso_week = f"{season_year:04d}-{week:02d}" if week else iso_start

    # --- Meta defaults required by artefact_meta + KPI schema overlay ---
    meta.setdefault("artifact_type", "KPI_PROFILE")
    meta.setdefault("schema_id", "KPIProfileInterface")
    meta.setdefault("schema_version", "1.0")
    meta.setdefault("version", "1.0")
    meta.setdefault("authority", "Binding")
    meta.setdefault("owner_agent", "Policy-Owner")
    meta.setdefault("run_id", f"kpi_profile_{season_year}")
    meta.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    meta.setdefault("scope", "Shared")
    meta.setdefault("iso_week", iso_week)
    meta.setdefault("iso_week_range", f"{iso_start}--{iso_end}")
    meta.setdefault("temporal_scope", {"from": valid_from.isoformat(), "to": valid_to.isoformat()})
    meta.setdefault("trace_data", [])
    meta.setdefault("trace_events", [])
    meta.setdefault("data_confidence", meta.get("data_confidence") or "HIGH")
    meta.setdefault("notes", meta.get("notes") or "Normalized by preflight.")
    trace_upstream = meta.setdefault("trace_upstream", [])
    if isinstance(trace_upstream, list):
        for ref in trace_upstream:
            if isinstance(ref, dict) and not ref.get("run_id"):
                ref["run_id"] = meta["run_id"]

    # --- Data normalization: thresholds need context+notes; kpis need notes ---
    def walk(obj: object, path: list[str] | None = None, parent_key: str | None = None) -> None:
        path = path or []
        if isinstance(obj, dict):
            in_decision_rules = bool(path and path[-1] == "decision_rules")
            if not in_decision_rules and {"green", "yellow", "red"}.issubset(obj.keys()):
                obj.setdefault("context", "")
                obj.setdefault("notes", "")
            for key, value in obj.items():
                walk(value, path + [key], key)
        elif isinstance(obj, list):
            for item in obj:
                if parent_key == "kpis" and isinstance(item, dict):
                    item.setdefault("notes", "")
                walk(item, path, parent_key)

    walk(data, [])
    logger.info("KPI profile normalization applied (lenient preflight).")
    return payload


def _preflight(
    athlete_id: str,
    workspace_root: Path,
    schema_dir: Path,
    logger: logging.Logger,
    year: int | None = None,
    week: int | None = None,
    kpi_profile: str | None = None,
    skip_availability: bool = False,
    skip_intervals: bool = False,
    force_intervals: bool = False,
) -> str:
    notes: list[str] = []
    athlete_root = workspace_root / athlete_id
    inputs_dir = athlete_root / "inputs"
    latest_dir = athlete_root / "latest"

    try:
        season_path, season_text = load_season_brief(athlete_root, year, None)
    except FileNotFoundError as exc:
        raise SystemExit("Missing Season Brief. Place season_brief_*.md in inputs/ or latest/.") from exc
    notes.append(f"Season Brief: {season_path.name}")

    events_path = _find_first([inputs_dir / "events.md", latest_dir / "events.md"])
    if not events_path:
        raise SystemExit("Missing events.md. Place events.md in inputs/ or latest/.")
    events_text = events_path.read_text(encoding="utf-8")
    notes.append(f"Events: {events_path.name}")

    season_errors = validate_season_brief_text(season_text, source=season_path.name)
    if season_errors:
        details = "\n".join(f"- {err}" for err in season_errors)
        raise SystemExit(f"Season Brief validation failed:\n{details}")

    events_errors = validate_events_text(events_text, source=events_path.name)
    if events_errors:
        details = "\n".join(f"- {err}" for err in events_errors)
        raise SystemExit(f"Events validation failed:\n{details}")

    selected_env = os.getenv("KPI_PROFILE_SELECTED")
    selected_name = kpi_profile or selected_env
    kpi_path = _select_kpi_profile(inputs_dir, selected_name, logger)
    if not kpi_path:
        raise SystemExit("Missing KPI profile in inputs/. Provide kpi_profile*.json.")
    notes.append(f"KPI profile: {kpi_path.name}")

    try:
        kpi_payload = json.loads(kpi_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"KPI profile JSON invalid: {kpi_path.name} ({exc})") from exc

    # Lenient preflight: normalize missing required meta/notes/context fields.
    kpi_payload = _normalize_kpi_profile_payload(
        kpi_payload,
        season_text=season_text,
        year=year,
        week=week,
        logger=logger,
    )
    validator = SchemaRegistry(schema_dir).validator_for("kpi_profile.schema.json")
    try:
        validate_or_raise(validator, kpi_payload)
    except SchemaValidationError as exc:
        details = "\n".join(f"- {err}" for err in exc.errors)
        raise SystemExit(f"KPI profile schema validation failed:\n{details}") from exc

    latest_dir.mkdir(parents=True, exist_ok=True)
    latest_kpi = latest_dir / "kpi_profile.json"
    latest_payload = json.dumps(kpi_payload, ensure_ascii=False, indent=2) + "\n"
    if not latest_kpi.exists() or latest_kpi.read_text(encoding="utf-8") != latest_payload:
        latest_kpi.write_text(latest_payload, encoding="utf-8")
        logger.info("Wrote normalized KPI profile to latest: %s", latest_kpi)
    named_copy = latest_dir / kpi_path.name
    if not named_copy.exists() or named_copy.read_text(encoding="utf-8") != latest_payload:
        named_copy.write_text(latest_payload, encoding="utf-8")
        logger.info("Wrote normalized KPI profile copy: %s", named_copy.name)
    notes.append("KPI profile normalized and copied to latest/.")

    if not skip_availability:
        latest_availability = latest_dir / "availability.json"
        if latest_availability.exists():
            logger.info("Availability already present: %s", latest_availability)
            notes.append("Availability: already present.")
        else:
            logger.info("Parsing availability from Season Brief.")
            parse_and_store_availability(
                athlete_id=athlete_id,
                workspace_root=workspace_root,
                schema_dir=schema_dir,
                year=year,
                season_brief_path=season_path,
                skip_validate=False,
            )
            notes.append("Availability: parsed from Season Brief.")
    else:
        notes.append("Availability: skipped.")

    if skip_intervals:
        notes.append("Intervals pipeline: skipped.")
        return "\n".join(notes)

    intervals_missing = [
        path
        for path in (
            latest_dir / "zone_model.json",
            latest_dir / "wellness.json",
            latest_dir / "activities_actual.json",
            latest_dir / "activities_trend.json",
        )
        if not path.exists()
    ]
    if intervals_missing:
        logger.info(
            "Intervals pipeline required (missing: %s).",
            ", ".join(path.name for path in intervals_missing),
        )
        args = argparse.Namespace(
            year=None,
            week=None,
            from_date=None,
            to_date=None,
            athlete=athlete_id,
            skip_validate=False,
        )
        run_intervals_pipeline(args, logger=logging.getLogger("rps.preflight.intervals"))
        notes.append(
            "Intervals pipeline: ran (missing: "
            + ", ".join(path.name for path in intervals_missing)
            + ")."
        )
        return "\n".join(notes)

    latest_trend = latest_dir / "activities_trend.json"
    if latest_trend.exists() and not force_intervals:
        try:
            meta = json.loads(latest_trend.read_text(encoding="utf-8")).get("meta", {})
            created_at = _parse_iso_datetime(meta.get("created_at"))
        except json.JSONDecodeError:
            created_at = None
        if created_at:
            age = datetime.now(timezone.utc) - created_at
            if age.total_seconds() < 2 * 60 * 60:
                logger.info("Intervals data is fresh (age=%s). Skipping fetch.", age)
                notes.append(f"Intervals pipeline: fresh data (age={age}).")
                return "\n".join(notes)

    if force_intervals:
        logger.info("Forcing Intervals pipeline refresh.")
    else:
        logger.info("Intervals data stale or missing freshness metadata. Refreshing.")

    args = argparse.Namespace(
        year=None,
        week=None,
        from_date=None,
        to_date=None,
        athlete=athlete_id,
        skip_validate=False,
    )
    run_intervals_pipeline(args, logger=logging.getLogger("rps.preflight.intervals"))
    notes.append("Intervals pipeline: refreshed.")
    return "\n".join(notes)


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

    def _build_runtime() -> tuple[AgentRuntime, callable, callable]:
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

        return base_runtime, runtime_for_agent, multi_runtime_for_agent

    if len(sys.argv) > 1 and sys.argv[1] in {
        "plan-week",
        "run-agent",
        "run-task",
        "preflight",
        "parse-availability",
        "parse-intervals",
    }:
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="cmd", required=True)

        preflight_parser = subparsers.add_parser("preflight")
        preflight_parser.add_argument("--athlete", default=default_athlete)
        preflight_parser.add_argument("--year", type=int)
        preflight_parser.add_argument("--kpi-profile", help="KPI profile filename in inputs/.")
        preflight_parser.add_argument("--skip-availability", action="store_true")
        preflight_parser.add_argument("--skip-intervals", action="store_true")
        preflight_parser.add_argument("--force-intervals", action="store_true")
        add_logging_args(preflight_parser)

        availability_parser = subparsers.add_parser("parse-availability")
        availability_parser.add_argument("--athlete", default=default_athlete)
        availability_parser.add_argument("--year", type=int)
        availability_parser.add_argument("--season-brief-path", type=Path)
        availability_parser.add_argument("--skip-validate", action="store_true")
        add_logging_args(availability_parser)

        intervals_parser = subparsers.add_parser("parse-intervals")
        intervals_parser.add_argument("--year", type=int, help="ISO year for the week, e.g. 2025")
        intervals_parser.add_argument("--week", type=int, help="ISO calendar week, e.g. 43")
        intervals_parser.add_argument("--from", dest="from_date", type=str, help="Start date YYYY-MM-DD")
        intervals_parser.add_argument("--to", dest="to_date", type=str, help="End date YYYY-MM-DD")
        intervals_parser.add_argument("--athlete", default=default_athlete)
        intervals_parser.add_argument(
            "--skip-validate",
            action="store_true",
            help="Skip JSON schema validation in compile steps",
        )
        add_logging_args(intervals_parser)

        plan_parser = subparsers.add_parser("plan-week")
        plan_parser.add_argument("--athlete", default=default_athlete)
        plan_parser.add_argument("--year", type=int, required=True)
        plan_parser.add_argument("--week", type=int, required=True)
        plan_parser.add_argument("--run-id", default="run_plan_week")
        plan_parser.add_argument("--no-file-search", action="store_true")
        plan_parser.add_argument("--no-preflight", action="store_true")
        plan_parser.add_argument("--kpi-profile", help="KPI profile filename in inputs/.")
        plan_parser.add_argument("--skip-intervals", action="store_true")
        plan_parser.add_argument("--force-intervals", action="store_true")
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
        run_parser.add_argument("--no-preflight", action="store_true")
        run_parser.add_argument("--kpi-profile", help="KPI profile filename in inputs/.")
        run_parser.add_argument("--skip-intervals", action="store_true")
        run_parser.add_argument("--force-intervals", action="store_true")
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
        task_parser.add_argument("--no-preflight", action="store_true")
        task_parser.add_argument("--kpi-profile", help="KPI profile filename in inputs/.")
        task_parser.add_argument("--skip-intervals", action="store_true")
        task_parser.add_argument("--force-intervals", action="store_true")
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
                "parse-intervals": f"parse_intervals_{timestamp}.log",
                "parse-availability": f"parse_availability_{timestamp}.log",
            }.get(args.cmd, f"app_{timestamp}.log")
            args.log_file = str(settings.workspace_root / args.athlete / "logs" / log_filename)

        setup_logging(args.log_level, args.log_file, log_stdout=args.log_stdout)
        logger = logging.getLogger("rps.preflight")

        if args.cmd == "parse-availability":
            result = parse_and_store_availability(
                athlete_id=args.athlete,
                workspace_root=settings.workspace_root,
                schema_dir=settings.schema_dir,
                year=args.year,
                season_brief_path=args.season_brief_path,
                skip_validate=args.skip_validate,
            )
            print({"ok": True, "path": str(result.output_path)})
            return

        if args.cmd == "preflight":
            _preflight(
                athlete_id=args.athlete,
                workspace_root=settings.workspace_root,
                schema_dir=settings.schema_dir,
                logger=logger,
                year=args.year,
                kpi_profile=args.kpi_profile,
                skip_availability=args.skip_availability,
                skip_intervals=args.skip_intervals,
                force_intervals=args.force_intervals,
            )
            print({"ok": True})
            return

        if args.cmd == "parse-intervals":
            run_intervals_pipeline(args, logger=logging.getLogger("rps.parse-intervals"))
            print({"ok": True})
            return

        _, runtime_for_agent, multi_runtime_for_agent = _build_runtime()

        if args.cmd == "plan-week":
            if not args.no_preflight:
                _preflight(
                    athlete_id=args.athlete,
                    workspace_root=settings.workspace_root,
                    schema_dir=settings.schema_dir,
                    logger=logger,
                    year=args.year,
                week=args.week,
                kpi_profile=args.kpi_profile,
                skip_intervals=args.skip_intervals,
                force_intervals=args.force_intervals,
            )
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
            if not args.no_preflight:
                _preflight(
                    athlete_id=args.athlete,
                    workspace_root=settings.workspace_root,
                    schema_dir=settings.schema_dir,
                    logger=logger,
                    year=getattr(args, "year", None),
                    kpi_profile=args.kpi_profile,
                    skip_intervals=args.skip_intervals,
                    force_intervals=args.force_intervals,
                )
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
            if not args.no_preflight:
                _preflight(
                    athlete_id=args.athlete,
                    workspace_root=settings.workspace_root,
                    schema_dir=settings.schema_dir,
                    logger=logger,
                    year=getattr(args, "year", None),
                    kpi_profile=args.kpi_profile,
                    skip_intervals=args.skip_intervals,
                    force_intervals=args.force_intervals,
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

        if not args.no_preflight:
            _preflight(
                athlete_id=args.athlete,
                workspace_root=settings.workspace_root,
                schema_dir=settings.schema_dir,
                logger=logger,
                year=getattr(args, "year", None),
                kpi_profile=args.kpi_profile,
                skip_intervals=args.skip_intervals,
                force_intervals=args.force_intervals,
            )
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

    _, runtime_for_agent, multi_runtime_for_agent = _build_runtime()

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
