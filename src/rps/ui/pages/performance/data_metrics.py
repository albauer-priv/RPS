from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path

try:
    import plotly.graph_objects as go
except Exception:  # pragma: no cover - optional dependency
    go = None
try:
    from plotly.subplots import make_subplots
except Exception:  # pragma: no cover - optional dependency
    make_subplots = None
import streamlit as st

from rps.ui.intervals_refresh import ensure_intervals_data, request_intervals_refresh
from rps.ui.shared import (
    SETTINGS,
    announce_log_file,
    get_athlete_id,
    get_iso_year_week,
    init_ui_state,
    render_global_sidebar,
    render_status_panel,
    set_status,
)
from rps.workspace.iso_helpers import (
    IsoWeek,
    next_iso_week,
    parse_iso_week,
    parse_iso_week_range,
    previous_iso_week,
)
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType

try:
    import pandas as pd
except Exception:  # pragma: no cover - optional dependency
    pd = None

DATE_PERIOD_MIN_TEXT_LENGTH = 21
DATE_PERIOD_PART_COUNT = 6


ROOT = SETTINGS.workspace_root
_INTERVALS_JOB_PREFIX = "intervals_refresh_job"
_ACTIVITY_WINDOW_WEEKS = 52



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



def _iter_weeks_in_range(range_spec):
    if not range_spec:
        return []
    weeks = []
    current = range_spec.start
    while True:
        weeks.append(current)
        if current == range_spec.end:
            break
        current = next_iso_week(current)
    return weeks


def _last_n_weeks(current: IsoWeek, count: int) -> list[IsoWeek]:
    if count <= 0:
        return []
    weeks = [current]
    while len(weeks) < count:
        current = previous_iso_week(current)
        weeks.append(current)
    return list(reversed(weeks))


def _season_corridor_by_week(store: LocalArtifactStore, athlete_id: str) -> dict[str, dict[str, float]]:
    if not store.latest_exists(athlete_id, ArtifactType.SEASON_PLAN):
        return {}
    payload = store.load_latest(athlete_id, ArtifactType.SEASON_PLAN)
    if not isinstance(payload, dict):
        return {}
    phases = (payload.get("data") or {}).get("phases", []) or []
    corridors: dict[str, dict[str, float]] = {}
    for phase in phases:
        iso_range = phase.get("iso_week_range")
        weekly_kj = (phase.get("weekly_load_corridor") or {}).get("weekly_kj") or {}
        minimum = weekly_kj.get("min")
        maximum = weekly_kj.get("max")
        range_spec = parse_iso_week_range(iso_range)
        if not range_spec and iso_range and "--" in iso_range:
            start, end = iso_range.split("--", maxsplit=1)
            start_label = _normalize_iso_label(start.strip())
            end_label = _normalize_iso_label(end.strip())
            if start_label and end_label:
                range_spec = parse_iso_week_range(f"{start_label}--{end_label}")
        if minimum is None or maximum is None or not range_spec:
            continue
        for week in _iter_weeks_in_range(range_spec):
            label = f"{week.year}-W{week.week:02d}"
            corridors[label] = {"min": minimum, "max": maximum}
    return corridors


def _phase_guardrails_by_week(store: LocalArtifactStore, athlete_id: str) -> dict[str, dict[str, float]]:
    corridors: dict[str, dict[str, float]] = {}
    for version in store.list_versions(athlete_id, ArtifactType.PHASE_GUARDRAILS):
        payload = store.load_version(athlete_id, ArtifactType.PHASE_GUARDRAILS, version)
        if not isinstance(payload, dict):
            continue
        bands = (payload.get("data") or {}).get("load_guardrails", {}).get("weekly_kj_bands", []) or []
        for band in bands:
            week = band.get("week")
            limits = (band.get("band") or {})
            minimum = limits.get("min")
            maximum = limits.get("max")
            if not week or minimum is None or maximum is None:
                continue
            label = f"{week}"
            existing = corridors.get(label)
            if existing:
                corridors[label] = {
                    "min": max(existing.get("min", minimum), minimum),
                    "max": min(existing.get("max", maximum), maximum),
                }
            else:
                corridors[label] = {"min": minimum, "max": maximum}
    return corridors


