from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
import time
import json
import difflib

import streamlit as st
import logging
import pandas as pd

from rps.ui.shared import (
    SETTINGS,
    announce_log_file,
    append_system_log,
    ensure_logging,
    build_phase_options,
    get_athlete_id,
    get_iso_year_week,
    init_ui_state,
    render_status_panel,
    set_status,
)
from rps.workspace.index_manager import WorkspaceIndexManager
from rps.workspace.iso_helpers import IsoWeek, next_iso_week, parse_iso_week, parse_iso_week_range, range_contains
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType
from rps.ui.run_store import (
    append_event,
    append_run,
    find_active_runs,
    load_events,
    load_runs,
    update_run,
)
from rps.openai.client import get_client
from rps.agents.multi_output_runner import AgentRuntime
from rps.orchestrator.queue_scheduler import enqueue_run, start_queue_scheduler, ensure_queue_dirs
from rps.openai.vectorstore_state import VectorStoreResolver
from rps.prompts.loader import PromptLoader


logger = logging.getLogger(__name__)

RESET_LATEST_TYPES = (
    ArtifactType.SEASON_PLAN,
    ArtifactType.PHASE_GUARDRAILS,
    ArtifactType.PHASE_STRUCTURE,
    ArtifactType.PHASE_PREVIEW,
    ArtifactType.WEEK_PLAN,
    ArtifactType.INTERVALS_WORKOUTS,
)

DELETE_LATEST_TYPES = (
    ArtifactType.SEASON_SCENARIOS,
    ArtifactType.SEASON_SCENARIO_SELECTION,
    *RESET_LATEST_TYPES,
)

STEP_DEFINITIONS = [
    {
        "step_id": "INPUTS_CHECK",
        "label": "Inputs",
        "agent": "Data Check",
        "writes": [],
        "authority": [],
    },
    {
        "step_id": "SEASON_SCENARIOS",
        "label": "Season Scenarios",
        "agent": "Scenario Planner",
        "writes": [ArtifactType.SEASON_SCENARIOS],
        "authority": ["Informational"],
    },
    {
        "step_id": "SCENARIO_SELECTION",
        "label": "Selected Scenario",
        "agent": "Selection",
        "writes": [ArtifactType.SEASON_SCENARIO_SELECTION],
        "authority": ["Binding-ish"],
    },
    {
        "step_id": "SEASON_PLAN",
        "label": "Season Plan",
        "agent": "Season Planner",
        "writes": [ArtifactType.SEASON_PLAN],
        "authority": ["Binding"],
    },
    {
        "step_id": "PHASE_GUARDRAILS",
        "label": "Phase Guardrails",
        "agent": "Phase Planner",
        "writes": [ArtifactType.PHASE_GUARDRAILS],
        "authority": ["Binding"],
    },
    {
        "step_id": "PHASE_STRUCTURE",
        "label": "Phase Structure",
        "agent": "Phase Planner",
        "writes": [ArtifactType.PHASE_STRUCTURE],
        "authority": ["Binding"],
    },
    {
        "step_id": "PHASE_PREVIEW",
        "label": "Phase Preview",
        "agent": "Phase Planner",
        "writes": [ArtifactType.PHASE_PREVIEW],
        "authority": ["Informational"],
    },
    {
        "step_id": "WEEK_PLAN",
        "label": "Week Plan",
        "agent": "Week Planner",
        "writes": [ArtifactType.WEEK_PLAN],
        "authority": ["Binding"],
    },
    {
        "step_id": "EXPORT_WORKOUTS",
        "label": "Build Workouts",
        "agent": "Workout Builder",
        "writes": [ArtifactType.INTERVALS_WORKOUTS],
        "authority": ["Raw"],
    },
]

PLANNING_SCOPE_SUBTYPE = {
    "Season Scenarios": "season_scenarios",
    "Selected Scenario": "scenario_selection",
    "Season Plan": "season_plan",
    "Phase (Guardrails + Structure)": "phase",
    "Week Plan": "week_plan",
    "Build Workouts": "export_workouts",
}

PLANNING_PRIORITY = {
    "orchestrated": 3,
    "season_scenarios": 3,
    "scenario_selection": 3,
    "season_plan": 3,
    "phase": 2,
    "week_plan": 1,
    "export_workouts": 0,
}


def _planning_priority(subtype: str | None) -> int:
    if not subtype:
        return 0
    return PLANNING_PRIORITY.get(subtype, 0)


def _planning_block_reason(root: Path, athlete_id: str, desired_subtype: str) -> str | None:
    active = find_active_runs(root, athlete_id, process_type="planning")
    if not active:
        return None
    desired_priority = _planning_priority(desired_subtype)
    for run in active:
        active_subtype = run.get("process_subtype") or "unknown"
        run_id = run.get("run_id") or "—"
        if active_subtype == desired_subtype:
            return (
                f"{desired_subtype.replace('_', ' ').title()} is already running "
                f"(run {run_id})."
            )
        if _planning_priority(active_subtype) > desired_priority:
            return (
                "A higher-priority planning run is active "
                f"(run {run_id}, {active_subtype.replace('_', ' ')}). "
                "Wait for it to finish before starting this run."
            )
    return None

STEP_DEPS = {
    "SEASON_SCENARIOS": ["INPUTS_CHECK"],
    "SCENARIO_SELECTION": ["SEASON_SCENARIOS"],
    "SEASON_PLAN": ["SCENARIO_SELECTION"],
    "PHASE_GUARDRAILS": ["SEASON_PLAN"],
    "PHASE_STRUCTURE": ["SEASON_PLAN", "PHASE_GUARDRAILS"],
    "PHASE_PREVIEW": ["PHASE_STRUCTURE"],
    "WEEK_PLAN": ["PHASE_GUARDRAILS", "PHASE_STRUCTURE"],
    "EXPORT_WORKOUTS": ["WEEK_PLAN"],
}

READINESS_DEPENDENCIES = {
    "season_scenarios": ["inputs"],
    "scenario_selection": ["season_scenarios"],
    "season_plan": ["scenario_selection"],
    "phase_guardrails": ["season_plan"],
    "phase_structure": ["season_plan"],
    "phase_preview": ["phase_structure"],
    "week_plan": ["phase_guardrails", "phase_structure"],
    "intervals_workouts": ["week_plan"],
}

