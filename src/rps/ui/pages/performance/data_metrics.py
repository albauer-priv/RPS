from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import altair as alt
import streamlit as st

from rps.ui.intervals_refresh import ensure_intervals_data, request_intervals_refresh
from rps.ui.shared import (
    SETTINGS,
    announce_log_file,
    get_athlete_id,
    init_ui_state,
    render_global_sidebar,
    render_status_panel,
    set_status,
)

try:
    import pandas as pd
except Exception:  # pragma: no cover - optional dependency
    pd = None


ROOT = SETTINGS.workspace_root
_INTERVALS_JOB_PREFIX = "intervals_refresh_job"



def _axis_domain(series, pad: float = 0.1) -> tuple[float, float] | None:
    valid = series.dropna()
    if valid.empty:
        return None
    minimum = float(valid.min())
    maximum = float(valid.max())
    padding = pad if maximum == minimum else abs(maximum - minimum) * pad
    lower = minimum - padding
    upper = maximum + padding
    return (min(0.0, lower), upper)


def _build_line_chart(df):
    ordered = df.sort_values("period_order")
    long_df = (
        ordered[["label", "durability_index", "decoupling_percent"]]
        .rename(columns={"durability_index": "Durability Index", "decoupling_percent": "Decoupling (%)"})
        .melt(id_vars="label", var_name="metric", value_name="value")
        .dropna(subset=["value"])
    )
    return (
        alt.Chart(long_df)
        .mark_line(point=True)
        .encode(
            x=alt.X("label:N", sort=list(ordered["label"]), axis=alt.Axis(title="Week", labelAngle=-45)),
            y=alt.Y("value:Q", axis=alt.Axis(title="Metric Value")),
            color=alt.Color("metric:N", scale=alt.Scale(domain=["Durability Index", "Decoupling (%)"], range=["#f15a22", "#2ca02c"])),
            tooltip=[alt.Tooltip("label:N", title="Week"), alt.Tooltip("metric:N"), alt.Tooltip("value:Q", format=".2f")],
        )
    )


def _flatten_weekly_trends(weekly_trends: list[dict]) -> list[dict]:
    def flatten_into(target: dict, source: dict | None, prefix: str) -> None:
        if not source:
            return
        for key, value in source.items():
            safe_key = f"{prefix}{key}"
            if safe_key not in target:
                target[safe_key] = value

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
        distribution = entry.get("distribution_metrics") or {}
        flag_counts = entry.get("flag_counts") or {}
        flag_any = entry.get("flag_any") or {}
        power_tiz = entry.get("power_tiz") or {}
        hr_tiz = entry.get("hr_tiz") or {}

        row: dict[str, object] = {
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
            "decoupling_percent": intensity.get("decoupling_percent"),
            "durability_index": intensity.get("durability_index"),
            "normalized_power_w": intensity.get("normalized_power_w"),
            "efficiency_factor": intensity.get("efficiency_factor"),
            "functional_intensity_ratio": intensity.get("functional_intensity_ratio"),
            "ftp_estimated_w": intensity.get("ftp_estimated_w"),
            "vo2_ftp": intensity.get("vo2_ftp"),
            "tsb_today": metrics.get("tsb_today"),
            "weekly_moving_time_total_min": metrics.get("weekly_moving_time_total_min"),
            "weekly_z2_time_total_min": metrics.get("weekly_z2_time_total_min"),
            "weekly_z2_share": metrics.get("weekly_z2_share"),
            "weekly_moving_time_max_min": metrics.get("weekly_moving_time_max_min"),
            "weekly_z2_time_max_min": metrics.get("weekly_z2_time_max_min"),
        }
        flatten_into(row, distribution, "distribution_")
        flatten_into(row, flag_counts, "flag_count_")
        flatten_into(row, flag_any, "flag_any_")
        flatten_into(row, power_tiz, "power_tiz_")
        flatten_into(row, hr_tiz, "hr_tiz_")
        rows.append(row)
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


