from __future__ import annotations

import json

import streamlit as st

from rps.agents.multi_output_runner import run_agent_multi_output
from rps.agents.registry import AGENTS
from rps.agents.tasks import AgentTask
from rps.orchestrator.plan_week import _build_injection_block
from rps.ui.shared import (
    CAPTURE_LOGGERS,
    SETTINGS,
    announce_log_file,
    append_system_log,
    capture_output,
    get_athlete_id,
    get_iso_year_week,
    init_ui_state,
    load_rendered_markdown,
    make_ui_run_id,
    multi_runtime_for,
)
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType


st.title("Season")

state = init_ui_state()
athlete_id = get_athlete_id()
year, week = get_iso_year_week()
announce_log_file(athlete_id)

st.caption(f"Athlete: {athlete_id}")

store = LocalArtifactStore(root=SETTINGS.workspace_root)


def _format_agent_result(result: object | None, fallback: str) -> str:
    if isinstance(result, dict):
        return json.dumps(result, indent=2)
    return fallback


def _action_scenarios() -> str:
    runtime = multi_runtime_for("season_scenario")
    spec = AGENTS["season_scenario"]
    injected_block = _build_injection_block("season_scenario", mode="scenario")
    user_input = (
        "Mode A. Generate the pre-decision scenarios. "
        f"Target ISO week: {year}-{week:02d}. "
        "Use workspace_get_input for Season Brief and Events. "
        f"{injected_block}"
        "Follow the Mandatory Output Chapter for SEASON_SCENARIOS."
    )
    run_id = make_ui_run_id(f"season_scenarios_{year}_{week:02d}")
    result, output = capture_output(
        lambda: run_agent_multi_output(
            runtime,
            agent_name=spec.name,
            agent_vs_name=spec.vector_store_name,
            athlete_id=athlete_id,
            tasks=[AgentTask.CREATE_SEASON_SCENARIOS],
            user_input=user_input,
            run_id=run_id,
            model_override=SETTINGS.model_for_agent(spec.name),
            temperature_override=SETTINGS.temperature_for_agent(spec.name),
            force_file_search=True,
            max_num_results=SETTINGS.file_search_max_results,
        ),
        loggers=CAPTURE_LOGGERS,
    )
    return output or _format_agent_result(result, f"Scenarios created: {run_id}")


def _action_select_scenario(selected: str, rationale: str | None) -> str:
    runtime = multi_runtime_for("season_scenario")
    spec = AGENTS["season_scenario"]
    injected_block = _build_injection_block("season_scenario", mode="scenario")
    rationale_line = f"Rationale: {rationale.strip()}. " if rationale else ""
    user_input = (
        f"Select Scenario {selected.upper()} for ISO week {year}-{week:02d}. "
        "Use the latest SEASON_SCENARIOS as context. "
        f"{rationale_line}"
        f"{injected_block}"
        "Follow the Mandatory Output Chapter for SEASON_SCENARIO_SELECTION."
    )
    run_id = make_ui_run_id(f"season_scenario_selection_{year}_{week:02d}")
    result, output = capture_output(
        lambda: run_agent_multi_output(
            runtime,
            agent_name=spec.name,
            agent_vs_name=spec.vector_store_name,
            athlete_id=athlete_id,
            tasks=[AgentTask.CREATE_SEASON_SCENARIO_SELECTION],
            user_input=user_input,
            run_id=run_id,
            model_override=SETTINGS.model_for_agent(spec.name),
            temperature_override=SETTINGS.temperature_for_agent(spec.name),
            force_file_search=True,
            max_num_results=SETTINGS.file_search_max_results,
        ),
        loggers=CAPTURE_LOGGERS,
    )
    return output or _format_agent_result(result, f"Scenario {selected.upper()} selected.")


def _action_season_plan(selected: str) -> str:
    runtime = multi_runtime_for("season_planner")
    spec = AGENTS["season_planner"]
    injected_block = _build_injection_block("season_planner", mode="season_plan")
    user_input = (
        f"Scenario {selected.upper()}. Mode A. Create the SEASON_PLAN. "
        f"Target ISO week: {year}-{week:02d}. "
        "Use the latest SEASON_SCENARIO_SELECTION and SEASON_SCENARIOS as context. "
        f"{injected_block}"
        "Follow the Mandatory Output Chapter for SEASON_PLAN."
    )
    run_id = make_ui_run_id(f"season_plan_{year}_{week:02d}")
    result, output = capture_output(
        lambda: run_agent_multi_output(
            runtime,
            agent_name=spec.name,
            agent_vs_name=spec.vector_store_name,
            athlete_id=athlete_id,
            tasks=[AgentTask.CREATE_SEASON_PLAN],
            user_input=user_input,
            run_id=run_id,
            model_override=SETTINGS.model_for_agent(spec.name),
            temperature_override=SETTINGS.temperature_for_agent(spec.name),
            force_file_search=True,
            max_num_results=SETTINGS.file_search_max_results,
        ),
        loggers=CAPTURE_LOGGERS,
    )
    return output or _format_agent_result(result, f"Season plan created: {run_id}")