SCOPE_STEPS = {
    "Season Scenarios": ["SEASON_SCENARIOS"],
    "Selected Scenario": ["SCENARIO_SELECTION"],
    "Season Plan": ["SEASON_PLAN", "PHASE_GUARDRAILS", "PHASE_STRUCTURE", "PHASE_PREVIEW", "WEEK_PLAN", "EXPORT_WORKOUTS"],
    "Phase (Guardrails + Structure)": ["PHASE_GUARDRAILS", "PHASE_STRUCTURE", "PHASE_PREVIEW", "WEEK_PLAN", "EXPORT_WORKOUTS"],
    "Week Plan": ["WEEK_PLAN", "EXPORT_WORKOUTS"],
    "Build Workouts": ["EXPORT_WORKOUTS"],
}


def _runtime_for_agent(agent_name: str) -> AgentRuntime:
    """Build a runtime for the given agent without Streamlit state."""
    client = get_client()
    return AgentRuntime(
        client=client,
        model=SETTINGS.openai_model,
        temperature=SETTINGS.openai_temperature,
        reasoning_effort=SETTINGS.reasoning_effort_for_agent(agent_name),
        reasoning_summary=SETTINGS.reasoning_summary_for_agent(agent_name),
        prompt_loader=PromptLoader(SETTINGS.prompts_dir),
        vs_resolver=VectorStoreResolver(SETTINGS.vs_state_path),
        schema_dir=SETTINGS.schema_dir,
        workspace_root=SETTINGS.workspace_root,
    )


@dataclass(frozen=True)
class ReadinessStep:
    """Represents readiness status for a planning pipeline step."""

    key: str
    label: str
    status: str
    summary: str
    reason: str
    latest: str | None = None
    run_id: str | None = None
    created_at: str | None = None
    optional: bool = False
    fix_label: str | None = None


def _parse_iso_datetime(value: str | None) -> datetime | None:
    """Parse ISO-8601 timestamps with optional Z suffix."""
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _latest_input(inputs_dir: Path, prefix: str) -> Path | None:
    """Return the latest markdown input file matching the prefix."""
    if not inputs_dir.exists():
        return None
    matches = sorted(inputs_dir.glob(f"{prefix}*.md"), key=lambda p: p.stat().st_mtime)
    return matches[-1] if matches else None


def _load_index(athlete_id: str) -> dict:
    """Load the workspace index for an athlete."""
    mgr = WorkspaceIndexManager(root=SETTINGS.workspace_root, athlete_id=athlete_id)
    return mgr.load()


def _latest_record(index: dict, artifact_type: ArtifactType) -> dict | None:
    """Return the latest record for an artifact type from index.json."""
    entry = (index.get("artefacts") or {}).get(artifact_type.value)
    if isinstance(entry, dict):
        return entry.get("latest")
    return None


def _record_matches_context(record: dict | None, target_week: IsoWeek) -> bool:
    """Check if a record's iso_week or iso_week_range matches the selected week."""
    if not isinstance(record, dict):
        return False
    iso_week = parse_iso_week(record.get("iso_week"))
    if iso_week and iso_week == target_week:
        return True
    iso_range = parse_iso_week_range(record.get("iso_week_range"))
    if iso_range and range_contains(iso_range, target_week):
        return True
    version_key = record.get("version_key")
    if isinstance(version_key, str):
        parsed = parse_iso_week(version_key)
        if parsed and parsed == target_week:
            return True
    return False


def _status_badge(status: str) -> str:
    """Return the badge icon for a status."""
    return {
        "ready": "✅",
        "stale": "⚠️",
        "missing": "❌",
        "blocked": "🔒",
    }.get(status, "•")


def _current_iso_week() -> IsoWeek:
    """Return the current ISO week based on today's date."""
    iso_year, iso_week, _ = date.today().isocalendar()
    return IsoWeek(year=iso_year, week=iso_week)


def _is_week_in_scope(target: IsoWeek) -> bool:
    """Return True if the target week is current or next ISO week."""
    current = _current_iso_week()
    return target == current or target == next_iso_week(current)


def _is_week_ready(readiness: list[ReadinessStep]) -> bool:
    """Return True if all required planning artifacts are ready."""
    required_keys = {
        "inputs",
        "season_scenarios",
        "scenario_selection",
        "season_plan",
        "phase_guardrails",
        "phase_structure",
        "week_plan",
        "intervals_workouts",
    }
    readiness_map = {step.key: step for step in readiness}
    for key in required_keys:
        step = readiness_map.get(key)
        if not step or step.status != "ready":
            return False
    return True


def _override_required(scope: str | None, readiness: list[ReadinessStep]) -> bool:
    """Return True when a scoped override is needed to modify existing artifacts."""
    if not scope:
        return False
    readiness_map = {step.key: step for step in readiness}
    key_map = {
        "Season Scenarios": "season_scenarios",
        "Selected Scenario": "scenario_selection",
        "Season Plan": "season_plan",
        "Phase (Guardrails + Structure)": "phase_guardrails",
        "Week Plan": "week_plan",
        "Build Workouts": "intervals_workouts",
    }
    readiness_key = key_map.get(scope)
    if not readiness_key:
        return False
    step = readiness_map.get(readiness_key)
    return bool(step and step.status in {"ready", "stale"})


