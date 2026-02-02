from __future__ import annotations

import json
from datetime import date, datetime, timezone

import streamlit as st
from jinja2 import BaseLoader, Environment

from rps.orchestrator.season_flow import create_season_plan, create_season_scenarios
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
    render_phase_markdown,
    render_global_sidebar,
    render_status_panel,
    set_status,
)
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType

ISO_WEEK_RANGE_FALLBACK = "N/A"

st.title("Season")

state = init_ui_state()
render_global_sidebar()
athlete_id = get_athlete_id()
year, week = get_iso_year_week()
announce_log_file(athlete_id)

st.caption(f"Athlete: {athlete_id}")

store = LocalArtifactStore(root=SETTINGS.workspace_root)
has_plan = store.latest_exists(athlete_id, ArtifactType.SEASON_PLAN)

SCENARIO_TEMPLATE = """
### Metadata
| Field | Value |
| --- | --- |
| Scenario ID | {{ scenario.scenario_id or 'N/A' }} |
| Name | {{ scenario.name or 'N/A' }} |
| Selected week range | {{ selection.selection_iso_week_range or 'N/A' }} |
| Selection rationale | {{ selection.selection_rationale or 'N/A' }} |
| Deload cadence | {{ guidance.deload_cadence or 'N/A' }} |
| Phase length (weeks) | {{ guidance.phase_length_weeks or 'N/A' }} |
| Phase count expected | {{ guidance.phase_count_expected or 'N/A' }} |
| Shortened phases allowed | {{ guidance.max_shortened_phases or 'N/A' }} |
| Shortening budget (weeks) | {{ guidance.shortening_budget_weeks or 'N/A' }} |
| Fixed rest days | {{ guidance.fixed_rest_days | join(', ') or 'N/A' }} |
| Constraint summary | {% if guidance.constraint_summary %}{% for item in guidance.constraint_summary %}{{ item }}<br>{% endfor %}{% else %}N/A{% endif %} |
| KPI guardrail notes | {% if guidance.kpi_guardrail_notes %}{% for note in guidance.kpi_guardrail_notes %}{{ note }}<br>{% endfor %}{% else %}N/A{% endif %} |
| Intensity guidance | Allowed: {{ guidance.intensity_guidance.allowed_domains | join(', ') or 'N/A' }}<br>Avoid: {{ guidance.intensity_guidance.avoid_domains | join(', ') or 'N/A' }} |

### Macro Intent & Principles
| Area | Details |
| --- | --- |
| Core idea | {{ scenario.core_idea or 'N/A' }} |
| Load philosophy | {{ scenario.load_philosophy or 'N/A' }} |
| Risk profile | {{ scenario.risk_profile or 'N/A' }} |
| Key differences | {{ scenario.key_differences or 'N/A' }} |
| Best suited if | {{ scenario.best_suited_if or 'N/A' }} |
| Decision notes | {% if guidance.decision_notes %}{% for note in guidance.decision_notes %}{{ note }}<br>{% endfor %}{% else %}None{% endif %} |
| Event alignment notes | {% if guidance.event_alignment_notes %}{% for note in guidance.event_alignment_notes %}{{ note }}<br>{% endfor %}{% else %}None{% endif %} |
| Risk flags | {% if guidance.risk_flags %}{% for note in guidance.risk_flags %}{{ note }}<br>{% endfor %}{% else %}None{% endif %} |
| Planning assumptions | {% if guidance.assumptions %}{% for item in guidance.assumptions %}{{ item }}<br>{% endfor %}{% else %}None{% endif %} |
| Unknowns | {% if guidance.unknowns %}{% for item in guidance.unknowns %}{{ item }}<br>{% endfor %}{% else %}None{% endif %} |
"""


def _format_agent_result(result: object | None, fallback: str) -> str:
    if isinstance(result, dict):
        return json.dumps(result, indent=2)
    return fallback


def _action_scenarios() -> str:
    run_id = make_ui_run_id(f"season_scenarios_{year}_{week:02d}")
    set_status(
        status_state="running",
        title="Season",
        message="Creating scenarios...",
        last_action="Create Scenarios",
        last_run_id=run_id,
    )
    result, output = capture_output(
        lambda: create_season_scenarios(
            lambda name: multi_runtime_for(name),
            athlete_id=athlete_id,
            year=year,
            week=week,
            run_id=run_id,
            model_resolver=SETTINGS.model_for_agent,
            temperature_resolver=SETTINGS.temperature_for_agent,
            force_file_search=True,
            max_num_results=SETTINGS.file_search_max_results,
        ),
        loggers=CAPTURE_LOGGERS,
    )
    set_status(
        status_state="done",
        title="Season",
        message="Scenarios created.",
        last_action="Create Scenarios",
        last_run_id=run_id,
    )
    return output or _format_agent_result(result, f"Scenarios created: {run_id}")