def _week_plan_corridor_by_week(store: LocalArtifactStore, athlete_id: str) -> dict[str, dict[str, float]]:
    corridors: dict[str, dict[str, float]] = {}
    for version in store.list_versions(athlete_id, ArtifactType.WEEK_PLAN):
        payload = store.load_version(athlete_id, ArtifactType.WEEK_PLAN, version)
        if not isinstance(payload, dict):
            continue
        meta = payload.get("meta") or {}
        iso_week = meta.get("iso_week")
        if not iso_week:
            continue
        week = parse_iso_week(iso_week)
        if not week:
            continue
        corridor = (payload.get("data") or {}).get("week_summary", {}).get("weekly_load_corridor_kj") or {}
        minimum = corridor.get("min")
        maximum = corridor.get("max")
        if minimum is None or maximum is None:
            continue
        label = f"{week.year}-W{week.week:02d}"
        corridors[label] = {"min": minimum, "max": maximum}
    return corridors


def _planned_weekly_kj_by_week(store: LocalArtifactStore, athlete_id: str) -> dict[str, float]:
    planned: dict[str, float] = {}
    for version in store.list_versions(athlete_id, ArtifactType.WEEK_PLAN):
        payload = store.load_version(athlete_id, ArtifactType.WEEK_PLAN, version)
        if not isinstance(payload, dict):
            continue
        meta = payload.get("meta") or {}
        iso_week = meta.get("iso_week")
        if not iso_week:
            continue
        normalized = _normalize_iso_label(iso_week)
        if not normalized:
            continue
        summary = (payload.get("data") or {}).get("week_summary") or {}
        value = summary.get("planned_weekly_load_kj")
        if value is None:
            continue
        planned[normalized] = float(value)
    return planned



def _normalize_iso_label(label: str) -> str | None:
    if not label:
        return None
    candidate = label
    if "-W" in candidate:
        candidate = candidate.replace("-W", "-")
    week = parse_iso_week(candidate)
    if not week:
        return None
    return f"{week.year}-W{week.week:02d}"


