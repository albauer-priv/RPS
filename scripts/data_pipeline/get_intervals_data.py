#!/usr/bin/env python3
"""Fetch Intervals.icu data and compile activities_actual + activities_trend outputs.

This script is intended to replace:
- intervals_export.py
- compile_activities_actual.py
- compile_activities_trend.py
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime, timedelta, date, timezone
from io import StringIO
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter, Retry
from requests.auth import HTTPBasicAuth

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    # Allow running the script directly without installing the package.
    sys.path.insert(0, str(ROOT))

from scripts.data_pipeline.common import (  # noqa: E402
    athlete_data_dir,
    athlete_latest_dir,
    configure_logging,
    load_env,
    record_index_write,
    require_env,
    resolve_athlete_id,
    resolve_schema_dir,
)
from app.workspace.schema_registry import SchemaRegistry, SchemaValidationError, validate_or_raise  # noqa: E402

# === Export configuration ===
SEPARATOR = ";"  # Intervals.icu export
QUOTECHAR = '"'
Z2_MIN_THRESHOLD_MIN = 90
TSS_PLAN_BY_WEEK: dict[tuple[int, int], int] = {}
DEFAULT_WEEKS = 24
REQUIRED_COLUMNS = [
    "Year",
    "ISO Week",
    "Period",
    "# Activities",
    "Moving Time (h:mm)",
    "Distance (km)",
    "Load (TSS)",
    "Work (kJ)",
    "Normalized Power (NP) (W)",
    "Intensity Factor (IF)",
    "Decoupling (%)",
    "Durability Index (DI)",
    "Efficiency Factor (EF)",
    "Functional Intensity Ratio (FIR) (MMP 5'/ MMP 20')",
    "FTP Estimated (W)",
    "VO2/FTP (MMP 300s (W) / FTP Estimated (W))",
    "TSB (today)",
    "Adherence (%)",
    "Z1 + Z2 Time (%)",
    "Z5 Time (%)",
    "Power TiZ Z1 (hh:mm:ss)",
    "Power TiZ Z2 (hh:mm:ss)",
    "Power TiZ Z3 (hh:mm:ss)",
    "Power TiZ Z4 (hh:mm:ss)",
    "Power TiZ Z5 (hh:mm:ss)",
    "Power TiZ Z6 (hh:mm:ss)",
    "Power TiZ Z7 (hh:mm:ss)",
    "HR TiZ Z1 (hh:mm:ss)",
    "HR TiZ Z2 (hh:mm:ss)",
    "HR TiZ Z3 (hh:mm:ss)",
    "HR TiZ Z4 (hh:mm:ss)",
    "HR TiZ Z5 (hh:mm:ss)",
    "HR TiZ Z6 (hh:mm:ss)",
    "HR TiZ Z7 (hh:mm:ss)",
    "Z2 Share (Power) (%)",
    "Sweet Spot TiZ (hh:mm:ss)",
    "VO2Max Power TiZ (hh:mm:ss)",
    "VO2Max HR TiZ (hh:mm:ss)",
    "VO2Max TiZ Eff (hh:mm:ss)",
    "MMP 60s (W)",
    "MMP 180s (W)",
    "MMP 300s (W)",
    "MMP 600s (W)",
    "MMP 1200s (W)",
    "MMP 1800s (W)",
    "MMP 3600s (W)",
    "MMP 5400s (W)",
    "MMP 7200s (W)",
    "MMP 9000s (W)",
    "MMP 10800s (W)",
    "MMP 14400s (W)",
    "MMP 18000s (W)",
    "MMP 21600s (W)",
    "Back-to-Back Z2 Days",
    "Weekly Moving Time Total (min)",
    "Weekly Z2 Time Total (min)",
    "Weekly Z2 Share (%)",
    "Weekly Moving Time Max (min)",
    "Weekly Z2 Time Max (min)",
    "Weekly Moving Time >=150min Sum (min)",
    "Weekly Moving Time >=180min Sum (min)",
    "Weekly Moving Time >=240min Sum (min)",
    "Weekly Z2 Time >=150min Sum (min)",
    "Weekly Z2 Time >=180min Sum (min)",
    "Weekly Z2 Time >=240min Sum (min)",
    "Weekly Moving Time DES Base Sum (min)",
    "Weekly Moving Time DES Build Sum (min)",
    "Weekly Z2 Time DES Base Sum (min)",
    "Weekly Z2 Time DES Build Sum (min)",
    "Count Flag Long Ride >=150min (count)",
    "Count Flag Long Ride >=180min (count)",
    "Count Flag Long Ride >=240min (count)",
    "Count Flag IF <= 0.75 (count)",
    "Count Flag IF <= 0.80 (count)",
    "Count Flag Z2 Share >= 60% (count)",
    "Count Flag Z2 Share >= 70% (count)",
    "Count Flag Drift Valid (Z2 >= 90min) (count)",
    "Count Flag DES Long Base Candidate (count)",
    "Count Flag DES Long Build Candidate (count)",
    "Count Flag Brevet Long Candidate (count)",
    "Any Flag Long Ride >=150min (bool)",
    "Any Flag Long Ride >=180min (bool)",
    "Any Flag Long Ride >=240min (bool)",
    "Any Flag IF <= 0.75 (bool)",
    "Any Flag IF <= 0.80 (bool)",
    "Any Flag Z2 Share >= 60% (bool)",
    "Any Flag Z2 Share >= 70% (bool)",
    "Any Flag Drift Valid (Z2 >= 90min) (bool)",
    "Any Flag DES Long Base Candidate (bool)",
    "Any Flag DES Long Build Candidate (bool)",
    "Any Flag Brevet Long Candidate (bool)",
]


# HTTP session with retries and a fixed timeout
session = requests.Session()
session.mount(
    "https://",
    HTTPAdapter(
        max_retries=Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504],
        )
    ),
)
DEFAULT_TIMEOUT = 15


# === Formatting and rounding policy ===
ZONE_IDS = range(1, 8)
MMP_SECONDS = [
    5,
    10,
    20,
    30,
    60,
    120,
    180,
    300,
    600,
    1200,
    1800,
    3600,
    5400,
    7200,
    9000,
    10800,
    14400,
    18000,
    21600,
]
COL_ACTIVITY_ID = ("Activity ID", "ID")
COL_START_TIME = ("Start Time (Local)", "Start Date", "Date")

INT_SUFFIXES = ("(W)", "(bpm)", "(rpm)", "(J)", "(kJ)")
INT_COLUMNS = [
    "Load (TSS)",
    "Strain Score",
    "Power Load",
    "HR Load (HRSS)",
    "Calories (kcal)",
    "CTL (Fitness)",
    "ATL (Fatigue)",
    "Power/HR Z2 Time (min)",
]
ONE_DECIMAL_COLUMNS = [
    "Distance (km)",
    "Avg Speed (m/s)",
    "Max Speed (m/s)",
    "Avg Speed (km/h)",
    "Max Speed (km/h)",
    "Elev Gain (m)",
    "Elev Loss (m)",
    "Avg Altitude (m)",
    "Min Altitude (m)",
    "Max Altitude (m)",
    "Avg Temp (C)",
    "Min Temp (C)",
    "Max Temp (C)",
    "Pa:Hr (HR drift)",
    "Decoupling (%)",
]
TWO_DECIMAL_COLUMNS = [
    "Power/HR (ratio)",
    "Efficiency Factor (EF)",
    "Intensity Factor (IF)",
    "Variability Index (VI)",
    "Power/HR Z2 (ratio)",
    "Polarization Index",
    "W' Drop (%)",
    "Durability Index (DI)",
    "Functional Intensity Ratio (FIR)",
    "VO2/FTP (MMP 300s (W) / FTP Estimated (W))",
]
PERCENT_INT_COLUMNS = ["Compliance (%)", "Sweet Spot Min (%FTP)", "Sweet Spot Max (%FTP)"]
FLAG_COLUMN_KEYS = {
    "Flag Long Ride >=150min (bool)": "long_ride_150min",
    "Flag Long Ride >=180min (bool)": "long_ride_180min",
    "Flag Long Ride >=240min (bool)": "long_ride_240min",
    "Flag IF <= 0.75 (bool)": "if_at_or_below_0_75",
    "Flag IF <= 0.80 (bool)": "if_at_or_below_0_80",
    "Flag Z2 Share >= 60% (bool)": "z2_share_at_or_above_60",
    "Flag Z2 Share >= 70% (bool)": "z2_share_at_or_above_70",
    "Flag Drift Valid (Z2 >= 90min) (bool)": "drift_valid_z2_90min",
    "Flag DES Long Base Candidate (bool)": "des_long_base_candidate",
    "Flag DES Long Build Candidate (bool)": "des_long_build_candidate",
    "Flag Brevet Long Candidate (bool)": "brevet_long_candidate",
}

# === Zone model defaults ===
DEFAULT_POWER_ZONE_BOUNDS_PCT = [55, 75, 90, 105, 120, 150, 200]
DEFAULT_SWEET_SPOT_RANGE_PCT = (84, 97)
ZONE_MODEL_DEFAULTS = {
    "Z1": {
        "name": "Active Recovery",
        "typical_if": 0.45,
        "training_intent": "Recovery / circulation",
    },
    "Z2": {
        "name": "Endurance",
        "typical_if": 0.68,
        "training_intent": "Aerobic base / fat oxidation",
    },
    "Z3": {
        "name": "Tempo",
        "typical_if": 0.83,
        "training_intent": "Sustained tempo work",
    },
    "SS": {
        "name": "Sweet Spot",
        "typical_if": 0.92,
        "training_intent": "Efficient threshold work",
    },
    "Z4": {
        "name": "Threshold",
        "typical_if": 0.98,
        "training_intent": "Threshold durability",
    },
    "Z5": {
        "name": "VO2 Max",
        "typical_if": 1.1,
        "training_intent": "VO2 capacity",
    },
    "Z6": {
        "name": "Anaerobic",
        "typical_if": 1.3,
        "training_intent": "W-prime system / peaks",
    },
    "Z7": {
        "name": "Neuromuscular",
        "typical_if": None,
        "training_intent": "Sprints / neuromuscular peaks",
    },
}


def seconds_to_hms(seconds: float | int | None) -> str:
    """Format seconds as HH:MM:SS, returning empty for missing values."""
    if pd.isna(seconds):
        return ""
    total_seconds = int(round(seconds))
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def round_numeric(df: pd.DataFrame, col: str, decimals: int, as_int: bool = False) -> None:
    """Round a DataFrame column in-place with optional integer casting."""
    if col not in df.columns:
        return
    series = pd.to_numeric(df[col], errors="coerce")
    if not series.notna().any():
        return
    if as_int or decimals == 0:
        df[col] = series.round(0).astype("Int64")
    else:
        df[col] = series.round(decimals)


def apply_rounding_policy(df: pd.DataFrame) -> None:
    """Apply consistent rounding rules across export/actual/trend preparation steps."""
    for col in df.columns:
        if col.endswith(INT_SUFFIXES):
            round_numeric(df, col, 0, as_int=True)
    for col in INT_COLUMNS:
        round_numeric(df, col, 0, as_int=True)
    for col in ONE_DECIMAL_COLUMNS:
        round_numeric(df, col, 1)
    for col in TWO_DECIMAL_COLUMNS:
        round_numeric(df, col, 2)
    for col in PERCENT_INT_COLUMNS:
        round_numeric(df, col, 0, as_int=True)
    round_numeric(df, "Session RPE (0-10)", 1)


def build_export_rename_map() -> dict[str, str]:
    """Return the canonical export column mapping for activity rows."""
    mapping = {
        "id": "Activity ID",
        "name": "Name",
        "type": "Type",
        "start_date_local": "Start Time (Local)",
        "moving_time": "Moving Time (s)",
        "elapsed_time": "Elapsed Time (s)",
        "icu_recording_time": "Recording Time (s)",
        "coasting_time": "Coasting Time (s)",
        "distance": "Distance (m)",
        "average_watts": "Avg Power (W)",
        "weighted_avg_watts": "NP (W)",
        "training_load": "Load (TSS)",
        "strain_score": "Strain Score",
        "average_heartrate": "Avg HR (bpm)",
        "max_heartrate": "Max HR (bpm)",
        "average_cadence": "Avg Cadence (rpm)",
        "p_max": "Peak Power (W)",
        "icu_joules": "Work (J)",
        "icu_power_hr": "Power/HR (ratio)",
        "icu_efficiency_factor": "Efficiency Factor (EF)",
        "icu_intensity": "Intensity Factor (IF)",
        "icu_variability_index": "Variability Index (VI)",
        "decoupling": "Decoupling (%)",
        "icu_power_hr_z2": "Power/HR Z2 (ratio)",
        "icu_power_hr_z2_mins": "Power/HR Z2 Time (min)",
        "ss": "Sweet Spot TiZ (s)",
        "icu_sweet_spot_min": "Sweet Spot Min (%FTP)",
        "icu_sweet_spot_max": "Sweet Spot Max (%FTP)",
        "icu_w_prime": "W' Capacity (J)",
        "icu_max_wbal_depletion": "W' Drop (J)",
        "icu_joules_above_ftp": "Work > FTP (J)",
        "total_elevation_gain": "Elev Gain (m)",
        "total_elevation_loss": "Elev Loss (m)",
        "average_altitude": "Avg Altitude (m)",
        "min_altitude": "Min Altitude (m)",
        "max_altitude": "Max Altitude (m)",
        "trainer": "Indoor Trainer (bool)",
        "device_watts": "Device Watts (bool)",
        "source": "Source",
        "device_name": "Device Name",
        "route_id": "Route ID",
        "tags": "Tags",
        "interval_summary": "Intervals Summary",
        "compliance": "Compliance (%)",
        "carbs_used": "Carbs Used (g)",
        "carbs_ingested": "Carbs Ingested (g)",
        "icu_cadence_z2": "Cadence Z2 (rpm)",
        "polarization_index": "Polarization Index",
        "power_load": "Power Load",
        "hr_load": "HR Load (HRSS)",
        "hr_load_type": "HR Load Type",
        "icu_ftp": "FTP (W)",
        "lthr": "LTHR (bpm)",
        "athlete_max_hr": "Max HR Athlete (bpm)",
        "icu_ctl": "CTL (Fitness)",
        "icu_atl": "ATL (Fatigue)",
        "average_speed": "Avg Speed (m/s)",
        "max_speed": "Max Speed (m/s)",
        "calories": "Calories (kcal)",
        "average_temp": "Avg Temp (C)",
        "min_temp": "Min Temp (C)",
        "max_temp": "Max Temp (C)",
        "session_rpe": "Session RPE (0-10)",
        "feel": "Feel",
        "icu_warmup_time": "Warmup Time (s)",
        "icu_cooldown_time": "Cooldown Time (s)",
    }
    for i in ZONE_IDS:
        mapping[f"z{i}"] = f"Power TiZ Z{i} (s)"
        mapping[f"hr_z{i}"] = f"HR TiZ Z{i} (s)"
    for secs in MMP_SECONDS:
        mapping[f"mmp_{secs}s"] = f"MMP {secs}s (W)"
    return mapping


def replace_column(df: pd.DataFrame, old: str, new: str, series: pd.Series) -> None:
    """Replace a column in place, preserving values under a new name."""
    df[new] = series
    if old != new:
        df.drop(columns=[old], inplace=True)


def apply_unit_conversions(df: pd.DataFrame) -> None:
    """Convert common units and update column names accordingly."""
    for col in [c for c in df.columns if c.endswith(" (s)")]:
        new_col = col.replace(" (s)", " (hh:mm:ss)")
        vals = pd.to_numeric(df[col], errors="coerce")
        replace_column(df, col, new_col, vals.map(seconds_to_hms))

    if "Distance (m)" in df.columns:
        vals = pd.to_numeric(df["Distance (m)"], errors="coerce") / 1000.0
        replace_column(df, "Distance (m)", "Distance (km)", vals.round(1))

    for col in [c for c in df.columns if c.endswith(" (J)")]:
        vals = pd.to_numeric(df[col], errors="coerce") / 1000.0
        replace_column(df, col, col.replace(" (J)", " (kJ)"), vals.round(0))

    for col in ["Avg Speed (m/s)", "Max Speed (m/s)"]:
        if col in df.columns:
            vals = pd.to_numeric(df[col], errors="coerce") * 3.6
            replace_column(df, col, col.replace("(m/s)", "(km/h)"), vals.round(1))


def getcol(columns: dict[str, str], *candidates: str) -> str | None:
    """Return the first matching column name for candidate headers."""
    for name in candidates:
        key = name.lower()
        if key in columns:
            return columns[key]
    return None


def standardize_activity_columns(df: pd.DataFrame) -> str:
    """Normalize the activity ID and timestamp columns for downstream steps."""
    cols = {c.lower(): c for c in df.columns}
    dt_col = getcol(cols, *COL_START_TIME)
    if dt_col is None:
        raise ValueError("No date column found (e.g. 'Start Time (Local)').")

    df[dt_col] = pd.to_datetime(df[dt_col], errors="coerce")
    df.dropna(subset=[dt_col], inplace=True)

    activity_id_col = getcol(cols, *COL_ACTIVITY_ID)
    if activity_id_col and activity_id_col != "Activity ID":
        replace_column(df, activity_id_col, "Activity ID", df[activity_id_col])

    if dt_col != "Start Time (Local)":
        replace_column(df, dt_col, "Start Time (Local)", df[dt_col])
        dt_col = "Start Time (Local)"

    return dt_col


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the end-to-end pipeline."""
    parser = argparse.ArgumentParser(
        description=(
            "Fetch Intervals.icu activity data, then compile activities_actual (latest week) "
            "and activities_trend in a single run."
        )
    )
    parser.add_argument("--year", type=int, help="ISO year for the week, e.g. 2025")
    parser.add_argument("--week", type=int, help="ISO calendar week, e.g. 43")
    parser.add_argument("--from", dest="from_date", type=str, help="Start date YYYY-MM-DD")
    parser.add_argument("--to", dest="to_date", type=str, help="End date YYYY-MM-DD")
    parser.add_argument("--athlete", help="Athlete ID (defaults to ATHLETE_ID from .env).")
    parser.add_argument(
        "--skip-validate",
        action="store_true",
        help="Skip JSON schema validation in compile steps",
    )
    return parser.parse_args()