def _action_select_scenario(selected: str, rationale: str | None, kpi_selection: dict | None) -> str:
    run_id = make_ui_run_id(f"season_scenario_selection_{year}_{week:02d}")
    set_status(
        status_state="running",
        title="Season",
        message=f"Selecting scenario {selected.upper()}...",
        last_action="Select Scenario",
        last_run_id=run_id,
    )

    scenarios_doc = store.load_latest(athlete_id, ArtifactType.SEASON_SCENARIOS)
    if not isinstance(scenarios_doc, dict):
        set_status(
            status_state="error",
            title="Season",
            message="Missing Season Scenarios.",
            last_action="Select Scenario",
            last_run_id=run_id,
        )
        return "Missing SEASON_SCENARIOS."

    kpi_doc = store.load_latest(athlete_id, ArtifactType.KPI_PROFILE)
    if not isinstance(kpi_doc, dict):
        set_status(
            status_state="error",
            title="Season",
            message="Missing KPI Profile.",
            last_action="Select Scenario",
            last_run_id=run_id,
        )
        return "Missing KPI_PROFILE."

    availability_doc = store.load_latest(athlete_id, ArtifactType.AVAILABILITY)
    if not isinstance(availability_doc, dict):
        set_status(
            status_state="error",
            title="Season",
            message="Missing Availability.",
            last_action="Select Scenario",
            last_run_id=run_id,
        )
        return "Missing AVAILABILITY."

    scenarios_meta = scenarios_doc.get("meta") or {}
    kpi_meta = kpi_doc.get("meta") or {}
    availability_meta = availability_doc.get("meta") or {}
    iso_week_range = scenarios_meta.get("iso_week_range") or f"{year:04d}-{week:02d}--{year:04d}-{week:02d}"
    temporal_scope = scenarios_meta.get("temporal_scope")
    if not isinstance(temporal_scope, dict):
        start = date.fromisocalendar(year, week, 1)
        end = date.fromisocalendar(year, week, 7)
        temporal_scope = {"from": start.isoformat(), "to": end.isoformat()}

    notes = [f"Selected scenario {selected.upper()} via Season UI."]
    selection_rationale = rationale.strip() if rationale else ""
    selection_source = "user"
    kpi_value = None
    if isinstance(kpi_selection, dict):
        segment = kpi_selection.get("segment")
        w_per_kg = kpi_selection.get("w_per_kg") or {}
        kj_per_kg = kpi_selection.get("kj_per_kg_per_hour") or {}
        if segment and w_per_kg and kj_per_kg:
            kpi_value = {
                "segment": segment,
                "w_per_kg": {"min": w_per_kg.get("min"), "max": w_per_kg.get("max")},
                "kj_per_kg_per_hour": {"min": kj_per_kg.get("min"), "max": kj_per_kg.get("max")},
            }

    meta = {
        "artifact_type": ArtifactType.SEASON_SCENARIO_SELECTION.value,
        "schema_id": "SeasonScenarioSelectionInterface",
        "schema_version": "1.1",
        "version": "1.0",
        "authority": "Informational",
        "owner_agent": "Season-Scenario-Agent",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Season",
        "iso_week": f"{year:04d}-{week:02d}",
        "iso_week_range": iso_week_range,
        "temporal_scope": temporal_scope,
        "trace_upstream": [
            {
                "artifact": "SEASON_SCENARIOS",
                "version": scenarios_meta.get("version_key"),
                "run_id": scenarios_meta.get("run_id"),
            },
            {
                "artifact": "KPI_PROFILE",
                "version": kpi_meta.get("version_key"),
                "run_id": kpi_meta.get("run_id"),
            },
            {
                "artifact": "AVAILABILITY",
                "version": availability_meta.get("version_key"),
                "run_id": availability_meta.get("run_id"),
            },
        ],
        "trace_data": [],
        "trace_events": [],
        "notes": "Scenario selection recorded from UI inputs.",
    }
    data = {
        "season_scenarios_ref": scenarios_meta.get("run_id") or scenarios_meta.get("version_key") or ISO_WEEK_RANGE_FALLBACK,
        "selected_scenario_id": selected.upper(),
        "selection_source": selection_source,
        "selection_rationale": selection_rationale,
        "notes": notes,
        "kpi_moving_time_rate_guidance_selection": kpi_value,
    }
    document = {"meta": meta, "data": data}
    store.save_document(
        athlete_id,
        ArtifactType.SEASON_SCENARIO_SELECTION,
        f"{year:04d}-{week:02d}",
        document,
        producer_agent="season_scenario",
        run_id=run_id,
    )
    set_status(
        status_state="done",
        title="Season",
        message=f"Scenario {selected.upper()} selected.",
        last_action="Select Scenario",
        last_run_id=run_id,
    )
    return f"Scenario {selected.upper()} selected and saved."


