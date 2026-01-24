#!/usr/bin/env python3
"""Mode A helper for Macro-Planner: scenarios + macro overview."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SYS_PATH = str(ROOT / "src")
if SYS_PATH not in sys.path:
    # Allow running this script directly without installing the package.
    sys.path.insert(0, SYS_PATH)

from app.agents.multi_output_runner import AgentRuntime, run_agent_multi_output  # noqa: E402
from app.agents.registry import AGENTS  # noqa: E402
from app.agents.tasks import AgentTask, OUTPUT_SPECS  # noqa: E402
from app.core.config import AppSettings, load_app_settings, load_env_file  # noqa: E402
from script_logging import configure_logging  # noqa: E402
from app.openai.client import get_client  # noqa: E402
from app.openai.vectorstore_state import VectorStoreResolver  # noqa: E402
from app.prompts.loader import PromptLoader  # noqa: E402
from app.workspace.local_store import LocalArtifactStore  # noqa: E402
from app.workspace.types import ArtifactType  # noqa: E402
from app.workspace.guarded_store import GuardedValidatedStore  # noqa: E402


def _load_season_brief(athlete_root: Path, year: int) -> tuple[str, str]:
    patterns = [f"season_brief_{year}.md", "season_brief_*.md"]
    candidates: list[Path] = []
    for folder in (athlete_root / "inputs", athlete_root / "latest"):
        if not folder.exists():
            continue
        for pattern in patterns:
            candidates.extend(folder.glob(pattern))
    if not candidates:
        raise FileNotFoundError(
            f"No season brief found for {year}. Place season_brief_*.md in inputs/ or latest/."
        )

    def sort_key(path: Path) -> tuple[int, float]:
        match_year = 1 if path.name.startswith(f"season_brief_{year}.") else 0
        return (match_year, path.stat().st_mtime)

    best = max(candidates, key=sort_key)
    return str(best), best.read_text(encoding="utf-8")


def _runtime(agent_name: str | None = None) -> tuple[AgentRuntime, AppSettings]:
    load_env_file(ROOT / ".env")
    settings = load_app_settings()
    reasoning_effort = (
        settings.reasoning_effort_for_agent(agent_name) if agent_name else settings.openai_reasoning_effort
    )
    reasoning_summary = (
        settings.reasoning_summary_for_agent(agent_name) if agent_name else settings.openai_reasoning_summary
    )
    runtime = AgentRuntime(
        client=get_client(),
        model=settings.openai_model,
        temperature=settings.openai_temperature,
        reasoning_effort=reasoning_effort,
        reasoning_summary=reasoning_summary,
        prompt_loader=PromptLoader(settings.prompts_dir),
        vs_resolver=VectorStoreResolver(settings.vs_state_path),
        shared_vs_name=settings.shared_vs_name,
        schema_dir=settings.schema_dir,
        workspace_root=settings.workspace_root,
    )
    return runtime, settings


def _default_athlete() -> str | None:
    load_env_file(ROOT / ".env")
    from os import getenv

    return getenv("ATHLETE_ID")


def _render_scenarios(scenarios_doc: dict) -> str:
    data = scenarios_doc.get("data", {}) if isinstance(scenarios_doc, dict) else {}
    scenarios = data.get("scenarios") or []
    ordered = {"A": None, "B": None, "C": None}
    for item in scenarios:
        if not isinstance(item, dict):
            continue
        scenario_id = str(item.get("scenario_id", "")).strip().upper()
        if scenario_id in ordered:
            ordered[scenario_id] = item

    lines = ["🧭 Macro Planning Scenarios (pre-decision)", ""]
    labels = [
        ("core_idea", "Core idea"),
        ("load_philosophy", "Load philosophy"),
        ("risk_profile", "Risk profile"),
        ("key_differences", "Key differences"),
        ("best_suited_if", "Best suited if"),
    ]
    for scenario_id in ("A", "B", "C"):
        item = ordered.get(scenario_id) or {}
        name = item.get("name") or "Unnamed"
        lines.append(f"Scenario {scenario_id} — {name}")
        for key, label in labels:
            value = item.get(key) or ""
            lines.append(f"- {label}: {value}")
        guidance = item.get("scenario_guidance") or {}
        if guidance:
            cadence = guidance.get("deload_cadence") or ""
            phase_len = guidance.get("phase_length_weeks")
            lines.append(f"- Deload cadence: {cadence}")
            if isinstance(phase_len, int) and phase_len > 0:
                lines.append(f"- Phase length: {phase_len} weeks")
            risk_flags = guidance.get("risk_flags") or []
            if risk_flags:
                lines.append(f"- Risk flags: {', '.join(str(item) for item in risk_flags)}")
            fixed_days = guidance.get("fixed_rest_days") or []
            if fixed_days:
                lines.append(f"- Fixed rest days: {', '.join(str(item) for item in fixed_days)}")
            constraints = guidance.get("constraint_summary") or []
            for note in constraints:
                lines.append(f"- Constraint: {note}")
            kpi_notes = guidance.get("kpi_guardrail_notes") or []
            for note in kpi_notes:
                lines.append(f"- KPI guardrails: {note}")
            decision_notes = guidance.get("decision_notes") or []
            for note in decision_notes:
                lines.append(f"- Decision note: {note}")
            intensity = guidance.get("intensity_guidance") or {}
            allowed = intensity.get("allowed_domains") or []
            avoid = intensity.get("avoid_domains") or []
            if allowed:
                lines.append(f"- Intensity focus: {', '.join(str(item) for item in allowed)}")
            if avoid:
                lines.append(f"- Intensity avoid: {', '.join(str(item) for item in avoid)}")
            summary = guidance.get("phase_plan_summary") or {}
            if isinstance(summary, dict):
                full_phases = summary.get("full_phases")
                shortened = summary.get("shortened_phases") or []
                if isinstance(full_phases, int):
                    lines.append(f"- Phase plan: {full_phases} full phases")
                if shortened:
                    parts = []
                    for item in shortened:
                        if not isinstance(item, dict):
                            continue
                        length = item.get("len")
                        count = item.get("count")
                        if isinstance(length, int) and isinstance(count, int):
                            parts.append(f"{count}x{length}w")
                    if parts:
                        lines.append(f"- Shortened phases: {', '.join(parts)}")
            notes = guidance.get("event_alignment_notes") or []
            for note in notes:
                lines.append(f"- Event alignment: {note}")
        lines.append("")
    lines.append("These scenarios are equally valid.")
    lines.append("Selection will determine the final MACRO_OVERVIEW.")
    return "\n".join(lines).strip() + "\n"


def _render_selected_scenario(scenarios_doc: dict, scenario_id: str) -> str:
    data = scenarios_doc.get("data", {}) if isinstance(scenarios_doc, dict) else {}
    scenarios = data.get("scenarios") or []
    selected = None
    target = str(scenario_id).strip().upper()
    for item in scenarios:
        if not isinstance(item, dict):
            continue
        if str(item.get("scenario_id", "")).strip().upper() == target:
            selected = item
            break
    if not selected:
        return ""

    lines = [f"Selected scenario details (Scenario {target})", ""]
    labels = [
        ("core_idea", "Core idea"),
        ("load_philosophy", "Load philosophy"),
        ("risk_profile", "Risk profile"),
        ("key_differences", "Key differences"),
        ("best_suited_if", "Best suited if"),
    ]
    name = selected.get("name") or "Unnamed"
    lines.append(f"Scenario {target} — {name}")
    for key, label in labels:
        value = selected.get(key) or ""
        lines.append(f"- {label}: {value}")
    guidance = selected.get("scenario_guidance") or {}
    if guidance:
        cadence = guidance.get("deload_cadence") or ""
        phase_len = guidance.get("phase_length_weeks")
        lines.append(f"- Deload cadence: {cadence}")
        if isinstance(phase_len, int) and phase_len > 0:
            lines.append(f"- Phase length: {phase_len} weeks")
        risk_flags = guidance.get("risk_flags") or []
        if risk_flags:
            lines.append(f"- Risk flags: {', '.join(str(item) for item in risk_flags)}")
        fixed_days = guidance.get("fixed_rest_days") or []
        if fixed_days:
            lines.append(f"- Fixed rest days: {', '.join(str(item) for item in fixed_days)}")
        constraints = guidance.get("constraint_summary") or []
        for note in constraints:
            lines.append(f"- Constraint: {note}")
        kpi_notes = guidance.get("kpi_guardrail_notes") or []
        for note in kpi_notes:
            lines.append(f"- KPI guardrails: {note}")
        decision_notes = guidance.get("decision_notes") or []
        for note in decision_notes:
            lines.append(f"- Decision note: {note}")
        intensity = guidance.get("intensity_guidance") or {}
        allowed = intensity.get("allowed_domains") or []
        avoid = intensity.get("avoid_domains") or []
        if allowed:
            lines.append(f"- Intensity focus: {', '.join(str(item) for item in allowed)}")
        if avoid:
            lines.append(f"- Intensity avoid: {', '.join(str(item) for item in avoid)}")
        summary = guidance.get("phase_plan_summary") or {}
        if isinstance(summary, dict):
            full_phases = summary.get("full_phases")
            shortened = summary.get("shortened_phases") or []
            if isinstance(full_phases, int):
                lines.append(f"- Phase plan: {full_phases} full phases")
            if shortened:
                parts = []
                for item in shortened:
                    if not isinstance(item, dict):
                        continue
                    length = item.get("len")
                    count = item.get("count")
                    if isinstance(length, int) and isinstance(count, int):
                        parts.append(f"{count}x{length}w")
                if parts:
                    lines.append(f"- Shortened phases: {', '.join(parts)}")
        notes = guidance.get("event_alignment_notes") or []
        for note in notes:
            lines.append(f"- Event alignment: {note}")

    return "\n".join(lines).strip() + "\n"


def run_scenarios(args: argparse.Namespace) -> int:
    spec = AGENTS["season_scenario"]
    runtime, settings = _runtime(spec.name)
    athlete_root = settings.workspace_root / args.athlete
    try:
        season_path, season_content = _load_season_brief(athlete_root, args.year)
        season_block = (
            f"Season brief content (loaded via workspace_get_input from {season_path}):\n"
            f"\"\"\"\n{season_content}\n\"\"\"\n"
        )
    except FileNotFoundError as exc:
        season_block = f"Season brief missing: {exc}\n"

    user_input = (
        "Mode A. Generate the pre-decision scenarios. "
        f"Target ISO week: {args.year}-{args.week:02d}. "
        "Use the Season Brief content provided in this prompt. "
        "Do not request additional tools unless the season brief is missing. "
        f"{season_block}"
        "Set meta.owner_agent to Season-Scenario-Agent, meta.schema_id to SeasonScenariosInterface, "
        "and meta.authority to Informational. "
        "Include all required scenario_guidance fields (even if empty arrays) and data.notes array. "
        "Output the SEASON_SCENARIOS JSON now and call store_season_scenarios."
    )

    model_override = args.model or settings.model_for_agent(spec.name)
    temperature_override = settings.temperature_for_agent(spec.name)
    result = run_agent_multi_output(
        runtime,
        agent_name=spec.name,
        agent_vs_name=spec.vector_store_name,
        athlete_id=args.athlete,
        tasks=[AgentTask.CREATE_SEASON_SCENARIOS],
        user_input=user_input,
        run_id=args.run_id,
        model_override=model_override,
        temperature_override=temperature_override,
        force_file_search=not args.no_file_search,
        max_num_results=args.max_num_results,
    )
    store = LocalArtifactStore(root=settings.workspace_root)
    try:
        scenarios_doc = store.load_latest(args.athlete, ArtifactType.SEASON_SCENARIOS)
    except FileNotFoundError:
        print(result)
        return 1

    text = _render_scenarios(scenarios_doc)
    if args.out:
        out_path = Path(args.out)
    else:
        out_dir = ROOT / ".cache" / "macro_scenarios"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{args.run_id}.md"
    out_path.write_text(text, encoding="utf-8")
    print(text)
    print(f"[saved] {out_path}")
    return 0


def run_overview(args: argparse.Namespace) -> int:
    spec = AGENTS["macro_planner"]
    runtime, settings = _runtime(spec.name)

    scenario = args.scenario.upper() if args.scenario else ""
    if scenario and scenario not in {"A", "B", "C"}:
        raise SystemExit("Scenario must be A, B, or C.")
    if not scenario:
        store = LocalArtifactStore(root=settings.workspace_root)
        try:
            selection = store.load_latest(args.athlete, ArtifactType.SEASON_SCENARIO_SELECTION)
            scenario = (
                selection.get("data", {}).get("selected_scenario_id", "").strip().upper()
                if isinstance(selection, dict)
                else ""
            )
        except FileNotFoundError:
            scenario = ""
    if not scenario:
        raise SystemExit("Missing scenario. Provide --scenario or store SEASON_SCENARIO_SELECTION.")

    trace_line = ""
    if args.scenario_run_id:
        trace_line = (
            f"Set meta.trace_upstream to include '{args.scenario_run_id}'. "
        )

    events_line = (
        "Load events.md via workspace_get_input('events') (required), include it in "
        "meta.trace_events, and reflect relevant events in phases[].events_constraints. "
        "If no relevant events apply to a phase, use an empty array for events_constraints. "
    )
    if args.allow_missing_events:
        events_line = (
            "Load events.md via workspace_get_input('events') when available. "
            "If events input is missing, set events_constraints to an empty array and proceed. "
        )

    scenario_block = ""
    if args.scenario_run_id:
        scenario_path = ROOT / ".cache" / "macro_scenarios" / f"{args.scenario_run_id}.md"
        if scenario_path.exists():
            # Extract only the selected scenario from the cached render.
            lines = scenario_path.read_text(encoding="utf-8").splitlines()
            start_token = f"Scenario {scenario} —"
            capture = []
            capturing = False
            for line in lines:
                if line.startswith("Scenario ") and line != start_token and capturing:
                    break
                if line.startswith(start_token):
                    capturing = True
                if capturing:
                    capture.append(line)
            if capture:
                scenario_block = (
                    "Selected scenario details (use verbatim to shape the plan):\n"
                    f"\"\"\"\n{'\n'.join(capture).strip()}\n\"\"\"\n"
                )

    if not scenario_block:
        store = LocalArtifactStore(root=settings.workspace_root)
        try:
            scenarios_doc = store.load_latest(args.athlete, ArtifactType.SEASON_SCENARIOS)
            scenario_text = _render_selected_scenario(scenarios_doc, scenario)
            if scenario_text:
                scenario_block = (
                    "Selected scenario details (use verbatim to shape the plan):\n"
                    f"\"\"\"\n{scenario_text}\n\"\"\"\n"
                )
        except FileNotFoundError:
            scenario_block = ""

    if not scenario_block:
        scenario_block = "Selected scenario details could not be loaded; proceed with Scenario label only.\n"

    band_line = ""
    if args.moving_time_rate_band:
        band_line = (
            "Use KPI moving_time_rate_guidance band '"
            f"{args.moving_time_rate_band}' when deriving weekly kJ corridors. "
        )

    user_input = (
        f"Scenario {scenario}. Mode A. Output the MACRO_OVERVIEW JSON now. "
        "Set meta.schema_id exactly to MacroOverviewInterface, "
        "meta.schema_version to 1.0, authority to Binding, owner_agent to Macro-Planner. "
        "Use workspace_get_input for season brief. "
        "Use workspace_get_latest with artifact_type KPI_PROFILE (not a filename). "
        "Use workspace_get_latest with artifact_type SEASON_SCENARIO_SELECTION when available "
        "and align the plan to the selected scenario label. "
        "If scenario guidance provides phase_length_weeks and/or deload_cadence, treat them as "
        "binding constraints for phase construction (exact phase length, cadence-aligned deloads). "
        f"{band_line}"
        "Strict schema guards: each phase MUST include structural_emphasis and events_constraints "
        "(use [] when no events). Put typical_duration_intensity_pattern and non_negotiables "
        "only inside overview, never at phase top level. allowed_forbidden_semantics must "
        "only include allowed_intensity_domains, allowed_load_modalities, forbidden_intensity_domains "
        "(do NOT add forbidden_load_modalities). "
        "Return a single JSON envelope with top-level {\"meta\": ..., \"data\": ...} only. "
        "Meta must include iso_week (YYYY-WW) and iso_week_range as an object with from/to "
        "NO: iso_week_range must be a string pattern YYYY-WW--YYYY-WW (not an object). "
        "Phase iso_week_range must use the same string pattern. "
        "Do not add any extra keys at phase level (e.g., no 'notes'). "
        "Output MUST be a single JSON object and nothing else "
        "(no prose, no markdown). If a store call fails, output only the same JSON envelope."
        f"{events_line}"
        f"{trace_line}"
        f"{scenario_block}"
        "Call store_macro_overview with the JSON envelope (meta + data) only."
    )

    model_override = args.model or settings.model_for_agent(spec.name)
    temperature_override = settings.temperature_for_agent(spec.name)
    result = run_agent_multi_output(
        runtime,
        agent_name=spec.name,
        agent_vs_name=spec.vector_store_name,
        athlete_id=args.athlete,
        tasks=[AgentTask.CREATE_MACRO_OVERVIEW],
        user_input=user_input,
        run_id=args.run_id,
        model_override=model_override,
        temperature_override=temperature_override,
        force_file_search=not args.no_file_search,
        max_num_results=args.max_num_results,
    )
    print(result)
    return 0


def run_select(args: argparse.Namespace) -> int:
    scenario = args.scenario.upper()
    if scenario not in {"A", "B", "C"}:
        raise SystemExit("Scenario must be A, B, or C.")

    load_env_file(ROOT / ".env")
    settings = load_app_settings()
    store = LocalArtifactStore(root=settings.workspace_root)
    try:
        scenarios_doc = store.load_latest(args.athlete, ArtifactType.SEASON_SCENARIOS)
    except FileNotFoundError:
        raise SystemExit("Missing SEASON_SCENARIOS. Run 'scenarios' first.")

    scenario_ref = args.scenario_run_id or scenarios_doc.get("meta", {}).get("run_id") or "latest"
    rationale = args.rationale or ""
    now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    today = datetime.now(timezone.utc).date().isoformat()
    scenarios_meta = scenarios_doc.get("meta", {}) if isinstance(scenarios_doc, dict) else {}
    iso_week_range = scenarios_meta.get("iso_week_range") or f"{args.year}-{args.week:02d}--{args.year}-{args.week:02d}"
    temporal_scope = scenarios_meta.get("temporal_scope") or {"from": today, "to": today}

    meta = {
        "artifact_type": "SEASON_SCENARIO_SELECTION",
        "schema_id": "SeasonScenarioSelectionInterface",
        "schema_version": "1.0",
        "version": "1.0",
        "authority": "Informational",
        "owner_agent": "Season-Scenario-Agent",
        "run_id": args.run_id,
        "created_at": now_iso,
        "scope": "Macro",
        "iso_week": f"{args.year}-{args.week:02d}",
        "iso_week_range": iso_week_range,
        "temporal_scope": temporal_scope,
        "trace_upstream": [
            {
                "artifact": "season_scenarios",
                "version": scenarios_meta.get("version", "1.0"),
                "run_id": scenario_ref,
            }
        ],
        "trace_data": [],
        "trace_events": [],
        "notes": "User selection recorded referencing season_scenarios.",
    }

    selection_doc = {
        "meta": meta,
        "data": {
            "season_scenarios_ref": scenario_ref,
            "selected_scenario_id": scenario,
            "selection_source": "user",
            "selection_rationale": rationale,
            "notes": [],
        },
    }

    guarded = GuardedValidatedStore(
        athlete_id=args.athlete,
        schema_dir=settings.schema_dir,
        workspace_root=settings.workspace_root,
    )
    result = guarded.guard_put_validated(
        output_spec=OUTPUT_SPECS[AgentTask.CREATE_SEASON_SCENARIO_SELECTION],
        document=selection_doc,
        run_id=args.run_id,
        producer_agent="season_scenario",
        update_latest=True,
    )
    print({"ok": True, "produced": {"store_season_scenario_selection": result}})
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
    overview.add_argument("--scenario", help="A, B, or C.")
    overview.add_argument("--scenario-run-id", help="Optional run id from scenarios step.")
    overview.add_argument("--allow-missing-events", action="store_true")
    overview.add_argument(
        "--moving-time-rate-band",
        help="Override KPI moving_time_rate_guidance band (e.g., brevet_ultra_sustainable, fast_competitive, top_record_oriented).",
    )
    overview.set_defaults(func=run_overview)

    select = subparsers.add_parser("select", parents=[base])
    select.add_argument("--scenario", required=True, help="A, B, or C.")
    select.add_argument("--scenario-run-id", help="Optional run id from scenarios step.")
    select.add_argument("--rationale", help="Optional selection rationale.")
    select.set_defaults(func=run_select)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    load_env_file(ROOT / ".env")
    logger = configure_logging(ROOT, Path(__file__).stem)
    logger.info("Macro mode A command=%s athlete=%s", getattr(args, "command", None), args.athlete)

    if not args.athlete:
        raise SystemExit("Missing athlete id. Set ATHLETE_ID in .env or pass --athlete.")

    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