def parse_ymd(value: str) -> date:
    """Parse a YYYY-MM-DD date string."""
    return datetime.strptime(value, "%Y-%m-%d").date()


def iso_week_to_dates(iso_year: int, iso_week: int) -> tuple[date, date]:
    """Convert an ISO week to its date range (Monday through Sunday)."""
    first_day = datetime.fromisocalendar(iso_year, iso_week, 1)
    last_day = first_day + timedelta(days=6)
    return first_day.date(), last_day.date()


def date_to_iso_week(target_date: date | datetime) -> tuple[int, int]:
    """Return the ISO year/week for a given date or datetime."""
    iso_year, iso_week, _ = target_date.isocalendar()
    return int(iso_year), int(iso_week)


def last_iso_week(iso_year: int) -> int:
    """Return the last ISO week number for the given ISO year."""
    return date(iso_year, 12, 28).isocalendar()[1]


def last_complete_week_end(today: date) -> date:
    """Return the last completed ISO week end (Sunday) before the given date."""
    if today.isoweekday() == 7:
        return today
    return today - timedelta(days=today.isoweekday())


def resolve_default_range(weeks: int = DEFAULT_WEEKS) -> tuple[date, date]:
    """Return the default date range covering the last N complete ISO weeks."""
    end_date = last_complete_week_end(datetime.now().date())
    end_monday = end_date - timedelta(days=6)
    start_monday = end_monday - timedelta(weeks=weeks - 1)
    return start_monday, end_date


# === Intervals.icu API helpers ===

def _get(url: str) -> requests.Response:
    """Perform a GET request with retry/timeout settings."""
    resp = session.get(url, timeout=DEFAULT_TIMEOUT)
    resp.raise_for_status()
    return resp


def get_activities(athlete_id: str, base_url: str, start_date: date, end_date: date) -> list[dict]:
    """Fetch activities for a date range."""
    url = f"{base_url}/athlete/{athlete_id}/activities?oldest={start_date}&newest={end_date}"
    return _get(url).json()


def get_activity_detail(base_url: str, activity_id: str | int) -> dict:
    """Fetch detailed activity data by activity id."""
    url = f"{base_url}/activity/{activity_id}"
    return _get(url).json()


def get_power_curves_csv(athlete_id: str, base_url: str, start_date: date, end_date: date) -> str:
    """Fetch the power curves CSV for a date range."""
    url = (
        f"{base_url}/athlete/{athlete_id}/activity-power-curves.csv"
        f"?oldest={start_date}&newest={end_date}"
    )
    return _get(url).text


# === Athlete + zone model helpers ===

def get_athlete(athlete_id: str, base_url: str) -> dict:
    """Fetch athlete profile including sport settings when available."""
    url = f"{base_url}/athlete/{athlete_id}"
    return _get(url).json()


def get_wellness(athlete_id: str, base_url: str, start_date: date, end_date: date) -> list[dict]:
    """Fetch wellness entries for a date range."""
    url = f"{base_url}/athlete/{athlete_id}/wellness?oldest={start_date}&newest={end_date}"
    return _get(url).json()


def _as_percent(value: float | int | None) -> float | None:
    if value is None:
        return None
    if value <= 1.5:
        return float(value) * 100.0
    return float(value)


def _round_pct(value: float) -> float | int:
    if abs(value - round(value)) < 1e-6:
        return int(round(value))
    return round(value, 1)


def _extract_weight_kg(athlete_data: dict) -> float | None:
    for key in ("weight", "icu_weight", "weight_kg", "body_weight", "bodyWeight", "weightKg"):
        val = athlete_data.get(key)
        if isinstance(val, (int, float)) and val > 0:
            return float(val)
    return None


def _extract_latest_weight_from_wellness(entries: list[dict]) -> float | None:
    latest_weight = None
    latest_date = None
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        weight = entry.get("weight")
        day = entry.get("id") or entry.get("date")
        if isinstance(weight, (int, float)) and weight > 0 and isinstance(day, str):
            if latest_date is None or day > latest_date:
                latest_date = day
                latest_weight = float(weight)
    return latest_weight


def _parse_date(value: str | None) -> date | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _num_or_none(value):
    value = normalize_scalar(value)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_sport_settings(raw: object) -> list[dict]:
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict):
        if "type" in raw:
            return [raw]
        settings = []
        for key, val in raw.items():
            if isinstance(val, dict):
                setting = dict(val)
                setting.setdefault("type", key)
                settings.append(setting)
        return settings
    return []


def _select_sport_setting(settings: list[dict], sport_types: Sequence[str]) -> dict | None:
    for sport_type in sport_types:
        for setting in settings:
            if setting.get("type") == sport_type:
                return setting
    return settings[0] if settings else None


def _extract_ftp_watts(setting: dict) -> float | None:
    for key in ("ftp", "ftp_watts", "ftpWatts", "threshold", "threshold_watts", "power_ftp"):
        val = setting.get(key)
        if isinstance(val, (int, float)) and val > 0:
            return float(val)
    return None


def _extract_sweet_spot_range(setting: dict) -> tuple[float, float] | None:
    for min_key, max_key in (
        ("sweet_spot_min", "sweet_spot_max"),
        ("sweetSpotMin", "sweetSpotMax"),
        ("sweet_spot_min_pct", "sweet_spot_max_pct"),
    ):
        min_val = _as_percent(setting.get(min_key))
        max_val = _as_percent(setting.get(max_key))
        if min_val and max_val and max_val > min_val:
            return (min_val, max_val)
    return None


