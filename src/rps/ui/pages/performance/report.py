from __future__ import annotations

import json
import threading
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Callable
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

import streamlit as st
import time

from rps.orchestrator.plan_week import create_performance_report
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
from rps.ui.run_store import start_background_run, update_run
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType
from rps.workspace.iso_helpers import IsoWeek


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
    run_id = start_background_run(
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
        "run_id": run_id,
    }

    def worker() -> None:
        job["status"] = "running"
        job["message"] = "Creating performance report..."
        update_run(
            SETTINGS.workspace_root,
            athlete_id,
            run_id,
            {"status": "RUNNING", "message": job["message"], "started_at": datetime.now(timezone.utc).isoformat()},
        )

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
            update_run(
                SETTINGS.workspace_root,
                athlete_id,
                run_id,
                {"status": "DONE", "message": job["message"], "finished_at": datetime.now(timezone.utc).isoformat()},
            )
        except Exception as exc:  # pragma: no cover - background failure
            job["result"] = {"ok": False, "message": str(exc)}
            job["message"] = f"Report creation failed: {exc}"
            job["status"] = "failed"
            update_run(
                SETTINGS.workspace_root,
                athlete_id,
                run_id,
                {"status": "FAILED", "message": job["message"], "finished_at": datetime.now(timezone.utc).isoformat()},
            )

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

st.markdown(
    "Report can only be generated for current or past weeks covered by `activities_trend`. "
    "If `activities_actual` is missing for the selection, run the intervals pipeline first."
)

job_key = _report_job_key(athlete_id, year, week)
job = st.session_state.get(job_key)
with st.expander("Actions", expanded=False):
    create_button = st.button("Create Report")
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
    with st.expander("Model reasoning", expanded=True):
        reasoning_text = "".join(job["reasonings"])
        if reasoning_text:
            st.text(reasoning_text)
        else:
            st.caption("Waiting for reasoning text...")
        logs = job.get("logs") or []
        if logs:
            st.caption("Agent log:")
            for entry in logs[-10:]:
                st.code(entry)
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

render_status_panel()

store = LocalArtifactStore(root=SETTINGS.workspace_root)
version_key = f"{year:04d}-{week:02d}"

rendered = load_rendered_markdown(
    athlete_id,
    ArtifactType.DES_ANALYSIS_REPORT,
    version_key=version_key,
)
if rendered:
    st.markdown(rendered, unsafe_allow_html=True)
else:
    try:
        report = store.load_version(athlete_id, ArtifactType.DES_ANALYSIS_REPORT, version_key)
    except FileNotFoundError:
        st.info(f"No des_analysis_report found for {version_key}.")
    else:
        st.json(report)
