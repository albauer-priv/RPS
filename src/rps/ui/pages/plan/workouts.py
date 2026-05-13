from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import streamlit as st

from rps.crewai_runtime.coach_chat import (
    CoachTool,
    ConversationalSurface,
    SpecialistToolsets,
    run_conversational_turn,
)
from rps.orchestrator.week_plan_edits import (
    WeekPlanApplyResult,
    apply_week_plan_edit,
    list_week_plan_workouts,
    load_week_plan_for_edit,
    preview_change_start_time,
    preview_move_workout,
    preview_update_workout_text,
)
from rps.orchestrator.week_revision import revise_week_plan
from rps.ui.intervals_post import delete_posted_workouts, post_to_intervals_commit
from rps.ui.shared import (
    CAPTURE_LOGGERS,
    SETTINGS,
    announce_log_file,
    append_system_log,
    capture_output,
    duration_minutes_from_workout_text,
    format_duration_hhmm,
    get_athlete_id,
    get_iso_year_week,
    init_ui_state,
    iso_week_date_range,
    make_ui_run_id,
    multi_runtime_for,
    parse_duration_minutes,
    render_global_sidebar,
    render_status_panel,
    set_status,
)
from rps.workspace.iso_helpers import parse_iso_week
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType

JsonMap = dict[str, object]
HistoryWorkoutRow = dict[str, str]
EDITOR_CHAT_KEY = "workout_editor_chat"
EDITOR_PENDING_KEY = "workout_editor_pending"
EDITOR_CONTEXT_KEY = "workout_editor_context"


