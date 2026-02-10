from __future__ import annotations

import json
from datetime import date, datetime

import streamlit as st

from rps.agents.multi_output_runner import run_agent_multi_output
from rps.agents.registry import AGENTS
from rps.agents.tasks import AgentTask
from rps.orchestrator.plan_week import _build_injection_block, _mode_for_task, create_performance_report
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
set_status(status_state="done", title="Feed Forward", message="Ready.")
render_status_panel()

store = LocalArtifactStore(root=SETTINGS.workspace_root)

def _load_trend_week_options(athlete_id: str) -> list[dict[str, int]]:
    trend_path = SETTINGS.workspace_root / athlete_id / "latest" / "activities_trend.json"
    if not trend_path.exists():
        return []
    with trend_path.open(encoding="utf-8") as fp:
        payload = json.load(fp)
    weeks = payload.get("data", {}).get("weekly_trends") or []
    options = []
    seen = set()
    for entry in sorted(weeks, key=lambda e: ((e.get("year") or 0), (e.get("iso_week") or 0)), reverse=True):
        year = entry.get("year")
        iso_week = entry.get("iso_week")
        if year is None or iso_week is None:
            continue
        key = (int(year), int(iso_week))
        if key in seen:
            continue
        seen.add(key)
        options.append({"year": int(year), "week": int(iso_week)})
    return options

trend_options = _load_trend_week_options(athlete_id)
selection = None
if trend_options:
    labels = [f"{opt['year']:04d}-W{opt['week']:02d}" for opt in trend_options]
    default_index = next(
        (idx for idx, opt in enumerate(trend_options) if opt["year"] == year and opt["week"] == week),
        0,
    )
    selection_idx = st.selectbox(
        "Select Feed Forward Week",
        range(len(labels)),
        format_func=lambda idx: labels[idx],
        index=default_index,
    )
    selection = trend_options[selection_idx]
    week = selection["week"]
    year = selection["year"]
else:
    col_week, col_year = st.columns(2)
    week = int(
        col_week.number_input(
            "ISO Week",
            min_value=1,
            max_value=53,
            value=week,
            step=1,
        )
    )
    year = int(
        col_year.number_input(
            "ISO Year",
            min_value=2000,
            max_value=2100,
            value=year,
            step=1,
        )
    )

selected_week = IsoWeek(year=year, week=week)
selected_week_key = f"{selected_week.year:04d}-{selected_week.week:02d}"

st.subheader("Feed Forward Readiness")
report_for_selected_week = store.exists(athlete_id, ArtifactType.DES_ANALYSIS_REPORT, selected_week_key)
report_latest = store.latest_exists(athlete_id, ArtifactType.DES_ANALYSIS_REPORT)
if report_for_selected_week:
    report_status = "Ready"
    report_detail = f"Report available ({selected_week_key})."
elif report_latest:
    report_status = "Stale"
    report_detail = "Latest DES report is from another week."
else:
    report_status = "Missing"
    report_detail = "No DES analysis report found."
st.table(
    [
        {
            "Check": "Performance Report (DES Analysis)",
            "Status": report_status,
            "Details": report_detail,
        }
    ]
)

run_cols = st.columns(1)
current_week = IsoWeek(*date.today().isocalendar()[:2])
allowed_scope = selected_week in {current_week, previous_iso_week(current_week)}
if not allowed_scope:
    st.caption("Feed Forward can only run for the current or previous ISO week.")

run_label = f"Run Feed Forward (Report → Season → Phase → Week) · {selected_week_key}"
if run_cols[0].button(run_label, disabled=not allowed_scope):
    report_run_id = make_ui_run_id(f"feed_forward_report_{year}_{week:02d}")
    set_status(
        status_state="running",
        title="Feed Forward",
        message="Creating DES analysis report...",
        last_action="DES Analysis Report",
        last_run_id=report_run_id,
    )
    report_result, report_output = capture_output(
        lambda: create_performance_report(
            multi_runtime_for,
            athlete_id=athlete_id,
            report_week=selected_week,
            run_id_prefix=report_run_id,
            force_file_search=True,
            max_num_results=SETTINGS.file_search_max_results,
            model_resolver=SETTINGS.model_for_agent,
            temperature_resolver=SETTINGS.temperature_for_agent,
        ),
        loggers=CAPTURE_LOGGERS,
    )
    if not (isinstance(report_result, dict) and report_result.get("ok")):
        message = report_result.get("message") if isinstance(report_result, dict) else "DES analysis report failed."
        set_status(
            status_state="error",
            title="Feed Forward",
            message=message,
            last_action="DES Analysis Report",
            last_run_id=report_run_id,
        )
        st.error(message)
    else:
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
        if status == "done":
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

report_payload = None
try:
    report_payload = store.load_version(athlete_id, ArtifactType.DES_ANALYSIS_REPORT, selected_week_key)
except FileNotFoundError:
    try:
        report_payload = store.load_latest(athlete_id, ArtifactType.DES_ANALYSIS_REPORT)
    except FileNotFoundError:
        report_payload = None

st.subheader(f"Week Analysis · {selected_week_key}")
summary_text = "N/A"
if store.latest_exists(athlete_id, ArtifactType.SEASON_PHASE_FEED_FORWARD):
    payload = store.load_latest(athlete_id, ArtifactType.SEASON_PHASE_FEED_FORWARD)
    decision = (payload.get("data") or {}).get("decision_summary") or {}
    summary_text = decision.get("conclusion") or "N/A"
elif store.latest_exists(athlete_id, ArtifactType.PHASE_FEED_FORWARD):
    payload = store.load_latest(athlete_id, ArtifactType.PHASE_FEED_FORWARD)
    reason = (payload.get("data") or {}).get("reason_context") or {}
    summary_text = reason.get("intent_of_adjustment") or "N/A"
st.markdown(f"**Summary:** {summary_text}")
if not report_payload:
    st.info("No DES analysis report found for the selected week.")
else:
    recommendation = (report_payload.get("data") or {}).get("recommendation") or {}
    st.markdown("**Recommendation for Season Planner**")
    st.markdown("- " + "\n- ".join(recommendation.get("suggested_considerations") or ["N/A"]))
    st.caption("Rationale: " + "; ".join(recommendation.get("rationale") or ["N/A"]))

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
    st.dataframe(rows, width="stretch")
else:
    st.info("No feed forward artefacts found yet.")
