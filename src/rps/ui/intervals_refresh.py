from __future__ import annotations

import argparse
import json
import logging
import os
import threading
from datetime import UTC, datetime
from pathlib import Path

import streamlit as st

from rps.core.config import load_app_settings, load_env_file
from rps.data_pipeline.intervals_data import run_pipeline as run_intervals_pipeline
from rps.ui.run_store import find_active_runs, start_background_tracker

ROOT = Path(__file__).resolve().parents[3]
load_env_file(ROOT / ".env")
SETTINGS = load_app_settings()

_INTERVALS_JOB_PREFIX = "intervals_refresh_job"


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _is_stale(path: Path, max_age_hours: float) -> bool:
    if not path.exists():
        return True
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return True
    created_at = _parse_iso_datetime(payload.get("meta", {}).get("created_at"))
    if not created_at:
        return True
    age = datetime.now(UTC) - created_at
    return age.total_seconds() > max_age_hours * 3600


def _intervals_job_key(athlete_id: str) -> str:
    return f"{_INTERVALS_JOB_PREFIX}_{athlete_id}"


def _schedule_intervals_refresh(
    athlete_id: str,
    logger: logging.Logger,
    job_key: str,
    *,
    year: int | None = None,
    week: int | None = None,
) -> dict:
    active = find_active_runs(
        SETTINGS.workspace_root,
        athlete_id,
        process_type="data_pipeline",
        process_subtype="intervals_fetch",
    )
    if active:
        run_id = active[0].get("run_id") or "active"
        return {
            "thread": None,
            "status": "running",
            "message": "Intervals pipeline already running.",
            "exception": None,
            "run_id": run_id,
        }
    historical_years = int(os.getenv("RPS_HISTORICAL_YEARS", "3"))
    args = argparse.Namespace(
        year=year,
        week=week,
        from_date=None,
        to_date=None,
        athlete=athlete_id,
        skip_validate=False,
        historical_years=historical_years,
    )
    tracker = start_background_tracker(
        SETTINGS.workspace_root,
        athlete_id,
        process_type="data_pipeline",
        process_subtype="intervals_fetch",
        message="Intervals refresh queued...",
        status="QUEUED",
    )
    job: dict = {
        "thread": None,
        "status": "queued",
        "message": "Intervals refresh queued...",
        "exception": None,
        "run_id": tracker.run_id,
    }
    if year is not None and week is not None:
        job["message"] = f"Intervals refresh queued for {year:04d}-W{week:02d}."

    def worker() -> None:
        job["status"] = "running"
        if year is not None and week is not None:
            job["message"] = f"Running Intervals pipeline for {year:04d}-W{week:02d}..."
        else:
            job["message"] = "Running Intervals pipeline..."
        tracker.mark_running(job["message"])
        try:
            run_intervals_pipeline(args, logger=logger)
            job["status"] = "done"
            if year is not None and week is not None:
                job["message"] = f"Intervals data refreshed for {year:04d}-W{week:02d}."
            else:
                job["message"] = "Intervals data refreshed."
            tracker.mark_done(job["message"])
        except Exception as exc:  # pragma: no cover - thread fallback
            job["status"] = "failed"
            job["message"] = f"Intervals pipeline failed: {exc}"
            job["exception"] = exc
            logger.exception("Intervals pipeline failed for athlete=%s", athlete_id)
            tracker.mark_failed(job["message"])

    thread = threading.Thread(target=worker, daemon=True)
    job["thread"] = thread
    st.session_state[job_key] = job
    thread.start()
    return job


def ensure_intervals_data(athlete_id: str, max_age_hours: float) -> tuple[bool, str]:
    """Ensure Intervals data is fresh or schedule a background refresh."""
    if os.getenv("RPS_DISABLE_INTERVALS_REFRESH") == "1":
        return True, "Intervals refresh disabled by config."

    logger = logging.getLogger("rps.ui.performance")
    latest_dir = SETTINGS.workspace_root / athlete_id / "latest"
    actual_path = latest_dir / "activities_actual.json"
    trend_path = latest_dir / "activities_trend.json"
    stale = _is_stale(actual_path, max_age_hours) or _is_stale(trend_path, max_age_hours)
    if not stale:
        return True, "Intervals data is fresh."

    job_key = _intervals_job_key(athlete_id)
    logger.info("Intervals data stale; scheduling refresh for athlete=%s", athlete_id)
    job = st.session_state.get(job_key)

    if job:
        thread = job.get("thread")
        if thread and thread.is_alive():
            return False, job.get("message", "Intervals pipeline is running...")
        if job.get("status") == "done":
            del st.session_state[job_key]
            return True, job.get("message", "Intervals data refreshed.")
        if job.get("status") == "failed":
            job = _schedule_intervals_refresh(athlete_id, logger, job_key)
            return False, str(job.get("message") or "Intervals pipeline is running...")
    job = _schedule_intervals_refresh(athlete_id, logger, job_key)
    return False, str(job.get("message") or "Intervals pipeline is running...")


def request_intervals_refresh(
    athlete_id: str,
    *,
    year: int | None = None,
    week: int | None = None,
) -> tuple[str, str | None, str | None]:
    """Force a background Intervals refresh, optionally scoped to one ISO week."""
    if os.getenv("RPS_DISABLE_INTERVALS_REFRESH") == "1":
        return "done", "Intervals refresh disabled by config.", None

    logger = logging.getLogger("rps.ui.performance")
    job_key = _intervals_job_key(athlete_id)
    job = _schedule_intervals_refresh(athlete_id, logger, job_key, year=year, week=week)
    status = job.get("status", "running")
    message = job.get("message")
    run_id = job.get("run_id")

    if status in {"queued", "running"}:
        return "running", message, run_id
    if status == "failed":
        return "error", message, run_id
    return "done", message, run_id