def _normalize_corridor(corridor: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    normalized: dict[str, dict[str, float]] = {}
    for key, value in corridor.items():
        label = _normalize_iso_label(str(key))
        if not label:
            continue
        normalized[label] = value
    return normalized


def _sorted_labels(*corridors: dict[str, dict[str, float]]) -> list[str]:
    labels: set[str] = set()
    for corridor in corridors:
        labels.update(_normalize_corridor(corridor).keys())
    return sorted(
        labels,
        key=lambda label: (
            int(label.split("-W")[0]),
            int(label.split("-W")[1]),
        ),
    )


def _label_order(label: str) -> tuple[int, int] | None:
    normalized = _normalize_iso_label(label)
    if not normalized:
        return None
    year_str, week_str = normalized.split("-W")
    return int(year_str), int(week_str)


def _build_corridor_overview_chart(
    season_corridor: dict[str, dict[str, float]],
    phase_corridor: dict[str, dict[str, float]],
    week_corridor: dict[str, dict[str, float]],
    actual_weekly_kj: dict[str, float],
    planned_weekly_kj: dict[str, float],
):
    if go is None:
        return None
    season_corridor = _normalize_corridor(season_corridor)
    phase_corridor = _normalize_corridor(phase_corridor)
    week_corridor = _normalize_corridor(week_corridor)
    labels = _sorted_labels(season_corridor)
    if not labels:
        return None

    def corridor_values(corridor: dict[str, dict[str, float]], key: str) -> list[float | None]:
        values: list[float | None] = []
        for label in labels:
            value = corridor.get(label, {}).get(key)
            values.append(float(value) if value is not None else None)
        return values

    fig = go.Figure()
    corridors = [
        ("Season", season_corridor, "#6c757d"),
        ("Phase", phase_corridor, "#8c564b"),
        ("Week Plan", week_corridor, "#2ca02c"),
    ]
    for name, corridor, color in corridors:
        min_vals = corridor_values(corridor, "min")
        max_vals = corridor_values(corridor, "max")
        if all(value is None for value in min_vals + max_vals):
            continue
        fig.add_trace(
            go.Scatter(
                x=labels,
                y=min_vals,
                mode="lines",
                name=f"{name} Min",
                line={"color": color, "dash": "dot"},
                hovertemplate="Week %{x}<br>%{fullData.name} %{y}<extra></extra>",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=labels,
                y=max_vals,
                mode="lines",
                name=f"{name} Max",
                line={"color": color},
                fill="tonexty",
                fillcolor=f"rgba{tuple(int(color[i:i+2], 16) for i in (1, 3, 5)) + (0.12,)}",
                hovertemplate="Week %{x}<br>%{fullData.name} %{y}<extra></extra>",
            )
        )
    if actual_weekly_kj:
        actual_vals = [actual_weekly_kj.get(label) for label in labels]
        fig.add_trace(
            go.Bar(
                x=labels,
                y=actual_vals,
                name="Actual Weekly kJ",
                marker_color="#0b6bcb",
                opacity=0.35,
                hovertemplate="Week %{x}<br>Actual kJ %{y}<extra></extra>",
            )
        )
    if planned_weekly_kj:
        planned_vals = [planned_weekly_kj.get(label) for label in labels]
        fig.add_trace(
            go.Scatter(
                x=labels,
                y=planned_vals,
                mode="lines+markers",
                name="Planned Weekly kJ",
                line={"color": "#1f77b4", "dash": "dash"},
                hovertemplate="Week %{x}<br>Planned kJ %{y}<extra></extra>",
            )
        )
    fig.update_layout(
        xaxis={"title": "Week", "tickangle": -45},
        yaxis={"title": "kJ Corridor"},
        legend_title_text="Corridor",
        barmode="overlay",
        margin={"l": 40, "r": 20, "t": 20, "b": 60},
    )
    return fig


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


def _coerce_bool(value: object) -> bool | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(int(value))
    if isinstance(value, str):
        cleaned = value.strip().lower()
        if cleaned in {"true", "t", "yes", "y", "1"}:
            return True
        if cleaned in {"false", "f", "no", "n", "0"}:
            return False
    return None


def _format_date_value(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (datetime, date)):
        return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    return str(value)


def _format_datetime_value(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _read_activities_actual_from_parquet(path: Path) -> list[dict]:
    df = pd.read_parquet(path)
    activities: list[dict] = []
    for row in df.to_dict(orient="records"):
        flags = {
            "flag_long_ride_150min_bool": _coerce_bool(row.get("Flag Long Ride >=150min (bool)")),
            "flag_long_ride_180min_bool": _coerce_bool(row.get("Flag Long Ride >=180min (bool)")),
            "flag_long_ride_240min_bool": _coerce_bool(row.get("Flag Long Ride >=240min (bool)")),
            "flag_if_0_75_bool": _coerce_bool(row.get("Flag IF <= 0.75 (bool)")),
            "flag_if_0_80_bool": _coerce_bool(row.get("Flag IF <= 0.80 (bool)")),
            "flag_z2_share_60_bool": _coerce_bool(row.get("Flag Z2 Share >= 60% (bool)")),
            "flag_z2_share_70_bool": _coerce_bool(row.get("Flag Z2 Share >= 70% (bool)")),
            "flag_drift_valid_z2_90min_bool": _coerce_bool(
                row.get("Flag Drift Valid (Z2 >= 90min) (bool)")
            ),
            "flag_des_long_base_candidate_bool": _coerce_bool(
                row.get("Flag DES Long Base Candidate (bool)")
            ),
            "flag_des_long_build_candidate_bool": _coerce_bool(
                row.get("Flag DES Long Build Candidate (bool)")
            ),
            "flag_brevet_long_candidate_bool": _coerce_bool(
                row.get("Flag Brevet Long Candidate (bool)")
            ),
        }
        metrics = {
            "decoupling": row.get("Decoupling (%)"),
            "durability_index_di": row.get("Durability Index (DI)"),
        }
        activities.append(
            {
                "iso_year": row.get("ISO Year"),
                "iso_week": row.get("ISO Week"),
                "day": _format_date_value(row.get("Day")),
                "day_of_week": row.get("Day of Week"),
                "activity_id": row.get("Activity ID"),
                "start_time_local": _format_datetime_value(row.get("Start Time (Local)")),
                "type": row.get("Type"),
                "moving_time": row.get("Moving Time (hh:mm:ss)"),
                "distance_km": row.get("Distance (km)"),
                "work_kj": row.get("Work (kJ)"),
                "load_tss": row.get("Load (TSS)"),
                "normalized_power_w": row.get("NP (W)"),
                "intensity_factor": row.get("Intensity Factor (IF)"),
                "avg_hr_bpm": row.get("Avg HR (bpm)"),
                "max_hr_bpm": row.get("Max HR (bpm)"),
                "flags": flags,
                "metrics": metrics,
            }
        )
    return activities


def _read_activities_actual_from_json(path: Path) -> list[dict]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return (payload.get("data", {}) or {}).get("activities") or []


def _read_activities_actual(path: Path) -> list[dict]:
    if path.suffix == ".parquet":
        return _read_activities_actual_from_parquet(path)
    return _read_activities_actual_from_json(path)


def _load_week_activities_actual(week_dir: Path) -> list[dict]:
    parquet_files = sorted(week_dir.glob("activities_actual_*.parquet"))
    json_files = sorted(week_dir.glob("activities_actual_*.json"))
    paths = parquet_files or json_files
    activities: list[dict] = []
    for path in paths:
        activities.extend(_read_activities_actual(path))
    return activities



def _load_activity_durability_points(
    data_root: Path,
    weeks: list[IsoWeek],
) -> list[dict[str, object]]:
    points: list[dict[str, object]] = []
    for week in weeks:
        week_dir = data_root / f"{week.year}" / f"{week.week:02d}"
        activities = _load_week_activities_actual(week_dir)
        for activity in activities:
            metrics = activity.get("metrics") or {}
            flags = activity.get("flags") or {}
            decoupling = metrics.get("decoupling")
            durability_index = metrics.get("durability_index_di")
            work_kj = activity.get("work_kj")
            if decoupling is None or durability_index is None or work_kj is None:
                continue
            start_time = activity.get("start_time_local")
            iso_year = activity.get("iso_year")
            iso_week = activity.get("iso_week")
            day_of_week = activity.get("day_of_week")
            activity_date = None
            if start_time:
                try:
                    activity_date = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                except ValueError:
                    activity_date = None
            if activity_date is None and iso_year and iso_week and day_of_week:
                try:
                    activity_date = datetime.fromisocalendar(int(iso_year), int(iso_week), int(day_of_week))
                except ValueError:
                    activity_date = None
            points.append(
                {
                    "work_kj": float(work_kj),
                    "durability_index": float(durability_index),
                    "decoupling": float(decoupling),
                    "day": activity.get("day"),
                    "type": activity.get("type"),
                    "moving_time": activity.get("moving_time"),
                    "intensity_factor": activity.get("intensity_factor"),
                    "start_time_local": activity.get("start_time_local"),
                    "activity_date": activity_date,
                    "flags": flags,
                }
            )
    return points


def _build_weekly_dose_outcome_chart(weekly_df):
    if go is None or make_subplots is None:
        return None
    if weekly_df is None or weekly_df.empty:
        return None
    ordered = weekly_df.sort_values("period_order")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=ordered["label"],
            y=ordered["weekly_kj"],
            name="Work (kJ)",
            marker_color="#0b6bcb",
            opacity=0.6,
            hovertemplate="Week %{x}<br>Work %{y} kJ<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=ordered["label"],
            y=ordered["durability_index"],
            mode="lines+markers",
            name="Durability Index",
            line={"color": "#f15a22"},
            hovertemplate="Week %{x}<br>DI %{y:.2f}<extra></extra>",
            yaxis="y2",
        ),
    )
    fig.add_trace(
        go.Scatter(
            x=ordered["label"],
            y=ordered["decoupling_percent"],
            mode="lines+markers",
            name="Decoupling (%)",
            line={"color": "#2ca02c", "dash": "dot"},
            hovertemplate="Week %{x}<br>Decoupling %{y:.2f}%<extra></extra>",
            yaxis="y3",
        ),
    )
    fig.update_layout(
        xaxis={"title": "Week", "tickangle": -45},
        legend_title_text="Series",
        yaxis={"title": "Work (kJ)"},
        yaxis2={
            "title": "Durability Index",
            "overlaying": "y",
            "side": "right",
        },
        yaxis3={
            "title": "Decoupling (%)",
            "overlaying": "y",
            "side": "right",
            "position": 0.98,
        },
        margin={"l": 40, "r": 70, "t": 20, "b": 60},
    )
    return fig


