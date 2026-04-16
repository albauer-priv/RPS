from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from typing import Any

import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

from rps.orchestrator.plan_week import create_performance_report
from rps.ui.intervals_refresh import request_intervals_refresh
from rps.ui.run_store import find_active_runs, start_background_tracker
from rps.ui.shared import (
    SETTINGS,
    announce_log_file,
    get_athlete_id,
    get_iso_year_week,
    init_ui_state,
    load_rendered_markdown,
    multi_runtime_for,
    render_global_sidebar,
    render_status_panel,
    set_status,
)
from rps.workspace.iso_helpers import IsoWeek
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType


def _resolve_report_activity_versions(
    store: LocalArtifactStore,
    athlete_id: str,
    report_key: str,
) -> dict[ArtifactType, str]:
    """Return week-specific activity artefact versions available for the selected report week."""
    resolved: dict[ArtifactType, str] = {}
    for artifact_type in (ArtifactType.ACTIVITIES_ACTUAL, ArtifactType.ACTIVITIES_TREND):
        version_key = store.resolve_week_version_key(athlete_id, artifact_type, report_key)
        if version_key:
            resolved[artifact_type] = version_key
    return resolved


def _report_job_key(athlete_id: str, year: int, week: int) -> str:
    return f"report_job_{athlete_id}_{year:04d}{week:02d}"


def _schedule_report_job(
    athlete_id: str,
    year: int,
    week: int,
    *,
    runtime_provider: Callable[[str], Any],
    run_id_prefix: str,
) -> dict:
    active = find_active_runs(
        SETTINGS.workspace_root,
        athlete_id,
        process_type="agent",
        process_subtype="performance_report",
    )
    if active:
        return {
            "thread": None,
            "status": "running",
            "message": "Report creation already running.",
            "reasonings": [],
            "logs": [],
            "result": None,
            "run_id": active[0].get("run_id") or "active",
        }
    tracker = start_background_tracker(
        SETTINGS.workspace_root,
        athlete_id,
        process_type="agent",
        process_subtype="performance_report",
        message="Queued report creation.",
        status="QUEUED",
    )
    job: dict = {
        "thread": None,
        "status": "queued",
        "message": "Queued report creation.",
        "reasonings": [],
        "logs": [],
        "result": None,
        "run_id": tracker.run_id,
    }

    def worker() -> None:
        job["status"] = "running"
        job["message"] = "Creating performance report..."
        tracker.mark_running(job["message"])

        def _capture_stream(delta: str) -> None:
            job["reasonings"].append(delta)

        try:
            result = create_performance_report(
                lambda agent: runtime_provider(agent),
                athlete_id=athlete_id,
                report_week=IsoWeek(year=year, week=week),
                run_id_prefix=run_id_prefix,
                reasoning_stream_handler=_capture_stream,
            )
            job["result"] = result
            job["logs"] = result.get("reasoning_log", [])
            job["message"] = result.get("message", "Report creation completed.")
            job["status"] = "done"
            tracker.mark_done(job["message"])
        except Exception as exc:  # pragma: no cover - background failure
            job["result"] = {"ok": False, "message": str(exc)}
            job["message"] = f"Report creation failed: {exc}"
            job["status"] = "failed"
            tracker.mark_failed(job["message"])

    thread = threading.Thread(target=worker, daemon=True)
    ctx = get_script_run_ctx()
    if ctx is not None:
        add_script_run_ctx(thread, ctx)
    job["thread"] = thread
    thread.start()
    return job


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


init_ui_state()
render_global_sidebar()
athlete_id = get_athlete_id()
year, week = get_iso_year_week()
announce_log_file(athlete_id)

st.title("Report")
st.caption(f"Athlete: {athlete_id}")
set_status(status_state="done", title="Report", message="Ready.")
render_status_panel()

store = LocalArtifactStore(root=SETTINGS.workspace_root)

trend_options = _load_trend_week_options(athlete_id)
selection = None
if trend_options:
    labels = [f"{opt['year']:04d}-W{opt['week']:02d}" for opt in trend_options]
    default_index = next(
        (idx for idx, opt in enumerate(trend_options) if opt["year"] == year and opt["week"] == week),
        0,
    )
    selection_idx = st.selectbox("Select report week", range(len(labels)), format_func=lambda idx: labels[idx], index=default_index)
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

report_key = f"{year:04d}-{week:02d}"
report_versions = _resolve_report_activity_versions(store, athlete_id, report_key)
has_week_actual = ArtifactType.ACTIVITIES_ACTUAL in report_versions
has_week_trend = ArtifactType.ACTIVITIES_TREND in report_versions
report_inputs_ready = has_week_actual and has_week_trend

st.subheader("Performance Report Readiness")
report_for_week = store.exists(athlete_id, ArtifactType.DES_ANALYSIS_REPORT, report_key)
report_latest = store.latest_exists(athlete_id, ArtifactType.DES_ANALYSIS_REPORT)
st.table(
    [
        {
            "Check": "Activities Actual",
            "Status": "Ready" if has_week_actual else "Missing",
            "Details": (
                f"Week-scoped activities_actual available for {report_key}."
                if has_week_actual
                else f"No activities_actual found for {report_key}."
            ),
        },
        {
            "Check": "Activities Trend",
            "Status": "Ready" if has_week_trend else "Missing",
            "Details": (
                f"Week-scoped activities_trend available for {report_key}."
                if has_week_trend
                else f"No activities_trend found for {report_key}."
            ),
        },
        {
            "Check": "Performance Report (DES Analysis)",
            "Status": (
                "Ready"
                if report_for_week
                else "Stale"
                if report_latest
                else "Missing"
            ),
            "Details": (
                f"Report available for {report_key}."
                if report_for_week
                else "Latest DES report is from another week."
                if report_latest
                else "No DES analysis report found."
            ),
        }
    ]
)

