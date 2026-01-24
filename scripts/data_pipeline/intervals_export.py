#!/usr/bin/env python3
"""Export Intervals.icu activity data to CSV for downstream processing."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta
from io import StringIO
import logging
from pathlib import Path
import sys
import warnings

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter, Retry
from requests.auth import HTTPBasicAuth

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    # Allow running the script directly without installing the package.
    sys.path.insert(0, str(ROOT))

from scripts.data_pipeline.common import (
    athlete_data_dir,
    athlete_latest_dir,
    configure_logging,
    load_env,
    require_env,
    resolve_athlete_id,
)

# ======================================================
# Configuration (initialized in main)
# ======================================================

ATHLETE_ID: str | None = None
API_KEY: str | None = None
BASE_URL: str | None = None
AUTH: HTTPBasicAuth | None = None
session: requests.Session | None = None
DEFAULT_TIMEOUT = 15


# ======================================================
# Global variables
# ======================================================
week: int | None = None
year: int | None = None


# ======================================================
# Helper functions
# ======================================================

def _get(url: str) -> requests.Response:
    """Perform a GET request with retry/timeout settings."""
    if session is None:
        raise RuntimeError("Session not initialized. Run main() first.")
    resp = session.get(url, timeout=DEFAULT_TIMEOUT)
    resp.raise_for_status()
    return resp


def _require_config() -> None:
    """Ensure required runtime config is initialized."""
    if BASE_URL is None or ATHLETE_ID is None:
        raise RuntimeError("Missing config. Ensure BASE_URL and ATHLETE_ID are set.")


def iso_week_to_dates(iso_year: int, iso_week: int) -> tuple[datetime.date, datetime.date]:
    """Convert an ISO week to its date range (Monday through Sunday)."""
    first_day = datetime.fromisocalendar(iso_year, iso_week, 1)
    last_day = first_day + timedelta(days=6)
    return first_day.date(), last_day.date()


def date_to_iso_week(target_date: datetime | datetime.date) -> tuple[int, int]:
    """Return the ISO year/week for a given date or datetime."""
    iso_year, iso_week, _ = target_date.isocalendar()
    return int(iso_year), int(iso_week)


def last_complete_week_end(today: datetime.date) -> datetime.date:
    """Return the last completed ISO week end (Sunday) before the given date."""
    if today.isoweekday() == 7:
        return today
    return today - timedelta(days=today.isoweekday())


def resolve_default_range(weeks: int = 24) -> tuple[datetime.date, datetime.date]:
    """Return the default date range covering the last N complete ISO weeks."""
    end_date = last_complete_week_end(datetime.now().date())
    end_monday = end_date - timedelta(days=6)
    start_monday = end_monday - timedelta(weeks=weeks - 1)
    return start_monday, end_date


def get_activities(start_date: datetime.date, end_date: datetime.date) -> list[dict]:
    """Fetch activities for a date range."""
    _require_config()
    url = f"{BASE_URL}/athlete/{ATHLETE_ID}/activities?oldest={start_date}&newest={end_date}"
    return _get(url).json()


def get_activity_detail(activity_id: str | int) -> dict:
    """Fetch detailed activity data by activity id."""
    _require_config()
    url = f"{BASE_URL}/activity/{activity_id}"
    return _get(url).json()


def get_power_curves_csv(start_date: datetime.date, end_date: datetime.date) -> str:
    """Fetch the power curves CSV for a date range."""
    _require_config()
    url = (
        f"{BASE_URL}/athlete/{ATHLETE_ID}/activity-power-curves.csv"
        f"?oldest={start_date}&newest={end_date}"
    )
    return _get(url).text


# ======================================================
# Data helpers
# ======================================================

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


# ======================================================
# Main entry for weekly export
# ======================================================

def export_week(iso_year: int, iso_week: int) -> None:
    """Export ~90 days of data ending at the end of the ISO week."""
    _, end_date = iso_week_to_dates(iso_year, iso_week)
    start_date = end_date - timedelta(days=90)
    export_range(start_date, end_date)


def export_range(from_date: datetime.date, to_date: datetime.date) -> None:
    """Export activities for a date range and write CSV outputs."""
    _require_config()
    print(f"Range: {from_date} to {to_date}")

    activities = get_activities(from_date, to_date)
    # Filter to riding activities only
    activities = [a for a in activities if a.get("type") in {"Ride", "VirtualRide"}]

    # Load power curves CSV and index by activity id
    curve_csv = get_power_curves_csv(from_date, to_date)
    curve_df = pd.read_csv(StringIO(curve_csv))
    if not curve_df.empty:
        curve_df.rename(columns={"activity": "id"}, inplace=True)
        curve_df["id"] = curve_df["id"].astype(str)
        curve_df.set_index("id", inplace=True)
    else:
        curve_df = pd.DataFrame()

    rows = []

    # ==================================================
    # Process activity details
    # ==================================================
    for act in activities:
        aid = act.get("id")
        detail = get_activity_detail(aid)

        # Power zone durations including Sweet Spot
        power_zone_secs = {z["id"]: z["secs"] for z in (detail.get("icu_zone_times") or [])}
        # HR zones normalized to 7 buckets
        hr_zones = (detail.get("icu_hr_zone_times") or []) + [0] * 7
        hr_zones = hr_zones[:7]

        # Safe defaults for potentially missing string fields
        tags = detail.get("tags") or []
        interval_summary = detail.get("interval_summary") or []

        # Core activity metrics
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

            # Power and load
            "average_watts": detail.get("icu_average_watts"),
            "weighted_avg_watts": detail.get("icu_weighted_avg_watts"),
            "training_load": detail.get("icu_training_load"),
            "strain_score": detail.get("strain_score"),

            # Heart rate and cadence
            "average_heartrate": detail.get("average_heartrate"),
            "max_heartrate": detail.get("max_heartrate"),
            "average_cadence": detail.get("average_cadence"),

            # Peaks and work
            "p_max": detail.get("p_max"),
            "icu_joules": detail.get("icu_joules"),

            # Efficiency / intensity
            "icu_power_hr": detail.get("icu_power_hr"),
            "icu_efficiency_factor": detail.get("icu_efficiency_factor"),
            "icu_intensity": div_or_none(detail.get("icu_intensity"), 100.0),
            "icu_variability_index": detail.get("icu_variability_index"),

            # Decoupling and Z2 power/HR
            "decoupling": detail.get("decoupling"),
            "icu_power_hr_z2": detail.get("icu_power_hr_z2"),
            "icu_power_hr_z2_mins": detail.get("icu_power_hr_z2_mins"),

            # Power zones
            "z1": power_zone_secs.get("Z1", 0),
            "z2": power_zone_secs.get("Z2", 0),
            "z3": power_zone_secs.get("Z3", 0),
            "z4": power_zone_secs.get("Z4", 0),
            "z5": power_zone_secs.get("Z5", 0),
            "z6": power_zone_secs.get("Z6", 0),
            "z7": power_zone_secs.get("Z7", 0),

            # Sweet Spot
            "ss": power_zone_secs.get("SS", 0),
            "icu_sweet_spot_min": detail.get("icu_sweet_spot_min"),
            "icu_sweet_spot_max": detail.get("icu_sweet_spot_max"),

            # HR zones
            "hr_z1": hr_zones[0],
            "hr_z2": hr_zones[1],
            "hr_z3": hr_zones[2],
            "hr_z4": hr_zones[3],
            "hr_z5": hr_zones[4],
            "hr_z6": hr_zones[5],
            "hr_z7": hr_zones[6],

            # Anaerobic metrics
            "icu_w_prime": detail.get("icu_w_prime"),
            "icu_max_wbal_depletion": detail.get("icu_max_wbal_depletion"),
            "icu_joules_above_ftp": detail.get("icu_joules_above_ftp"),

            # Elevation
            "total_elevation_gain": detail.get("total_elevation_gain"),
            "total_elevation_loss": detail.get("total_elevation_loss"),
            "average_altitude": detail.get("average_altitude"),
            "min_altitude": detail.get("min_altitude"),
            "max_altitude": detail.get("max_altitude"),

            # Session metadata
            "trainer": detail.get("trainer", act.get("trainer")),
            "device_watts": detail.get("device_watts", act.get("device_watts")),
            "source": detail.get("source"),
            "device_name": detail.get("device_name"),
            "route_id": detail.get("route_id"),
            "tags": ",".join(tags) if isinstance(tags, list) else tags,
            "interval_summary": "; ".join(interval_summary) if isinstance(interval_summary, list) else interval_summary,
            "compliance": detail.get("compliance"),

            # Nutrition / context
            "carbs_used": detail.get("carbs_used"),
            "carbs_ingested": detail.get("carbs_ingested"),

            # Z2
            "icu_cadence_z2": detail.get("icu_cadence_z2"),

            # Polarization and loads
            "polarization_index": detail.get("polarization_index"),
            "power_load": detail.get("power_load"),
            "hr_load": detail.get("hr_load"),
            "hr_load_type": detail.get("hr_load_type"),

            # Individual anchors
            "icu_ftp": detail.get("icu_ftp"),
            "lthr": detail.get("lthr"),
            "athlete_max_hr": detail.get("athlete_max_hr"),

            # Status fields
            "icu_ctl": detail.get("icu_ctl"),
            "icu_atl": detail.get("icu_atl"),

            # Speed / energy / environment
            "average_speed": detail.get("average_speed"),
            "max_speed": detail.get("max_speed"),
            "calories": detail.get("calories"),
            "average_temp": detail.get("average_temp"),
            "min_temp": detail.get("min_temp"),
            "max_temp": detail.get("max_temp"),

            # Subjective load
            "session_rpe": detail.get("session_rpe"),
            "feel": detail.get("feel"),

            # Warmup / cooldown
            "icu_warmup_time": detail.get("icu_warmup_time"),
            "icu_cooldown_time": detail.get("icu_cooldown_time"),
        }

        # Join MMP values from power curves
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

    # ==================================================
    # DataFrame + column mapping
    # ==================================================
    df = pd.DataFrame(rows)
    df = df.where(pd.notnull(df), "")

    rename_map = {
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

    for i in range(1, 8):
        rename_map[f"z{i}"] = f"Power TiZ Z{i} (s)"
        rename_map[f"hr_z{i}"] = f"HR TiZ Z{i} (s)"

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
        rename_map[f"mmp_{secs}s"] = f"MMP {secs}s (W)"

    df.rename(columns=rename_map, inplace=True)

    # Derived metrics
    df["W' Drop (%)"] = (df["W' Drop (J)"] / df["W' Capacity (J)"] * 100).round(2)
    df["TSB (today)"] = (df["CTL (Fitness)"] - df["ATL (Fatigue)"]).round(2)

    # VO2 TiZ (Power) = Power TiZ Z5 (s)
    df["VO2Max Power TiZ (s)"] = df["Power TiZ Z5 (s)"]

    # VO2 TiZ (HR) = HR TiZ Z4..Z7 (s)
    df["VO2Max HR TiZ (s)"] = (
        df["HR TiZ Z4 (s)"]
        + df["HR TiZ Z5 (s)"]
        + df["HR TiZ Z6 (s)"]
        + df["HR TiZ Z7 (s)"]
    )

    # VO2 TiZ Eff (s) = max(VO2 TiZ Power, VO2 TiZ HR)
    df["VO2Max TiZ Eff (s)"] = df[["VO2Max Power TiZ (s)", "VO2Max HR TiZ (s)"]].max(axis=1)

    # Power TiZ Share Z2 (%) = (Z1 + Z2) / (Z1..Z7) * 100
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

    # Long-ride flags (phase-agnostic)
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

    # Clean empty strings/whitespace and coerce to numeric
    df["MMP 300s (W)"] = to_num(df["MMP 300s (W)"])
    df["MMP 1200s (W)"] = to_num(df["MMP 1200s (W)"])
    df["Decoupling (%)"] = to_num(df["Decoupling (%)"])

    # DI (Durability Index) = 1 - (abs(Decoupling %) / 100)
    df["Durability Index (DI)"] = (1 - (df["Decoupling (%)"].abs() / 100)).round(3)

    # Pa:Hr (HR drift) = Decoupling (%)
    df["Pa:Hr (HR drift)"] = (df["Decoupling (%)"]).round(3)

    # FIR = MMP 300s / MMP 1200s
    den = df["MMP 1200s (W)"]
    df["Functional Intensity Ratio (FIR)"] = (df["MMP 300s (W)"] / den.where(den != 0)).round(3)

    # FTP estimated = 0.95 * MMP 1200s
    df["FTP Estimated (W)"] = (0.95 * df["MMP 1200s (W)"]).round(0)

    # VO2/FTP (5'/FTP) = MMP 300s / FTP Estimated
    den = df["FTP Estimated (W)"]
    df["VO2/FTP (MMP 300s (W) / FTP Estimated (W))"] = (
        df["MMP 300s (W)"] / den.where(den != 0)
    ).round(3)

    # Rounding rules (align with activities_actual conventions)
    def round_numeric(col: str, decimals: int, as_int: bool = False) -> None:
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

    # Integer-like metrics
    for col in df.columns:
        if col.endswith("(W)") or col.endswith("(bpm)") or col.endswith("(rpm)") or col.endswith("(J)"):
            round_numeric(col, 0, as_int=True)
    for col in [
        "Load (TSS)",
        "Strain Score",
        "Power Load",
        "HR Load (HRSS)",
        "Calories (kcal)",
        "CTL (Fitness)",
        "ATL (Fatigue)",
        "Power/HR Z2 Time (min)",
    ]:
        round_numeric(col, 0, as_int=True)

    # One-decimal metrics
    for col in [
        "Avg Speed (m/s)",
        "Max Speed (m/s)",
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
    ]:
        round_numeric(col, 1)

    # Two-decimal metrics
    for col in [
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
    ]:
        round_numeric(col, 2)

    # Percent and scale columns with specific precision
    for col in ["Compliance (%)", "Sweet Spot Min (%FTP)", "Sweet Spot Max (%FTP)"]:
        round_numeric(col, 0, as_int=True)
    round_numeric("Session RPE (0-10)", 1)

    # Export
    week_str = f"{int(week):02d}" if week is not None else "00"
    year_str = f"{int(year):04d}" if year is not None else "0000"

    data_dir = athlete_data_dir(ATHLETE_ID)
    latest_dir = athlete_latest_dir(ATHLETE_ID)

    out_file = data_dir / year_str / week_str / f"intervals_data_{from_date}_{to_date}.csv"
    latest_file = latest_dir / "intervals_data_latest.csv"

    out_file.parent.mkdir(parents=True, exist_ok=True)
    latest_dir.mkdir(parents=True, exist_ok=True)

    df.to_csv(
        out_file,
        index=False,
        sep=";",
        quoting=csv.QUOTE_ALL,
        quotechar='"',
        doublequote=True,
        encoding="utf-8-sig",
        lineterminator="\n",
        na_rep="",
    )

    latest_file.write_bytes(out_file.read_bytes())

    print(f"CSV exported: {out_file}")
    logger = logging.getLogger(Path(__file__).stem)
    logger.info("CSV exported path=%s rows=%d", out_file, len(df))


# ======================================================
# Entry point (ISO week OR date range)
# ======================================================

def _parse_ymd(value: str) -> datetime.date:
    """Parse a YYYY-MM-DD string into a date object."""
    return datetime.strptime(value, "%Y-%m-%d").date()


def main() -> int:
    """CLI entry point for the export script."""
    warn_msg = (
        "DEPRECATED: scripts/data_pipeline/intervals_export.py is superseded by "
        "scripts/data_pipeline/get_intervals_data.py. Please migrate to the new script."
    )
    print(warn_msg, file=sys.stderr)
    warnings.warn(warn_msg, DeprecationWarning, stacklevel=2)

    global week, year
    load_env()
    logger = configure_logging(Path(__file__).stem)
    parser = argparse.ArgumentParser(
        description=(
            "Export Intervals.icu data (ISO week OR date range). "
            "If no range is provided, exports the last 24 complete ISO weeks."
        )
    )

    # All flags optional; validate valid combinations below
    parser.add_argument("--year", type=int, help="ISO year for the week, e.g. 2025")
    parser.add_argument("--week", type=int, help="ISO calendar week, e.g. 43")
    parser.add_argument("--from", dest="from_date", type=str, help="Start date YYYY-MM-DD")
    parser.add_argument("--to", dest="to_date", type=str, help="End date YYYY-MM-DD")
    parser.add_argument("--athlete", help="Athlete ID (defaults to ATHLETE_ID from .env).")

    args = parser.parse_args()
    athlete_id = args.athlete or resolve_athlete_id()
    api_key = require_env("API_KEY")
    base_url = require_env("BASE_URL")
    logger.info("Intervals export athlete=%s base_url=%s", athlete_id, base_url)

    global ATHLETE_ID, API_KEY, BASE_URL, AUTH, session
    ATHLETE_ID = athlete_id
    API_KEY = api_key
    BASE_URL = base_url
    AUTH = HTTPBasicAuth("API_KEY", API_KEY)
    session = requests.Session()
    session.auth = AUTH
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

    # Decision logic: either (year & week) OR (from & to)
    has_week = args.year is not None and args.week is not None
    has_range = args.from_date is not None and args.to_date is not None

    if has_week and has_range:
        parser.error("Provide EITHER `--year --week` OR `--from --to`, not both.")

    if has_week:
        week = args.week
        year = args.year
        logger.info("Export week year=%s week=%s", args.year, args.week)
        export_week(args.year, args.week)
        return 0

    if has_range:
        try:
            from_d = _parse_ymd(args.from_date)
            to_d = _parse_ymd(args.to_date)
        except ValueError:
            parser.error("Invalid date format. Expected YYYY-MM-DD, e.g. --from 2025-10-28")

        if from_d > to_d:
            parser.error(f"--from {from_d} is after --to {to_d}.")

        iso_year, iso_week = date_to_iso_week(datetime.combine(to_d, datetime.min.time()))
        week = iso_week
        year = iso_year
        logger.info("Export range from=%s to=%s", from_d, to_d)
        export_range(from_d, to_d)
        return 0

    # Default: last 24 complete ISO weeks ending with the prior Sunday.
    from_d, to_d = resolve_default_range(weeks=24)
    iso_year, iso_week = date_to_iso_week(to_d)
    week = iso_week
    year = iso_year
    logger.info("Export default range from=%s to=%s", from_d, to_d)
    export_range(from_d, to_d)
    return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