def _build_daily_durability_scatter(points: list[dict[str, object]]):
    if go is None:
        return None
    if not points:
        return None
    fig = go.Figure()
    filtered = []
    for point in points:
        raw_flags = point.get("flags")
        if not isinstance(raw_flags, dict):
            continue
        if raw_flags.get("flag_drift_valid_z2_90min_bool"):
            filtered.append(point)
    if not filtered:
        return None
    fig.add_trace(
        go.Scatter(
            x=[p["work_kj"] for p in filtered],
            y=[p["durability_index"] for p in filtered],
            mode="markers",
            name="Activity",
            marker={
                "size": 10,
                "color": [p["decoupling"] for p in filtered],
                "colorscale": "RdYlGn_r",
                "colorbar": {"title": "Decoupling"},
                "showscale": True,
            },
            hovertemplate=(
                "Work %{x} kJ<br>"
                "DI %{y:.2f}<br>"
                "Decoupling %{marker.color:.2f}%<br>"
                "%{text}<extra></extra>"
            ),
            text=[
                f"{p.get('day')} {p.get('type')} · {p.get('moving_time')} · IF {p.get('intensity_factor')}"
                for p in filtered
            ],
        )
    )
    fig.update_layout(
        xaxis={"title": "Work (kJ)"},
        yaxis={"title": "Durability Index"},
        margin={"l": 40, "r": 20, "t": 20, "b": 60},
    )
    return fig