def _as_map(value: object) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _json_result(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _editor_reset(context_key: str) -> None:
    st.session_state.pop(EDITOR_CHAT_KEY, None)
    st.session_state.pop(EDITOR_PENDING_KEY, None)
    st.session_state[EDITOR_CONTEXT_KEY] = context_key


def _editor_pending() -> JsonMap | None:
    pending = st.session_state.get(EDITOR_PENDING_KEY)
    return pending if isinstance(pending, dict) else None


def _editor_base_document(store: LocalArtifactStore, athlete_id: str, year: int, week: int) -> JsonMap:
    pending = _editor_pending()
    if pending:
        document = pending.get("document")
        if isinstance(document, dict):
            return document
    return load_week_plan_for_edit(store, athlete_id, year, week)


def _workout_editor_tools(
    *,
    store: LocalArtifactStore,
    athlete_id: str,
    year: int,
    week: int,
    version_key: str,
) -> list[CoachTool]:
    schema_dir = Path("specs/schemas")

    def _list_current_week_plan_workouts() -> str:
        try:
            document = _editor_base_document(store, athlete_id, year, week)
        except FileNotFoundError:
            return _json_result(
                {
                    "ok": False,
                    "message": f"No WEEK_PLAN exists for {version_key}. Plan the week first.",
                }
            )
        pending = _editor_pending()
        return _json_result(
            {
                "ok": True,
                "iso_week": version_key,
                "pending_edit_present": bool(pending),
                "workouts": list_week_plan_workouts(document),
            }
        )

    def _preview_move_workout(workout_id: str, target_day: str, target_start: str | None = None) -> str:
        base = _editor_base_document(store, athlete_id, year, week)
        preview = preview_move_workout(
            base,
            year=year,
            week=week,
            workout_id=workout_id,
            target_day=target_day,
            target_start=target_start,
        )
        st.session_state[EDITOR_PENDING_KEY] = json.loads(preview.to_json())
        append_system_log("workouts", f"Workout editor preview created: move {workout_id} -> {target_day} ({version_key}).")
        return preview.to_json()

    def _preview_change_start_time(workout_id: str, start: str) -> str:
        base = _editor_base_document(store, athlete_id, year, week)
        preview = preview_change_start_time(base, workout_id=workout_id, start=start)
        st.session_state[EDITOR_PENDING_KEY] = json.loads(preview.to_json())
        append_system_log("workouts", f"Workout editor preview created: start {workout_id} -> {start} ({version_key}).")
        return preview.to_json()

    def _preview_update_workout_text(
        workout_id: str,
        workout_text: str,
        title: str | None = None,
        notes: str | None = None,
        start: str | None = None,
    ) -> str:
        base = _editor_base_document(store, athlete_id, year, week)
        preview = preview_update_workout_text(
            base,
            workout_id=workout_id,
            workout_text=workout_text,
            title=title,
            notes=notes,
            start=start,
        )
        st.session_state[EDITOR_PENDING_KEY] = json.loads(preview.to_json())
        append_system_log("workouts", f"Workout editor preview created: text update {workout_id} ({version_key}).")
        return preview.to_json()

    def _show_pending_week_plan_edit() -> str:
        pending = _editor_pending()
        if not pending:
            return _json_result({"ok": False, "message": "No pending edit."})
        return _json_result({"ok": True, **pending})

    def _discard_pending_week_plan_edit() -> str:
        st.session_state.pop(EDITOR_PENDING_KEY, None)
        append_system_log("workouts", f"Workout editor pending edit discarded for {version_key}.")
        return _json_result({"ok": True, "message": "Pending edit discarded."})

    def _apply_pending_week_plan_edit() -> str:
        pending = _editor_pending()
        if not pending:
            return _json_result({"ok": False, "message": "No pending edit to apply."})
        issues = pending.get("issues")
        if isinstance(issues, list) and issues:
            return _json_result(
                {
                    "ok": False,
                    "message": "Pending edit still has validation issues. Fix or discard it before apply.",
                    "issues": issues,
                }
            )
        document = pending.get("document")
        if not isinstance(document, dict):
            return _json_result({"ok": False, "message": "Pending edit document missing or invalid."})

        run_id = make_ui_run_id(f"workout_editor_apply_{year}_{week:02d}")
        append_system_log("workouts", f"Workout editor apply started for {version_key}.")
        try:
            result = apply_week_plan_edit(
                workspace_root=store.root,
                schema_dir=schema_dir,
                athlete_id=athlete_id,
                document=document,
                run_id=run_id,
            )
            output = json.loads(result.to_json())
            if result.ok:
                st.session_state.pop(EDITOR_PENDING_KEY, None)
                append_system_log("workouts", f"Workout editor apply completed for {version_key}.")
            else:
                append_system_log("workouts", f"Workout editor apply failed for {version_key}: {result.error or result.summary}")
            return _json_result(output)
        except Exception as exc:
            append_system_log("workouts", f"Workout editor apply failed for {version_key}: {exc}")
            failed = WeekPlanApplyResult(
                ok=False,
                summary="Workout editor apply failed.",
                week_plan_version_key=None,
                week_plan_path=None,
                export_version_key=None,
                export_path=None,
                error=str(exc),
            )
            return failed.to_json()

    return [
        CoachTool(
            name="list_current_week_plan_workouts",
            description="Return the current selected week's agenda-linked workouts and basic metadata.",
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
            description="Preview changing one workout's start time.",
            parameters={
                "type": "object",
                "properties": {
                    "workout_id": {"type": "string"},
                    "start": {"type": "string"},
                },
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
            name="show_pending_week_plan_edit",
            description="Return the currently pending preview edit, if one exists.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=lambda: _show_pending_week_plan_edit(),
        ),
        CoachTool(
            name="discard_pending_week_plan_edit",
            description="Discard the currently pending week-plan edit preview.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=lambda: _discard_pending_week_plan_edit(),
        ),
        CoachTool(
            name="apply_pending_week_plan_edit",
            description="Store the current pending week-plan edit and rebuild the workout export.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=lambda: _apply_pending_week_plan_edit(),
        ),
    ]


def _workout_editor_toolsets(tools: list[CoachTool]) -> SpecialistToolsets:
    """Return strict per-specialist tool visibility for the Workout Editor crew."""

    by_name = {tool.name: tool for tool in tools}
    return SpecialistToolsets(
        context=[by_name[name] for name in ["list_current_week_plan_workouts"] if name in by_name],
        recommendation=[],
        preview=[
            by_name[name]
            for name in [
                "preview_move_workout",
                "preview_change_start_time",
                "preview_update_workout_text",
            ]
            if name in by_name
        ],
        pending=[
            by_name[name]
            for name in [
                "show_pending_week_plan_edit",
                "apply_pending_week_plan_edit",
                "discard_pending_week_plan_edit",
            ]
            if name in by_name
        ],
    )


state = init_ui_state()
render_global_sidebar()
athlete_id = get_athlete_id()
year, week = get_iso_year_week()
announce_log_file(athlete_id)

week_start, week_end = iso_week_date_range(year, week)
st.title(f"Workouts · {week_start} to {week_end}")
st.caption(f"Athlete: {athlete_id}")
set_status(status_state="done", title="Workouts", message="Ready.")
render_status_panel()

store = LocalArtifactStore(root=SETTINGS.workspace_root)
version_key = f"{year:04d}-{week:02d}"
editor_context_key = f"{athlete_id}:{version_key}"
if st.session_state.get(EDITOR_CONTEXT_KEY) != editor_context_key:
    _editor_reset(editor_context_key)

with st.expander("Actions", expanded=False):
    with st.form("workouts_actions"):
        post_submit = st.form_submit_button("Post to Intervals")
        delete_submit = st.form_submit_button("Delete posted workouts")
        delete_removed = st.checkbox("Delete removed workouts", value=False)

    with st.form("workouts_revise"):
        message = st.text_area("Message to coach (Week Planner)")
        revise_submit = st.form_submit_button("Revise week plan")

if post_submit:
    result = post_to_intervals_commit(
        store,
        athlete_id,
        year=year,
        week=week,
        run_id=f"post_intervals_{version_key}",
        allow_delete=delete_removed,
    )
    if result.ok:
        st.success(
            f"Posted {result.posted} workouts (skipped {result.skipped}, deleted {result.deleted})."
        )
    else:
        st.error(result.error or "Intervals posting failed.")

if delete_submit:
    result = delete_posted_workouts(
        store,
        athlete_id,
        year=year,
        week=week,
        run_id=f"delete_intervals_{version_key}",
    )
    if result.ok:
        st.success(f"Deleted {result.deleted} posted workouts.")
    else:
        st.error(result.error or "Intervals delete failed.")

if revise_submit:
    if not message.strip():
        st.warning("Please provide a message for the Week Planner.")
    else:
        run_id = make_ui_run_id(f"workouts_revise_{year}_{week:02d}")
        append_system_log("workouts", f"Revise Week Plan started for {version_key}.")
        set_status(
            status_state="running",
            title="Workouts",
            message=f"Revising week {version_key}...",
            last_action="Revise Week Plan",
            last_run_id=run_id,
        )
        raw_result, output = capture_output(
            lambda: revise_week_plan(
                lambda name: multi_runtime_for(name),
                athlete_id=athlete_id,
                year=year,
                week=week,
                message=message,
                run_id=run_id,
                model_resolver=SETTINGS.model_for_agent,
                temperature_resolver=SETTINGS.temperature_for_agent,
                force_file_search=True,
                max_num_results=SETTINGS.file_search_max_results,
            ),
            loggers=CAPTURE_LOGGERS,
        )
        revise_result = raw_result
        status = "done" if isinstance(revise_result, dict) or getattr(revise_result, "ok", False) else "error"
        set_status(
            status_state=status,
            title="Workouts",
            message=f"Revise complete for {version_key}.",
            last_action="Revise Week Plan",
            last_run_id=run_id,
        )
        if output:
            with st.expander("Revise output", expanded=False):
                st.code(output)

week_plan_payload = None
try:
    week_plan_payload = store.load_version(athlete_id, ArtifactType.WEEK_PLAN, version_key)
except FileNotFoundError:
    week_plan_payload = None

st.subheader("Workout Editor")
pending = _editor_pending()
if pending:
    summary = str(pending.get("summary") or "Pending edit exists.")
    issues = pending.get("issues")
    if isinstance(issues, list) and issues:
        st.warning(f"Pending edit has validation issues. {summary}")
    else:
        st.info(f"Pending edit ready to apply. {summary}")

if not isinstance(week_plan_payload, dict):
    st.info("Workout Editor requires an existing WEEK_PLAN for the selected ISO week.")
else:
    editor_tools = _workout_editor_tools(
        store=store,
        athlete_id=athlete_id,
        year=year,
        week=week,
        version_key=version_key,
    )
    toolsets = _workout_editor_toolsets(editor_tools)
    surface = ConversationalSurface(
        name="workout_editor",
        scope_summary=f"athlete={athlete_id}, iso_week={version_key}",
        shared_context=(
            f"Current editor scope: athlete={athlete_id}, iso_week={version_key}.\n"
            "All changes apply only to this selected ISO week.\n"
            "No claim of persistence is allowed before apply succeeds.\n"
            "This surface is the bounded Workout Editor chat for selected-week workout edits.\n"
            f"Current pending editor operation: {json.dumps(_editor_pending(), ensure_ascii=False) if _editor_pending() else 'none'}"
        ),
        prompts_dir=SETTINGS.prompts_dir,
    )
    messages = st.session_state.setdefault(EDITOR_CHAT_KEY, [])
    if not isinstance(messages, list):
        messages = []
        st.session_state[EDITOR_CHAT_KEY] = messages
    st.caption("Bounded editor for the selected week. The editor previews first and only writes after explicit confirmation.")
    with st.expander("Editor Examples", expanded=False):
        st.markdown("- Move the Saturday workout to Sunday.\n- Change the Tuesday workout start time to 19:00.\n- Replace the Thursday workout text with an easier endurance session.")
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role") or "assistant")
        content = str(message.get("content") or "")
        if not content.strip():
            continue
        with st.chat_message(role):
            st.markdown(content)
    prompt = st.chat_input("Move a workout, change a start time, or replace workout text…", key="workout_editor_chat_input")
    if prompt and prompt.strip():
        messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        try:
            reply = run_conversational_turn(
                surface=surface,
                user_message=prompt,
                history=messages[:-1],
                toolsets=toolsets,
                model_override=SETTINGS.model_for_agent("workout_editor"),
                temperature_override=SETTINGS.temperature_for_agent("workout_editor"),
                workspace_root=Path(SETTINGS.workspace_root),
                athlete_id=athlete_id,
                run_id=make_ui_run_id(f"workout_editor_chat_{year}_{week:02d}"),
            )
        except Exception as exc:
            reply = f"Workout editor failed: {exc}"
        messages.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.markdown(reply)
    try:
        week_plan_payload = store.load_version(athlete_id, ArtifactType.WEEK_PLAN, version_key)
    except FileNotFoundError:
        week_plan_payload = None

intervals_payload = None
try:
    intervals_payload = store.load_version(athlete_id, ArtifactType.INTERVALS_WORKOUTS, version_key)
except FileNotFoundError:
    try:
        intervals_payload = store.load_latest(athlete_id, ArtifactType.INTERVALS_WORKOUTS)
    except FileNotFoundError:
        intervals_payload = None

if not isinstance(intervals_payload, list) or not intervals_payload:
    st.info("No Intervals workouts found for this week.")
else:
    day_lookup: dict[str, list[dict[str, str]]] = {}
    if isinstance(week_plan_payload, dict):
        week_plan_data = _as_map(week_plan_payload.get("data"))
        agenda_rows = _as_list(week_plan_data.get("agenda"))
        workout_rows = _as_list(week_plan_data.get("workouts"))
        workout_map = {
            _as_map(workout).get("workout_id"): _as_map(workout)
            for workout in workout_rows
            if _as_map(workout).get("workout_id")
        }
        for row in agenda_rows:
            row_map = _as_map(row)
            workout_id = row_map.get("workout_id")
            workout = workout_map.get(workout_id, {})
            name = workout.get("title") or workout_id or "Workout"
            date = row_map.get("date") or ""
            duration = row_map.get("planned_duration") or workout.get("duration") or ""
            load_kj = str(row_map.get("planned_kj") or "")
            day = str(row_map.get("day") or "")
            date_key = str(date)
            if date_key:
                day_lookup.setdefault(date_key, []).append(
                    {
                        "name": str(name),
                        "duration": str(duration),
                        "load_kj": load_kj,
                        "day": day,
                    }
                )

    st.subheader("Current Week Workouts")
    for item in intervals_payload:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or "Workout"
        start = item.get("start_date_local") or ""
        description = item.get("description") or ""
        date_str = start.split("T")[0] if "T" in start else start
        time_str = start.split("T")[1][:5] if "T" in start else ""
        duration_source = ""
        load_kj = ""
        day = ""
        if date_str and date_str in day_lookup:
            candidates = day_lookup[date_str]
            match: dict[str, str] | None
            if len(candidates) == 1:
                match = candidates[0]
            else:
                match = None
                name_lower = name.lower()
                for candidate in candidates:
                    if candidate["name"].lower() in name_lower:
                        match = candidate
                        break
                if match is None:
                    match = candidates[0]
            duration_source = match.get("duration", "")
            load_kj = match.get("load_kj", "")
            day = match.get("day", "")
        duration_minutes = parse_duration_minutes(duration_source) if duration_source else 0
        if not duration_minutes:
            duration_minutes = duration_minutes_from_workout_text(description)
        duration_label = format_duration_hhmm(duration_minutes)
        header = name
        if day:
            focus = name.split(" - ")[-1] if " - " in name else name
            if isinstance(focus, str) and focus.lower().startswith(day.lower()):
                focus = focus[len(day) :].lstrip()
            header = f"{day}: {focus}"
            if duration_label:
                header = f"{header} - {duration_label} Duration"
            if load_kj:
                header = f"{header} - {load_kj} kJ Load"
        else:
            if date_str:
                header = f"{header} · {date_str}"
            if time_str:
                header = f"{header} {time_str}"
            if duration_label:
                header = f"{header} · {duration_label}"
        with st.expander(header, expanded=False):
            st.code(description)

st.subheader("Workouts History")
exports_dir = store.root / athlete_id / "data" / "exports"
workout_files = sorted(exports_dir.glob("workouts_*.json"), reverse=True)

if not workout_files:
    st.info("No exported workouts found yet.")
else:
    month_map: dict[str, dict[str, list[HistoryWorkoutRow]]] = defaultdict(lambda: defaultdict(list))
    for path in workout_files:
        week_label = path.stem.replace("workouts_", "")
        iso_week = parse_iso_week(week_label)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            continue
        for item in payload:
            if not isinstance(item, dict):
                continue
            start = item.get("start_date_local") or ""
            date_str = start.split("T")[0] if "T" in start else ""
            if date_str:
                try:
                    month_key = datetime.fromisoformat(date_str).strftime("%Y-%m")
                except ValueError:
                    month_key = week_label
            elif iso_week:
                month_key = datetime.fromisocalendar(iso_week.year, iso_week.week, 1).strftime("%Y-%m")
            else:
                month_key = "unknown"
            month_map[month_key][week_label].append(
                {
                    "name": item.get("name") or "Workout",
                    "start": start or "—",
                    "description": item.get("description") or "",
                }
            )

    for month_key in sorted(month_map.keys(), reverse=True):
        with st.expander(month_key, expanded=False):
            month_weeks = month_map[month_key]
            for week_label in sorted(month_weeks.keys(), reverse=True):
                with st.expander(f"Week {week_label}", expanded=False):
                    for workout_row in month_weeks[week_label]:
                        st.markdown(f"**{workout_row['name']}** · {workout_row['start']}")
                        if workout_row["description"]:
                            st.code(workout_row["description"])