def _action_season_plan(selected: str) -> str:
    run_id = make_ui_run_id(f"season_plan_{year}_{week:02d}")
    set_status(
        status_state="running",
        title="Season",
        message="Creating season plan...",
        last_action="Create Season Plan",
        last_run_id=run_id,
    )
    result, output = capture_output(
        lambda: create_season_plan(
            lambda name: multi_runtime_for(name),
            athlete_id=athlete_id,
            year=year,
            week=week,
            run_id=run_id,
            selected=selected,
            model_resolver=SETTINGS.model_for_agent,
            temperature_resolver=SETTINGS.temperature_for_agent,
            force_file_search=True,
            max_num_results=SETTINGS.file_search_max_results,
        ),
        loggers=CAPTURE_LOGGERS,
    )
    set_status(
        status_state="done",
        title="Season",
        message="Season plan created.",
        last_action="Create Season Plan",
        last_run_id=run_id,
    )
    return output or _format_agent_result(result, f"Season plan created: {run_id}")


def _load_latest_payload(store: LocalArtifactStore, artifact_type: ArtifactType) -> dict | None:
    if not store.latest_exists(athlete_id, artifact_type):
        return None
    payload = store.load_latest(athlete_id, artifact_type)
    return payload if isinstance(payload, dict) else None


def _render_selected_scenario_markdown(store: LocalArtifactStore, athlete_id: str) -> str | None:
    selection = _load_latest_payload(store, ArtifactType.SEASON_SCENARIO_SELECTION)
    if not selection:
        return None
    selected_id = (selection.get("data") or {}).get("selected_scenario_id")
    scenarios_payload = _load_latest_payload(store, ArtifactType.SEASON_SCENARIOS)
    if not scenarios_payload or not selected_id:
        return None
    scenario = next(
        (s for s in (scenarios_payload.get("data") or {}).get("scenarios", []) if s.get("scenario_id") == selected_id),
        None,
    )
    if not scenario:
        return None
    guidance = scenario.get("scenario_guidance") or {}
    env = Environment(loader=BaseLoader(), autoescape=False)
    template = env.from_string(SCENARIO_TEMPLATE)
    return template.render(
        scenario=scenario,
        guidance=guidance,
        selection={
            "selection_rationale": (selection.get("data") or {}).get("selection_rationale"),
            "selection_iso_week_range": (selection.get("meta") or {}).get("iso_week_range"),
        },
    )


def _render_phase_panels(plan_payload: dict | None) -> None:
    if not isinstance(plan_payload, dict):
        return
    phases = plan_payload.get("data", {}).get("phases", [])
    if not phases:
        return
    st.subheader("Phases")
    for phase in phases:
        phase_id = phase.get("phase_id", "Phase")
        name = phase.get("name") or "Phase"
        iso_range = phase.get("iso_week_range") or ""
        header = f"{phase_id} · {name}"
        if iso_range:
            header = f"{header} · {iso_range}"
        with st.expander(header, expanded=False):
            st.markdown(render_phase_markdown(phase), unsafe_allow_html=True)


def _show_reset_delete_actions() -> None:
    with st.form("season_plan_actions"):
        action = st.selectbox("Action", options=["Reset Season Plan", "Delete Season Plan"])
        confirmation = st.text_input('Type "YES I WANT TO PROCEED" to continue')
        submitted = st.form_submit_button("Proceed", disabled=confirmation != "YES I WANT TO PROCEED")
    if submitted:
        append_system_log("season", f"{action} requested.")
        st.info(f"{action} flow will trigger (TODO).")
        set_status(
            status_state="running",
            title="Season",
            message=f"{action} requested.",
            last_action=action,
        )


scenarios_payload = None
if store.latest_exists(athlete_id, ArtifactType.SEASON_SCENARIOS):
    scenarios_payload = store.load_latest(athlete_id, ArtifactType.SEASON_SCENARIOS)

selection_payload = None
if store.latest_exists(athlete_id, ArtifactType.SEASON_SCENARIO_SELECTION):
    selection_payload = store.load_latest(athlete_id, ArtifactType.SEASON_SCENARIO_SELECTION)

selected_default = None
if selection_payload:
    selected_default = selection_payload.get("data", {}).get("selected_scenario_id")