def _weekly_trends_from_dataframe(df: pd.DataFrame) -> list[dict]:
    def _split_period(raw: object) -> tuple[str | None, str | None]:
        if raw is None or (isinstance(raw, float) and pd.isna(raw)):
            return None, None
        text = str(raw)
        if "-" in text and len(text) >= DATE_PERIOD_MIN_TEXT_LENGTH:
            parts = text.split("-")
            if len(parts) >= DATE_PERIOD_PART_COUNT:
                start = "-".join(parts[:3])
                end = "-".join(parts[3:6])
                return start, end
        if " to " in text:
            start, end = text.split(" to ", 1)
            return start.strip(), end.strip()
        return None, None

    rows = []
    for _, row in df.iterrows():
        year = row.get("Year")
        iso_week = row.get("ISO Week")
        if pd.isna(year) or pd.isna(iso_week):
            continue
        period_from, period_to = _split_period(row.get("Period"))
        rows.append(
            {
                "year": int(year),
                "iso_week": int(iso_week),
                "weekly_aggregates": {
                    "activity_count": row.get("# Activities"),
                    "moving_time": row.get("Moving Time (h:mm)"),
                    "distance_km": row.get("Distance (km)"),
                    "load_tss": row.get("Load (TSS)"),
                    "work_kj": row.get("Work (kJ)"),
                },
                "intensity_load_metrics": {
                    "durability_index": row.get("Durability Index (DI)"),
                    "decoupling_percent": row.get("Decoupling (%)"),
                    "intensity_factor": row.get("Intensity Factor (IF)"),
                    "normalized_power_w": row.get("Normalized Power (NP) (W)"),
                    "efficiency_factor": row.get("Efficiency Factor (EF)"),
                    "functional_intensity_ratio": row.get(
                        "Functional Intensity Ratio (FIR) (MMP 5'/ MMP 20')"
                    ),
                    "ftp_estimated_w": row.get("FTP Estimated (W)"),
                    "vo2_ftp": row.get("VO2/FTP (MMP 300s (W) / FTP Estimated (W))"),
                },
                "metrics": {
                    "tsb_today": row.get("TSB (today)"),
                    "weekly_moving_time_total_min": row.get("Weekly Moving Time Total (min)"),
                    "weekly_z2_time_total_min": row.get("Weekly Z2 Time Total (min)"),
                    "weekly_z2_share": row.get("Weekly Z2 Share (%)"),
                    "weekly_moving_time_max_min": row.get("Weekly Moving Time Max (min)"),
                    "weekly_z2_time_max_min": row.get("Weekly Z2 Time Max (min)"),
                },
                "period": {
                    "from": period_from,
                    "to": period_to,
                    "label": row.get("Period"),
                },
            }
        )
    return rows


