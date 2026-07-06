from __future__ import annotations

import json
import os
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path

import streamlit as st

from rps.agents.runtime import resolve_agent_runtime_selection
from rps.crewai_runtime.coach_chat import (
    CoachTool,
    ConversationalSurface,
    SpecialistToolsets,
    run_conversational_turn,
)
from rps.crewai_runtime.flows import run_coach_flow
from rps.orchestrator.coach_operations import (
    apply_feed_forward_operation,
    apply_report_operation,
    apply_scoped_week_replan_operation,
    apply_week_plan_preview,
    preview_change_start_time_operation,
    preview_feed_forward_operation,
    preview_move_workout_operation,
    preview_read_context,
    preview_report_operation,
    preview_scoped_week_replan_operation,
    preview_update_workout_text_operation,
)
from rps.orchestrator.context_snapshots import (
    build_advisory_memory_prompt_block,
    build_athlete_state_snapshot_prompt_block,
    build_current_week_status_snapshot_prompt_block,
    build_planning_context_snapshot_prompt_block,
    ensure_current_week_status_snapshot,
)
from rps.orchestrator.week_plan_edits import list_week_plan_workouts, load_week_plan_for_edit
from rps.planning.deterministic_context import (
    build_coach_operation_context,
    render_coach_operation_context_block,
)
from rps.tools.workspace_read_tools import ReadToolContext, read_tool_handlers
from rps.ui.run_store import append_run, update_run
from rps.ui.shared import (
    SETTINGS,
    get_athlete_id,
    get_iso_year_week,
    init_ui_state,
    make_ui_run_id,
    multi_runtime_for,
    render_status_panel,
    set_status,
    ui_log,
)
from rps.workspace.iso_helpers import IsoWeek
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType

JsonMap = dict[str, object]
COACH_PENDING_KEY = "coach_pending_operation"
COACH_CONTEXT_KEY = "coach_context_key"
COACH_MESSAGES_KEY = "coach_messages"
COACH_ACTIVE_RUN_ID_KEY = "coach_active_run_id"


def _coach_preload_specs(year: int, week: int) -> list[tuple[str, str, dict[str, object]]]:
    """Return the auto-preloaded Coach workspace artefacts and inputs."""
    week_key = f"{year:04d}-{week:02d}"
    return [
        ("athlete_profile", "workspace_get_input", {"input_type": "athlete_profile"}),
        ("planning_events", "workspace_get_input", {"input_type": "planning_events"}),
        ("logistics", "workspace_get_input", {"input_type": "logistics"}),
        ("availability", "workspace_get_input", {"input_type": "availability"}),
        ("activities_actual", "workspace_get_version", {"artifact_type": "ACTIVITIES_ACTUAL", "version_key": week_key}),
        ("activities_trend", "workspace_get_version", {"artifact_type": "ACTIVITIES_TREND", "version_key": week_key}),
        ("season_plan", "workspace_get_latest", {"artifact_type": "SEASON_PLAN"}),
        ("phase_preview", "workspace_get_version", {"artifact_type": "PHASE_PREVIEW", "version_key": week_key}),
        ("phase_guardrails", "workspace_get_version", {"artifact_type": "PHASE_GUARDRAILS", "version_key": week_key}),
        ("kpi_profile", "workspace_get_latest", {"artifact_type": "KPI_PROFILE"}),
        ("zone_model", "workspace_get_latest", {"artifact_type": "ZONE_MODEL"}),
        ("wellness", "workspace_get_latest", {"artifact_type": "WELLNESS"}),
    ]