def _extract_power_zone_bounds(setting: dict) -> list[float] | None:
    raw = None
    for key in ("power_zones", "powerZones", "power_zone_limits", "powerZoneLimits"):
        if key in setting:
            raw = setting.get(key)
            break
    if not raw:
        return None
    if isinstance(raw, list) and raw and isinstance(raw[0], dict):
        bounds = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            max_val = None
            for max_key in ("max", "high", "upper"):
                if max_key in entry:
                    max_val = _as_percent(entry.get(max_key))
                    break
            if max_val is not None:
                bounds.append(max_val)
        return bounds or None
    if isinstance(raw, list):
        bounds = [_as_percent(val) for val in raw if isinstance(val, (int, float))]
        return bounds or None
    return None


def _build_zone_ranges(bounds: list[float]) -> dict[str, tuple[float, float]]:
    if len(bounds) < 7:
        bounds = DEFAULT_POWER_ZONE_BOUNDS_PCT
    bounds = [float(b) for b in bounds[:7]]
    ranges: dict[str, tuple[float, float]] = {}
    prev = 0.0
    for zone_id, max_pct in zip(["Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7"], bounds):
        ranges[zone_id] = (prev, max_pct)
        prev = max_pct
    return ranges


def build_zone_model_payload(
    *,
    athlete_id: str,
    athlete_data: dict,
    run_ts: datetime,
    source_label: str,
) -> dict | None:
    settings = _normalize_sport_settings(athlete_data.get("sportSettings"))
    setting = _select_sport_setting(settings, ["Ride", "VirtualRide", "Gravel"])
    if not setting:
        return None

    ftp_watts = _extract_ftp_watts(setting)
    if not ftp_watts:
        return None

    bounds = _extract_power_zone_bounds(setting)
    zone_ranges = _build_zone_ranges(bounds or [])
    sweet_spot = _extract_sweet_spot_range(setting) or DEFAULT_SWEET_SPOT_RANGE_PCT

    valid_from = run_ts.date().isoformat()
    iso_year, iso_week = date_to_iso_week(run_ts)
    version_key = f"{iso_year}-{iso_week:02d}"
    last_week = last_iso_week(iso_year)
    iso_week_range = f"{version_key}--{iso_year}-{last_week:02d}"
    filename = f"zone_model_power_{int(round(ftp_watts))}W_{valid_from}"

    zones = []
    for zone_id in ["Z1", "Z2", "Z3", "SS", "Z4", "Z5", "Z6", "Z7"]:
        if zone_id == "SS":
            min_pct, max_pct = sweet_spot
        else:
            min_pct, max_pct = zone_ranges[zone_id]
        zone_def = ZONE_MODEL_DEFAULTS[zone_id]
        zones.append(
            {
                "zone_id": zone_id,
                "name": zone_def["name"],
                "ftp_percent_range": {
                    "min": _round_pct(min_pct),
                    "max": _round_pct(max_pct),
                },
                "watt_range": {
                    "min": int(round(ftp_watts * (min_pct / 100.0))),
                    "max": int(round(ftp_watts * (max_pct / 100.0))),
                },
                "typical_if": zone_def["typical_if"],
                "training_intent": zone_def["training_intent"],
            }
        )

    payload = {
        "meta": {
            "artifact_type": "ZONE_MODEL",
            "schema_id": "ZoneModelInterface",
            "schema_version": "1.0",
            "version": "1.0",
            "authority": "Binding",
            "owner_agent": "Data-Pipeline",
            "run_id": f"{run_ts.strftime('%Y%m%d-%H%M%S')}-data-pipeline-zone-model",
            "created_at": run_ts.isoformat(),
            "scope": "Shared",
            "iso_week": version_key,
            "iso_week_range": iso_week_range,
            "temporal_scope": {
                "from": valid_from,
                "to": f"{iso_year}-12-31",
            },
            "trace_upstream": [
                {
                    "artifact": "intervals_icu_athlete",
                    "version": "1.0",
                    "run_id": source_label,
                }
            ],
            "trace_data": [],
            "trace_events": [],
            "notes": "Generated from Intervals.icu athlete sportSettings (Ride).",
        },
        "data": {
            "model_metadata": {
                "valid_from": valid_from,
                "ftp_watts": int(round(ftp_watts)),
                "purpose": "Power zone model derived from Intervals.icu sport settings.",
                "filename": filename,
            },
            "zones": zones,
            "examples": [],
            "versioning_usage": [
                "Use this zone model for IF/TSS calculations and workout encoding.",
                "Update when FTP changes materially or sportSettings are recalibrated.",
            ],
        },
    }
    return payload


def write_zone_model(
    *,
    athlete_id: str,
    base_url: str,
    latest_dir: Path,
    skip_validate: bool,
) -> None:
    run_ts = datetime.now(timezone.utc)
    athlete = get_athlete(athlete_id, base_url)
    weight_kg = _extract_weight_kg(athlete)
    if not weight_kg:
        try:
            end_date = run_ts.date()
            start_date = end_date - timedelta(days=14)
            wellness_entries = get_wellness(athlete_id, base_url, start_date, end_date)
            weight_kg = _extract_latest_weight_from_wellness(wellness_entries)
        except requests.RequestException:
            weight_kg = None
    if weight_kg:
        print(f"Intervals athlete weight: {weight_kg:.1f} kg")

    payload = build_zone_model_payload(
        athlete_id=athlete_id,
        athlete_data=athlete,
        run_ts=run_ts,
        source_label=str(athlete_id),
    )
    if not payload:
        print("Zone model skipped (missing sport settings or FTP).")
        return

    schema_dir = resolve_schema_dir()
    validator = SchemaRegistry(schema_dir).validator_for("zone_model.schema.json")
    if not skip_validate:
        validate_or_raise(validator, payload)

    ftp_watts = payload["data"]["model_metadata"]["ftp_watts"]
    latest_dir.mkdir(parents=True, exist_ok=True)
    out_file = latest_dir / f"zone_model_power_{ftp_watts}W.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    latest_alias = latest_dir / "zone_model.json"
    latest_alias.write_bytes(out_file.read_bytes())

    record_index_write(
        athlete_id=athlete_id,
        artifact_type="ZONE_MODEL",
        version_key=payload["meta"]["iso_week"],
        path=out_file,
        run_id=payload["meta"]["run_id"],
        producer_agent=payload["meta"]["owner_agent"],
        created_at=payload["meta"]["created_at"],
        iso_week=payload["meta"]["iso_week"],
    )

    print(f"Zone model written: {out_file}")


def write_wellness(
    *,
    athlete_id: str,
    base_url: str,
    from_date: date,
    to_date: date,
    skip_validate: bool,
) -> None:
    run_ts = datetime.now(timezone.utc)
    athlete_data = get_athlete(athlete_id, base_url)
    body_mass_kg = _extract_weight_kg(athlete_data)
    entries = get_wellness(athlete_id, base_url, from_date, to_date)
    if not entries:
        print("Wellness skipped (no entries).")
        return

    normalized = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entry_date = entry.get("id") or entry.get("date")
        parsed_date = _parse_date(entry_date)
        if not parsed_date:
            continue
        normalized.append(
            {
                "date": parsed_date.isoformat(),
                "weight_kg": _num_or_none(entry.get("weight")),
                "resting_hr_bpm": _num_or_none(entry.get("restingHR")),
                "hrv_ms": _num_or_none(entry.get("hrv")),
                "sleep_seconds": _num_or_none(entry.get("sleepSecs")),
                "sleep_quality": _num_or_none(entry.get("sleepQuality")),
                "soreness": _num_or_none(entry.get("soreness")),
                "fatigue": _num_or_none(entry.get("fatigue")),
                "stress": _num_or_none(entry.get("stress")),
                "mood": _num_or_none(entry.get("mood")),
                "motivation": _num_or_none(entry.get("motivation")),
                "spo2_percent": _num_or_none(entry.get("spO2")),
                "systolic_mm_hg": _num_or_none(entry.get("systolic")),
                "diastolic_mm_hg": _num_or_none(entry.get("diastolic")),
                "kcal_consumed": _num_or_none(entry.get("kcalConsumed")),
                "menstrual_phase": normalize_scalar(entry.get("menstrualPhase")),
                "updated_at": normalize_scalar(entry.get("updated")),
                "source": "intervals_icu_wellness",
            }
        )

    if not normalized:
        print("Wellness skipped (no dated entries).")
        return

    if body_mass_kg is None:
        body_mass_kg = _extract_latest_weight_from_wellness(entries)

    normalized.sort(key=lambda item: item["date"])
    start_day = _parse_date(normalized[0]["date"])
    end_day = _parse_date(normalized[-1]["date"])
    if not start_day or not end_day:
        print("Wellness skipped (invalid date range).")
        return

    start_week = f"{date_to_iso_week(start_day)[0]}-{date_to_iso_week(start_day)[1]:02d}"
    end_week = f"{date_to_iso_week(end_day)[0]}-{date_to_iso_week(end_day)[1]:02d}"
    version_key = end_week

    meta = {
        "artifact_type": "WELLNESS",
        "schema_id": "WellnessInterface",
        "schema_version": "1.0",
        "version": "1.0",
        "authority": "Binding",
        "owner_agent": "Data-Pipeline",
        "run_id": f"{run_ts.strftime('%Y%m%d-%H%M%S')}-data-pipeline-wellness",
        "created_at": run_ts.isoformat(),
        "scope": "Shared",
        "iso_week": version_key,
        "iso_week_range": f"{start_week}--{end_week}",
        "temporal_scope": {
            "from": start_day.isoformat(),
            "to": end_day.isoformat(),
        },
        "trace_upstream": [
            {
                "artifact": "intervals_icu_wellness",
                "version": "1.0",
                "run_id": str(athlete_id),
            }
        ],
        "trace_data": [],
        "trace_events": [],
        "notes": "Derived from Intervals.icu wellness export.",
    }
    payload = {
        "meta": meta,
        "data": {
            "entries": normalized,
            "body_mass_kg": body_mass_kg,
            "notes": "Intervals.icu wellness daily entries.",
        },
    }

    schema_dir = resolve_schema_dir()
    validator = SchemaRegistry(schema_dir).validator_for("wellness.schema.json")
    if not skip_validate:
        validate_or_raise(validator, payload)

    data_dir = athlete_data_dir(athlete_id)
    latest_dir = athlete_latest_dir(athlete_id)
    out_dir = data_dir / end_week.split("-")[0] / end_week.split("-")[1]
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"wellness_{end_week}.json"

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    latest_dir.mkdir(parents=True, exist_ok=True)
    latest_file = latest_dir / "wellness.json"
    latest_file.write_bytes(out_file.read_bytes())

    record_index_write(
        athlete_id=athlete_id,
        artifact_type="WELLNESS",
        version_key=version_key,
        path=out_file,
        run_id=meta["run_id"],
        producer_agent=meta["owner_agent"],
        created_at=meta["created_at"],
        iso_week=meta["iso_week"],
        iso_week_range=meta["iso_week_range"],
    )

    print(f"Wellness written: {out_file}")
# === Export helpers ===

def to_num(s: pd.Series) -> pd.Series:
    """Convert a Series to numeric, coercing empty strings to NaN."""
    return pd.to_numeric(
        s.astype(str).str.strip().replace({"": np.nan}),
        errors="coerce",
    )


def div_or_none(value: float | int | None, denom: float | int) -> float | None:
    """Divide only when the numerator exists, otherwise return None."""
    if value is None:
        return None
    return value / denom