def _compute_readiness(athlete_id: str, year: int, week: int) -> list[ReadinessStep]:
    """Compute readiness across the planning pipeline."""
    logger.info("Computing readiness athlete=%s iso=%04d-W%02d", athlete_id, year, week)
    target_week = IsoWeek(year=year, week=week)
    index = _load_index(athlete_id)
    store = LocalArtifactStore(root=SETTINGS.workspace_root)
    inputs_dir = SETTINGS.workspace_root / athlete_id / "inputs"

    steps: list[ReadinessStep] = []
    status_map: dict[str, ReadinessStep] = {}

    def add_step(step: ReadinessStep) -> None:
        steps.append(step)
        status_map[step.key] = step

    # Step 1: Inputs
    inputs_required = [
        ("season_brief", "Season Brief"),
        ("events", "Events"),
    ]
    inputs_missing = [
        label
        for prefix, label in inputs_required
        if _latest_input(inputs_dir, prefix) is None
    ]
    input_artifacts = [
        (ArtifactType.KPI_PROFILE, "KPI Profile"),
        (ArtifactType.AVAILABILITY, "Availability"),
        (ArtifactType.ZONE_MODEL, "Zones"),
        (ArtifactType.WELLNESS, "Wellness"),
    ]
    for artifact_type, label in input_artifacts:
        if not store.latest_exists(athlete_id, artifact_type):
            inputs_missing.append(label)
    if inputs_missing:
        add_step(
            ReadinessStep(
                key="inputs",
                label="Inputs",
                status="missing",
                summary="Missing inputs",
                reason="Missing: " + ", ".join(inputs_missing),
                fix_label="Add Inputs",
            )
        )
    else:
        add_step(
            ReadinessStep(
                key="inputs",
                label="Inputs",
                status="ready",
                summary="Inputs present",
                reason="All required inputs found.",
            )
        )

    # Helper to evaluate artifact steps
    def artifact_step(
        key: str,
        label: str,
        artifact_type: ArtifactType,
        required: list[str],
        *,
        match_context: bool = True,
        optional: bool = False,
        fix_label: str | None = None,
    ) -> None:
        record = _latest_record(index, artifact_type)
        if not store.latest_exists(athlete_id, artifact_type):
            record = None
        created_at = record.get("created_at") if record else None
        latest_ts = _parse_iso_datetime(created_at)
        latest_label = record.get("version_key") if record else None
        run_id = record.get("run_id") if record else None

        missing = record is None
        blocked = missing and any(status_map[r].status in {"missing", "blocked"} for r in required)
        stale = False
        reason = ""
        if not missing:
            if match_context and not _record_matches_context(record, target_week):
                stale = True
                reason = "Latest does not match the selected ISO week."
            for upstream in required:
                upstream_ts = _parse_iso_datetime(status_map[upstream].created_at)
                if latest_ts and upstream_ts and upstream_ts > latest_ts:
                    stale = True
                    reason = "Upstream artifact is newer."
        if missing and optional:
            status = "missing"
            summary = "Missing (optional)"
            reason = "Optional step; no artifact present."
        elif blocked:
            status = "blocked"
            summary = "Blocked"
            reason = "Required upstream artifacts are missing."
        elif missing:
            status = "missing"
            summary = "Missing"
            reason = "No artifact found."
        elif stale:
            status = "stale"
            summary = "Stale"
        else:
            status = "ready"
            summary = "Ready"
            reason = "Latest artifact is current."

        add_step(
            ReadinessStep(
                key=key,
                label=label,
                status=status,
                summary=summary,
                reason=reason,
                latest=latest_label,
                run_id=run_id,
                created_at=created_at,
                optional=optional,
                fix_label=fix_label,
            )
        )

    artifact_step(
        key="season_scenarios",
        label="Season Scenarios",
        artifact_type=ArtifactType.SEASON_SCENARIOS,
        required=["inputs"],
        match_context=False,
        fix_label="Create Scenarios",
    )
    artifact_step(
        key="scenario_selection",
        label="Selected Scenario",
        artifact_type=ArtifactType.SEASON_SCENARIO_SELECTION,
        required=["season_scenarios"],
        match_context=False,
        fix_label="Select Scenario",
    )
    artifact_step(
        key="season_plan",
        label="Season Plan",
        artifact_type=ArtifactType.SEASON_PLAN,
        required=["scenario_selection"],
        fix_label="Create Season Plan",
    )
    artifact_step(
        key="phase_guardrails",
        label="Phase Guardrails",
        artifact_type=ArtifactType.PHASE_GUARDRAILS,
        required=["season_plan"],
        fix_label="Run Phase Guardrails",
    )
    artifact_step(
        key="phase_structure",
        label="Phase Structure",
        artifact_type=ArtifactType.PHASE_STRUCTURE,
        required=["season_plan"],
        fix_label="Run Phase Structure",
    )
    artifact_step(
        key="phase_preview",
        label="Phase Preview (optional)",
        artifact_type=ArtifactType.PHASE_PREVIEW,
        required=["phase_structure"],
        optional=True,
        fix_label="Create Phase Preview",
    )
    artifact_step(
        key="week_plan",
        label="Week Plan",
        artifact_type=ArtifactType.WEEK_PLAN,
        required=["phase_guardrails", "phase_structure"],
        fix_label="Plan This Week",
    )
    artifact_step(
        key="intervals_workouts",
        label="Build Workouts",
        artifact_type=ArtifactType.INTERVALS_WORKOUTS,
        required=["week_plan"],
        fix_label="Build Workouts",
    )
    return steps


def _show_reset_delete_actions(athlete_id: str) -> None:
    """Render reset/delete season plan actions with confirmation."""
    with st.form("plan_hub_season_actions"):
        action = st.selectbox("Action", options=["Reset Season Plan", "Delete Season Plan"])
        confirmation = st.text_input('Type "YES I WANT TO PROCEED" to continue')
        submitted = st.form_submit_button("Proceed")
    if submitted and confirmation != "YES I WANT TO PROCEED":
        st.error('Confirmation must match exactly: "YES I WANT TO PROCEED".')
        return
    if submitted:
        set_status(
            status_state="running",
            title="Plan Hub",
            message=f"{action} requested.",
            last_action=action,
        )
        append_system_log("plan_hub", f"{action} requested.")
        store = LocalArtifactStore(root=SETTINGS.workspace_root)
        types = DELETE_LATEST_TYPES if action == "Delete Season Plan" else RESET_LATEST_TYPES
        removed = _clear_latest_artifacts(store, athlete_id, types)
        if removed:
            st.success(f"Removed {len(removed)} latest artefacts.")
            with st.expander("Removed artefacts", expanded=False):
                st.code("\n".join(removed))
        else:
            st.info("No latest artefacts were removed.")
        set_status(
            status_state="done",
            title="Plan Hub",
            message=f"{action} completed.",
            last_action=action,
        )
        st.rerun()