def _as_map(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _load_selected_week_artifact(
    store: LocalArtifactStore,
    athlete_id: str,
    artifact_type: ArtifactType,
    week_key: str,
) -> dict[str, object] | None:
    version_key = store.resolve_week_version_key(athlete_id, artifact_type, week_key)
    if not version_key:
        return None
    try:
        return _as_map(store.load_version(athlete_id, artifact_type, version_key))
    except FileNotFoundError:
        return None


def _coach_memory_blocks(athlete_id: str, year: int, week: int) -> list[str]:
    """Load preferred snapshot/advisory memory blocks for Coach."""
    payloads = _coach_memory_payloads(athlete_id, year, week)
    blocks: list[str] = []
    athlete_snapshot = payloads.get("athlete_snapshot")
    if athlete_snapshot:
        blocks.append(build_athlete_state_snapshot_prompt_block(athlete_snapshot))
    planning_snapshot = payloads.get("planning_snapshot")
    if planning_snapshot:
        blocks.append(build_planning_context_snapshot_prompt_block(planning_snapshot))
    current_week_status = payloads.get("current_week_status")
    if current_week_status:
        blocks.append(build_current_week_status_snapshot_prompt_block(current_week_status))
    advisory_memory = payloads.get("advisory_memory")
    if advisory_memory:
        blocks.append(build_advisory_memory_prompt_block(advisory_memory))
    return [block for block in blocks if block.strip()]


def _coach_memory_payloads(athlete_id: str, year: int, week: int) -> dict[str, dict[str, object]]:
    """Load Coach-preferred snapshot payloads for the selected week."""

    store = LocalArtifactStore(root=SETTINGS.workspace_root)
    week_key = f"{year:04d}-{week:02d}"
    week_plan_payload = _load_selected_week_artifact(store, athlete_id, ArtifactType.WEEK_PLAN, week_key) or {}
    return {
        "week_plan": week_plan_payload,
        "athlete_snapshot": store.load_latest_payload(athlete_id, ArtifactType.ATHLETE_STATE_SNAPSHOT) or {},
        "planning_snapshot": _load_selected_week_artifact(
            store, athlete_id, ArtifactType.PLANNING_CONTEXT_SNAPSHOT, week_key
        )
        or {},
        "current_week_status": ensure_current_week_status_snapshot(
            store,
            athlete_id,
            target_week=IsoWeek(year=year, week=week),
            run_id="coach_current_week_status",
            week_plan_payload=week_plan_payload,
        )
        or {},
        "advisory_memory": _load_selected_week_artifact(store, athlete_id, ArtifactType.ADVISORY_MEMORY, week_key)
        or {},
    }


def _prompt_block_map(payload: dict[str, object] | None) -> dict[str, str]:
    """Return string prompt blocks from a snapshot/advisory payload."""

    if not isinstance(payload, dict):
        return {}
    data = payload.get("data")
    if not isinstance(data, dict):
        return {}
    prompt_blocks = data.get("prompt_blocks")
    if not isinstance(prompt_blocks, dict):
        return {}
    return {str(key): str(value) for key, value in prompt_blocks.items() if isinstance(value, str) and value.strip()}


def _extract_keyed_lines(block: str) -> dict[str, str]:
    """Parse simple `key: value` lines from a memory block."""

    parsed: dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key_clean = key.strip()
        value_clean = value.strip()
        if key_clean and value_clean and not key_clean.startswith("**"):
            parsed[key_clean] = value_clean
    return parsed


def _extract_bullets(block: str) -> list[str]:
    """Return markdown bullet lines from a memory block."""

    return [line.strip() for line in block.splitlines() if line.strip().startswith("- ")]


def _extract_section_bullets(block: str, section_name: str) -> list[str]:
    """Return bullet lines that belong to a named section within a memory block."""

    bullets: list[str] = []
    in_section = False
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line:
            if in_section:
                break
            continue
        if line.endswith(":") and not line.startswith("- "):
            in_section = line[:-1] == section_name
            continue
        if in_section and line.startswith("- "):
            bullets.append(line)
        elif in_section and not line.startswith("- "):
            break
    return bullets


def _extract_section_rows(block: str, section_name: str) -> list[list[str]]:
    """Return pipe-delimited row values from a named bullet section."""

    rows: list[list[str]] = []
    for bullet in _extract_section_bullets(block, section_name):
        payload = bullet[2:].strip()
        rows.append([part.strip() or "-" for part in payload.split("|")])
    return rows


def _markdown_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    """Build a markdown table from headers and row values."""

    if not rows:
        return []
    normalized_rows: list[list[str]] = []
    width = len(headers)
    for row in rows:
        padded = (row + (["-"] * width))[:width]
        normalized_rows.append([cell.replace("|", "\\|") for cell in padded])
    header_line = "| " + " | ".join(headers) + " |"
    divider_line = "| " + " | ".join(["---"] * width) + " |"
    body_lines = ["| " + " | ".join(row) + " |" for row in normalized_rows]
    return [header_line, divider_line, *body_lines]


def _coach_intro_message(
    *,
    year: int,
    week: int,
    payloads: dict[str, dict[str, object]],
    pending: JsonMap | None,
) -> str | None:
    """Build one deterministic startup summary from Coach memory payloads."""

    planning_blocks = _prompt_block_map(payloads.get("planning_snapshot"))
    advisory_blocks = _prompt_block_map(payloads.get("advisory_memory"))
    phase = _extract_keyed_lines(planning_blocks.get("phase", ""))
    load = _extract_keyed_lines(planning_blocks.get("load_governance", ""))
    week_summary = _extract_keyed_lines(advisory_blocks.get("week", ""))
    planned_workout_rows = _extract_section_rows(
        advisory_blocks.get("current_week_plan", ""),
        "planned_workouts_table",
    )
    if not planned_workout_rows:
        week_plan_payload_raw = payloads.get("week_plan")
        week_plan_payload: dict[str, object] = week_plan_payload_raw if isinstance(week_plan_payload_raw, dict) else {}
        planned_workout_rows = [
            [
                str(row.get("day") or "-"),
                str(row.get("date") or "-"),
                str(row.get("day_role") or "-"),
                str(row.get("title") or "-"),
                str(row.get("duration") or row.get("planned_duration") or "-"),
                (str(row.get("planned_kj")) + " kJ") if row.get("planned_kj") not in (None, "") else "-",
            ]
            for row in list_week_plan_workouts(week_plan_payload)
            if isinstance(row, dict)
        ]
    current_status_blocks = _prompt_block_map(payloads.get("current_week_status"))
    current_actuals = _extract_keyed_lines(current_status_blocks.get("current_week_actuals", ""))
    completed_session_rows = _extract_section_rows(
        current_status_blocks.get("current_week_actuals", ""),
        "completed_sessions_table",
    )
    plan_vs_actual = _extract_keyed_lines(current_status_blocks.get("plan_vs_actual", ""))
    open_planned_day_rows = _extract_section_rows(
        current_status_blocks.get("plan_vs_actual", ""),
        "open_planned_days_table",
    )

    if not phase and not week_summary and not planned_workout_rows and not current_actuals and not completed_session_rows and not plan_vs_actual:
        return None

    lines = [f"Context loaded for {year:04d}-{week:02d}."]
    lines.extend(["", "**Phase Summary**"])
    phase_name = phase.get("phase_name")
    phase_type = phase.get("phase_type")
    phase_index = phase.get("phase_week_index")
    phase_range = phase.get("phase_iso_week_range")
    if phase_name or phase_type:
        phase_line = "- "
        if phase_name:
            phase_line += phase_name
        if phase_type:
            phase_line += f" ({phase_type})" if phase_name else phase_type
        if phase_index:
            phase_line += f", week {phase_index}"
        if phase_range:
            phase_line += f", range {phase_range}"
        lines.append(phase_line)
    band = next(
        (
            value
            for key, value in load.items()
            if key.startswith("phase_guardrails.active_weekly_kj_band")
        ),
        "",
    )
    if band:
        lines.append(f"- Active load governance: {band}")

    lines.extend(["", "**Week Summary**"])
    objective = week_summary.get("week_objective")
    if objective:
        lines.append(f"- Objective: {objective}")
    planned_load = week_summary.get("planned_weekly_load_kj")
    if planned_load:
        lines.append(f"- Planned weekly load: {planned_load}")
    if planned_workout_rows:
        lines.extend(["", "Planned workouts:", ""])
        lines.extend(
            _markdown_table(
                ["Day", "Date", "Day-Role", "Title", "Planned Duration", "Planned Load (kJ)"],
                planned_workout_rows,
            )
        )
        lines.append("")

    if current_actuals or completed_session_rows:
        lines.extend(["", "**Current Week Actuals**"])
        completed_count = current_actuals.get("completed_sessions_count")
        if completed_count:
            lines.append(f"- Completed sessions so far: {completed_count}")
        completed_time = current_actuals.get("completed_moving_time")
        if completed_time:
            lines.append(f"- Completed moving time: {completed_time}")
        completed_work = current_actuals.get("completed_work_kj")
        if completed_work:
            lines.append(f"- Completed work: {completed_work} kJ")
        if completed_session_rows:
            lines.extend(["", "Completed sessions:", ""])
            lines.extend(
                _markdown_table(
                    ["Day", "Date", "Type", "Title", "Actual Duration", "Actual Load (kJ)", "IF", "TSS"],
                    completed_session_rows,
                )
            )
            lines.append("")

    if plan_vs_actual:
        lines.extend(["", "**Plan vs Actual**"])
        matched_days = plan_vs_actual.get("matched_planned_days_count")
        if matched_days:
            lines.append(f"- Matched planned days: {matched_days}")
        open_days = plan_vs_actual.get("open_planned_days_count")
        if open_days:
            lines.append(f"- Open planned days: {open_days}")
        unplanned_days = plan_vs_actual.get("unplanned_completed_days_count")
        if unplanned_days:
            lines.append(f"- Unplanned completed days: {unplanned_days}")
        completed_work_so_far = plan_vs_actual.get("completed_work_kj_so_far")
        if completed_work_so_far:
            lines.append(f"- Completed work so far: {completed_work_so_far} kJ")
        if open_planned_day_rows:
            lines.extend(["", "Open planned day details:", ""])
            lines.extend(
                _markdown_table(
                    ["Day", "Date", "Day-Role", "Title", "Planned Duration", "Planned Load (kJ)"],
                    open_planned_day_rows,
                )
            )
            lines.append("")

    if pending:
        lines.extend(["", "**Pending Status**"])
        lines.append(f"- Pending operation: {str(pending.get('summary') or 'Pending coach operation exists.')}")
    return "\n".join(lines)


def _json_result(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _coach_pending() -> JsonMap | None:
    pending = st.session_state.get(COACH_PENDING_KEY)
    return pending if isinstance(pending, dict) else None


def _coach_reset(context_key: str) -> None:
    st.session_state.pop(COACH_MESSAGES_KEY, None)
    st.session_state.pop(COACH_PENDING_KEY, None)
    st.session_state[COACH_CONTEXT_KEY] = context_key


def _coach_messages() -> list[JsonMap]:
    messages = st.session_state.setdefault(COACH_MESSAGES_KEY, [])
    if not isinstance(messages, list):
        messages = []
        st.session_state[COACH_MESSAGES_KEY] = messages
    return messages


def _start_coach_turn_run(*, athlete_id: str, year: int, week: int, user_message: str) -> str:
    """Create one foreground run-store record for a Coach turn."""

    run_id = make_ui_run_id(f"coach_turn_{year}_{week:02d}")
    append_run(
        SETTINGS.workspace_root,
        athlete_id,
        {
            "run_id": run_id,
            "status": "RUNNING",
            "mode": "Interactive",
            "process_type": "COACH",
            "process_subtype": "TURN",
            "scope": f"{year:04d}-{week:02d}",
            "message": user_message,
            "current_step": "coach_flow",
            "started_at": datetime.now(UTC).isoformat(),
        },
    )
    return run_id


def _coach_summary(messages: list[JsonMap]) -> str:
    latest_user = ""
    for message in reversed(messages):
        if str(message.get("role") or "") == "user":
            latest_user = str(message.get("content") or "").strip()
            break
    if not latest_user:
        return "New Chat"
    words = latest_user.split()
    return " ".join(words[:4]) if words else "New Chat"


def _coach_base_document(
    store: LocalArtifactStore,
    athlete_id: str,
    year: int,
    week: int,
) -> JsonMap:
    pending = _coach_pending()
    if pending:
        document = pending.get("document")
        if isinstance(document, dict):
            return document
    return load_week_plan_for_edit(store, athlete_id, year, week)


def _active_coach_functions(
    *,
    store: LocalArtifactStore,
    athlete_id: str,
    year: int,
    week: int,
) -> list[CoachTool]:
    version_key = f"{year:04d}-{week:02d}"

    def _read_current_plan_context() -> str:
        preview = preview_read_context(store=store, athlete_id=athlete_id, year=year, week=week)
        return preview.model_dump_json(indent=2)

    def _list_current_week_plan_workouts() -> str:
        try:
            document = _coach_base_document(store, athlete_id, year, week)
        except FileNotFoundError:
            return _json_result(
                {
                    "ok": False,
                    "message": f"No WEEK_PLAN exists for {version_key}. Plan the week first.",
                }
            )
        return _json_result(
            {
                "ok": True,
                "iso_week": version_key,
                "pending_operation_present": bool(_coach_pending()),
                "workouts": list_week_plan_workouts(document),
            }
        )

    def _preview_move_workout(workout_id: str, target_day: str, target_start: str | None = None) -> str:
        base = _coach_base_document(store, athlete_id, year, week)
        preview = preview_move_workout_operation(
            base,
            year=year,
            week=week,
            workout_id=workout_id,
            target_day=target_day,
            target_start=target_start,
        )
        st.session_state[COACH_PENDING_KEY] = preview.model_dump()
        return preview.model_dump_json(indent=2)

    def _preview_change_start_time(workout_id: str, start: str) -> str:
        base = _coach_base_document(store, athlete_id, year, week)
        preview = preview_change_start_time_operation(base, workout_id=workout_id, start=start)
        st.session_state[COACH_PENDING_KEY] = preview.model_dump()
        return preview.model_dump_json(indent=2)

    def _preview_update_workout_text(
        workout_id: str,
        workout_text: str,
        title: str | None = None,
        notes: str | None = None,
        start: str | None = None,
    ) -> str:
        base = _coach_base_document(store, athlete_id, year, week)
        preview = preview_update_workout_text_operation(
            base,
            workout_id=workout_id,
            workout_text=workout_text,
            title=title,
            notes=notes,
            start=start,
        )
        st.session_state[COACH_PENDING_KEY] = preview.model_dump()
        return preview.model_dump_json(indent=2)

    def _preview_scoped_week_replan(message: str) -> str:
        active_run_id = st.session_state.get(COACH_ACTIVE_RUN_ID_KEY)
        preview_run_id = (
            f"{active_run_id}_preview"
            if isinstance(active_run_id, str) and active_run_id
            else make_ui_run_id(f"coach_preview_scoped_replan_{year}_{week:02d}")
        )
        preview = preview_scoped_week_replan_operation(
            multi_runtime_for,
            store=store,
            athlete_id=athlete_id,
            year=year,
            week=week,
            message=message,
            run_id=preview_run_id,
            model_resolver=SETTINGS.model_for_agent,
            temperature_resolver=SETTINGS.temperature_for_agent,
        )
        st.session_state[COACH_PENDING_KEY] = preview.model_dump()
        return preview.model_dump_json(indent=2)

    def _preview_run_performance_report() -> str:
        preview = preview_report_operation(year=year, week=week)
        st.session_state[COACH_PENDING_KEY] = preview.model_dump()
        return preview.model_dump_json(indent=2)

    def _preview_run_feed_forward() -> str:
        preview = preview_feed_forward_operation(year=year, week=week)
        st.session_state[COACH_PENDING_KEY] = preview.model_dump()
        return preview.model_dump_json(indent=2)

    def _show_pending_coach_operation() -> str:
        pending = _coach_pending()
        if not pending:
            return _json_result({"ok": False, "message": "No pending coach operation."})
        metadata = pending.get("metadata")
        metadata_map = metadata if isinstance(metadata, dict) else {}
        return _json_result(
            {
                "ok": True,
                **pending,
                "change_table_markdown": metadata_map.get("change_table_markdown"),
                "diff_text": metadata_map.get("diff_text"),
            }
        )

    def _discard_pending_coach_operation() -> str:
        st.session_state.pop(COACH_PENDING_KEY, None)
        return _json_result({"ok": True, "message": "Pending coach operation discarded."})

    def _apply_pending_coach_operation() -> str:
        pending = _coach_pending()
        if not pending:
            return _json_result({"ok": False, "message": "No pending coach operation to apply."})
        if isinstance(pending.get("issues"), list) and pending["issues"]:
            return _json_result(
                {
                    "ok": False,
                    "message": "Pending coach operation still has validation issues.",
                    "issues": pending["issues"],
                }
            )
        operation = str(pending.get("operation") or "")
        active_run_id = st.session_state.get(COACH_ACTIVE_RUN_ID_KEY)
        run_id = (
            str(active_run_id)
            if isinstance(active_run_id, str) and active_run_id
            else make_ui_run_id(f"coach_op_{operation}_{year}_{week:02d}")
        )
        if operation == "preview_artifact_edit":
            document = pending.get("document")
            if not isinstance(document, dict):
                return _json_result({"ok": False, "message": "Pending edit document missing or invalid."})
            result = apply_week_plan_preview(
                workspace_root=store.root,
                athlete_id=athlete_id,
                document=document,
                run_id=run_id,
            )
        elif operation == "preview_scoped_replan":
            document = pending.get("document")
            if isinstance(document, dict):
                applied = apply_week_plan_preview(
                    workspace_root=store.root,
                    athlete_id=athlete_id,
                    document=document,
                    run_id=run_id,
                )
                result = applied.model_copy(
                    update={
                        "operation": "apply_scoped_replan",
                        "summary": (
                            f"Scoped week replan applied for {year:04d}-{week:02d}."
                            if applied.ok
                            else f"Scoped week replan failed for {year:04d}-{week:02d}."
                        ),
                    }
                )
            else:
                metadata = pending.get("metadata")
                metadata_map = metadata if isinstance(metadata, dict) else {}
                message = str(metadata_map.get("message") or "")
                result = apply_scoped_week_replan_operation(
                    multi_runtime_for,
                    workspace_root=store.root,
                    athlete_id=athlete_id,
                    year=year,
                    week=week,
                    message=message,
                    run_id=run_id,
                    model_resolver=SETTINGS.model_for_agent,
                    temperature_resolver=SETTINGS.temperature_for_agent,
                )
        elif operation == "preview_report":
            result = apply_report_operation(
                multi_runtime_for,
                athlete_id=athlete_id,
                year=year,
                week=week,
                run_id=run_id,
                model_resolver=SETTINGS.model_for_agent,
                temperature_resolver=SETTINGS.temperature_for_agent,
            )
        elif operation == "preview_feed_forward":
            result = apply_feed_forward_operation(
                multi_runtime_for,
                workspace_root=Path(SETTINGS.workspace_root),
                athlete_id=athlete_id,
                year=year,
                week=week,
                run_id=run_id,
                model_resolver=SETTINGS.model_for_agent,
                temperature_resolver=SETTINGS.temperature_for_agent,
            )
        else:
            return _json_result({"ok": False, "message": f"Unsupported pending operation: {operation}"})
        output = result.model_dump()
        if result.ok:
            st.session_state.pop(COACH_PENDING_KEY, None)
        return _json_result(output)

    return [
        CoachTool(
            name="read_current_plan_context",
            description="Return selected-week planning context and current workout summary for the active coach.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=lambda: _read_current_plan_context(),
        ),
        CoachTool(
            name="list_current_week_plan_workouts",
            description="Return the current selected week's agenda-linked workouts and metadata.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=lambda: _list_current_week_plan_workouts(),
        ),
        CoachTool(
            name="preview_move_workout",
            description="Preview moving one workout to an empty target day within the selected ISO week.",
            parameters={
                "type": "object",
                "properties": {
                    "workout_id": {"type": "string"},
                    "target_day": {"type": "string"},
                    "target_start": {"type": ["string", "null"]},
                },
                "required": ["workout_id", "target_day"],
                "additionalProperties": False,
            },
            handler=_preview_move_workout,
        ),
        CoachTool(
            name="preview_change_start_time",
            description="Preview changing one workout start time.",
            parameters={
                "type": "object",
                "properties": {"workout_id": {"type": "string"}, "start": {"type": "string"}},
                "required": ["workout_id", "start"],
                "additionalProperties": False,
            },
            handler=_preview_change_start_time,
        ),
        CoachTool(
            name="preview_update_workout_text",
            description="Preview replacing a workout's workout_text and optional title, notes, or start time.",
            parameters={
                "type": "object",
                "properties": {
                    "workout_id": {"type": "string"},
                    "workout_text": {"type": "string"},
                    "title": {"type": ["string", "null"]},
                    "notes": {"type": ["string", "null"]},
                    "start": {"type": ["string", "null"]},
                },
                "required": ["workout_id", "workout_text"],
                "additionalProperties": False,
            },
            handler=_preview_update_workout_text,
        ),
        CoachTool(
            name="preview_scoped_week_replan",
            description="Preview a scoped week replan for the selected ISO week using a coach message.",
            parameters={
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
                "additionalProperties": False,
            },
            handler=_preview_scoped_week_replan,
        ),
        CoachTool(
            name="preview_run_performance_report",
            description="Preview running DES analysis report generation for the selected ISO week.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=lambda: _preview_run_performance_report(),
        ),
        CoachTool(
            name="preview_run_feed_forward",
            description="Preview running the report and feed-forward chain for the selected ISO week.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=lambda: _preview_run_feed_forward(),
        ),
        CoachTool(
            name="show_pending_coach_operation",
            description="Return the currently pending coach operation preview, if one exists.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=lambda: _show_pending_coach_operation(),
        ),
        CoachTool(
            name="discard_pending_coach_operation",
            description="Discard the currently pending coach operation preview.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=lambda: _discard_pending_coach_operation(),
        ),
        CoachTool(
            name="apply_pending_coach_operation",
            description="Apply the currently pending coach operation after explicit confirmation.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=lambda: _apply_pending_coach_operation(),
        ),
    ]


def _coach_specialist_toolsets(tools: list[CoachTool]) -> SpecialistToolsets:
    """Return strict per-specialist tool visibility for the Coach conversational crew."""

    by_name = {tool.name: tool for tool in tools}
    context_names = [
        "read_current_plan_context",
        "list_current_week_plan_workouts",
    ]
    preview_names = [
        "preview_scoped_week_replan",
    ]
    pending_names = [
        "show_pending_coach_operation",
        "apply_pending_coach_operation",
        "discard_pending_coach_operation",
    ]
    return SpecialistToolsets(
        context=[by_name[name] for name in context_names if name in by_name],
        recommendation=[],
        preview=[by_name[name] for name in preview_names if name in by_name],
        pending=[by_name[name] for name in pending_names if name in by_name],
    )


init_ui_state()
athlete_id = get_athlete_id()
year, week = get_iso_year_week()
coach_context_key = f"{athlete_id}:{year:04d}-{week:02d}"
if st.session_state.get(COACH_CONTEXT_KEY) != coach_context_key:
    _coach_reset(coach_context_key)

st.title("Coach")
st.caption(f"Athlete: {athlete_id}")
set_status(status_state="done", title="Coach", message="Ready.")
render_status_panel()

runtime_selection = resolve_agent_runtime_selection()
if runtime_selection.effective_backend == "crewai":
    st.caption("Agent runtime: CrewAI")
else:
    st.caption(f"Agent runtime: legacy fallback. {runtime_selection.reason}")

ctx = ReadToolContext(
    athlete_id=athlete_id,
    workspace_root=SETTINGS.workspace_root,
)
handlers = read_tool_handlers(ctx)
tools = _active_coach_functions(
    store=LocalArtifactStore(root=SETTINGS.workspace_root),
    athlete_id=athlete_id,
    year=year,
    week=week,
)
toolsets = _coach_specialist_toolsets(tools)

preload_enabled = os.getenv("RPS_COACH_PRELOAD_ARTIFACTS", "1").lower() in {"1", "true", "yes"}
per_artifact_max = int(os.getenv("RPS_COACH_PRELOAD_MAX_CHARS", "12000"))
snapshot_blocks: list[str] = []
context_chunks: list[str] = []

def _stringify(value: object) -> str:
    text = json.dumps(value, ensure_ascii=False)
    if len(text) > per_artifact_max:
        return text[:per_artifact_max] + "...(truncated)"
    return text

def _append_context(label: str, fn, args: dict[str, object]) -> None:
    try:
        result = fn(args)
    except Exception as exc:
        result = {"ok": False, "error": str(exc)}
    context_chunks.append(f"{label}:\n{_stringify(result)}")

if preload_enabled:
    with suppress(Exception):
        snapshot_blocks = _coach_memory_blocks(athlete_id, year, week)
    if not snapshot_blocks:
        for label, handler_name, args in _coach_preload_specs(year, week):
            handler = handlers.get(handler_name)
            if handler is None:
                continue
            _append_context(label, handler, args)

conversation_context_parts: list[str] = []
if snapshot_blocks:
    conversation_context_parts.append(
        "Workspace memory (auto-loaded, preferred).\n" + "\n\n".join(snapshot_blocks)
    )
elif context_chunks:
    conversation_context_parts.append(
        "Workspace artifacts (fallback raw reads):\n" + "\n\n".join(context_chunks)
    )
conversation_context_parts.append(
    "\n".join(
        [
            f"Active coach scope: athlete={athlete_id}, iso_week={year:04d}-{week:02d}.",
            "No claim of persistence is allowed before apply succeeds.",
            "This surface is the active Coach chat for selected-week analysis, coaching, previews, and pending-resolution.",
        ]
    )
)
pending_snapshot = _coach_pending()
conversation_context_parts.append(
    render_coach_operation_context_block(
        build_coach_operation_context(
            athlete_id=athlete_id,
            target_week=IsoWeek(year=year, week=week),
            pending_operation=pending_snapshot if isinstance(pending_snapshot, dict) else None,
        )
    )
)
if pending_snapshot:
    conversation_context_parts.append(
        "Current pending coach operation snapshot:\n"
        + json.dumps(pending_snapshot, ensure_ascii=False, indent=2)
    )
conversation_context = "\n\n".join(part for part in conversation_context_parts if part.strip())

surface = ConversationalSurface(
    name="coach",
    scope_summary=f"athlete={athlete_id}, iso_week={year:04d}-{week:02d}",
    shared_context=conversation_context,
    prompts_dir=SETTINGS.prompts_dir,
)
model = SETTINGS.model_for_agent("coach")
base_url = os.getenv("RPS_LLM_BASE_URL")
key_hint = "set" if os.getenv("RPS_LLM_API_KEY") else "missing"
ui_log(f"Coach initialized with model={model} base_url={base_url or 'default'} api_key={key_hint}")

pending = _coach_pending()
if pending:
    summary = str(pending.get("summary") or "Pending coach operation exists.")
    issues = pending.get("issues")
    if isinstance(issues, list) and issues:
        st.warning(f"Pending coach operation has validation issues. {summary}")
    else:
        st.info(f"Pending coach operation ready to apply. {summary}")
messages = _coach_messages()
if not messages:
    intro = _coach_intro_message(
        year=year,
        week=week,
        payloads=_coach_memory_payloads(athlete_id, year, week),
        pending=pending,
    )
    if intro:
        messages.append({"role": "assistant", "content": intro})
st.info(f"Summary: {_coach_summary(messages)}")
for message in messages:
    role = str(message.get("role") or "assistant")
    content = str(message.get("content") or "")
    with st.chat_message(role):
        st.markdown(content)

prompt = st.chat_input("Ask the active coach to inspect, adjust, or replan…")
if prompt:
    user_prompt = prompt
    messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)
    if runtime_selection.effective_backend != "crewai" or not runtime_selection.can_execute:
        reply = (
            "Coach conversation runtime is not executable in this interpreter. "
            f"{runtime_selection.reason}"
        )
    else:
        turn_run_id = _start_coach_turn_run(
            athlete_id=athlete_id,
            year=year,
            week=week,
            user_message=user_prompt,
        )
        st.session_state[COACH_ACTIVE_RUN_ID_KEY] = turn_run_id
        with st.spinner("Coach is thinking…"):
            try:
                flow_result = run_coach_flow(
                    workspace_root=Path(SETTINGS.workspace_root),
                    athlete_id=athlete_id,
                    run_id=turn_run_id,
                    user_message=user_prompt,
                    chat_runner=lambda: run_conversational_turn(
                        surface=surface,
                        user_message=user_prompt,
                        history=messages[:-1],
                        toolsets=toolsets,
                        model_override=model,
                        temperature_override=SETTINGS.temperature_for_agent("coach"),
                        workspace_root=Path(SETTINGS.workspace_root),
                        athlete_id=athlete_id,
                        run_id=turn_run_id,
                    ),
                )
                reply = flow_result["response"]
                update_run(
                    SETTINGS.workspace_root,
                    athlete_id,
                    turn_run_id,
                    {
                        "status": "DONE",
                        "current_step": None,
                        "route": flow_result.get("route"),
                        "message": user_prompt,
                        "finished_at": datetime.now(UTC).isoformat(),
                    },
                )
            except Exception as exc:
                reply = f"Coach turn failed: {exc}"
                update_run(
                    SETTINGS.workspace_root,
                    athlete_id,
                    turn_run_id,
                    {
                        "status": "FAILED",
                        "current_step": None,
                        "message": user_prompt,
                        "finished_at": datetime.now(UTC).isoformat(),
                    },
                )
            finally:
                st.session_state.pop(COACH_ACTIVE_RUN_ID_KEY, None)
    messages.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.markdown(reply)