has_plan = store.latest_exists(athlete_id, ArtifactType.SEASON_PLAN)
if has_plan:
    st.success("Season plan exists for this athlete.")
    rendered = load_rendered_markdown(athlete_id, ArtifactType.SEASON_PLAN)
    if rendered:
        st.markdown(rendered)
    else:
        plan_payload = store.load_latest(athlete_id, ArtifactType.SEASON_PLAN)
        st.json(plan_payload)
    st.stop()


if st.button("Create Scenarios"):
    append_system_log("season", "Create Scenarios started.")
    output = _action_scenarios()
    state["season_scenarios_output"] = output
    append_system_log("season", "Create Scenarios done.")

if output := state.get("season_scenarios_output"):
    with st.expander("Create Scenarios Output", expanded=False):
        st.code(output)

scenarios_payload = None
if store.latest_exists(athlete_id, ArtifactType.SEASON_SCENARIOS):
    scenarios_payload = store.load_latest(athlete_id, ArtifactType.SEASON_SCENARIOS)

if not scenarios_payload:
    st.info("No SEASON_SCENARIOS found yet.")
    st.stop()

st.subheader("Season Scenarios")
rendered = load_rendered_markdown(athlete_id, ArtifactType.SEASON_SCENARIOS)
if rendered:
    st.markdown(rendered)
else:
    scenarios = scenarios_payload.get("data", {}).get("scenarios", [])
    for scenario in scenarios:
        scenario_id = scenario.get("scenario_id", "?")
        st.markdown(f"**Scenario {scenario_id}: {scenario.get('name', '')}**")
        st.markdown(f"- Core idea: {scenario.get('core_idea', 'N/A')}")
        st.markdown(f"- Load philosophy: {scenario.get('load_philosophy', 'N/A')}")
        st.markdown(f"- Risk profile: {scenario.get('risk_profile', 'N/A')}")
        st.markdown(f"- Key differences: {scenario.get('key_differences', 'N/A')}")
        st.markdown(f"- Best suited if: {scenario.get('best_suited_if', 'N/A')}")

selection_payload = None
if store.latest_exists(athlete_id, ArtifactType.SEASON_SCENARIO_SELECTION):
    selection_payload = store.load_latest(athlete_id, ArtifactType.SEASON_SCENARIO_SELECTION)

selected_default = None
if selection_payload:
    selected_default = selection_payload.get("data", {}).get("selected_scenario_id")

scenario_options = [s.get("scenario_id") for s in scenarios_payload.get("data", {}).get("scenarios", [])]
scenario_options = [opt for opt in scenario_options if opt]

if not scenario_options:
    st.info("No scenario IDs available to select.")
    st.stop()

st.subheader("Scenario Selection")
selected = st.radio(
    "Choose scenario",
    options=scenario_options,
    index=scenario_options.index(selected_default) if selected_default in scenario_options else 0,
    horizontal=True,
)
rationale = st.text_area("Rationale (optional)")

if st.button("Confirm Scenario Selection"):
    append_system_log("season", f"Selecting scenario {selected}.")
    output = _action_select_scenario(selected, rationale)
    state["season_selection_output"] = output
    append_system_log("season", f"Scenario {selected} selected.")
    st.rerun()

if output := state.get("season_selection_output"):
    with st.expander("Scenario Selection Output", expanded=False):
        st.code(output)

if store.latest_exists(athlete_id, ArtifactType.SEASON_SCENARIO_SELECTION):
    st.subheader("Create Season Plan")
    if st.button("Create Season Plan"):
        append_system_log("season", "Create Season Plan started.")
        output = _action_season_plan(selected)
        state["season_plan_output"] = output
        append_system_log("season", "Create Season Plan done.")
        st.rerun()

if output := state.get("season_plan_output"):
    with st.expander("Create Season Plan Output", expanded=False):
        st.code(output)
