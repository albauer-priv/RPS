from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from rps.rendering.auto_render import prune_rendered_sidecars
from rps.core.logging import prune_old_logs
from rps.openai.vectorstore_state import DEFAULT_STATE_PATH, load_state, write_state
from rps.openai.vectorstores import compute_manifest_hash, load_manifest, sync_manifest
from rps.ui.intervals_refresh import ensure_intervals_data
from rps.ui.run_store import clear_queue_folders, find_active_runs, prune_run_history, start_background_tracker
from rps.ui.shared import SETTINGS, get_athlete_id
from rps.workspace.index_manager import WorkspaceIndexManager

st.set_page_config(page_title="RPS - Randonneur Performance System", layout="wide")


def _cleanup_index_background(root: Path) -> None:
    """Background cleanup for missing index entries."""
    for athlete_dir in root.iterdir():
        if not athlete_dir.is_dir():
            continue
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
    for athlete_dir in root.iterdir():
        if not athlete_dir.is_dir():
            continue
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
    for athlete_dir in root.iterdir():
        if not athlete_dir.is_dir():
            continue
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


def _vectorstore_sync_background(root: Path, athlete_id: str, interval_minutes: int) -> None:
    """Background sync for vector stores based on manifest hash."""
    if os.getenv("RPS_DISABLE_VECTORSTORE_SYNC") == "1":
        return
    manifest_path = Path("knowledge/all_agents/manifest.yaml")
    if not manifest_path.exists():
        return
    try:
        manifest = load_manifest(manifest_path)
    except Exception:
        return

    state = load_state(DEFAULT_STATE_PATH)
    store_entry = state.setdefault("vectorstores", {}).setdefault(manifest.vector_store_name, {})
    last_check_at = store_entry.get("last_check_at")
    if last_check_at:
        try:
            last_check_dt = datetime.fromisoformat(last_check_at)
        except ValueError:
            last_check_dt = None
        else:
            elapsed = datetime.now(timezone.utc) - last_check_dt
            if elapsed.total_seconds() < interval_minutes * 60:
                return

    active = find_active_runs(
        root,
        athlete_id,
        process_type="system_housekeeping",
        process_subtype="vectorstore_sync",
    )
    if active:
        return

    tracker = start_background_tracker(
        root,
        athlete_id,
        process_type="system_housekeeping",
        process_subtype="vectorstore_sync",
        message="Checking vector store sync state.",
        status="RUNNING",
    )
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        manifest_hash = compute_manifest_hash(manifest_path)
        store_entry["last_check_at"] = now_iso
        if store_entry.get("manifest_hash") == manifest_hash and store_entry.get("vector_store_id"):
            write_state(DEFAULT_STATE_PATH, state)
            tracker.mark_done("Vector store is up to date.")
            return

        tracker.mark_running("Vector store out of date; resetting and syncing.")
        stats = sync_manifest(
            manifest_path=manifest_path,
            delete_removed=True,
            reset=True,
            progress=False,
            state=state,
        )
        store_entry["manifest_hash"] = manifest_hash
        store_entry["last_sync_at"] = now_iso
        store_entry["last_sync_status"] = "reset"
        write_state(DEFAULT_STATE_PATH, state)
        tracker.mark_done(
            f"Vector store reset complete. added={stats['added']} "
            f"updated={stats['updated']} removed={stats['removed']} skipped={stats['skipped']}."
        )
    except Exception as exc:  # pragma: no cover - background guard
        store_entry["last_check_at"] = now_iso
        write_state(DEFAULT_STATE_PATH, state)
        tracker.mark_failed(f"Vector store sync failed: {exc}")


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

if "vectorstore_sync_started" not in st.session_state:
    st.session_state["vectorstore_sync_started"] = True
    try:
        interval_minutes = int(os.getenv("RPS_VECTORSTORE_SYNC_INTERVAL_MINUTES", "60"))
    except ValueError:
        interval_minutes = 60
    vectorstore_thread = threading.Thread(
        target=_vectorstore_sync_background,
        args=(SETTINGS.workspace_root, get_athlete_id(), interval_minutes),
        daemon=True,
    )
    vectorstore_thread.start()

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
