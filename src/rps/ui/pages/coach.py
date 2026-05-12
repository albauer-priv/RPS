from __future__ import annotations

import json
import os
from contextlib import suppress
from pathlib import Path

import streamlit as st

from rps.agents.knowledge_injection import build_injection_block
from rps.agents.runtime import resolve_agent_runtime_selection
from rps.crewai_runtime.coach_chat import CoachTool, run_coach_turn
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
    build_planning_context_snapshot_prompt_block,
)
from rps.orchestrator.week_plan_edits import list_week_plan_workouts, load_week_plan_for_edit
from rps.prompts.loader import PromptLoader
from rps.tools.workspace_read_tools import ReadToolContext, read_tool_defs, read_tool_handlers
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
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType

JsonMap = dict[str, object]
COACH_PENDING_KEY = "coach_pending_operation"
COACH_CONTEXT_KEY = "coach_context_key"
COACH_MESSAGES_KEY = "coach_messages"


def _coach_preload_specs(year: int, week: int) -> list[tuple[str, str, dict[str, object]]]:
    """Return the auto-preloaded Coach workspace artefacts and inputs."""
    week_key = f"{year:04d}-{week:02d}"
    return [
        ("athlete_profile", "workspace_get_input", {"input_type": "athlete_profile"}),
        ("planning_events", "workspace_get_input", {"input_type": "planning_events"}),
        ("logistics", "workspace_get_input", {"input_type": "logistics"}),
        ("availability", "workspace_get_input", {"input_type": "availability"}),
        ("activities_trend", "workspace_get_version", {"artifact_type": "ACTIVITIES_TREND", "version_key": week_key}),
        ("activities_actual", "workspace_get_version", {"artifact_type": "ACTIVITIES_ACTUAL", "version_key": week_key}),
        ("season_plan", "workspace_get_latest", {"artifact_type": "SEASON_PLAN"}),
        ("phase_preview", "workspace_get_version", {"artifact_type": "PHASE_PREVIEW", "version_key": week_key}),
        ("phase_guardrails", "workspace_get_version", {"artifact_type": "PHASE_GUARDRAILS", "version_key": week_key}),
        ("kpi_profile", "workspace_get_latest", {"artifact_type": "KPI_PROFILE"}),
        ("zone_model", "workspace_get_latest", {"artifact_type": "ZONE_MODEL"}),
        ("wellness", "workspace_get_latest", {"artifact_type": "WELLNESS"}),
    ]