def _load_weekly_trends_cached(
    trend_path: Path,
    trend_parquet_path: Path,
) -> tuple[list[dict], str | None, bool]:
    """Read weekly trend data (prefer parquet), fall back to cached payload while updates are in-flight."""
    cached_trends = st.session_state.get("cached_weekly_trends") or []
    cached_notes = st.session_state.get("cached_weekly_trend_notes")
    used_cache = False
    weekly_trends: list[dict] = []
    notes: str | None = None
    if trend_parquet_path.exists():
        try:
            df = pd.read_parquet(trend_parquet_path)
            weekly_trends = _weekly_trends_from_dataframe(df)
            if weekly_trends:
                st.session_state.cached_weekly_trends = weekly_trends
                st.session_state.cached_weekly_trend_notes = notes
            else:
                used_cache = True
                weekly_trends = cached_trends
                notes = cached_notes
        except Exception:
            used_cache = True
            weekly_trends = cached_trends
            notes = cached_notes
    elif trend_path.exists():
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
set_status(status_state="running", title="Data & Metrics", message="Checking intervals data...")
render_status_panel()

latest_dir = ROOT / athlete_id / "latest"
actual_path = latest_dir / "activities_actual.json"
actual_parquet_path = latest_dir / "activities_actual.parquet"
trend_path = latest_dir / "activities_trend.json"
trend_parquet_path = latest_dir / "activities_trend.parquet"

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
weekly_trends, trend_notes, trend_used_cache = _load_weekly_trends_cached(
    trend_path,
    trend_parquet_path,
)
store = LocalArtifactStore(root=SETTINGS.workspace_root)
season_corridor = _season_corridor_by_week(store, athlete_id)
phase_corridor = _phase_guardrails_by_week(store, athlete_id)
week_corridor = _week_plan_corridor_by_week(store, athlete_id)
planned_weekly_kj = _planned_weekly_kj_by_week(store, athlete_id)
current_year, current_week = get_iso_year_week()
recent_activity_weeks = _last_n_weeks(IsoWeek(current_year, current_week), _ACTIVITY_WINDOW_WEEKS)