def export_range(
    *,
    athlete_id: str,
    base_url: str,
    from_date: date,
    to_date: date,
) -> Path:
    """Export activities for a date range and write CSV outputs."""
    print(f"Range: {from_date} to {to_date}")

    activities = get_activities(athlete_id, base_url, from_date, to_date)
    activities = [a for a in activities if a.get("type") in {"Ride", "VirtualRide"}]

    curve_csv = get_power_curves_csv(athlete_id, base_url, from_date, to_date)
    curve_df = pd.read_csv(StringIO(curve_csv))
    if not curve_df.empty:
        curve_df.rename(columns={"activity": "id"}, inplace=True)
        curve_df["id"] = curve_df["id"].astype(str)
        curve_df.set_index("id", inplace=True)
    else:
        curve_df = pd.DataFrame()

    rows = []
    for act in activities:
        aid = act.get("id")
        detail = get_activity_detail(base_url, aid)

        power_zone_secs = {z["id"]: z["secs"] for z in (detail.get("icu_zone_times") or [])}
        hr_zones = (detail.get("icu_hr_zone_times") or []) + [0] * 7
        hr_zones = hr_zones[:7]

        tags = detail.get("tags") or []
        interval_summary = detail.get("interval_summary") or []

        row = {
            "id": aid,
            "name": act.get("name"),
            "type": act.get("type"),
            "start_date_local": act.get("start_date_local"),
            "moving_time": act.get("moving_time"),
            "elapsed_time": detail.get("elapsed_time"),
            "icu_recording_time": detail.get("icu_recording_time"),
            "coasting_time": detail.get("coasting_time"),
            "distance": act.get("distance"),
            "average_watts": detail.get("icu_average_watts"),
            "weighted_avg_watts": detail.get("icu_weighted_avg_watts"),
            "training_load": detail.get("icu_training_load"),
            "strain_score": detail.get("strain_score"),
            "average_heartrate": detail.get("average_heartrate"),
            "max_heartrate": detail.get("max_heartrate"),
            "average_cadence": detail.get("average_cadence"),
            "p_max": detail.get("p_max"),
            "icu_joules": detail.get("icu_joules"),
            "icu_power_hr": detail.get("icu_power_hr"),
            "icu_efficiency_factor": detail.get("icu_efficiency_factor"),
            "icu_intensity": div_or_none(detail.get("icu_intensity"), 100.0),
            "icu_variability_index": detail.get("icu_variability_index"),
            "decoupling": detail.get("decoupling"),
            "icu_power_hr_z2": detail.get("icu_power_hr_z2"),
            "icu_power_hr_z2_mins": detail.get("icu_power_hr_z2_mins"),
            "z1": power_zone_secs.get("Z1", 0),
            "z2": power_zone_secs.get("Z2", 0),
            "z3": power_zone_secs.get("Z3", 0),
            "z4": power_zone_secs.get("Z4", 0),
            "z5": power_zone_secs.get("Z5", 0),
            "z6": power_zone_secs.get("Z6", 0),
            "z7": power_zone_secs.get("Z7", 0),
            "ss": power_zone_secs.get("SS", 0),
            "icu_sweet_spot_min": detail.get("icu_sweet_spot_min"),
            "icu_sweet_spot_max": detail.get("icu_sweet_spot_max"),
            "hr_z1": hr_zones[0],
            "hr_z2": hr_zones[1],
            "hr_z3": hr_zones[2],
            "hr_z4": hr_zones[3],
            "hr_z5": hr_zones[4],
            "hr_z6": hr_zones[5],
            "hr_z7": hr_zones[6],
            "icu_w_prime": detail.get("icu_w_prime"),
            "icu_max_wbal_depletion": detail.get("icu_max_wbal_depletion"),
            "icu_joules_above_ftp": detail.get("icu_joules_above_ftp"),
            "total_elevation_gain": detail.get("total_elevation_gain"),
            "total_elevation_loss": detail.get("total_elevation_loss"),
            "average_altitude": detail.get("average_altitude"),
            "min_altitude": detail.get("min_altitude"),
            "max_altitude": detail.get("max_altitude"),
            "trainer": detail.get("trainer", act.get("trainer")),
            "device_watts": detail.get("device_watts", act.get("device_watts")),
            "source": detail.get("source"),
            "device_name": detail.get("device_name"),
            "route_id": detail.get("route_id"),
            "tags": ",".join(tags) if isinstance(tags, list) else tags,
            "interval_summary": "; ".join(interval_summary) if isinstance(interval_summary, list) else interval_summary,
            "compliance": detail.get("compliance"),
            "carbs_used": detail.get("carbs_used"),
            "carbs_ingested": detail.get("carbs_ingested"),
            "icu_cadence_z2": detail.get("icu_cadence_z2"),
            "polarization_index": detail.get("polarization_index"),
            "power_load": detail.get("power_load"),
            "hr_load": detail.get("hr_load"),
            "hr_load_type": detail.get("hr_load_type"),
            "icu_ftp": detail.get("icu_ftp"),
            "lthr": detail.get("lthr"),
            "athlete_max_hr": detail.get("athlete_max_hr"),
            "icu_ctl": detail.get("icu_ctl"),
            "icu_atl": detail.get("icu_atl"),
            "average_speed": detail.get("average_speed"),
            "max_speed": detail.get("max_speed"),
            "calories": detail.get("calories"),
            "average_temp": detail.get("average_temp"),
            "min_temp": detail.get("min_temp"),
            "max_temp": detail.get("max_temp"),
            "session_rpe": detail.get("session_rpe"),
            "feel": detail.get("feel"),
            "icu_warmup_time": detail.get("icu_warmup_time"),
            "icu_cooldown_time": detail.get("icu_cooldown_time"),
        }

        aid_str = str(aid)
        if not curve_df.empty and aid_str in curve_df.index:
            for secs in [
                5,
                10,
                20,
                30,
                60,
                120,
                180,
                300,
                600,
                1200,
                1800,
                3600,
                5400,
                7200,
                9000,
                10800,
                14400,
                18000,
                21600,
            ]:
                col = str(secs)
                row[f"mmp_{secs}s"] = curve_df.at[aid_str, col] if col in curve_df.columns else None

        rows.append(row)

    df = pd.DataFrame(rows)
    df = df.where(pd.notnull(df), "")

    rename_map = build_export_rename_map()
    df.rename(columns=rename_map, inplace=True)

    df["W' Drop (%)"] = (df["W' Drop (J)"] / df["W' Capacity (J)"] * 100).round(2)
    df["TSB (today)"] = (df["CTL (Fitness)"] - df["ATL (Fatigue)"]).round(2)
    df["VO2Max Power TiZ (s)"] = df["Power TiZ Z5 (s)"]
    df["VO2Max HR TiZ (s)"] = (
        df["HR TiZ Z4 (s)"]
        + df["HR TiZ Z5 (s)"]
        + df["HR TiZ Z6 (s)"]
        + df["HR TiZ Z7 (s)"]
    )
    df["VO2Max TiZ Eff (s)"] = df[["VO2Max Power TiZ (s)", "VO2Max HR TiZ (s)"]].max(axis=1)

    pz_total = (
        df["Power TiZ Z1 (s)"]
        + df["Power TiZ Z2 (s)"]
        + df["Power TiZ Z3 (s)"]
        + df["Power TiZ Z4 (s)"]
        + df["Power TiZ Z5 (s)"]
        + df["Power TiZ Z6 (s)"]
        + df["Power TiZ Z7 (s)"]
    )
    df["Power TiZ Share Z2 (%)"] = (
        (df["Power TiZ Z1 (s)"] + df["Power TiZ Z2 (s)"]) / pz_total.where(pz_total != 0) * 100.0
    ).round(1)

    move_min = df["Moving Time (s)"] / 60.0
    z2_min = df["Power TiZ Z2 (s)"] / 60.0
    z2_share = df["Power TiZ Share Z2 (%)"]
    if_val = df["Intensity Factor (IF)"]

    df["Flag Long Ride >=150min (bool)"] = move_min >= 150
    df["Flag Long Ride >=180min (bool)"] = move_min >= 180
    df["Flag Long Ride >=240min (bool)"] = move_min >= 240
    df["Flag IF <= 0.75 (bool)"] = if_val <= 0.75
    df["Flag IF <= 0.80 (bool)"] = if_val <= 0.80
    df["Flag Z2 Share >= 60% (bool)"] = z2_share >= 60
    df["Flag Z2 Share >= 70% (bool)"] = z2_share >= 70
    df["Flag Drift Valid (Z2 >= 90min) (bool)"] = z2_min >= 90
    df["Flag DES Long Base Candidate (bool)"] = (
        df["Flag Long Ride >=150min (bool)"]
        & df["Flag IF <= 0.75 (bool)"]
        & df["Flag Z2 Share >= 60% (bool)"]
    )
    df["Flag DES Long Build Candidate (bool)"] = (
        df["Flag Long Ride >=150min (bool)"]
        & df["Flag IF <= 0.80 (bool)"]
        & df["Flag Z2 Share >= 60% (bool)"]
    )
    df["Flag Brevet Long Candidate (bool)"] = (
        df["Flag Long Ride >=240min (bool)"]
        & df["Flag IF <= 0.80 (bool)"]
        & df["Flag Z2 Share >= 70% (bool)"]
    )

    df["MMP 300s (W)"] = to_num(df["MMP 300s (W)"])
    df["MMP 1200s (W)"] = to_num(df["MMP 1200s (W)"])
    df["Decoupling (%)"] = to_num(df["Decoupling (%)"])
    df["Durability Index (DI)"] = (1 - (df["Decoupling (%)"].abs() / 100)).round(3)
    df["Pa:Hr (HR drift)"] = (df["Decoupling (%)"]).round(3)
    den = df["MMP 1200s (W)"]
    df["Functional Intensity Ratio (FIR)"] = (df["MMP 300s (W)"] / den.where(den != 0)).round(3)
    df["FTP Estimated (W)"] = (0.95 * df["MMP 1200s (W)"]).round(0)
    den = df["FTP Estimated (W)"]
    df["VO2/FTP (MMP 300s (W) / FTP Estimated (W))"] = (
        df["MMP 300s (W)"] / den.where(den != 0)
    ).round(3)

    apply_rounding_policy(df)

    iso_year, iso_week = date_to_iso_week(to_date)
    data_dir = athlete_data_dir(athlete_id)
    latest_dir = athlete_latest_dir(athlete_id)
    out_dir = data_dir / f"{iso_year:04d}" / f"{iso_week:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / f"intervals_data_{from_date}_{to_date}.csv"
    latest_file = latest_dir / "intervals_data_latest.csv"
    latest_dir.mkdir(parents=True, exist_ok=True)

    df.to_csv(
        out_file,
        index=False,
        sep=SEPARATOR,
        quoting=csv.QUOTE_ALL,
        quotechar=QUOTECHAR,
        doublequote=True,
        encoding="utf-8-sig",
        lineterminator="\n",
        na_rep="",
    )

    latest_file.write_bytes(out_file.read_bytes())
    print(f"CSV exported: {out_file}")
    return out_file


# === Activities Actual helpers ===

def normalize_key(label: str) -> str:
    """Normalize a column label into a snake_case key."""
    key = re.sub(r"[^a-zA-Z0-9]+", "_", label.strip()).strip("_").lower()
    return key or "col"


def unique_key(base: str, used: set[str]) -> str:
    """Return a unique key, suffixing with _N if needed."""
    if base not in used:
        return base
    idx = 2
    while f"{base}_{idx}" in used:
        idx += 1
    return f"{base}_{idx}"


def normalize_scalar(value):
    """Normalize pandas scalars into native Python values."""
    if pd.isna(value):
        return None
    if isinstance(value, str) and not value.strip():
        return None
    if isinstance(value, pd.Timestamp):
        return value
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def normalize_bool(value):
    """Normalize a scalar into a boolean when possible."""
    value = normalize_scalar(value)
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(int(value))
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False
    return None


def format_date(value):
    """Format a scalar into a YYYY-MM-DD date string."""
    value = normalize_scalar(value)
    if value is None:
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.date().isoformat()
    text = str(value)
    if "T" in text:
        return text.split("T", 1)[0]
    return text.split(" ", 1)[0]


