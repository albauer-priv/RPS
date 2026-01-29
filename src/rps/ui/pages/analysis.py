from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from rps.data_pipeline.intervals_data import run_pipeline as run_intervals_pipeline
from rps.ui.shared import SETTINGS, announce_log_file, get_athlete_id, init_ui_state

try:
    import pandas as pd
except Exception:  # pragma: no cover - optional dependency
    pd = None


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
    age = datetime.now(timezone.utc) - created_at
    return age.total_seconds() > max_age_hours * 3600


def _ensure_intervals_data(athlete_id: str, max_age_hours: float) -> tuple[bool, str]:
    latest_dir = ROOT / "var" / "athletes" / athlete_id / "latest"
    actual_path = latest_dir / "activities_actual.json"
    trend_path = latest_dir / "activities_trend.json"
    stale = _is_stale(actual_path, max_age_hours) or _is_stale(trend_path, max_age_hours)
    if not stale:
        return True, "Intervals data is fresh."

    args = argparse.Namespace(
        year=None,
        week=None,
        from_date=None,
        to_date=None,
        athlete=athlete_id,
        skip_validate=False,
    )
    logger = logging.getLogger("rps.ui.analysis")
    try:
        run_intervals_pipeline(args, logger=logger)
    except Exception as exc:
        return False, f"Intervals pipeline failed: {exc}"
    return True, "Intervals data refreshed."


import argparse

st.set_page_config(
    page_title="RPS - Randonneur Performance System",
    layout="wide",
)

ROOT = SETTINGS.workspace_root

st.title("Analyse")

init_ui_state()
athlete_id = get_athlete_id()
announce_log_file(athlete_id)
latest_dir = ROOT / athlete_id / "latest"
actual_path = latest_dir / "activities_actual.json"
trend_path = latest_dir / "activities_trend.json"

max_age_hours = float(os.getenv("RPS_INTERVALS_MAX_AGE_HOURS", "2"))
ok, message = _ensure_intervals_data(athlete_id, max_age_hours)
if not ok:
    st.error(message)
elif message:
    st.info(message)


def _flatten_weekly_trends(weekly_trends: list[dict]) -> list[dict]:
    rows: list[dict] = []
    ordered = sorted(
        weekly_trends,
        key=lambda entry: (
            entry.get("year") or 0,
            entry.get("iso_week") or 0,
        ),
        reverse=True,
    )
    for entry in ordered:
        period = entry.get("period") or {}
        aggregates = entry.get("weekly_aggregates") or {}
        intensity = entry.get("intensity_load_metrics") or {}
        metrics = entry.get("metrics") or {}
        rows.append(
            {
                "year": entry.get("year"),
                "iso_week": entry.get("iso_week"),
                "period_from": period.get("from"),
                "period_to": period.get("to"),
                "activity_count": aggregates.get("activity_count"),
                "moving_time": aggregates.get("moving_time"),
                "distance_km": aggregates.get("distance_km"),
                "load_tss": aggregates.get("load_tss"),
                "work_kj": aggregates.get("work_kj"),
                "intensity_factor": intensity.get("intensity_factor"),
                "durability_index": intensity.get("durability_index"),
                "weekly_moving_time_total_min": metrics.get("weekly_moving_time_total_min"),
                "weekly_z2_share": metrics.get("weekly_z2_share"),
                "tsb_today": metrics.get("tsb_today"),
            }
        )
    return rows


def _flatten_activities_actual(activities: list[dict]) -> list[dict]:
    rows: list[dict] = []
    ordered = sorted(
        activities,
        key=lambda entry: (
            entry.get("iso_year") or 0,
            entry.get("iso_week") or 0,
            entry.get("day") or "",
        ),
        reverse=True,
    )
    for entry in ordered:
        flags = entry.get("flags") or {}
        rows.append(
            {
                "iso_year": entry.get("iso_year"),
                "iso_week": entry.get("iso_week"),
                "day": entry.get("day"),
                "day_of_week": entry.get("day_of_week"),
                "type": entry.get("type"),
                "moving_time": entry.get("moving_time"),
                "distance_km": entry.get("distance_km"),
                "work_kj": entry.get("work_kj"),
                "load_tss": entry.get("load_tss"),
                "intensity_factor": entry.get("intensity_factor"),
                "avg_hr_bpm": entry.get("avg_hr_bpm"),
                "max_hr_bpm": entry.get("max_hr_bpm"),
                "flag_long_ride_150min": flags.get("flag_long_ride_150min_bool"),
                "flag_long_ride_180min": flags.get("flag_long_ride_180min_bool"),
                "flag_if_0_80": flags.get("flag_if_0_80_bool"),
                "flag_z2_share_70": flags.get("flag_z2_share_70_bool"),
            }
        )
    return rows


with st.container():
    st.subheader("Weekly Load and Durability Metrics")
    if trend_path.exists() and pd:
        trend_payload = json.loads(trend_path.read_text(encoding="utf-8"))
        weekly_trends = trend_payload.get("data", {}).get("weekly_trends") or []
        ordered = sorted(
            weekly_trends,
            key=lambda entry: (
                entry.get("year") or 0,
                entry.get("iso_week") or 0,
            ),
        )
        rows: list[dict[str, object]] = []
        for entry in ordered:
            year = entry.get("year")
            iso_week = entry.get("iso_week")
            label = f"{year}-W{int(iso_week):02d}" if year and iso_week else None
            weekly_kj = (entry.get("weekly_aggregates") or {}).get("work_kj")
            durability_index = (entry.get("intensity_load_metrics") or {}).get("durability_index")
            rows.append(
                {
                    "label": label or "",
                    "weekly_kj": weekly_kj,
                    "durability_index": durability_index,
                }
            )
        df = pd.DataFrame(rows).dropna(subset=["label"]).set_index("label")
        st.caption("Weekly kJ")
        st.bar_chart(df["weekly_kj"])
        st.caption("Durability Index")
        st.line_chart(df["durability_index"])
    elif trend_path.exists():
        st.info("Charts require pandas; showing data tables below.")
    else:
        st.info("Charts will appear once activities_trend is available.")

with st.container():
    st.subheader("Activities Trend")
    if trend_path.exists():
        trend_payload = json.loads(trend_path.read_text(encoding="utf-8"))
        weekly_trends = trend_payload.get("data", {}).get("weekly_trends") or []
        st.data_editor(
            _flatten_weekly_trends(weekly_trends),
            num_rows="dynamic",
            width="stretch",
        )
        notes = trend_payload.get("data", {}).get("notes")
        if notes:
            st.write(notes)
    else:
        st.error("No activities_trend.json found for this athlete.")

with st.container():
    st.subheader("Activities Actual")
    if actual_path.exists():
        actual_payload = json.loads(actual_path.read_text(encoding="utf-8"))
        activities = actual_payload.get("data", {}).get("activities") or []
        st.data_editor(
            _flatten_activities_actual(activities),
            num_rows="dynamic",
            width="stretch",
        )
        notes = actual_payload.get("data", {}).get("notes")
        if notes:
            st.write(notes)
    else:
        st.error("No activities_actual.json found for this athlete.")
