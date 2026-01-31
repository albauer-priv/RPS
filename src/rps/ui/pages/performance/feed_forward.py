from __future__ import annotations

import json
from datetime import datetime

import streamlit as st

from rps.agents.multi_output_runner import run_agent_multi_output
from rps.agents.registry import AGENTS
from rps.agents.tasks import AgentTask
from rps.orchestrator.plan_week import _build_injection_block, _mode_for_task
from rps.ui.run_store import load_runs
from rps.ui.shared import (
    CAPTURE_LOGGERS,
    SETTINGS,
    announce_log_file,
    capture_output,
    get_athlete_id,
    get_iso_year_week,
    init_ui_state,
    make_ui_run_id,
    multi_runtime_for,
    render_global_sidebar,
    render_status_panel,
    set_status,
)
from rps.workspace.index_manager import WorkspaceIndexManager
from rps.workspace.iso_helpers import IsoWeek, previous_iso_week
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType


st.title("Feed Forward")

# CHECKLIST (Analyse -> Feed Forward)
# - Show last week DES analysis recommendation for Season Planner.
# - Allow triggering feed-forward actions (Season->Phase, Phase->Week).
# - Show latest feed-forward summaries (Season->Phase, Phase->Week).
# - Show process status table + feed-forward artefact table with validity.

init_ui_state()
render_global_sidebar()
athlete_id = get_athlete_id()
year, week = get_iso_year_week()
announce_log_file(athlete_id)

st.caption(f"Athlete: {athlete_id}")

store = LocalArtifactStore(root=SETTINGS.workspace_root)

last_week = previous_iso_week(IsoWeek(year=year, week=week))
last_week_key = f"{last_week.year:04d}-{last_week.week:02d}"

report_payload = None
try:
    report_payload = store.load_version(athlete_id, ArtifactType.DES_ANALYSIS_REPORT, last_week_key)
except FileNotFoundError:
    try:
        report_payload = store.load_latest(athlete_id, ArtifactType.DES_ANALYSIS_REPORT)
    except FileNotFoundError:
        report_payload = None

st.subheader(f"Last Week Analysis · {last_week_key}")
if not report_payload:
    st.info("No DES analysis report found for last week.")
else:
    recommendation = (report_payload.get("data") or {}).get("recommendation") or {}
    st.markdown("**Recommendation for Season Planner**")
    st.markdown("- " + "\n- ".join(recommendation.get("suggested_considerations") or ["N/A"]))
    st.caption("Rationale: " + "; ".join(recommendation.get("rationale") or ["N/A"]))

st.subheader("Trigger Feed Forward")
run_cols = st.columns(2)
if run_cols[0].button("Run Season → Phase Feed Forward"):
    runtime = multi_runtime_for("season_planner")
    spec = AGENTS["season_planner"]
    injected_block = _build_injection_block("season_planner", mode=_mode_for_task(AgentTask.CREATE_SEASON_PHASE_FEED_FORWARD))
    run_id = make_ui_run_id(f"season_phase_feed_forward_{year}_{week:02d}")
    set_status(
        status_state="running",
        title="Feed Forward",
        message="Creating Season → Phase feed forward...",
        last_action="Season → Phase Feed Forward",
        last_run_id=run_id,
    )
    result, output = capture_output(
        lambda: run_agent_multi_output(
            runtime,
            agent_name=spec.name,
            agent_vs_name=spec.vector_store_name,
            athlete_id=athlete_id,
            tasks=[AgentTask.CREATE_SEASON_PHASE_FEED_FORWARD],
            user_input=(
                f"Target ISO week: {year}-{week:02d}. "
                "Use latest DES analysis report to produce SEASON_PHASE_FEED_FORWARD. "
                f"{injected_block}"
            ),
            run_id=run_id,
            model_override=SETTINGS.model_for_agent(spec.name),
            temperature_override=SETTINGS.temperature_for_agent(spec.name),
            force_file_search=True,
            max_num_results=SETTINGS.file_search_max_results,
        ),
        loggers=CAPTURE_LOGGERS,
    )
    status = "done" if isinstance(result, dict) or getattr(result, "ok", False) else "error"
    set_status(
        status_state=status,
        title="Feed Forward",
        message="Season → Phase feed forward complete.",
        last_action="Season → Phase Feed Forward",
        last_run_id=run_id,
    )
    if output:
        with st.expander("Output", expanded=False):
            st.code(output)