st.markdown(
    "Report can only be generated for current or past weeks covered by `activities_trend`. "
    "If week-specific activity data is missing, refresh the selected week first."
)

job_key = _report_job_key(athlete_id, year, week)
job = st.session_state.get(job_key)
with st.expander("Actions", expanded=False):
    fetch_week_button = st.button(
        f"Fetch Week Data: {year:04d}-W{week:02d}",
        disabled=bool(job and job["status"] == "running"),
    )
    create_button = st.button(
        "Create Report",
        disabled=not trend_options or not report_inputs_ready,
    )
if fetch_week_button:
    status_state, message, run_id = request_intervals_refresh(
        athlete_id,
        year=year,
        week=week,
    )
    if message:
        st.info(message)
    set_status(
        status_state=status_state,
        title="Report",
        message=message or f"Queued Intervals refresh for {report_key}.",
        last_action="Fetch Week Data",
        run_id=run_id,
    )
if create_button:
    if job and job["status"] == "running":
        st.info("Report creation already requested; please wait for completion.")
        set_status(
            status_state="running",
            title="Report",
            message="Report already running.",
            last_action="Create Report",
        )
    else:
        job = _schedule_report_job(
            athlete_id,
            year,
            week,
            runtime_provider=lambda agent: multi_runtime_for(agent),
            run_id_prefix=f"report_ui_{year:04d}{week:02d}",
        )
        st.session_state[job_key] = job
        st.info(job["message"])
        set_status(
            status_state="running",
            title="Report",
            message=job["message"],
            last_action="Create Report",
        )

if job:
    st.info(job["message"])
    status_state = "running" if job["status"] == "running" else "done"
    if job["status"] == "failed":
        status_state = "error"
    set_status(
        status_state=status_state,
        title="Report",
        message=job["message"],
        last_action="Create Report",
    )
    if job["status"] == "running":
        refresh_interval = 1.5
        next_refresh = st.session_state.get("report_next_refresh", 0.0)
        now = time.time()
        if now >= next_refresh:
            st.session_state["report_next_refresh"] = now + refresh_interval
            rerun_fn = getattr(st, "experimental_rerun", None)
            if callable(rerun_fn):
                rerun_fn()
elif not trend_options:
    st.warning("Create Report is disabled until you select a week covered by activities_trend.")
    set_status(
        status_state="idle",
        title="Report",
        message="Select a week covered by activities_trend.",
    )
elif not report_inputs_ready:
    missing_parts: list[str] = []
    if not has_week_actual:
        missing_parts.append("activities_actual")
    if not has_week_trend:
        missing_parts.append("activities_trend")
    st.warning(
        "Create Report is disabled because the selected week is missing: "
        + ", ".join(missing_parts)
        + "."
    )
    set_status(
        status_state="idle",
        title="Report",
        message=f"Fetch week data for {report_key} before creating the report.",
    )

store = LocalArtifactStore(root=SETTINGS.workspace_root)
version_key = f"{year:04d}-{week:02d}"

def _render_narrative_report(payload: dict) -> None:
    narrative = (payload.get("data") or {}).get("narrative_report")
    if not narrative:
        return
    st.subheader("Narrative Report")
    if isinstance(narrative, str):
        st.markdown(narrative)
        return
    if isinstance(narrative, dict):
        for key, value in narrative.items():
            title = key.replace("_", " ").title()
            st.markdown(f"**{title}**")
            if value:
                st.markdown(str(value))
        return
    st.markdown(str(narrative))


def _render_kpi_summary(payload: dict) -> None:
    summary = (payload.get("data") or {}).get("kpi_summary")
    if not summary:
        return
    with st.expander("KPI Summary", expanded=True):
        if isinstance(summary, dict):
            for key, value in summary.items():
                label = key.replace("_", " ").title()
                st.markdown(f"**{label}**")
                if isinstance(value, dict):
                    delta = value.get("delta_vs_baseline")
                    if delta:
                        st.markdown(str(delta))
                    else:
                        st.caption("No delta vs baseline available.")
                else:
                    st.markdown(str(value))
        else:
            st.markdown(str(summary))


def _render_trend_analysis(payload: dict) -> None:
    trend = (payload.get("data") or {}).get("trend_analysis")
    if not trend:
        return
    with st.expander("Trend Analysis", expanded=True):
        observations = trend.get("observations") if isinstance(trend, dict) else None
        if isinstance(observations, list) and observations:
            for obs in observations:
                if not isinstance(obs, dict):
                    continue
                metric = obs.get("metric") or "Metric"
                label = str(metric).replace("_", " ").title()
                st.markdown(f"**{label}**")
                interpretation = obs.get("interpretation")
                if interpretation:
                    st.markdown(str(interpretation))
                else:
                    st.caption("No interpretation available.")
        else:
            st.caption("No trend analysis observations available.")


rendered = load_rendered_markdown(
    athlete_id,
    ArtifactType.DES_ANALYSIS_REPORT,
    version_key=version_key,
)
try:
    report = store.load_version(athlete_id, ArtifactType.DES_ANALYSIS_REPORT, version_key)
except FileNotFoundError:
    report = None

if isinstance(report, dict):
    _render_narrative_report(report)
    _render_kpi_summary(report)
    _render_trend_analysis(report)

if rendered:
    st.markdown(rendered, unsafe_allow_html=True)
elif report is None:
    st.info(f"No des_analysis_report found for {version_key}.")