with st.container():
    st.subheader("Planning Load Corridors")
    if not pd:
        st.info("Charts require pandas; showing data tables below.")
    else:
        if go is None:
            st.info("Plotly is not available; charts are hidden.")
        else:
            actual_weekly_kj: dict[str, float] = {}
            for entry in weekly_trends:
                year = entry.get("year")
                iso_week = entry.get("iso_week")
                if not year or iso_week is None:
                    continue
                if (int(year), int(iso_week)) > (current_year, current_week):
                    continue
                label = _normalize_iso_label(f"{int(year)}-{int(iso_week):02d}")
                if not label:
                    continue
                weekly_kj = (entry.get("weekly_aggregates") or {}).get("work_kj")
                if weekly_kj is None:
                    continue
                actual_weekly_kj[label] = float(weekly_kj)
            planned_weekly_kj = {
                label: value
                for label, value in planned_weekly_kj.items()
                if (_label_order(label) or (9999, 99)) <= (current_year, current_week)
            }
            corridor_fig = _build_corridor_overview_chart(
                season_corridor,
                phase_corridor,
                week_corridor,
                actual_weekly_kj,
                planned_weekly_kj,
            )
            if corridor_fig is None:
                st.info("No corridor data available yet.")
            else:
                st.plotly_chart(corridor_fig, width="stretch")

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
            decoupling_percent = (entry.get("intensity_load_metrics") or {}).get("decoupling_percent")
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
        df = pd.DataFrame(
            rows,
            columns=[
                "year",
                "iso_week",
                "label",
                "weekly_kj",
                "durability_index",
                "decoupling_percent",
            ],
        )
        df = df.dropna(subset=["label"]).sort_values(["year", "iso_week"])
        if df.empty:
            st.info("No weekly trend data available yet.")
        else:
            df["period_order"] = df["year"] * 100 + df["iso_week"]
            df["durability_index"] = pd.to_numeric(df["durability_index"], errors="coerce")
            df["decoupling_percent"] = pd.to_numeric(df["decoupling_percent"], errors="coerce")
            df["durability_avg"] = df["durability_index"].rolling(window=4, min_periods=1).mean()
            df["decoupling_avg"] = df["decoupling_percent"].rolling(window=4, min_periods=1).mean()
            df["season_min"] = df["label"].map(lambda label: season_corridor.get(label, {}).get("min"))
            df["season_max"] = df["label"].map(lambda label: season_corridor.get(label, {}).get("max"))
            df["phase_min"] = df["label"].map(lambda label: phase_corridor.get(label, {}).get("min"))
            df["phase_max"] = df["label"].map(lambda label: phase_corridor.get(label, {}).get("max"))
            df["week_min"] = df["label"].map(lambda label: week_corridor.get(label, {}).get("min"))
            df["week_max"] = df["label"].map(lambda label: week_corridor.get(label, {}).get("max"))
            corridor_df = (
                df.melt(
                    id_vars=["label"],
                    value_vars=[
                        "phase_min",
                        "phase_max",
                    ],
                    var_name="metric",
                    value_name="value",
                )
                .dropna(subset=["value"])
                .assign(
                    metric=lambda frame: frame["metric"].map(
                        {
                            "phase_min": "Phase Min",
                            "phase_max": "Phase Max",
                        }
                    )
                )
            )
            st.subheader("Weekly Dose → Outcome")
            st.caption(
                "Interpretation: Higher work (kJ) should be accompanied by stable or rising DI and stable or falling "
                "decoupling. Judge outcomes relative to dose, not in isolation. DI and decoupling now use separate "
                "right-side axes."
            )
            dose_fig = _build_weekly_dose_outcome_chart(df)
            if dose_fig is None:
                st.info("Plotly is not available; charts are hidden.")
            else:
                st.plotly_chart(dose_fig, width="stretch")

        st.subheader("Daily Durability Scatter")
        st.caption(
            "Interpretation: At similar work (kJ), higher DI with lower decoupling is a good signal. "
            "Points are filtered to drift-valid sessions (Z2 ≥ 90 min)."
        )
        st.markdown(
            "**Legend**: x = Work (kJ), y = Durability Index (DI), color = Decoupling (%). "
            "Good signal = high DI with low decoupling at similar kJ."
        )
        drift_only = st.checkbox(
            "Filter: Drift Valid (Z2 ≥ 90 min)",
            value=True,
        )
        long_ride_only = st.checkbox(
            "Filter: Long Ride ≥ 180 min",
            value=False,
        )
        weeks_back = st.slider(
            "Show last N weeks (including current)",
            min_value=1,
            max_value=26,
            value=12,
        )
        recent_weeks = _last_n_weeks(IsoWeek(current_year, current_week), weeks_back)
        activity_durability_points = _load_activity_durability_points(
            ROOT / athlete_id / "data",
            recent_weeks,
        )
        filtered_points = []
        for point in activity_durability_points:
            flags = point.get("flags")
            if not isinstance(flags, dict):
                flags = {}
            if drift_only and not flags.get("flag_drift_valid_z2_90min_bool"):
                continue
            if long_ride_only and not flags.get("flag_long_ride_180min_bool"):
                continue
            filtered_points.append(point)
        scatter_fig = _build_daily_durability_scatter(filtered_points)
        if scatter_fig is None:
            st.info("No drift-valid activities available yet.")
        else:
            st.plotly_chart(scatter_fig, width="stretch")

with st.container():
    st.subheader("Activities Trend")
    if trend_path.exists() or trend_parquet_path.exists():
        newest_first = st.toggle(
            "Newest first",
            value=True,
            key="trend_table_newest_first",
        )
        trend_rows = _flatten_weekly_trends(weekly_trends)
        if not newest_first:
            trend_rows = list(reversed(trend_rows))
        st.data_editor(
            trend_rows,
            num_rows="dynamic",
            width="stretch",
        )
        if trend_notes:
            st.write(trend_notes)
    else:
        st.info("No activities_trend.json found for this athlete.")

with st.container():
    st.subheader("Activities Actual")
    if actual_parquet_path.exists() or actual_path.exists():
        if actual_parquet_path.exists():
            activities = _read_activities_actual_from_parquet(actual_parquet_path)
            notes = None
        else:
            actual_payload = json.loads(actual_path.read_text(encoding="utf-8"))
            activities = actual_payload.get("data", {}).get("activities") or []
            notes = actual_payload.get("data", {}).get("notes")
        newest_first = st.toggle(
            "Newest first",
            value=True,
            key="actual_table_newest_first",
        )
        actual_rows = _flatten_activities_actual(activities)
        if not newest_first:
            actual_rows = list(reversed(actual_rows))
        st.data_editor(
            actual_rows,
            num_rows="dynamic",
            width="stretch",
        )
        if notes:
            st.write(notes)
    else:
        st.info("No activities_actual data found for this athlete.")