def _load_weekly_trends_cached(trend_path: Path) -> tuple[list[dict], str | None, bool]:
    """Read weekly trend data, fall back to last cached payload while updates are in-flight."""
    cached_trends = st.session_state.get("cached_weekly_trends") or []
    cached_notes = st.session_state.get("cached_weekly_trend_notes")
    used_cache = False
    weekly_trends: list[dict] = []
    notes: str | None = None
    if trend_path.exists():
        try:
            payload = json.loads(trend_path.read_text(encoding="utf-8"))
            weekly_trends = payload.get("data", {}).get("weekly_trends") or []
            notes = payload.get("data", {}).get("notes")
            if weekly_trends:
                st.session_state.cached_weekly_trends = weekly_trends
                st.session_state.cached_weekly_trend_notes = notes
            else:
                used_cache = True
                weekly_trends = cached_trends
                notes = cached_notes
        except json.JSONDecodeError:
            used_cache = True
            weekly_trends = cached_trends
            notes = cached_notes
    else:
        used_cache = True
        weekly_trends = cached_trends
        notes = cached_notes
    return weekly_trends, notes, used_cache


init_ui_state()
render_global_sidebar()
athlete_id = get_athlete_id()
announce_log_file(athlete_id)

st.title("Data & Metrics")
st.caption(f"Athlete: {athlete_id}")

latest_dir = ROOT / athlete_id / "latest"
actual_path = latest_dir / "activities_actual.json"
trend_path = latest_dir / "activities_trend.json"

with st.container():
    refresh_col, info_col = st.columns([1, 3])
    with refresh_col:
        refresh_clicked = st.button("Refresh Intervals Data")
    with info_col:
        st.caption("Runs the Intervals pipeline in the background.")

    if refresh_clicked:
        status_state, status_message, run_id = request_intervals_refresh(athlete_id)
        set_status(
            status_state=status_state,
            title="Data & Metrics",
            message=status_message or "Intervals refresh queued.",
            last_action="Intervals refresh",
            last_run_id=run_id,
        )

max_age_hours = float(os.getenv("RPS_INTERVALS_MAX_AGE_HOURS", "2"))
if not refresh_clicked:
    ok, message = ensure_intervals_data(athlete_id, max_age_hours)
    if not ok:
        status_state = "running" if message and any(word in message.lower() for word in ("running", "queued")) else "error"
        set_status(status_state=status_state, title="Data & Metrics", message=message or "Intervals refresh failed.")
    elif message:
        set_status(status_state="done", title="Data & Metrics", message=message)
    else:
        set_status(status_state="done", title="Data & Metrics", message="Intervals data ready.")
weekly_trends, trend_notes, trend_used_cache = _load_weekly_trends_cached(trend_path)

render_status_panel()

with st.container():
    st.subheader("Weekly Load and Durability Metrics")
    if not pd:
        st.info("Charts require pandas; showing data tables below.")
    else:
        if trend_used_cache:
            st.info("Using the most recent valid workflow output because the latest file is still being written.")
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
            if not year or iso_week is None:
                continue
            label = f"{year}-W{int(iso_week):02d}"
            weekly_kj = (entry.get("weekly_aggregates") or {}).get("work_kj")
            durability_index = (entry.get("intensity_load_metrics") or {}).get("durability_index")
            decoupling_percent = (entry.get("metrics") or {}).get("decoupling_percent")
            rows.append(
                {
                    "year": year,
                    "iso_week": iso_week,
                    "label": label,
                    "weekly_kj": weekly_kj,
                    "durability_index": durability_index,
                    "decoupling_percent": decoupling_percent,
                }
            )
        df = (
            pd.DataFrame(rows)
            .dropna(subset=["label"])
            .sort_values(["year", "iso_week"])
        )
        if not df.empty:
            df["period_order"] = df["year"] * 100 + df["iso_week"]
            df["durability_index"] = pd.to_numeric(df["durability_index"], errors="coerce")
            df["decoupling_percent"] = pd.to_numeric(df["decoupling_percent"], errors="coerce")
            df["durability_avg"] = df["durability_index"].rolling(window=4, min_periods=1).mean()
            df["decoupling_avg"] = df["decoupling_percent"].rolling(window=4, min_periods=1).mean()
            load_df = df.set_index("label")[["weekly_kj"]]
            st.caption("Weekly load (kJ) and raw Durability/Decoupling trends.")
            st.bar_chart(load_df)
            st.altair_chart(
                _build_line_chart(df),
                width="stretch",
            )

with st.container():
    st.subheader("Activities Trend")
    if trend_path.exists():
        st.data_editor(
            _flatten_weekly_trends(weekly_trends),
            num_rows="dynamic",
            width="stretch",
        )
        if trend_notes:
            st.write(trend_notes)
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