def _clear_latest_artifacts(
    store: LocalArtifactStore,
    athlete_id: str,
    artifact_types: tuple[ArtifactType, ...],
) -> list[str]:
    """Delete latest artefact files for the given types and return removed paths."""
    removed: list[str] = []
    for artifact_type in artifact_types:
        path = store.latest_path(athlete_id, artifact_type)
        if not path.exists():
            continue
        try:
            path.unlink()
            removed.append(str(path))
            logger.info("Deleted latest artefact %s", path)
        except OSError as exc:
            logger.warning("Failed to delete latest artefact %s: %s", path, exc)
    if removed:
        mgr = WorkspaceIndexManager(root=SETTINGS.workspace_root, athlete_id=athlete_id)
        summary = mgr.prune_missing()
        logger.info(
            "Pruned index after delete athlete=%s removed_versions=%s removed_types=%s",
            athlete_id,
            summary.get("removed_versions"),
            summary.get("removed_types"),
        )
    return removed


def _latest_outputs(athlete_id: str) -> list[dict[str, str]]:
    """Return a list of latest artifact summaries for cards."""
    logger.info("Building latest outputs athlete=%s", athlete_id)
    index = _load_index(athlete_id)
    targets = [
        (ArtifactType.SEASON_PLAN, "Season Plan"),
        (ArtifactType.PHASE_GUARDRAILS, "Phase Guardrails"),
        (ArtifactType.PHASE_STRUCTURE, "Phase Structure"),
        (ArtifactType.WEEK_PLAN, "Week Plan"),
        (ArtifactType.INTERVALS_WORKOUTS, "Build Workouts"),
    ]
    rows = []
    for artifact_type, label in targets:
        record = _latest_record(index, artifact_type) or {}
        rows.append(
            {
                "Type": artifact_type.value,
                "Title": label,
                "Version": str(record.get("version_key") or "—"),
                "Run": str(record.get("run_id") or "—"),
                "Updated": str(record.get("created_at") or "—"),
            }
        )
    return rows


def _run_history(
    athlete_id: str,
    *,
    limit: int = 20,
    allowed: set[str] | None = None,
) -> list[dict[str, str]]:
    """Build a flattened run history table from index.json."""
    logger.info("Building run history athlete=%s", athlete_id)
    index = _load_index(athlete_id)
    entries: list[dict[str, str]] = []
    artefacts = index.get("artefacts") or {}
    for artifact_type, entry in artefacts.items():
        if allowed is not None and artifact_type not in allowed:
            continue
        versions = (entry or {}).get("versions") or {}
        for version_key, record in versions.items():
            if not isinstance(record, dict):
                continue
            entries.append(
                {
                    "Artifact": artifact_type,
                    "Version": str(version_key),
                    "Run": str(record.get("run_id") or "—"),
                    "Producer": str(record.get("producer_agent") or "—"),
                    "Created": str(record.get("created_at") or "—"),
                }
            )
    entries.sort(key=lambda e: e.get("Created") or "", reverse=True)
    return entries[:limit]


def _run_store_history(athlete_id: str, *, limit: int = 20) -> list[dict[str, str]]:
    """Return recent Plan Hub runs from the run store."""
    runs = load_runs(SETTINGS.workspace_root, athlete_id, limit=limit)
    rows: list[dict[str, str]] = []
    for run in runs:
        rows.append(
            {
                "Run ID": str(run.get("run_id") or "—"),
                "Status": str(run.get("status") or "—"),
                "Mode": str(run.get("mode") or "—"),
                "Scope": str(run.get("scope") or "—"),
                "Created": str(run.get("created_at") or "—"),
                "Superseded By": str(run.get("superseded_by") or "—"),
            }
        )
    return rows


