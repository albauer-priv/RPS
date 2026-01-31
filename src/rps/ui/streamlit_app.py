from __future__ import annotations

import os
import threading
from pathlib import Path

import streamlit as st

from rps.ui.intervals_refresh import ensure_intervals_data
from rps.ui.shared import SETTINGS, get_athlete_id
from rps.workspace.index_manager import WorkspaceIndexManager

st.set_page_config(page_title="RPS - Randonneur Performance System", layout="wide")


def _cleanup_index_background(root: Path) -> None:
    """Background cleanup for missing index entries."""
    for athlete_dir in root.iterdir():
        if not athlete_dir.is_dir():
            continue
        mgr = WorkspaceIndexManager(root=root, athlete_id=athlete_dir.name)
        mgr.prune_missing()


if "index_cleanup_started" not in st.session_state:
    st.session_state["index_cleanup_started"] = True
    cleanup_thread = threading.Thread(
        target=_cleanup_index_background,
        args=(SETTINGS.workspace_root,),
        daemon=True,
    )
    cleanup_thread.start()

home = st.Page("pages/home.py", title="Home", icon=":material/home:", default=True)
coach = st.Page("pages/coach.py", title="Coach", icon=":material/support_agent:")

performance_data = st.Page(
    "pages/performance/data_metrics.py",
    title="Data & Metrics",
    icon=":material/insights:",
)
performance_report = st.Page(
    "pages/performance/report.py",
    title="Report",
    icon=":material/assignment:",
)
performance_feed_forward = st.Page(
    "pages/performance/feed_forward.py",
    title="Feed Forward",
    icon=":material/forward:",
)

plan_season = st.Page(
    "pages/plan/season.py",
    title="Season",
    icon=":material/emoji_events:",
)
plan_hub = st.Page(
    "pages/plan/hub.py",
    title="Plan Hub",
    icon=":material/view_kanban:",
)
plan_phase = st.Page(
    "pages/plan/phase.py",
    title="Phase",
    icon=":material/timeline:",
)
plan_week = st.Page(
    "pages/plan/week.py",
    title="Week",
    icon=":material/calendar_month:",
)
plan_workouts = st.Page(
    "pages/plan/workouts.py",
    title="Workouts",
    icon=":material/fitness_center:",
)

about_you = st.Page(
    "pages/athlete_profile/about_you.py",
    title="About You",
    icon=":material/person:",
)
season_brief = st.Page(
    "pages/athlete_profile/season_brief.py",
    title="Season Brief",
    icon=":material/article:",
)
availability = st.Page(
    "pages/athlete_profile/availability.py",
    title="Availability",
    icon=":material/event_available:",
)
kpi_profile = st.Page(
    "pages/athlete_profile/kpi_profile.py",
    title="KPI Profile",
    icon=":material/analytics:",
)
logistics = st.Page(
    "pages/athlete_profile/logistics.py",
    title="Logistics",
    icon=":material/local_shipping:",
)
zones = st.Page(
    "pages/athlete_profile/zones.py",
    title="Zones",
    icon=":material/straighten:",
)

system_status = st.Page(
    "pages/system/status.py",
    title="Status",
    icon=":material/monitor_heart:",
)
system_history = st.Page(
    "pages/system/history.py",
    title="History",
    icon=":material/history:",
)
system_log = st.Page(
    "pages/system/log.py",
    title="Log",
    icon=":material/receipt_long:",
)

pg = st.navigation(
        {
            "Home": [home],
            "Coach": [coach],
        "Analyse": [performance_data, performance_report, performance_feed_forward],
        "Plan": [plan_hub, plan_season, plan_phase, plan_week, plan_workouts],
        "Athlete Profile": [about_you, season_brief, availability, kpi_profile, logistics, zones],
        "System": [system_status, system_history, system_log],
    }
)
max_age_hours = float(os.getenv("RPS_INTERVALS_MAX_AGE_HOURS", "2"))
ensure_intervals_data(get_athlete_id(), max_age_hours)
pg.run()