def format_datetime(value):
    """Format a scalar into an ISO 8601 timestamp string."""
    value = normalize_scalar(value)
    if value is None:
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    return str(value)


def format_duration_hms(value):
    """Format a scalar into HH:MM:SS when possible."""
    value = normalize_scalar(value)
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return seconds_to_hms(value)
    text = str(value)
    return text if text.strip() else None


def format_number(value):
    """Normalize numeric values into floats."""
    value = normalize_scalar(value)
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def format_int(value):
    """Normalize numeric values into integers."""
    value = normalize_scalar(value)
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def format_string(value):
    """Normalize values into strings, returning None for empties."""
    value = normalize_scalar(value)
    if value is None:
        return None
    return str(value)


def ensure_keys(label: str, actual_keys: set[str], expected_keys: set[str], context: str) -> None:
    """Raise if actual keys differ from expected keys."""
    missing = expected_keys - actual_keys
    extra = actual_keys - expected_keys
    if not missing and not extra:
        return
    details = []
    if missing:
        details.append(f"missing: {sorted(missing)}")
    if extra:
        details.append(f"extra: {sorted(extra)}")
    detail_text = "; ".join(details)
    raise ValueError(f"{label} keys mismatch ({context}): {detail_text}")


def compile_activities_actual(
    *,
    athlete_id: str,
    input_csv: Path,
    skip_validate: bool,
) -> None:
    """Compile activities_actual JSON for the latest ISO week in the export."""
    df = pd.read_csv(input_csv, sep=SEPARATOR, quotechar=QUOTECHAR)
    dt_col = standardize_activity_columns(df)
    df = df.copy()

    iso = df[dt_col].dt.isocalendar()
    df["ISO Year"] = iso.year.astype(int)
    df["ISO Week"] = iso.week.astype(int)
    df["Day"] = df[dt_col].dt.floor("D")
    df["Day of Week"] = df[dt_col].dt.dayofweek.map(
        {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
    )

    apply_unit_conversions(df)

    apply_rounding_policy(df)

    required_columns = [
        "ISO Year",
        "ISO Week",
        "Day",
        "Day of Week",
        "Activity ID",
        "Start Time (Local)",
        "Type",
        "Moving Time (hh:mm:ss)",
        "Distance (km)",
        "Work (kJ)",
        "Load (TSS)",
        "NP (W)",
        "Avg Power (W)",
        "Peak Power (W)",
        "Intensity Factor (IF)",
        "Variability Index (VI)",
        "Efficiency Factor (EF)",
        "Durability Index (DI)",
        "Functional Intensity Ratio (FIR)",
        "Polarization Index",
        "VO2/FTP (MMP 300s (W) / FTP Estimated (W))",
        "W' Drop (%)",
        "Work > FTP (kJ)",
        "Decoupling (%)",
        "Avg HR (bpm)",
        "Max HR (bpm)",
        "Power TiZ Z1 (hh:mm:ss)",
        "Power TiZ Z2 (hh:mm:ss)",
        "Power TiZ Z3 (hh:mm:ss)",
        "Power TiZ Z4 (hh:mm:ss)",
        "Power TiZ Z5 (hh:mm:ss)",
        "Power TiZ Z6 (hh:mm:ss)",
        "Power TiZ Z7 (hh:mm:ss)",
        "HR TiZ Z1 (hh:mm:ss)",
        "HR TiZ Z2 (hh:mm:ss)",
        "HR TiZ Z3 (hh:mm:ss)",
        "HR TiZ Z4 (hh:mm:ss)",
        "HR TiZ Z5 (hh:mm:ss)",
        "HR TiZ Z6 (hh:mm:ss)",
        "HR TiZ Z7 (hh:mm:ss)",
        "Sweet Spot TiZ (hh:mm:ss)",
        "Power TiZ Share Z2 (%)",
        "VO2Max TiZ Eff (hh:mm:ss)",
        "VO2Max Power TiZ (hh:mm:ss)",
        "VO2Max HR TiZ (hh:mm:ss)",
        "Flag Long Ride >=150min (bool)",
        "Flag Long Ride >=180min (bool)",
        "Flag Long Ride >=240min (bool)",
        "Flag IF <= 0.75 (bool)",
        "Flag IF <= 0.80 (bool)",
        "Flag Z2 Share >= 60% (bool)",
        "Flag Z2 Share >= 70% (bool)",
        "Flag Drift Valid (Z2 >= 90min) (bool)",
        "Flag DES Long Base Candidate (bool)",
        "Flag DES Long Build Candidate (bool)",
        "Flag Brevet Long Candidate (bool)",
        "MMP 5s (W)",
        "MMP 30s (W)",
        "MMP 60s (W)",
        "MMP 120s (W)",
        "MMP 300s (W)",
        "MMP 600s (W)",
        "MMP 1200s (W)",
        "MMP 3600s (W)",
        "MMP 5400s (W)",
        "MMP 7200s (W)",
        "MMP 9000s (W)",
        "MMP 10800s (W)",
        "MMP 14400s (W)",
        "MMP 18000s (W)",
        "MMP 21600s (W)",
    ]

    for col in required_columns:
        if col not in df.columns:
            df[col] = pd.NA
    output_cols = required_columns

    required_field_map = {
        "iso_year": "ISO Year",
        "iso_week": "ISO Week",
        "day": "Day",
        "day_of_week": "Day of Week",
        "activity_id": "Activity ID",
        "start_time_local": "Start Time (Local)",
        "type": "Type",
        "moving_time": "Moving Time (hh:mm:ss)",
        "distance_km": "Distance (km)",
        "work_kj": "Work (kJ)",
        "load_tss": "Load (TSS)",
        "normalized_power_w": "NP (W)",
        "intensity_factor": "Intensity Factor (IF)",
        "avg_hr_bpm": "Avg HR (bpm)",
        "max_hr_bpm": "Max HR (bpm)",
        "power_tiz_z1": "Power TiZ Z1 (hh:mm:ss)",
        "power_tiz_z2": "Power TiZ Z2 (hh:mm:ss)",
        "power_tiz_z3": "Power TiZ Z3 (hh:mm:ss)",
        "power_tiz_z4": "Power TiZ Z4 (hh:mm:ss)",
        "power_tiz_z5": "Power TiZ Z5 (hh:mm:ss)",
        "power_tiz_z6": "Power TiZ Z6 (hh:mm:ss)",
        "power_tiz_z7": "Power TiZ Z7 (hh:mm:ss)",
        "hr_tiz_z1": "HR TiZ Z1 (hh:mm:ss)",
        "hr_tiz_z2": "HR TiZ Z2 (hh:mm:ss)",
        "hr_tiz_z3": "HR TiZ Z3 (hh:mm:ss)",
        "hr_tiz_z4": "HR TiZ Z4 (hh:mm:ss)",
        "hr_tiz_z5": "HR TiZ Z5 (hh:mm:ss)",
        "hr_tiz_z6": "HR TiZ Z6 (hh:mm:ss)",
        "hr_tiz_z7": "HR TiZ Z7 (hh:mm:ss)",
        "sweet_spot_tiz": "Sweet Spot TiZ (hh:mm:ss)",
    }

    non_null_fields = [
        "iso_year",
        "iso_week",
        "day",
        "day_of_week",
        "activity_id",
        "start_time_local",
        "type",
    ]

    flag_columns = [
        "Flag Long Ride >=150min (bool)",
        "Flag Long Ride >=180min (bool)",
        "Flag Long Ride >=240min (bool)",
        "Flag IF <= 0.75 (bool)",
        "Flag IF <= 0.80 (bool)",
        "Flag Z2 Share >= 60% (bool)",
        "Flag Z2 Share >= 70% (bool)",
        "Flag Drift Valid (Z2 >= 90min) (bool)",
        "Flag DES Long Base Candidate (bool)",
        "Flag DES Long Build Candidate (bool)",
        "Flag Brevet Long Candidate (bool)",
    ]

    groups = list(df.groupby(["ISO Year", "ISO Week"], sort=True))
    if not groups:
        raise ValueError("No rows available for activities_actual export.")
    groups = [groups[-1]]

    run_ts = datetime.now(timezone.utc)
    run_stamp = run_ts.strftime("%Y%m%d-%H%M%S")

    schema_dir = resolve_schema_dir()
    validator = SchemaRegistry(schema_dir).validator_for("activities_actual.schema.json")

    data_dir = athlete_data_dir(athlete_id)
    latest_dir = athlete_latest_dir(athlete_id)

    for (yr, wk), g in groups:
        g = g.sort_values(dt_col)
        out_df = g[output_cols]

        iso_week = f"{int(wk):02d}"
        out_file = data_dir / f"{int(yr):04d}" / iso_week / f"activities_actual_{int(yr)}-{iso_week}.csv"
        out_json_file = out_file.with_suffix(".json")
        out_file.parent.mkdir(parents=True, exist_ok=True)

        out_df.to_csv(
            out_file,
            index=False,
            sep=SEPARATOR,
            quoting=csv.QUOTE_ALL,
            quotechar=QUOTECHAR,
            doublequote=True,
            encoding="utf-8-sig",
            lineterminator="\n",
            na_rep="",
        )

        required_columns_set = set(required_field_map.values())
        metric_columns = [
            c for c in out_df.columns
            if c not in required_columns_set
            and c not in flag_columns
        ]

        flag_key_map: dict[str, str] = {}
        used_flag_keys: set[str] = set()
        for col in flag_columns:
            key = unique_key(normalize_key(col), used_flag_keys)
            used_flag_keys.add(key)
            flag_key_map[col] = key

        metric_key_map: dict[str, str] = {}
        used_metric_keys: set[str] = set()
        for col in metric_columns:
            key = unique_key(normalize_key(col), used_metric_keys)
            used_metric_keys.add(key)
            metric_key_map[col] = key

        expected_activity_keys = set(required_field_map.keys()) | {"flags", "metrics"}
        expected_flag_keys = set(flag_key_map.values())
        expected_metric_keys = set(metric_key_map.values())

        activities = []
        for _, row in out_df.iterrows():
            activity = {
                "iso_year": format_int(row.get(required_field_map["iso_year"])),
                "iso_week": format_int(row.get(required_field_map["iso_week"])),
                "day": format_date(row.get(required_field_map["day"])),
                "day_of_week": format_string(row.get(required_field_map["day_of_week"])),
                "activity_id": format_string(row.get(required_field_map["activity_id"])),
                "start_time_local": format_datetime(row.get(required_field_map["start_time_local"])),
                "type": format_string(row.get(required_field_map["type"])),
                "moving_time": format_duration_hms(row.get(required_field_map["moving_time"])),
                "distance_km": format_number(row.get(required_field_map["distance_km"])),
                "work_kj": format_number(row.get(required_field_map["work_kj"])),
                "load_tss": format_number(row.get(required_field_map["load_tss"])),
                "normalized_power_w": format_number(row.get(required_field_map["normalized_power_w"])),
                "intensity_factor": format_number(row.get(required_field_map["intensity_factor"])),
                "avg_hr_bpm": format_number(row.get(required_field_map["avg_hr_bpm"])),
                "max_hr_bpm": format_number(row.get(required_field_map["max_hr_bpm"])),
                "power_tiz_z1": format_duration_hms(row.get(required_field_map["power_tiz_z1"])),
                "power_tiz_z2": format_duration_hms(row.get(required_field_map["power_tiz_z2"])),
                "power_tiz_z3": format_duration_hms(row.get(required_field_map["power_tiz_z3"])),
                "power_tiz_z4": format_duration_hms(row.get(required_field_map["power_tiz_z4"])),
                "power_tiz_z5": format_duration_hms(row.get(required_field_map["power_tiz_z5"])),
                "power_tiz_z6": format_duration_hms(row.get(required_field_map["power_tiz_z6"])),
                "power_tiz_z7": format_duration_hms(row.get(required_field_map["power_tiz_z7"])),
                "hr_tiz_z1": format_duration_hms(row.get(required_field_map["hr_tiz_z1"])),
                "hr_tiz_z2": format_duration_hms(row.get(required_field_map["hr_tiz_z2"])),
                "hr_tiz_z3": format_duration_hms(row.get(required_field_map["hr_tiz_z3"])),
                "hr_tiz_z4": format_duration_hms(row.get(required_field_map["hr_tiz_z4"])),
                "hr_tiz_z5": format_duration_hms(row.get(required_field_map["hr_tiz_z5"])),
                "hr_tiz_z6": format_duration_hms(row.get(required_field_map["hr_tiz_z6"])),
                "hr_tiz_z7": format_duration_hms(row.get(required_field_map["hr_tiz_z7"])),
                "sweet_spot_tiz": format_duration_hms(row.get(required_field_map["sweet_spot_tiz"])),
            }

            missing_fields = [key for key in non_null_fields if activity.get(key) is None]
            if missing_fields:
                raise ValueError(
                    f"Missing required values for {', '.join(missing_fields)} "
                    f"in ISO week {int(yr)}-{iso_week}."
                )

            flags = {}
            for col in flag_columns:
                flags[flag_key_map[col]] = normalize_bool(row.get(col))
            activity["flags"] = flags

            metrics = {}
            for col in metric_columns:
                value = normalize_scalar(row.get(col))
                if isinstance(value, pd.Timestamp):
                    value = value.isoformat()
                metrics[metric_key_map[col]] = value
            activity["metrics"] = metrics

            context_label = f"ISO week {int(yr)}-{iso_week}, activity {activity.get('activity_id') or 'N/A'}"
            ensure_keys("activity", set(activity.keys()), expected_activity_keys, context_label)
            ensure_keys("activity.flags", set(flags.keys()), expected_flag_keys, context_label)
            ensure_keys("activity.metrics", set(metrics.keys()), expected_metric_keys, context_label)

            activities.append(activity)

        version_key = f"{int(yr)}-{iso_week}"
        meta = {
            "artifact_type": "ACTIVITIES_ACTUAL",
            "schema_id": "ActivitiesActualInterface",
            "schema_version": "1.0",
            "version": "1.0",
            "authority": "Binding",
            "owner_agent": "Data-Pipeline",
            "run_id": f"{run_stamp}-data-pipeline-{int(yr)}{iso_week}",
            "created_at": run_ts.isoformat(),
            "iso_week": version_key,
            "iso_week_range": f"{version_key}--{version_key}",
            "temporal_scope": {
                "from": format_date(g["Day"].min()),
                "to": format_date(g["Day"].max()),
            },
            "scope": "Shared",
            "trace_upstream": [
                {
                    "artifact": input_csv.name,
                    "version": "1.0",
                    "run_id": run_stamp,
                }
            ],
            "trace_data": [],
            "trace_events": [],
            "notes": "Derived from Intervals.icu activity export.",
        }
        payload = {
            "meta": meta,
            "data": {
                "activities": activities,
                "notes": "Derived from Intervals.icu activity export.",
            },
        }

        if not skip_validate:
            try:
                validate_or_raise(validator, payload)
            except SchemaValidationError as exc:
                print("Schema validation failed for ACTIVITIES_ACTUAL:")
                for err in exc.errors:
                    print(f"- {err}")
                raise

        with open(out_json_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        latest_dir.mkdir(parents=True, exist_ok=True)
        latest_csv = latest_dir / "activities_actual.csv"
        latest_json = latest_dir / "activities_actual.json"
        latest_csv.write_bytes(out_file.read_bytes())
        latest_json.write_bytes(out_json_file.read_bytes())

        record_index_write(
            athlete_id=athlete_id,
            artifact_type="ACTIVITIES_ACTUAL",
            version_key=version_key,
            path=out_json_file,
            run_id=meta["run_id"],
            producer_agent=meta["owner_agent"],
            created_at=meta["created_at"],
            iso_week=meta["iso_week"],
        )

        print(f"JSON exported: {out_json_file}")


# === Activities Trend helpers ===

def compile_activities_trend(
    *,
    athlete_id: str,
    input_csv: Path,
    skip_validate: bool,
) -> None:
    """Compile activities_trend outputs from the export CSV."""
    df = pd.read_csv(input_csv, sep=SEPARATOR, quotechar=QUOTECHAR)
    dt_col = standardize_activity_columns(df)
    df = df.copy()
    cols = {c.lower(): c for c in df.columns}

    iso = df[dt_col].dt.isocalendar()
    df["ISO_Year"] = iso.year.astype(int)
    df["ISO_Week"] = iso.week.astype(int)
    df["Day"] = df[dt_col].dt.floor("D")
    range_start = df["Day"].min()
    range_end = df["Day"].max()
    if pd.isna(range_start) or pd.isna(range_end):
        fallback_day = datetime.now(timezone.utc).date()
        range_start = fallback_day
        range_end = fallback_day
    start_day = range_start.date() if hasattr(range_start, "date") else range_start
    end_day = range_end.date() if hasattr(range_end, "date") else range_end

    col_move_s = getcol(cols, "Moving Time (s)")
    col_dist_m = getcol(cols, "Distance (m)")
    col_tss = getcol(cols, "Load (TSS)", "TSS")
    col_work_j = getcol(cols, "Work (J)")
    col_np = getcol(cols, "NP (W)")
    col_if = getcol(cols, "Intensity Factor (IF)")
    col_decoup = getcol(cols, "Decoupling (%)", "Pa:Hr (%)")
    col_ef = getcol(cols, "Efficiency Factor (EF)")
    col_tsb = getcol(cols, "TSB (today)", "TSB")
    flag_columns_present = {c for c in FLAG_COLUMN_KEYS if c in df.columns}

    pz_cols = {z: getcol(cols, f"Power TiZ Z{z} (s)") for z in range(1, 8)}
    col_sst_s = getcol(cols, "Sweet Spot TiZ (s)")

    hr_cols = {z: getcol(cols, f"HR TiZ Z{z} (s)") for z in range(1, 8)}

    col_mmp = {
        60: getcol(cols, "MMP 60s (W)"),
        180: getcol(cols, "MMP 180s (W)"),
        300: getcol(cols, "MMP 300s (W)"),
        600: getcol(cols, "MMP 600s (W)"),
        1200: getcol(cols, "MMP 1200s (W)"),
        1800: getcol(cols, "MMP 1800s (W)"),
        3600: getcol(cols, "MMP 3600s (W)"),
        5400: getcol(cols, "MMP 5400s (W)"),
        7200: getcol(cols, "MMP 7200s (W)"),
        9000: getcol(cols, "MMP 9000s (W)"),
        10800: getcol(cols, "MMP 10800s (W)"),
        14400: getcol(cols, "MMP 14400s (W)"),
        18000: getcol(cols, "MMP 18000s (W)"),
        21600: getcol(cols, "MMP 21600s (W)"),
    }

    col_vo2_power_s = getcol(cols, "VO2Max Power TiZ (s)")
    col_vo2_hr_s = getcol(cols, "VO2Max HR TiZ (s)")

    col_ftp_est = getcol(cols, "FTP Estimated (W)")
    col_vo2_ftp = getcol(cols, "VO2/FTP (MMP 300s (W) / FTP Estimated (W))")

    if col_ftp_est is None and col_mmp[1200] is not None:
        df["FTP Estimated (W)"] = 0.95 * pd.to_numeric(df[col_mmp[1200]], errors="coerce")
        col_ftp_est = "FTP Estimated (W)"

    if col_vo2_ftp is None and col_mmp[300] is not None and col_ftp_est is not None:
        den = pd.to_numeric(df[col_ftp_est], errors="coerce")
        num = pd.to_numeric(df[col_mmp[300]], errors="coerce")
        df["VO2/FTP (MMP 300s (W) / FTP Estimated (W))"] = num / den.where(den != 0)
        col_vo2_ftp = "VO2/FTP (MMP 300s (W) / FTP Estimated (W))"

    def sum_seconds(series: pd.Series) -> float:
        return pd.to_numeric(series, errors="coerce").fillna(0).sum()

    def sum_seconds_to_hmm(seconds: float) -> str:
        total_minutes = int(round(seconds / 60.0))
        h = total_minutes // 60
        m = total_minutes % 60
        return f"{h:02d}:{m:02d}"

    def sum_m_to_km_raw(series: pd.Series) -> float:
        return pd.to_numeric(series, errors="coerce").fillna(0).sum() / 1000.0

    def sum_j_to_kj_raw(series: pd.Series) -> float:
        return pd.to_numeric(series, errors="coerce").fillna(0).sum() / 1000.0

    def avg(series: pd.Series) -> float:
        v = pd.to_numeric(series, errors="coerce").dropna()
        if not len(v):
            return np.nan
        return float(v.mean())

    def last(series: pd.Series) -> float:
        v = pd.to_numeric(series, errors="coerce").dropna()
        if not len(v):
            return np.nan
        return v.iloc[-1]

    def fmt_int(value: float) -> int | str:
        return "" if pd.isna(value) else int(round(value))

    def fmt_dec(value: float, nd: int) -> float | str:
        return "" if pd.isna(value) else round(float(value), nd)

    def num_or_none(value):
        value = normalize_scalar(value)
        if value is None:
            return None
        try:
            return float(value)
        except Exception:
            return None

    def int_or_none(value):
        value = normalize_scalar(value)
        if value is None:
            return None
        try:
            return int(value)
        except Exception:
            return None

    def duration_hm_from_seconds(seconds: float) -> str | None:
        if pd.isna(seconds):
            return None
        return sum_seconds_to_hmm(seconds)

    def duration_hms_from_seconds(seconds: float) -> str | None:
        if pd.isna(seconds):
            return None
        return seconds_to_hms(seconds)

    def count_back_to_back_z2_days(g_week: pd.DataFrame, z2_col: str | None) -> int | float:
        if z2_col is None:
            return np.nan
        tmp = g_week.copy()
        tmp["Z2_min"] = pd.to_numeric(tmp[z2_col], errors="coerce").fillna(0) / 60.0
        day_sum = tmp.groupby("Day")["Z2_min"].sum().sort_index()
        z2_days = day_sum[day_sum >= Z2_MIN_THRESHOLD_MIN].index.sort_values()
        if len(z2_days) < 2:
            return 0
        count = 0
        for d1, d2 in zip(z2_days, z2_days[1:]):
            if (d2 - d1).days == 1:
                count += 1
        return int(count)

    rows = []
    weekly_trends_json = []
    for (yr, wk), g in df.groupby(["ISO_Year", "ISO_Week"], sort=True):
        start = g[dt_col].min().date()
        end = g[dt_col].max().date()
        period = f"{start}-{end}"

        move_seconds = sum_seconds(g[col_move_s]) if col_move_s else np.nan
        dist_km_raw = sum_m_to_km_raw(g[col_dist_m]) if col_dist_m else np.nan
        tss_sum_raw = pd.to_numeric(g[col_tss], errors="coerce").fillna(0).sum() if col_tss else np.nan
        kj_sum_raw = sum_j_to_kj_raw(g[col_work_j]) if col_work_j else np.nan
        np_mean_raw = avg(g[col_np]) if col_np else np.nan
        if_mean_raw = avg(g[col_if]) if col_if else np.nan
        dec_mean_raw = avg(g[col_decoup]) if col_decoup else np.nan
        di_val_raw = (1 - abs(dec_mean_raw) / 100.0) if (dec_mean_raw == dec_mean_raw) else np.nan
        ef_mean_raw = avg(g[col_ef]) if col_ef else np.nan
        tsb_last_raw = last(g[col_tsb]) if col_tsb else np.nan
        move_min_series = (
            pd.to_numeric(g[col_move_s], errors="coerce") / 60.0 if col_move_s else pd.Series(dtype="float64")
        )

        pz_sec_raw = {z: (sum_seconds(g[pz_cols[z]]) if pz_cols[z] else 0.0) for z in range(1, 8)}
        pz_min_raw = {z: (pz_sec_raw[z] / 60.0) for z in range(1, 8)}
        pz_sum = sum(pz_min_raw.values())
        hr_sec_raw = {z: (sum_seconds(g[hr_cols[z]]) if hr_cols[z] else 0.0) for z in range(1, 8)}
        z2_min_series = (
            pd.to_numeric(g[pz_cols[2]], errors="coerce") / 60.0 if pz_cols[2] else pd.Series(dtype="float64")
        )

        sst_sec_raw = sum_seconds(g[col_sst_s]) if col_sst_s else 0.0
        if col_vo2_power_s:
            vo2_p_sec_raw = sum_seconds(g[col_vo2_power_s])
        else:
            vo2_p_sec_raw = pz_sec_raw[5]
        if col_vo2_hr_s:
            vo2_hr_sec_raw = sum_seconds(g[col_vo2_hr_s])
        else:
            hr_seconds = 0
            for z in range(4, 8):
                c = hr_cols[z]
                if c is not None:
                    hr_seconds += sum_seconds(g[c])
            vo2_hr_sec_raw = hr_seconds if hr_seconds > 0 else 0.0
        vo2_eff_sec_raw = max(vo2_p_sec_raw, vo2_hr_sec_raw)

        z2_pct_raw = (100.0 * pz_min_raw[2] / pz_sum) if pz_sum > 0 else np.nan
        z1z2_pct_raw = (100.0 * (pz_min_raw[1] + pz_min_raw[2]) / pz_sum) if pz_sum > 0 else np.nan
        z5_pct_raw = (100.0 * pz_min_raw[5] / pz_sum) if pz_sum > 0 else np.nan

        mmp_out_raw = {}
        for dur in (60, 180, 300, 600, 1200, 1800, 3600, 5400, 7200, 9000, 10800, 14400, 18000, 21600):
            c = col_mmp[dur]
            mmp_out_raw[dur] = avg(g[c]) if c is not None and len(g[c].dropna()) else np.nan
        ftp_est_mean_raw = avg(g[col_ftp_est]) if col_ftp_est else np.nan
        fir = np.nan
        if not pd.isna(mmp_out_raw[300]) and not pd.isna(mmp_out_raw[1200]) and mmp_out_raw[1200] != 0:
            fir = mmp_out_raw[300] / mmp_out_raw[1200]
        vo2_ftp_ratio = np.nan
        if not pd.isna(mmp_out_raw[300]) and not pd.isna(ftp_est_mean_raw) and ftp_est_mean_raw != 0:
            vo2_ftp_ratio = mmp_out_raw[300] / ftp_est_mean_raw

        adher = None
        if (yr, wk) in TSS_PLAN_BY_WEEK and not pd.isna(tss_sum_raw):
            plan = TSS_PLAN_BY_WEEK[(yr, wk)]
            if plan:
                adher = int(round(100.0 * tss_sum_raw / plan))

        b2b = count_back_to_back_z2_days(g, pz_cols[2])

        weekly_flag_counts = {}
        weekly_flag_any = {}
        flag_counts_json = {}
        flag_any_json = {}
        for c, key in FLAG_COLUMN_KEYS.items():
            if c in flag_columns_present:
                if c == "Flag IF <= 0.75 (bool)" and col_if:
                    mask = pd.to_numeric(g[col_if], errors="coerce").round(3) <= 0.75
                elif c == "Flag IF <= 0.80 (bool)" and col_if:
                    mask = pd.to_numeric(g[col_if], errors="coerce").round(3) <= 0.80
                else:
                    mask = g[c].fillna(False).astype(bool)
                count_val = int(mask.sum())
                any_val = bool(mask.any())
            else:
                count_val = None
                any_val = None
            count_key = f"Count {c}".replace("(bool)", "(count)")
            weekly_flag_counts[count_key] = count_val
            weekly_flag_any[f"Any {c}"] = any_val
            flag_counts_json[key] = count_val
            flag_any_json[key] = any_val

        move_min_total = float(move_min_series.sum()) if len(move_min_series) else np.nan
        move_min_max = float(move_min_series.max()) if len(move_min_series) else np.nan
        z2_min_total = float(z2_min_series.sum()) if len(z2_min_series) else np.nan
        z2_min_max = float(z2_min_series.max()) if len(z2_min_series) else np.nan
        weekly_z2_share_pct = (z2_min_total / move_min_total * 100.0) if move_min_total else np.nan

        def sum_minutes_where(mask_col: str, minutes_series: pd.Series) -> float:
            if mask_col not in g.columns or len(minutes_series) == 0:
                return np.nan
            mask = g[mask_col].fillna(False).astype(bool)
            return float(minutes_series.where(mask, 0).sum())

        move_min_150plus = sum_minutes_where("Flag Long Ride >=150min (bool)", move_min_series)
        move_min_180plus = sum_minutes_where("Flag Long Ride >=180min (bool)", move_min_series)
        move_min_240plus = sum_minutes_where("Flag Long Ride >=240min (bool)", move_min_series)
        move_min_des_long_base = sum_minutes_where("Flag DES Long Base Candidate (bool)", move_min_series)
        move_min_des_long_build = sum_minutes_where("Flag DES Long Build Candidate (bool)", move_min_series)
        z2_min_des_long_base = sum_minutes_where("Flag DES Long Base Candidate (bool)", z2_min_series)
        z2_min_des_long_build = sum_minutes_where("Flag DES Long Build Candidate (bool)", z2_min_series)
        z2_min_150plus = sum_minutes_where("Flag Long Ride >=150min (bool)", z2_min_series)
        z2_min_180plus = sum_minutes_where("Flag Long Ride >=180min (bool)", z2_min_series)
        z2_min_240plus = sum_minutes_where("Flag Long Ride >=240min (bool)", z2_min_series)

        row = {
            "Year": int(yr),
            "ISO Week": int(wk),
            "Period": period,
            "# Activities": int(len(g)),
            "Moving Time (h:mm)": "" if pd.isna(move_seconds) else sum_seconds_to_hmm(move_seconds),
            "Distance (km)": fmt_dec(dist_km_raw, 1),
            "Load (TSS)": fmt_int(tss_sum_raw),
            "Work (kJ)": fmt_int(kj_sum_raw),
            "Normalized Power (NP) (W)": fmt_int(np_mean_raw),
            "Intensity Factor (IF)": fmt_dec(if_mean_raw, 2),
            "Decoupling (%)": fmt_dec(dec_mean_raw, 1),
            "Durability Index (DI)": fmt_dec(di_val_raw, 2),
            "Efficiency Factor (EF)": fmt_dec(ef_mean_raw, 2),
            "Functional Intensity Ratio (FIR) (MMP 5'/ MMP 20')": fmt_dec(fir, 2),
            "FTP Estimated (W)": fmt_int(ftp_est_mean_raw),
            "VO2/FTP (MMP 300s (W) / FTP Estimated (W))": fmt_dec(vo2_ftp_ratio, 2),
            "TSB (today)": fmt_dec(tsb_last_raw, 1),
            "Adherence (%)": adher,
            "Z1 + Z2 Time (%)": fmt_dec(z1z2_pct_raw, 1),
            "Z5 Time (%)": fmt_dec(z5_pct_raw, 1),
            "Power TiZ Z1 (hh:mm:ss)": seconds_to_hms(pz_sec_raw[1]),
            "Power TiZ Z2 (hh:mm:ss)": seconds_to_hms(pz_sec_raw[2]),
            "Power TiZ Z3 (hh:mm:ss)": seconds_to_hms(pz_sec_raw[3]),
            "Power TiZ Z4 (hh:mm:ss)": seconds_to_hms(pz_sec_raw[4]),
            "Power TiZ Z5 (hh:mm:ss)": seconds_to_hms(pz_sec_raw[5]),
            "Power TiZ Z6 (hh:mm:ss)": seconds_to_hms(pz_sec_raw[6]),
            "Power TiZ Z7 (hh:mm:ss)": seconds_to_hms(pz_sec_raw[7]),
            "HR TiZ Z1 (hh:mm:ss)": seconds_to_hms(hr_sec_raw[1]),
            "HR TiZ Z2 (hh:mm:ss)": seconds_to_hms(hr_sec_raw[2]),
            "HR TiZ Z3 (hh:mm:ss)": seconds_to_hms(hr_sec_raw[3]),
            "HR TiZ Z4 (hh:mm:ss)": seconds_to_hms(hr_sec_raw[4]),
            "HR TiZ Z5 (hh:mm:ss)": seconds_to_hms(hr_sec_raw[5]),
            "HR TiZ Z6 (hh:mm:ss)": seconds_to_hms(hr_sec_raw[6]),
            "HR TiZ Z7 (hh:mm:ss)": seconds_to_hms(hr_sec_raw[7]),
            "Z2 Share (Power) (%)": fmt_dec(z2_pct_raw, 1),
            "Sweet Spot TiZ (hh:mm:ss)": seconds_to_hms(sst_sec_raw),
            "VO2Max Power TiZ (hh:mm:ss)": seconds_to_hms(vo2_p_sec_raw),
            "VO2Max HR TiZ (hh:mm:ss)": seconds_to_hms(vo2_hr_sec_raw),
            "VO2Max TiZ Eff (hh:mm:ss)": seconds_to_hms(vo2_eff_sec_raw),
            "MMP 60s (W)": fmt_int(mmp_out_raw[60]),
            "MMP 180s (W)": fmt_int(mmp_out_raw[180]),
            "MMP 300s (W)": fmt_int(mmp_out_raw[300]),
            "MMP 600s (W)": fmt_int(mmp_out_raw[600]),
            "MMP 1200s (W)": fmt_int(mmp_out_raw[1200]),
            "MMP 1800s (W)": fmt_int(mmp_out_raw[1800]),
            "MMP 3600s (W)": fmt_int(mmp_out_raw[3600]),
            "MMP 5400s (W)": fmt_int(mmp_out_raw[5400]),
            "MMP 7200s (W)": fmt_int(mmp_out_raw[7200]),
            "MMP 9000s (W)": fmt_int(mmp_out_raw[9000]),
            "MMP 10800s (W)": fmt_int(mmp_out_raw[10800]),
            "MMP 14400s (W)": fmt_int(mmp_out_raw[14400]),
            "MMP 18000s (W)": fmt_int(mmp_out_raw[18000]),
            "MMP 21600s (W)": fmt_int(mmp_out_raw[21600]),
            "Back-to-Back Z2 Days": b2b,
            "Weekly Moving Time Total (min)": fmt_int(move_min_total),
            "Weekly Z2 Time Total (min)": fmt_int(z2_min_total),
            "Weekly Z2 Share (%)": fmt_dec(weekly_z2_share_pct, 1),
            "Weekly Moving Time Max (min)": fmt_int(move_min_max),
            "Weekly Z2 Time Max (min)": fmt_int(z2_min_max),
            "Weekly Moving Time >=150min Sum (min)": fmt_int(move_min_150plus),
            "Weekly Moving Time >=180min Sum (min)": fmt_int(move_min_180plus),
            "Weekly Moving Time >=240min Sum (min)": fmt_int(move_min_240plus),
            "Weekly Z2 Time >=150min Sum (min)": fmt_int(z2_min_150plus),
            "Weekly Z2 Time >=180min Sum (min)": fmt_int(z2_min_180plus),
            "Weekly Z2 Time >=240min Sum (min)": fmt_int(z2_min_240plus),
            "Weekly Moving Time DES Base Sum (min)": fmt_int(move_min_des_long_base),
            "Weekly Moving Time DES Build Sum (min)": fmt_int(move_min_des_long_build),
            "Weekly Z2 Time DES Base Sum (min)": fmt_int(z2_min_des_long_base),
            "Weekly Z2 Time DES Build Sum (min)": fmt_int(z2_min_des_long_build),
            **weekly_flag_counts,
            **weekly_flag_any,
        }
        rows.append(row)

        trend_entry = {
            "year": int(yr),
            "iso_week": int(wk),
            "period": {
                "from": start.isoformat(),
                "to": end.isoformat(),
            },
            "weekly_aggregates": {
                "activity_count": int(len(g)),
                "moving_time": duration_hm_from_seconds(move_seconds),
                "distance_km": num_or_none(fmt_dec(dist_km_raw, 1)),
                "load_tss": int_or_none(fmt_int(tss_sum_raw)),
                "work_kj": int_or_none(fmt_int(kj_sum_raw)),
            },
            "intensity_load_metrics": {
                "normalized_power_w": int_or_none(fmt_int(np_mean_raw)),
                "intensity_factor": num_or_none(fmt_dec(if_mean_raw, 2)),
                "decoupling_percent": num_or_none(fmt_dec(dec_mean_raw, 1)),
                "durability_index": num_or_none(fmt_dec(di_val_raw, 2)),
                "efficiency_factor": num_or_none(fmt_dec(ef_mean_raw, 2)),
                "functional_intensity_ratio": num_or_none(fmt_dec(fir, 2)),
                "ftp_estimated_w": int_or_none(fmt_int(ftp_est_mean_raw)),
                "vo2_ftp": num_or_none(fmt_dec(vo2_ftp_ratio, 2)),
            },
            "power_tiz": {
                "z1": duration_hms_from_seconds(pz_sec_raw[1]),
                "z2": duration_hms_from_seconds(pz_sec_raw[2]),
                "z3": duration_hms_from_seconds(pz_sec_raw[3]),
                "z4": duration_hms_from_seconds(pz_sec_raw[4]),
                "z5": duration_hms_from_seconds(pz_sec_raw[5]),
                "z6": duration_hms_from_seconds(pz_sec_raw[6]),
                "z7": duration_hms_from_seconds(pz_sec_raw[7]),
            },
            "hr_tiz": {
                "z1": duration_hms_from_seconds(hr_sec_raw[1]),
                "z2": duration_hms_from_seconds(hr_sec_raw[2]),
                "z3": duration_hms_from_seconds(hr_sec_raw[3]),
                "z4": duration_hms_from_seconds(hr_sec_raw[4]),
                "z5": duration_hms_from_seconds(hr_sec_raw[5]),
                "z6": duration_hms_from_seconds(hr_sec_raw[6]),
                "z7": duration_hms_from_seconds(hr_sec_raw[7]),
            },
        }

        optional_tiz = {
            "sweet_spot": duration_hms_from_seconds(sst_sec_raw),
            "vo2max_power": duration_hms_from_seconds(vo2_p_sec_raw),
            "vo2max_hr": duration_hms_from_seconds(vo2_hr_sec_raw),
            "vo2max_tiz_efficiency": duration_hms_from_seconds(vo2_eff_sec_raw),
        }
        trend_entry["optional_tiz"] = optional_tiz

        distribution_metrics = {
            "adherence_percent": int_or_none(adher),
            "z1_z2_time_percent": num_or_none(fmt_dec(z1z2_pct_raw, 1)),
            "z5_time_percent": num_or_none(fmt_dec(z5_pct_raw, 1)),
            "z2_share_power_percent": num_or_none(fmt_dec(z2_pct_raw, 1)),
            "back_to_back_z2_days_count": int_or_none(b2b),
        }
        trend_entry["distribution_metrics"] = distribution_metrics

        peak_metrics = {}
        for duration, key in [
            (60, "mmp_60s"),
            (180, "mmp_180s"),
            (300, "mmp_300s"),
            (600, "mmp_600s"),
            (1200, "mmp_1200s"),
            (1800, "mmp_1800s"),
            (3600, "mmp_3600s"),
            (5400, "mmp_5400s"),
            (7200, "mmp_7200s"),
            (9000, "mmp_9000s"),
            (10800, "mmp_10800s"),
            (14400, "mmp_14400s"),
            (18000, "mmp_18000s"),
            (21600, "mmp_21600s"),
        ]:
            peak_metrics[key] = int_or_none(fmt_int(mmp_out_raw[duration]))
        trend_entry["peak_metrics"] = peak_metrics

        trend_entry["flag_counts"] = flag_counts_json
        trend_entry["flag_any"] = flag_any_json

        metrics = {
            "tsb_today": num_or_none(fmt_dec(tsb_last_raw, 1)),
            "weekly_moving_time_total_min": int_or_none(move_min_total),
            "weekly_z2_time_total_min": int_or_none(z2_min_total),
            "weekly_z2_share": num_or_none(fmt_dec(weekly_z2_share_pct, 1)),
            "weekly_moving_time_max_min": int_or_none(move_min_max),
            "weekly_z2_time_max_min": int_or_none(z2_min_max),
            "weekly_moving_time_150min_sum_min": int_or_none(move_min_150plus),
            "weekly_moving_time_180min_sum_min": int_or_none(move_min_180plus),
            "weekly_moving_time_240min_sum_min": int_or_none(move_min_240plus),
            "weekly_z2_time_150min_sum_min": int_or_none(z2_min_150plus),
            "weekly_z2_time_180min_sum_min": int_or_none(z2_min_180plus),
            "weekly_z2_time_240min_sum_min": int_or_none(z2_min_240plus),
            "weekly_moving_time_des_base_sum_min": int_or_none(move_min_des_long_base),
            "weekly_moving_time_des_build_sum_min": int_or_none(move_min_des_long_build),
            "weekly_z2_time_des_base_sum_min": int_or_none(z2_min_des_long_base),
            "weekly_z2_time_des_build_sum_min": int_or_none(z2_min_des_long_build),
        }
        trend_entry["metrics"] = metrics

        weekly_trends_json.append(trend_entry)

    out = pd.DataFrame(rows, columns=REQUIRED_COLUMNS).sort_values(["Year", "ISO Week"]).reset_index(drop=True)

    if out.empty:
        raise ValueError("No data available for export.")

    run_ts = datetime.now(timezone.utc)
    run_stamp = run_ts.strftime("%Y%m%d-%H%M%S")

    latest = out[["Year", "ISO Week"]].sort_values(["Year", "ISO Week"]).iloc[-1]
    year = int(latest["Year"])
    week = int(latest["ISO Week"])
    iso_week = f"{week:02d}"

    data_dir = athlete_data_dir(athlete_id)
    latest_dir = athlete_latest_dir(athlete_id)

    out_file = data_dir / f"{year:04d}" / iso_week / f"activities_trend_{year}-{iso_week}.csv"
    out_json_file = out_file.with_suffix(".json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    latest_dir.mkdir(parents=True, exist_ok=True)

    out.to_csv(
        out_file,
        index=False,
        sep=SEPARATOR,
        quoting=csv.QUOTE_ALL,
        quotechar=QUOTECHAR,
        doublequote=True,
        encoding="utf-8-sig",
        lineterminator="\n",
        na_rep="",
    )

    schema_dir = resolve_schema_dir()
    validator = SchemaRegistry(schema_dir).validator_for("activities_trend.schema.json")

    version_key = f"{year}-{iso_week}"
    start_week = f"{date_to_iso_week(start_day)[0]}-{date_to_iso_week(start_day)[1]:02d}"
    end_week = f"{date_to_iso_week(end_day)[0]}-{date_to_iso_week(end_day)[1]:02d}"
    meta = {
        "artifact_type": "ACTIVITIES_TREND",
        "schema_id": "ActivitiesTrendInterface",
        "schema_version": "1.0",
        "version": "1.0",
        "authority": "Binding",
        "owner_agent": "Data-Pipeline",
        "run_id": f"{run_stamp}-data-pipeline-{year}{iso_week}",
        "created_at": run_ts.isoformat(),
        "iso_week": version_key,
        "iso_week_range": f"{start_week}--{end_week}",
        "temporal_scope": {
            "from": start_day.isoformat(),
            "to": end_day.isoformat(),
        },
        "scope": "Shared",
        "trace_upstream": [
            {
                "artifact": input_csv.name,
                "version": "1.0",
                "run_id": run_stamp,
            }
        ],
        "trace_data": [],
        "trace_events": [],
        "notes": "Derived from Intervals.icu activity export.",
    }
    payload = {
        "meta": meta,
        "data": {
            "weekly_trends": weekly_trends_json,
            "notes": "Derived from Intervals.icu activity export.",
        },
    }

    if not skip_validate:
        try:
            validate_or_raise(validator, payload)
        except SchemaValidationError as exc:
            print("Schema validation failed for ACTIVITIES_TREND:")
            for err in exc.errors:
                print(f"- {err}")
            raise

    with open(out_json_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    latest_csv = latest_dir / "activities_trend.csv"
    latest_json = latest_dir / "activities_trend.json"
    latest_csv.write_bytes(out_file.read_bytes())
    latest_json.write_bytes(out_json_file.read_bytes())

    record_index_write(
        athlete_id=athlete_id,
        artifact_type="ACTIVITIES_TREND",
        version_key=version_key,
        path=out_json_file,
        run_id=meta["run_id"],
        producer_agent=meta["owner_agent"],
        created_at=meta["created_at"],
        iso_week=meta["iso_week"],
        iso_week_range=meta["iso_week_range"],
    )

    print(f"JSON exported: {out_json_file}")


def main() -> int:
    """Run the end-to-end Intervals.icu pipeline."""
    load_env()
    logger = configure_logging(Path(__file__).stem)
    args = parse_args()
    athlete_id = args.athlete or resolve_athlete_id()
    api_key = require_env("API_KEY")
    base_url = require_env("BASE_URL")
    logger.info("Intervals pipeline athlete=%s base_url=%s", athlete_id, base_url)

    session.auth = HTTPBasicAuth("API_KEY", api_key)
    has_week = args.year is not None and args.week is not None
    has_range = args.from_date is not None and args.to_date is not None

    if has_week and has_range:
        raise SystemExit("Provide either --year/--week OR --from/--to, not both.")

    if has_week:
        _, end_date = iso_week_to_dates(args.year, args.week)
        from_date = end_date - timedelta(days=90)
        to_date = end_date
    elif has_range:
        try:
            from_date = parse_ymd(args.from_date)
            to_date = parse_ymd(args.to_date)
        except ValueError:
            raise SystemExit("Invalid date format. Expected YYYY-MM-DD, e.g. --from 2025-10-28")
        if from_date > to_date:
            raise SystemExit(f"--from {from_date} is after --to {to_date}.")
    else:
        from_date, to_date = resolve_default_range(weeks=DEFAULT_WEEKS)

    logger.info("Intervals pipeline range from=%s to=%s", from_date, to_date)
    latest_dir = athlete_latest_dir(athlete_id)

    print("[1/5] Fetching athlete settings + zone model...")
    logger.info("Stage 1: zone model")
    write_zone_model(
        athlete_id=athlete_id,
        base_url=base_url,
        latest_dir=latest_dir,
        skip_validate=args.skip_validate,
    )

    print("[2/5] Fetching wellness data...")
    logger.info("Stage 2: wellness data")
    write_wellness(
        athlete_id=athlete_id,
        base_url=base_url,
        from_date=from_date,
        to_date=to_date,
        skip_validate=args.skip_validate,
    )

    print("[3/5] Fetching activity data from Intervals.icu...")
    logger.info("Stage 3: activity data")
    export_csv = export_range(
        athlete_id=athlete_id,
        base_url=base_url,
        from_date=from_date,
        to_date=to_date,
    )

    print("[4/5] Compiling activities_actual (latest week)...")
    logger.info("Stage 4: activities_actual")
    compile_activities_actual(
        athlete_id=athlete_id,
        input_csv=export_csv,
        skip_validate=args.skip_validate,
    )

    print("[5/5] Compiling activities_trend...")
    logger.info("Stage 5: activities_trend")
    compile_activities_trend(
        athlete_id=athlete_id,
        input_csv=export_csv,
        skip_validate=args.skip_validate,
    )

    logger.info("Pipeline complete latest_dir=%s", latest_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