def _style_superseded(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    """Apply muted style to superseded rows."""
    def _row_style(row: pd.Series) -> list[str]:
        if row.get("Status") == "SUPERSEDED":
            return ["color: #8c8c8c; background-color: #f5f5f5;"] * len(row)
        return ["" for _ in row]

    return df.style.apply(_row_style, axis=1)


def _version_records(index: dict, artifact_type: ArtifactType) -> list[dict]:
    """Return all version records for an artifact type."""
    entry = (index.get("artefacts") or {}).get(artifact_type.value) or {}
    versions = entry.get("versions") or {}
    records = []
    for version_key, record in versions.items():
        if isinstance(record, dict):
            record = dict(record)
            record["version_key"] = version_key
            records.append(record)
    records.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return records


def _load_artifact_json(athlete_id: str, record: dict) -> dict | list | None:
    """Load an artifact JSON from a record path if possible."""
    path = record.get("path") or record.get("relative_path")
    if not isinstance(path, str):
        return None
    full_path = SETTINGS.workspace_root / athlete_id / path
    if not full_path.exists():
        return None
    try:
        return json.loads(full_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _diff_json(a: dict | list | None, b: dict | list | None) -> str:
    """Return a unified diff between two JSON documents."""
    if a is None or b is None:
        return "No diff available."
    left = json.dumps(a, ensure_ascii=False, indent=2).splitlines()
    right = json.dumps(b, ensure_ascii=False, indent=2).splitlines()
    diff = difflib.unified_diff(left, right, lineterm="")
    return "\n".join(diff) or "No differences."


def _build_execution_steps(
    readiness: list[ReadinessStep],
    mode: str,
    scope: str | None,
) -> list[dict[str, Any]]:
    """Build execution steps from readiness + scope mapping."""
    readiness_map = {step.key: step for step in readiness}
    selected_steps = [step["step_id"] for step in STEP_DEFINITIONS if step["step_id"] != "INPUTS_CHECK"]
    if mode == "Scoped" and scope in SCOPE_STEPS:
        selected_steps = SCOPE_STEPS[scope]

    steps: list[dict[str, Any]] = []
    for definition in STEP_DEFINITIONS:
        step_id = definition["step_id"]
        if step_id == "INPUTS_CHECK":
            continue
        if step_id not in selected_steps:
            continue
        readiness_key = {
            "SEASON_SCENARIOS": "season_scenarios",
            "SCENARIO_SELECTION": "scenario_selection",
            "SEASON_PLAN": "season_plan",
            "PHASE_GUARDRAILS": "phase_guardrails",
            "PHASE_STRUCTURE": "phase_structure",
            "PHASE_PREVIEW": "phase_preview",
            "WEEK_PLAN": "week_plan",
            "EXPORT_WORKOUTS": "intervals_workouts",
        }.get(step_id)
        readiness_step = readiness_map.get(readiness_key, ReadinessStep("", "", "missing", "", ""))
        readiness_status = readiness_step.status
        readiness_reason = readiness_step.reason or "—"
        if readiness_status == "blocked":
            status = "BLOCKED"
            details = readiness_reason
        elif readiness_status in {"missing", "stale"}:
            status = "QUEUED"
            details = readiness_reason
        else:
            status = "SKIPPED"
            details = "Already up-to-date."
        writes_detail = []
        for artifact_type, authority in zip(definition["writes"], definition["authority"]):
            writes_detail.append(
                {
                    "artifact_key": artifact_type.value,
                    "display_name": artifact_type.value,
                    "authority": authority,
                }
            )
        steps.append(
            {
                "Step": definition["label"],
                "Agent": definition["agent"],
                "Writes": ", ".join([t.value for t in definition["writes"]]),
                "Authority": ", ".join(definition["authority"]),
                "Status": status,
                "Started": None,
                "Duration": None,
                "Ended": None,
                "Details": details,
                "step_id": step_id,
                "response_id": None,
                "write_types": [t.value for t in definition["writes"]],
                "writes": writes_detail,
                "Deps": STEP_DEPS.get(step_id, []),
                "Outputs": [],
            }
        )
    return steps


def _ensure_worker(
    root: Path,
    athlete_id: str,
    run_id: str,
    *,
    allow_delete: bool,
    process_subtype: str | None,
) -> None:
    """Ensure scheduler is running and enqueue the run."""
    @st.cache_resource
    def _get_scheduler() -> dict:
        return start_queue_scheduler(
            root=root,
            runtime_for_agent=_runtime_for_agent,
            model_resolver=SETTINGS.model_for_agent,
            temperature_resolver=SETTINGS.temperature_for_agent,
            reasoning_effort_resolver=SETTINGS.reasoning_effort_for_agent,
            reasoning_summary_resolver=SETTINGS.reasoning_summary_for_agent,
            force_file_search=True,
            max_num_results=SETTINGS.file_search_max_results,
        )

    ensure_queue_dirs(root)
    scheduler = _get_scheduler()
    if not scheduler.get("thread") or not scheduler["thread"].is_alive():
        _get_scheduler.clear()
        scheduler = _get_scheduler()
    enqueue_run(
        root,
        run_id,
        {
            "athlete_id": athlete_id,
            "process_type": "planning",
            "process_subtype": process_subtype or "orchestrated",
            "allow_delete_intervals": allow_delete,
        },
    )


def _enqueue_scoped_run(
    athlete_id: str,
    *,
    iso_year: int,
    iso_week: int,
    phase_label: str | None,
    scope: str,
    override_text: str | None = None,
    run_id: str | None = None,
) -> None:
    """Queue a scoped planning run for a single scope."""
    desired_subtype = PLANNING_SCOPE_SUBTYPE.get(scope, "scoped")
    block_reason = _planning_block_reason(SETTINGS.workspace_root, athlete_id, desired_subtype)
    if block_reason:
        st.warning(block_reason)
        st.stop()
    readiness = _compute_readiness(athlete_id, iso_year, iso_week)
    steps = _build_execution_steps(readiness, "Scoped", scope)
    log_ref = ensure_logging(athlete_id)
    for step in steps:
        step["Log"] = log_ref
    resolved_run_id = run_id or f"ui_{desired_subtype}_{iso_year:04d}W{iso_week:02d}_{time.strftime('%Y%m%d_%H%M%S')}"
    record = {
        "run_id": resolved_run_id,
        "athlete_id": athlete_id,
        "iso_year": iso_year,
        "iso_week": iso_week,
        "phase_label": phase_label,
        "mode": "Scoped",
        "process_type": "planning",
        "process_subtype": desired_subtype,
        "scope": scope,
        "status": "QUEUED",
        "steps": steps,
        "log_ref": log_ref,
        "summary": {"steps_done": 0, "steps_failed": 0, "artefacts_written": 0},
        "current_step": None,
        "override_text": (override_text or "").strip() or None,
    }
    append_run(SETTINGS.workspace_root, athlete_id, record)
    st.session_state["plan_hub_running"] = True
    st.session_state["plan_hub_active_run_id"] = resolved_run_id
    _ensure_worker(
        SETTINGS.workspace_root,
        athlete_id,
        resolved_run_id,
        allow_delete=False,
        process_subtype=desired_subtype,
    )
    st.info("Run requested (placeholder).")
    st.rerun()


def _mark_runs_superseded(root: Path, athlete_id: str, run_ids: list[str], new_run_id: str) -> None:
    """Mark previous runs as superseded."""
    for old_run_id in run_ids:
        update_run(
            root,
            athlete_id,
            old_run_id,
            {"status": "SUPERSEDED", "superseded_by": new_run_id},
        )


st.title("Plan Hub")

state = init_ui_state()
athlete_id = get_athlete_id()
year, week = get_iso_year_week()
announce_log_file(athlete_id)

hub_scope = st.session_state.get("hub_scope") or {
    "athlete_id": athlete_id,
    "iso_year": year,
    "iso_week": week,
    "phase_label": st.session_state.get("selected_phase_label"),
}

active_run_id = st.session_state.get("plan_hub_active_run_id")
run_records = load_runs(SETTINGS.workspace_root, hub_scope["athlete_id"], limit=5)
active_run = None
if active_run_id:
    for record in run_records:
        if record.get("run_id") == active_run_id:
            active_run = record
            break
elif run_records:
    active_run = run_records[0]

if active_run and active_run.get("status") in {"QUEUED", "RUNNING"}:
    active_run_id = active_run.get("run_id")
    st.session_state["plan_hub_active_run_id"] = active_run_id

run_state = bool(active_run and active_run.get("status") in {"QUEUED", "RUNNING"})
st.session_state["plan_hub_running"] = run_state
scope_lock = run_state

if run_state:
    st.autorefresh(interval=2000, key="plan_hub_autorefresh")

if active_run_id:
    _ensure_worker(SETTINGS.workspace_root, hub_scope["athlete_id"], active_run_id, allow_delete=bool(active_run.get("delete_removed_intervals")), process_subtype=active_run.get("process_subtype"))

st.subheader("Readiness")
st.caption("Review required artefacts and resolve missing or stale steps before planning.")
readiness = _compute_readiness(hub_scope["athlete_id"], hub_scope["iso_year"], hub_scope["iso_week"])
readiness_map = {step.key: step for step in readiness}
required_steps = [step for step in readiness if not step.optional]
total_required = len(required_steps)
ready_required = sum(1 for step in required_steps if step.status == "ready")
has_attention = any(step.status in {"missing", "blocked", "stale"} for step in required_steps)
has_blockers = any(step.status in {"missing", "blocked"} for step in required_steps)
blocked_messages: list[str] = []
if has_blockers:
    for step in required_steps:
        if step.status not in {"missing", "blocked"}:
            continue
        deps = READINESS_DEPENDENCIES.get(step.key, [])
        blocking = []
        for dep_key in deps:
            dep_step = readiness_map.get(dep_key)
            if dep_step and dep_step.status in {"missing", "blocked"}:
                blocking.append(dep_step.label)
        if blocking:
            blocked_messages.append(f"{step.label} blocked by missing {', '.join(blocking)}")
        elif step.status == "missing":
            blocked_messages.append(f"{step.label} missing")
        else:
            blocked_messages.append(f"{step.label} blocked")
overall_status = "ready" if not has_attention else "stale"
overall_message = (
    f"{ready_required}/{total_required} ready · "
    f"{sum(1 for step in required_steps if step.status == 'stale')} warnings · "
    f"{sum(1 for step in required_steps if step.status in {'missing', 'blocked'})} missing/blocked"
)
status_state = "done" if overall_status == "ready" else "stale"
status_message = "Ready" if overall_status == "ready" else "Attention needed"
if run_state:
    status_state = "running"
    status_message = "Running"
set_status(status_state=status_state, title="Plan Hub", message=status_message)
render_status_panel()
st.caption(overall_message)

readiness_container = st.container()
readiness_cols = readiness_container.columns(2)
split_idx = (len(readiness) + 1) // 2
for col, steps in zip(readiness_cols, [readiness[:split_idx], readiness[split_idx:]]):
    with col:
        for step in steps:
            header = f"{_status_badge(step.status)} {step.label}"
            with st.expander(header, expanded=step.status in {"missing", "blocked"}):
                st.write(step.summary)
                st.caption(step.reason)
                if step.latest:
                    st.caption(f"Latest version: {step.latest}")
                if step.run_id:
                    st.caption(f"Run id: {step.run_id}")
                if step.fix_label:
                    allow_fix = step.key == "season_scenarios" and readiness_map.get("inputs", step).status == "ready"
                    clicked = st.button(step.fix_label, key=f"fix_{step.key}", disabled=not allow_fix)
                    if clicked:
                        if not allow_fix:
                            st.warning("Resolve required inputs before running this step.")
                            st.stop()
                        _enqueue_scoped_run(
                            hub_scope["athlete_id"],
                            iso_year=hub_scope["iso_year"],
                            iso_week=hub_scope["iso_week"],
                            phase_label=hub_scope.get("phase_label"),
                            scope="Season Scenarios",
                        )

with st.expander("Season Plan: Delete or Reset", expanded=False):
    store = LocalArtifactStore(root=SETTINGS.workspace_root)
    has_plan = store.latest_exists(hub_scope["athlete_id"], ArtifactType.SEASON_PLAN)
    if has_plan:
        _show_reset_delete_actions(hub_scope["athlete_id"])
    else:
        st.caption("No season plan available for reset/delete actions.")

summary_text = None
if has_blockers:
    info_lines = ["Resolve missing inputs/artifacts above before Run Planning is available."]
    if blocked_messages:
        info_lines.append("")
        info_lines.extend([f"- {msg}" for msg in blocked_messages])
    st.info("\n".join(info_lines))
else:
    scope_col, run_col = st.columns([1, 1])

if not has_blockers:
    with scope_col:
        st.subheader("Scope")
        st.caption(f"Athlete: {hub_scope['athlete_id']} · ISO {hub_scope['iso_year']}-W{hub_scope['iso_week']:02d}")
    athlete_id = st.text_input(
        "Athlete",
        value=hub_scope["athlete_id"],
        disabled=scope_lock,
    )
    year = int(
        st.number_input(
            "ISO Year",
            min_value=2000,
            max_value=2100,
            value=hub_scope["iso_year"],
            step=1,
            disabled=scope_lock,
        )
    )
    week = int(
        st.number_input(
            "ISO Week",
            min_value=1,
            max_value=53,
            value=hub_scope["iso_week"],
            step=1,
            disabled=scope_lock,
        )
    )
    phase_label = hub_scope.get("phase_label")
    phases = []
    season_plan = None
    try:
        season_plan = store.load_latest(athlete_id, ArtifactType.SEASON_PLAN)
    except FileNotFoundError:
        season_plan = None
    if isinstance(season_plan, dict):
        phases = season_plan.get("data", {}).get("phases", []) or []
    if phases:
        options, _ = build_phase_options(phases)
        if phase_label not in options:
            phase_label = options[0]
        phase_label = st.selectbox(
            "Phase",
            options=options,
            index=options.index(phase_label),
            disabled=scope_lock,
        )
    hub_scope = {
        "athlete_id": athlete_id,
        "iso_year": year,
        "iso_week": week,
        "phase_label": phase_label,
    }
    st.session_state["hub_scope"] = hub_scope
    if run_state:
        st.caption(f"Running for {athlete_id} · {year}-W{week:02d}")

    with run_col:
        st.subheader("Run Planning")
        run_readiness = _compute_readiness(athlete_id, year, week)
        base_week = IsoWeek(year=year, week=week)
        current_week = _current_iso_week()
        plan_next = base_week == current_week and _is_week_ready(run_readiness)
        target_week = next_iso_week(base_week) if plan_next else base_week
        target_readiness = _compute_readiness(athlete_id, target_week.year, target_week.week)
        cta_prefix = "Plan Next Week" if plan_next else "Plan Week"
        cta_label = f"{cta_prefix}: {target_week.year:04d}-W{target_week.week:02d}"
        cta_disabled = scope_lock or not _is_week_in_scope(target_week)

        run_mode = st.radio("Run mode", ["Orchestrated", "Scoped"], index=1)
        scope = None
        if run_mode == "Scoped":
            scope = st.selectbox(
                "Scope",
                [
                    "Season Scenarios",
                    "Selected Scenario",
                    "Season Plan",
                    "Phase (Guardrails + Structure)",
                    "Week Plan",
                    "Build Workouts",
                ],
                index=4,
            )
        override_required = _override_required(scope, run_readiness)
        override_text = None
        if run_mode == "Scoped":
            override_text = st.text_area(
                "Override (optional)",
                placeholder="Describe what to change at the selected scope.",
                disabled=not scope,
            )
            if override_required and not (override_text or "").strip():
                st.warning("Override required when modifying existing artifacts.")
        default_run_id = (
            f"plan_hub_{hub_scope['iso_year']:04d}W{hub_scope['iso_week']:02d}_"
            f"{time.strftime('%Y%m%d_%H%M%S')}"
        )
        if not st.session_state.get("plan_hub_run_id"):
            st.session_state["plan_hub_run_id"] = default_run_id
        run_id = st.text_input("Run ID", key="plan_hub_run_id")
        validate_only = st.checkbox("Validate only (no write)", value=False)
        scope_summary = {
            None: "Will write: Season Plan, Phase Guardrails, Phase Structure, Week Plan, Build Workouts",
            "Season Scenarios": "Will write: Season Scenarios",
            "Selected Scenario": "Will write: Selected Scenario",
            "Season Plan": "Will write: Season Plan",
            "Phase (Guardrails + Structure)": "Will write: Phase Guardrails, Phase Structure",
            "Week Plan": "Will write: Week Plan",
            "Build Workouts": "Will write: Build Workouts",
        }
        summary_text = scope_summary.get(scope, scope_summary[None])
        run_actions = st.container()
        with run_actions:
            st.markdown("**Run actions**")
            st.caption(
                "Plan Week runs a scoped week plan for the current/next ISO week. "
                "Run orchestrated executes the full plan cascade. Run scoped only reruns the selected scope "
                "and dependent outputs."
            )
            col_week, col_scoped, col_orchestrated = st.columns(3)
            run_week = col_week.button(cta_label, disabled=cta_disabled)
            run_scoped = col_scoped.button(
                "Run scoped",
                disabled=run_mode != "Scoped",
            )
            run_orchestrated = col_orchestrated.button(
                "Run orchestrated",
                disabled=scope_lock or run_mode != "Orchestrated",
            )

    if run_week:
        if not _is_week_in_scope(target_week):
            st.warning("Planning scope is limited to the current or next ISO week.")
            st.stop()
        if _override_required("Week Plan", target_readiness):
            st.warning("This week already has planning artifacts. Use a scoped run with an override.")
            st.stop()
        desired_subtype = PLANNING_SCOPE_SUBTYPE["Week Plan"]
        block_reason = _planning_block_reason(
            SETTINGS.workspace_root,
            athlete_id,
            desired_subtype,
        )
        if block_reason:
            st.warning(block_reason)
            st.stop()
        run_id = f"plan_week_{target_week.year:04d}W{target_week.week:02d}"
        steps = _build_execution_steps(target_readiness, "Scoped", "Week Plan")
        log_ref = ensure_logging(athlete_id)
        for step in steps:
            step["Log"] = log_ref
        record = {
            "run_id": run_id,
            "athlete_id": athlete_id,
            "iso_year": target_week.year,
            "iso_week": target_week.week,
            "phase_label": phase_label,
            "mode": "Scoped",
            "process_type": "planning",
            "process_subtype": desired_subtype,
            "scope": "Week Plan",
            "status": "QUEUED",
            "steps": steps,
            "log_ref": log_ref,
            "summary": {"steps_done": 0, "steps_failed": 0, "artefacts_written": 0},
            "current_step": None,
            "override_text": None,
        }
        append_run(SETTINGS.workspace_root, athlete_id, record)
        st.session_state["plan_hub_running"] = True
        st.session_state["plan_hub_active_run_id"] = run_id
        _ensure_worker(
            SETTINGS.workspace_root,
            athlete_id,
            run_id,
            allow_delete=False,
            process_subtype=desired_subtype,
        )
        st.info("Run requested (placeholder).")

    if run_orchestrated:
        if not _is_week_in_scope(base_week):
            st.warning("Planning scope is limited to the current or next ISO week.")
            st.stop()
        block_reason = _planning_block_reason(
            SETTINGS.workspace_root,
            hub_scope["athlete_id"],
            "orchestrated",
        )
        if block_reason:
            st.warning(block_reason)
            st.stop()
        steps = _build_execution_steps(run_readiness, "Orchestrated", None)
        log_ref = ensure_logging(hub_scope["athlete_id"])
        for step in steps:
            step["Log"] = log_ref
        record = {
            "run_id": run_id,
            "athlete_id": hub_scope["athlete_id"],
            "iso_year": hub_scope["iso_year"],
            "iso_week": hub_scope["iso_week"],
            "phase_label": hub_scope.get("phase_label"),
            "mode": "Orchestrated",
            "process_type": "planning",
            "process_subtype": "orchestrated",
            "scope": None,
            "status": "QUEUED",
            "steps": steps,
            "log_ref": log_ref,
            "summary": {"steps_done": 0, "steps_failed": 0, "artefacts_written": 0},
            "current_step": None,
            "override_text": None,
        }
        append_run(SETTINGS.workspace_root, hub_scope["athlete_id"], record)
        st.session_state["plan_hub_running"] = True
        st.session_state["plan_hub_active_run_id"] = run_id
        _ensure_worker(
            SETTINGS.workspace_root,
            hub_scope["athlete_id"],
            run_id,
            allow_delete=False,
            process_subtype="orchestrated",
        )
        st.info("Run requested (placeholder).")

    if run_scoped:
        desired_subtype = PLANNING_SCOPE_SUBTYPE.get(scope, "scoped")
        block_reason = _planning_block_reason(
            SETTINGS.workspace_root,
            hub_scope["athlete_id"],
            desired_subtype,
        )
        if block_reason:
            st.warning(block_reason)
            st.stop()
        if not _is_week_in_scope(base_week):
            st.warning("Planning scope is limited to the current or next ISO week.")
            st.stop()
        if override_required and not (override_text or "").strip():
            st.warning("Override required when modifying existing artifacts.")
            st.stop()
        steps = _build_execution_steps(run_readiness, "Scoped", scope)
        log_ref = ensure_logging(hub_scope["athlete_id"])
        for step in steps:
            step["Log"] = log_ref
        record = {
            "run_id": run_id,
            "athlete_id": hub_scope["athlete_id"],
            "iso_year": hub_scope["iso_year"],
            "iso_week": hub_scope["iso_week"],
            "phase_label": hub_scope.get("phase_label"),
            "mode": "Scoped",
            "process_type": "planning",
            "process_subtype": desired_subtype,
            "scope": scope,
            "status": "QUEUED",
            "steps": steps,
            "log_ref": log_ref,
            "summary": {"steps_done": 0, "steps_failed": 0, "artefacts_written": 0},
            "current_step": None,
            "override_text": (override_text or "").strip() or None,
        }
        append_run(SETTINGS.workspace_root, hub_scope["athlete_id"], record)
        st.session_state["plan_hub_running"] = True
        st.session_state["plan_hub_active_run_id"] = run_id
        _ensure_worker(SETTINGS.workspace_root, hub_scope["athlete_id"], run_id, allow_delete=False, process_subtype=desired_subtype)
        st.info("Run requested (placeholder).")

if summary_text:
    st.info(summary_text)

st.subheader("Run Execution")
if active_run:
    steps = active_run.get("steps") or []
    if active_run.get("log_ref"):
        st.caption(f"Log file: {active_run.get('log_ref')}")
    if active_run.get("status") == "FAILED":
        if any(step.get("Details") == "Athlete lock busy." for step in steps):
            st.info("Another run is active for this athlete. Try again after it finishes.")
    can_restart = False
    if active_run.get("status") == "FAILED":
        store = LocalArtifactStore(root=SETTINGS.workspace_root)
        can_restart = store.latest_exists(hub_scope["athlete_id"], ArtifactType.SEASON_SCENARIO_SELECTION)
    if active_run.get("summary"):
        summary = active_run.get("summary") or {}
        st.caption(
            "Summary: "
            f"{summary.get('steps_done', 0)} done · "
            f"{summary.get('steps_failed', 0)} failed · "
            f"{summary.get('artefacts_written', 0)} outputs"
        )
    if active_run.get("current_step"):
        st.caption(f"Current step: {active_run.get('current_step')}")
    manual_missing = False
    if any(step.get("step_id") == "SCENARIO_SELECTION" and step.get("Status") == "FAILED" for step in steps):
        store = LocalArtifactStore(root=SETTINGS.workspace_root)
        manual_missing = not store.latest_exists(hub_scope["athlete_id"], ArtifactType.SEASON_SCENARIO_SELECTION)
    if manual_missing:
        st.info("Scenario selection is manual. Complete it on the Season page, then restart the run.")
        st.page_link("pages/plan/season.py", label="Go to Season page")
    if can_restart and st.button("Restart run"):
        new_run_id = f"plan_hub_{hub_scope['iso_year']:04d}W{hub_scope['iso_week']:02d}_{int(time.time())}"
        readiness = _compute_readiness(hub_scope["athlete_id"], hub_scope["iso_year"], hub_scope["iso_week"])
        new_steps = _build_execution_steps(readiness, "Orchestrated", None)
        log_ref = ensure_logging(hub_scope["athlete_id"])
        for step in new_steps:
            step["Log"] = log_ref
        record = {
            "run_id": new_run_id,
            "athlete_id": hub_scope["athlete_id"],
            "iso_year": hub_scope["iso_year"],
            "iso_week": hub_scope["iso_week"],
            "phase_label": hub_scope.get("phase_label"),
            "mode": "Orchestrated",
            "scope": None,
            "status": "QUEUED",
            "steps": new_steps,
            "log_ref": log_ref,
            "summary": {"steps_done": 0, "steps_failed": 0, "artefacts_written": 0},
            "current_step": None,
            "override_text": None,
        }
        append_run(SETTINGS.workspace_root, hub_scope["athlete_id"], record)
        _mark_runs_superseded(
            SETTINGS.workspace_root,
            hub_scope["athlete_id"],
            [active_run.get("run_id")] if active_run.get("run_id") else [],
            new_run_id,
        )
        st.session_state["plan_hub_running"] = True
        st.session_state["plan_hub_active_run_id"] = new_run_id
        _ensure_worker(
            SETTINGS.workspace_root,
            hub_scope["athlete_id"],
            new_run_id,
            allow_delete=False,
            process_subtype=active_run.get("process_subtype"),
        )
        st.rerun()
    st.dataframe(steps, width="stretch")
    events = load_events(SETTINGS.workspace_root, hub_scope["athlete_id"], active_run.get("run_id") or "", limit=200)
    if events:
        with st.expander("Run events", expanded=False):
            event_types = sorted({event.get("type") for event in events if event.get("type")})
            filter_options = ["All", "STEP_*", "RUN_*"] + event_types
            default_index = 1 if active_run and active_run.get("status") in {"QUEUED", "RUNNING"} else 0
            selected_filter = st.selectbox("Filter", options=filter_options, index=default_index)
            event_rows = []
            for event in events:
                event_type = event.get("type") or ""
                if selected_filter == "STEP_*" and not event_type.startswith("STEP_"):
                    continue
                if selected_filter == "RUN_*" and not event_type.startswith("RUN_"):
                    continue
                if selected_filter not in {"All", "STEP_*", "RUN_*"} and event_type != selected_filter:
                    continue
                event_rows.append(
                    {
                        "Timestamp": event.get("ts") or "—",
                        "Type": event_type or "—",
                        "Step": event.get("step_id") or "—",
                        "Details": event.get("reason") or event.get("outputs") or "—",
                    }
                )
            st.dataframe(pd.DataFrame(event_rows), width="stretch")
    cols = st.columns(2)
    if cols[0].button("Mark run done"):
        update_run(
            SETTINGS.workspace_root,
            hub_scope["athlete_id"],
            active_run.get("run_id") or "",
            {"status": "DONE"},
        )
        st.session_state["plan_hub_running"] = False
        st.session_state["plan_hub_active_run_id"] = None
        st.rerun()
    if cols[1].button("Clear run state"):
        st.session_state["plan_hub_running"] = False
        st.session_state["plan_hub_active_run_id"] = None
        st.rerun()
    if st.button("Cancel run"):
        update_run(
            SETTINGS.workspace_root,
            hub_scope["athlete_id"],
            active_run.get("run_id") or "",
            {"cancel_requested": True},
        )
        st.info("Cancel requested. The worker will stop after the current step.")
        st.rerun()
else:
    st.info("No active run. Start planning to see execution steps.")
logger = logging.getLogger(__name__)