def _as_map(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _load_latest_payload(
    store: LocalArtifactStore,
    athlete_id: str,
    artifact_type: ArtifactType,
) -> dict[str, object] | None:
    try:
        return _as_map(store.load_latest(athlete_id, artifact_type))
    except Exception:
        return None


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
    store = LocalArtifactStore(root=SETTINGS.workspace_root)
    week_key = f"{year:04d}-{week:02d}"
    blocks: list[str] = []
    athlete_snapshot = _load_latest_payload(store, athlete_id, ArtifactType.ATHLETE_STATE_SNAPSHOT)
    if athlete_snapshot:
        blocks.append(build_athlete_state_snapshot_prompt_block(athlete_snapshot))
    planning_snapshot = _load_selected_week_artifact(
        store, athlete_id, ArtifactType.PLANNING_CONTEXT_SNAPSHOT, week_key
    )
    if planning_snapshot:
        blocks.append(build_planning_context_snapshot_prompt_block(planning_snapshot))
    advisory_memory = _load_selected_week_artifact(store, athlete_id, ArtifactType.ADVISORY_MEMORY, week_key)
    if advisory_memory:
        blocks.append(build_advisory_memory_prompt_block(advisory_memory))
    return [block for block in blocks if block.strip()]


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
        preview = preview_scoped_week_replan_operation(year=year, week=week, message=message)
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
        return _json_result({"ok": True, **pending})

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
        run_id = make_ui_run_id(f"coach_op_{operation}_{year}_{week:02d}")
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
                max_num_results=SETTINGS.file_search_max_results,
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
                max_num_results=SETTINGS.file_search_max_results,
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
                max_num_results=SETTINGS.file_search_max_results,
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
tools: list[CoachTool] = []
for spec in read_tool_defs():
    raw_name = spec.get("name")
    if not isinstance(raw_name, str):
        continue
    name = raw_name
    handler = handlers.get(name)
    if handler is None:
        continue
    description = spec.get("description", "")
    if not isinstance(description, str):
        description = ""
    parameters = spec.get("parameters", {})
    if not isinstance(parameters, dict):
        parameters = {}

    def _wrap(h=handler):
        return lambda **kwargs: _json_result(h(kwargs))

    tools.append(
        CoachTool(
            name=name,
            description=description,
            parameters=parameters,
            handler=_wrap(),
        )
    )

tools.extend(
    _active_coach_functions(
        store=LocalArtifactStore(root=SETTINGS.workspace_root),
        athlete_id=athlete_id,
        year=year,
        week=week,
    )
)

prompt_loader = PromptLoader(SETTINGS.prompts_dir)
base_prompt = prompt_loader.combined_system_prompt("coach")
base_prompt = base_prompt.replace("SEASON_BRIEF_YEAR", str(year))
injected = build_injection_block("coach", mode="coach")

instructions = base_prompt
if injected:
    instructions = f"{base_prompt}\n\n{injected}"

preload_enabled = os.getenv("RPS_COACH_PRELOAD_ARTIFACTS", "1").lower() in {"1", "true", "yes"}
if preload_enabled:
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

    with suppress(Exception):
        snapshot_blocks = _coach_memory_blocks(athlete_id, year, week)

    if snapshot_blocks:
        instructions = (
            f"{instructions}\n\n"
            "Workspace memory (auto-loaded, preferred). Use these derived blocks before raw artefact reads:\n"
            + "\n\n".join(snapshot_blocks)
        )
    else:
        for label, handler_name, args in _coach_preload_specs(year, week):
            _append_context(label, handlers[handler_name], args)

        if context_chunks:
            instructions = (
                f"{instructions}\n\n"
                "Workspace artifacts (auto-loaded fallback). Use these instead of asking for missing artifacts:\n"
                + "\n\n".join(context_chunks)
            )

instructions = (
    f"{instructions}\n\n"
    f"Active coach scope: athlete={athlete_id}, iso_week={year:04d}-{week:02d}.\n"
    "You can inspect plan context, preview bounded week-plan edits, preview scoped week replans, "
    "preview report/feed-forward runs, and apply only after explicit confirmation.\n"
    "Never claim that a change was stored before apply_pending_coach_operation succeeds."
)
model = os.getenv("RPS_LLM_MODEL_COACH") or os.getenv("RPS_LLM_MODEL") or "openai/gpt-5-mini"
base_url = os.getenv("RPS_LLM_BASE_URL_COACH") or os.getenv("RPS_LLM_BASE_URL")
key_hint = "set" if os.getenv("RPS_LLM_API_KEY_COACH") or os.getenv("RPS_LLM_API_KEY") else "missing"
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
st.info(f"Summary: {_coach_summary(messages)}")
for message in messages:
    role = str(message.get("role") or "assistant")
    content = str(message.get("content") or "")
    with st.chat_message(role):
        st.markdown(content)

prompt = st.chat_input("Ask the active coach to inspect, adjust, or replan…")
if prompt:
    messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    if runtime_selection.effective_backend != "crewai" or not runtime_selection.can_execute:
        reply = (
            "Coach conversation runtime is not executable in this interpreter. "
            f"{runtime_selection.reason}"
        )
    else:
        with st.spinner("Coach is thinking…"):
            try:
                reply = run_coach_turn(
                    instructions=instructions,
                    user_message=prompt,
                    history=messages[:-1],
                    tools=tools,
                    agent_name="coach",
                    model_override=model,
                )
            except Exception as exc:
                reply = f"Coach turn failed: {exc}"
    messages.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.markdown(reply)