if run_cols[1].button("Run Phase → Week Feed Forward"):
    runtime = multi_runtime_for("phase_architect")
    spec = AGENTS["phase_architect"]
    injected_block = _build_injection_block("phase_architect", mode=_mode_for_task(AgentTask.CREATE_PHASE_FEED_FORWARD))
    run_id = make_ui_run_id(f"phase_feed_forward_{year}_{week:02d}")
    set_status(
        status_state="running",
        title="Feed Forward",
        message="Creating Phase → Week feed forward...",
        last_action="Phase → Week Feed Forward",
        last_run_id=run_id,
    )
    result, output = capture_output(
        lambda: run_agent_multi_output(
            runtime,
            agent_name=spec.name,
            agent_vs_name=spec.vector_store_name,
            athlete_id=athlete_id,
            tasks=[AgentTask.CREATE_PHASE_FEED_FORWARD],
            user_input=(
                f"Target ISO week: {year}-{week:02d}. "
                "Use latest SEASON_PHASE_FEED_FORWARD and DES analysis report to produce PHASE_FEED_FORWARD. "
                f"{injected_block}"
            ),
            run_id=run_id,
            model_override=SETTINGS.model_for_agent(spec.name),
            temperature_override=SETTINGS.temperature_for_agent(spec.name),
            force_file_search=True,
            max_num_results=SETTINGS.file_search_max_results,
        ),
        loggers=CAPTURE_LOGGERS,
    )
    status = "done" if isinstance(result, dict) or getattr(result, "ok", False) else "error"
    set_status(
        status_state=status,
        title="Feed Forward",
        message="Phase → Week feed forward complete.",
        last_action="Phase → Week Feed Forward",
        last_run_id=run_id,
    )
    if output:
        with st.expander("Output", expanded=False):
            st.code(output)

render_status_panel()

st.subheader("Feed Forward Summaries")
latest_ff = []
for artifact_type, label in (
    (ArtifactType.SEASON_PHASE_FEED_FORWARD, "Season → Phase"),
    (ArtifactType.PHASE_FEED_FORWARD, "Phase → Week"),
):
    if store.latest_exists(athlete_id, artifact_type):
        payload = store.load_latest(athlete_id, artifact_type)
        data = payload.get("data") if isinstance(payload, dict) else {}
        summary = "N/A"
        if artifact_type == ArtifactType.SEASON_PHASE_FEED_FORWARD:
            decision = (data or {}).get("decision_summary") or {}
            summary = decision.get("conclusion") or "N/A"
        if artifact_type == ArtifactType.PHASE_FEED_FORWARD:
            reason = (data or {}).get("reason_context") or {}
            summary = reason.get("intent_of_adjustment") or "N/A"
        latest_ff.append({"Type": label, "Summary": summary})

if latest_ff:
    st.table(latest_ff)
else:
    st.info("No feed forward artefacts found.")

st.subheader("Process Status")
runs = load_runs(SETTINGS.workspace_root, athlete_id, limit=25)
if runs:
    status_rows = []
    for run in runs:
        status_rows.append(
            {
                "Run ID": run.get("run_id"),
                "Status": run.get("status"),
                "Mode": run.get("mode") or "—",
                "Scope": run.get("scope") or "—",
                "Created": run.get("created_at") or "—",
            }
        )
    st.dataframe(status_rows, use_container_width=True)
else:
    st.info("No runs found.")

st.subheader("Feed Forward Artefacts")
index = WorkspaceIndexManager(root=SETTINGS.workspace_root, athlete_id=athlete_id).load()
rows = []
for artifact_type in (
    ArtifactType.DES_ANALYSIS_REPORT,
    ArtifactType.SEASON_PHASE_FEED_FORWARD,
    ArtifactType.PHASE_FEED_FORWARD,
):
    entry = (index.get("artefacts") or {}).get(artifact_type.value) or {}
    versions = entry.get("versions") or {}
    for version_key, record in versions.items():
        if not isinstance(record, dict):
            continue
        recommendation = "—"
        analysis_ref = "—"
        if artifact_type == ArtifactType.DES_ANALYSIS_REPORT:
            try:
                payload = store.load_version(athlete_id, artifact_type, str(version_key))
                recommendation = ", ".join((payload.get("data") or {}).get("recommendation", {}).get("suggested_considerations", [])) or "—"
                analysis_ref = str(version_key)
            except FileNotFoundError:
                pass
        if artifact_type == ArtifactType.SEASON_PHASE_FEED_FORWARD:
            try:
                payload = store.load_version(athlete_id, artifact_type, str(version_key))
                data = payload.get("data") or {}
                recommendation = (data.get("decision_summary") or {}).get("conclusion") or "—"
                analysis_ref = (data.get("source_context") or {}).get("des_analysis_report_ref") or "—"
            except FileNotFoundError:
                pass
        if artifact_type == ArtifactType.PHASE_FEED_FORWARD:
            try:
                payload = store.load_version(athlete_id, artifact_type, str(version_key))
                data = payload.get("data") or {}
                recommendation = (data.get("reason_context") or {}).get("intent_of_adjustment") or "—"
                analysis_ref = (data.get("body_metadata") or {}).get("derived_from") or "—"
            except FileNotFoundError:
                pass
        rows.append(
            {
                "Artefact": artifact_type.value,
                "Version": str(version_key),
                "Validity": record.get("iso_week_range") or record.get("iso_week") or "—",
                "Created": record.get("created_at") or "—",
                "Producer": record.get("producer_agent") or "—",
                "Recommendation": recommendation,
                "Analysis Report": analysis_ref,
            }
        )

rows.sort(key=lambda row: row.get("Created") or "", reverse=True)
if rows:
    st.dataframe(rows, use_container_width=True)
else:
    st.info("No feed forward artefacts found yet.")
