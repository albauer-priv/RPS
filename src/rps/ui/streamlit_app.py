from __future__ import annotations

import os
import threading
from datetime import UTC, datetime
from pathlib import Path

import streamlit as st

from rps.core.logging import prune_old_logs
from rps.evidence import evidence_refresh_due, refresh_evidence_library
from rps.rendering.auto_render import prune_rendered_sidecars
from rps.ui.intervals_refresh import ensure_intervals_data
from rps.ui.run_store import (
    clear_queue_folders,
    find_active_runs,
    prune_run_history,
    start_background_tracker,
)
from rps.ui.shared import SETTINGS, ensure_logging, get_athlete_id
from rps.workspace.index_manager import WorkspaceIndexManager

st.set_page_config(page_title="RPS - Randonneur Performance System", layout="wide")
ensure_logging(get_athlete_id())


def _iter_athlete_workspace_dirs(root: Path):
    """Yield only real athlete workspace directories under the runtime root."""

    for candidate in root.iterdir():
        if not candidate.is_dir():
            continue
        if candidate.name == "runs":
            continue
        if not ((candidate / "data").is_dir() or (candidate / "latest").is_dir()):
            continue
        yield candidate


def _cleanup_index_background(root: Path) -> None:
    """Background cleanup for missing index entries."""
    for athlete_dir in _iter_athlete_workspace_dirs(root):
        active = find_active_runs(
            root,
            athlete_dir.name,
            process_type="system_housekeeping",
            process_subtype="index_cleanup",
        )
        if active:
            continue
        tracker = start_background_tracker(
            root,
            athlete_dir.name,
            process_type="system_housekeeping",
            process_subtype="index_cleanup",
            message="Pruning missing index entries and rendered sidecars.",
            status="RUNNING",
        )
        mgr = WorkspaceIndexManager(root=root, athlete_id=athlete_dir.name)
        try:
            mgr.prune_missing()
            prune_rendered_sidecars(root, athlete_dir.name)
            tracker.mark_done("Housekeeping cleanup complete.")
        except Exception as exc:  # pragma: no cover - background guard
            tracker.mark_failed(f"Housekeeping cleanup failed: {exc}")


def _cleanup_logs_background(root: Path, retention_days: int) -> None:
    """Background cleanup for stale log files."""
    for athlete_dir in _iter_athlete_workspace_dirs(root):
        active = find_active_runs(
            root,
            athlete_dir.name,
            process_type="system_housekeeping",
            process_subtype="log_cleanup",
        )
        if active:
            continue
        tracker = start_background_tracker(
            root,
            athlete_dir.name,
            process_type="system_housekeeping",
            process_subtype="log_cleanup",
            message=f"Pruning logs older than {retention_days} days.",
            status="RUNNING",
        )
        try:
            log_dir = root / athlete_dir.name / "logs"
            removed = prune_old_logs(log_dir, retention_days)
            tracker.mark_done(f"Log cleanup complete. Removed {removed} files.")
        except Exception as exc:  # pragma: no cover - background guard
            tracker.mark_failed(f"Log cleanup failed: {exc}")


def _cleanup_runs_background(root: Path, retention_days: int) -> None:
    """Background cleanup for run history + queue files."""
    for athlete_dir in _iter_athlete_workspace_dirs(root):
        active = find_active_runs(
            root,
            athlete_dir.name,
            process_type="system_housekeeping",
            process_subtype="run_cleanup",
        )
        if active:
            continue
        tracker = start_background_tracker(
            root,
            athlete_dir.name,
            process_type="system_housekeeping",
            process_subtype="run_cleanup",
            message=f"Pruning run history older than {retention_days} days and clearing queues.",
            status="RUNNING",
        )
        try:
            removed_runs = prune_run_history(root, athlete_dir.name, retention_days)
            removed_queue = clear_queue_folders(root)
            tracker.mark_done(
                f"Run cleanup complete. Removed {removed_runs} runs; cleared {removed_queue} queue items."
            )
        except Exception as exc:  # pragma: no cover - background guard
            tracker.mark_failed(f"Run cleanup failed: {exc}")