kpi_selection_default = None
if selection_payload:
    kpi_selection_default = (selection_payload.get("data") or {}).get("kpi_moving_time_rate_guidance_selection")

scenario_options = []
if scenarios_payload:
    scenario_options = [s.get("scenario_id") for s in scenarios_payload.get("data", {}).get("scenarios", [])]
    scenario_options = [opt for opt in scenario_options if opt]

selected = selected_default or (scenario_options[0] if scenario_options else None)

kpi_profile = None
if store.latest_exists(athlete_id, ArtifactType.KPI_PROFILE):
    kpi_profile = store.load_latest(athlete_id, ArtifactType.KPI_PROFILE)

kpi_bands = []
if isinstance(kpi_profile, dict):
    bands = (
        (kpi_profile.get("data") or {})
        .get("durability", {})
        .get("moving_time_rate_guidance", {})
        .get("bands", [])
    )
    for band in bands:
        segment = band.get("segment")
        w_per_kg = band.get("w_per_kg") or {}
        if not segment or "min" not in w_per_kg or "max" not in w_per_kg:
            continue
        label = f"{segment.replace('_', ' ').title()}: {w_per_kg.get('min')} - {w_per_kg.get('max')} W/kg"
        kpi_bands.append({"label": label, "value": band})

with st.expander("Actions", expanded=False):
    if has_plan:
        _show_reset_delete_actions()
        set_status(status_state="done", title="Season", message="Season plan exists.")
    else:
        if scenario_options:
            with st.form("season_scenario_selection"):
                selected = st.radio(
                    "Choose scenario",
                    options=scenario_options,
                    index=scenario_options.index(selected_default) if selected_default in scenario_options else 0,
                    horizontal=True,
                )
                kpi_selection = None
                if kpi_bands:
                    kpi_labels = [item["label"] for item in kpi_bands]
                    default_label = None
                    if isinstance(kpi_selection_default, dict):
                        default_segment = kpi_selection_default.get("segment")
                        for item in kpi_bands:
                            if item["value"].get("segment") == default_segment:
                                default_label = item["label"]
                                break
                    kpi_selection_label = st.selectbox(
                        "KPI moving_time_rate_guidance",
                        options=kpi_labels,
                        index=kpi_labels.index(default_label) if default_label in kpi_labels else 0,
                    )
                    selected_band = next(
                        (item for item in kpi_bands if item["label"] == kpi_selection_label),
                        None,
                    )
                    kpi_selection = selected_band["value"] if selected_band else None
                else:
                    st.caption("No KPI profile bands available.")
                rationale = st.text_area("Rationale (optional)")
                select_submit = st.form_submit_button("Confirm Scenario Selection")
            if select_submit:
                append_system_log("season", f"Selecting scenario {selected}.")
                output = _action_select_scenario(selected, rationale, kpi_selection)
                state["season_selection_output"] = output
                append_system_log("season", f"Scenario {selected} selected.")
                saved = store.latest_exists(athlete_id, ArtifactType.SEASON_SCENARIO_SELECTION)
                state["season_selection_saved"] = saved
                if not saved:
                    state["season_selection_error_output"] = output
                st.rerun()
        if selection_payload:
            st.info("Season plan creation happens in Plan → Hub.")
        if not scenario_options:
            st.info("Create Season Scenarios from Plan → Hub.")

render_status_panel()

if has_plan:
    rendered = load_rendered_markdown(athlete_id, ArtifactType.SEASON_PLAN)
    plan_payload = store.load_latest(athlete_id, ArtifactType.SEASON_PLAN)
    if rendered:
        st.markdown(rendered)
    scenario_intro = _render_selected_scenario_markdown(store, athlete_id)
    if scenario_intro:
        with st.container():
            st.markdown(scenario_intro, unsafe_allow_html=True)
    _render_phase_panels(plan_payload)
    st.stop()

if output := state.get("season_scenarios_output"):
    with st.expander("Create Scenarios Output", expanded=False):
        st.code(output)

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

if not scenario_options:
    st.info("No scenario IDs available to select.")
    st.stop()

if output := state.get("season_selection_output"):
    with st.expander("Scenario Selection Output", expanded=False):
        st.code(output)

if selection_payload:
    st.subheader("Create Season Plan")
    if state.pop("season_selection_saved", False):
        st.success("Scenario selection saved.")
    st.page_link("pages/plan/hub.py", label="Back to Plan Hub")

if output := state.get("season_plan_output"):
    with st.expander("Create Season Plan Output", expanded=False):
        st.code(output)

if output := state.pop("season_selection_error_output", None):
    st.error("Scenario selection did not write. Check the output below.")
    with st.expander("Scenario Selection Output", expanded=True):
        st.code(output)