def _refresh_evidence_background(root: Path, athlete_id: str, interval_days: int) -> None:
    """Run a due-only evidence refresh in the background for the current athlete."""

    active = find_active_runs(
        root,
        athlete_id,
        process_type="evidence",
        process_subtype="literature_refresh",
    )
    if active:
        return
    if not evidence_refresh_due(now=datetime.now(UTC), interval_days=interval_days):
        return
    tracker = start_background_tracker(
        root,
        athlete_id,
        process_type="evidence",
        process_subtype="literature_refresh",
        message="Refreshing canonical evidence library from primary sources.",
        status="RUNNING",
    )
    try:
        try:
            max_entries_per_refresh = int(os.getenv("RPS_EVIDENCE_REFRESH_MAX_ENTRIES", "5"))
        except ValueError:
            max_entries_per_refresh = 5
        result = refresh_evidence_library(
            refresh_interval_days=interval_days,
            max_entries_per_refresh=max_entries_per_refresh,
            athlete_id=athlete_id,
            workspace_root=root,
            run_id=tracker.run_id,
        )
        tracker.mark_done(f"Evidence refresh complete: {result.get('status', 'done')}.")
    except Exception as exc:  # pragma: no cover - background guard
        tracker.mark_failed(f"Evidence refresh failed: {exc}")


if "index_cleanup_started" not in st.session_state:
    st.session_state["index_cleanup_started"] = True
    cleanup_thread = threading.Thread(
        target=_cleanup_index_background,
        args=(SETTINGS.workspace_root,),
        daemon=True,
    )
    cleanup_thread.start()

if "log_cleanup_started" not in st.session_state:
    st.session_state["log_cleanup_started"] = True
    try:
        retention_days = int(os.getenv("RPS_LOG_RETENTION_DAYS", "7"))
    except ValueError:
        retention_days = 7
    log_cleanup_thread = threading.Thread(
        target=_cleanup_logs_background,
        args=(SETTINGS.workspace_root, retention_days),
        daemon=True,
    )
    log_cleanup_thread.start()

if "run_cleanup_started" not in st.session_state:
    st.session_state["run_cleanup_started"] = True
    try:
        retention_days = int(os.getenv("RPS_RUN_RETENTION_DAYS", "7"))
    except ValueError:
        retention_days = 7
    run_cleanup_thread = threading.Thread(
        target=_cleanup_runs_background,
        args=(SETTINGS.workspace_root, retention_days),
        daemon=True,
    )
    run_cleanup_thread.start()

if "evidence_refresh_started" not in st.session_state:
    st.session_state["evidence_refresh_started"] = True
    if os.getenv("RPS_EVIDENCE_REFRESH_ENABLED", "1").strip().lower() not in {"0", "false", "no"}:
        try:
            evidence_interval_days = int(os.getenv("RPS_EVIDENCE_REFRESH_INTERVAL_DAYS", "7"))
        except ValueError:
            evidence_interval_days = 7
        evidence_refresh_thread = threading.Thread(
            target=_refresh_evidence_background,
            args=(SETTINGS.workspace_root, get_athlete_id(), evidence_interval_days),
            daemon=True,
        )
        evidence_refresh_thread.start()

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
    title="About You & Goals",
    icon=":material/person:",
)
availability = st.Page(
    "pages/athlete_profile/availability.py",
    title="Availability",
    icon=":material/event_available:",
)
events = st.Page(
    "pages/athlete_profile/events.py",
    title="Events",
    icon=":material/emoji_events:",
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
historic_data = st.Page(
    "pages/athlete_profile/historic_data.py",
    title="Historic Data",
    icon=":material/timeline:",
)
zones = st.Page(
    "pages/athlete_profile/zones.py",
    title="Zones",
    icon=":material/straighten:",
)
data_operations = st.Page(
    "pages/athlete_profile/data_operations.py",
    title="Data Operations",
    icon=":material/cloud_download:",
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
        "Athlete Profile": [
            about_you,
            availability,
            events,
            logistics,
            historic_data,
            zones,
            kpi_profile,
            data_operations,
        ],
        "System": [system_status, system_history, system_log],
    }
)
max_age_hours = float(os.getenv("RPS_INTERVALS_MAX_AGE_HOURS", "2"))
ensure_intervals_data(get_athlete_id(), max_age_hours)
pg.run()
