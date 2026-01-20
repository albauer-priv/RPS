#!/usr/bin/env python3
"""Compile per-week activities_actual artifacts from Intervals.icu exports."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
import sys
import warnings

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    # Allow running the script directly without installing the package.
    sys.path.insert(0, str(ROOT))

from scripts.data_pipeline.common import (
    athlete_data_dir,
    athlete_latest_dir,
    load_env,
    record_index_write,
    resolve_athlete_id,
    resolve_schema_dir,
)

from app.workspace.schema_registry import SchemaRegistry, validate_or_raise

# === Configuration ===
SEPARATOR = ";"  # Intervals.icu export
QUOTECHAR = '"'


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the activities_actual compiler."""
    parser = argparse.ArgumentParser(
        description="Export per-ISO-week activities CSVs from an Intervals.icu export."
    )
    parser.add_argument("input_csv", help="Path to the input CSV")
    parser.add_argument(
        "--skip-validate",
        action="store_true",
        help="Skip JSON schema validation before writing output",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Only export the newest ISO week found in the input",
    )
    parser.add_argument("--athlete", help="Athlete ID (defaults to ATHLETE_ID from .env).")
    return parser.parse_args()


def getcol(columns: dict[str, str], *candidates: str) -> str | None:
    """Return the first matching column name for candidate headers."""
    for name in candidates:
        key = name.lower()
        if key in columns:
            return columns[key]
    return None


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


def main() -> int:
    """Compile per-week activities_actual CSV + JSON artifacts."""
    warn_msg = (
        "DEPRECATED: scripts/data_pipeline/compile_activities_actual.py is superseded by "
        "scripts/data_pipeline/get_intervals_data.py. Please migrate to the new script."
    )
    print(warn_msg, file=sys.stderr)
    warnings.warn(warn_msg, DeprecationWarning, stacklevel=2)

    load_env()
    args = parse_args()
    athlete_id = args.athlete or resolve_athlete_id()
    schema_dir = resolve_schema_dir()
    validator = SchemaRegistry(schema_dir).validator_for("activities_actual.schema.json")

    # === Load data ===
    df = pd.read_csv(args.input_csv, sep=SEPARATOR, quotechar=QUOTECHAR)

    # Helper: find columns robustly (case-insensitive)
    cols = {c.lower(): c for c in df.columns}

    # Required: date/time
    dt_col = getcol(cols, "Start Time (Local)", "Start Date", "Date")
    if dt_col is None:
        raise ValueError("No date column found (e.g. 'Start Time (Local)').")
    df[dt_col] = pd.to_datetime(df[dt_col], errors="coerce")
    df = df.dropna(subset=[dt_col]).copy()

    # ISO calendar fields
    iso = df[dt_col].dt.isocalendar()
    df["ISO Year"] = iso.year.astype(int)
    df["ISO Week"] = iso.week.astype(int)
    df["Day"] = df[dt_col].dt.floor("D")
    df["Day of Week"] = df[dt_col].dt.dayofweek.map(
        {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
    )

    # === Unit conversions and formatting (match trend export) ===
    name_map: dict[str, str] = {}

    def replace_col(old: str, new: str, series: pd.Series) -> None:
        """Replace a column with a new name and values."""
        df[new] = series
        name_map[old] = new
        if old != new:
            df.drop(columns=[old], inplace=True)

    activity_id_col = getcol(cols, "Activity ID", "ID")
    if activity_id_col and activity_id_col != "Activity ID":
        replace_col(activity_id_col, "Activity ID", df[activity_id_col])

    if dt_col != "Start Time (Local)":
        replace_col(dt_col, "Start Time (Local)", df[dt_col])
        dt_col = "Start Time (Local)"

    # Convert all duration columns from seconds to hh:mm:ss strings.
    for col in [c for c in df.columns if c.endswith(" (s)")]:
        new_col = col.replace(" (s)", " (hh:mm:ss)")
        vals = pd.to_numeric(df[col], errors="coerce")
        replace_col(col, new_col, vals.map(seconds_to_hms))

    # Distance meters -> km (1 decimal)
    if "Distance (m)" in df.columns:
        vals = pd.to_numeric(df["Distance (m)"], errors="coerce") / 1000.0
        replace_col("Distance (m)", "Distance (km)", vals.round(1))

    # Joules -> kJ (all energy columns)
    for col in [c for c in df.columns if c.endswith(" (J)")]:
        vals = pd.to_numeric(df[col], errors="coerce") / 1000.0
        replace_col(col, col.replace(" (J)", " (kJ)"), vals.round(0))

    # Speed m/s -> km/h (1 decimal)
    for col in ["Avg Speed (m/s)", "Max Speed (m/s)"]:
        if col in df.columns:
            vals = pd.to_numeric(df[col], errors="coerce") * 3.6
            replace_col(col, col.replace("(m/s)", "(km/h)"), vals.round(1))

    # === Rounding rules (align with trend export conventions) ===
    for col in df.columns:
        if col.endswith("(W)") or col.endswith("(bpm)") or col.endswith("(rpm)") or col.endswith("(kJ)"):
            round_numeric(df, col, 0, as_int=True)
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
        round_numeric(df, col, 0, as_int=True)

    # One-decimal metrics
    for col in [
        "Distance (km)",
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
    ]:
        round_numeric(df, col, 1)

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
        round_numeric(df, col, 2)

    # Percent and scale columns with specific precision
    for col in ["Compliance (%)", "Sweet Spot Min (%FTP)", "Sweet Spot Max (%FTP)"]:
        round_numeric(df, col, 0, as_int=True)
    round_numeric(df, "Session RPE (0-10)", 1)

    # Columns that must appear first in the export (if present)
    preferred_order = [
        "Activity ID",
        "Name",
        "Type",
        "Start Time (Local)",
        "Moving Time (hh:mm:ss)",
        "Elapsed Time (hh:mm:ss)",
        "Recording Time (hh:mm:ss)",
        "Coasting Time (hh:mm:ss)",
        "Distance (km)",
        "Avg Power (W)",
        "NP (W)",
        "Load (TSS)",
        "Strain Score",
        "Avg HR (bpm)",
        "Max HR (bpm)",
        "Avg Cadence (rpm)",
        "Peak Power (W)",
    ]
    preferred_cols = [name_map.get(c, c) for c in preferred_order if name_map.get(c, c) in df.columns]

    # Keep ISO fields at the start, then preferred columns, then append remaining columns.
    excluded = set(preferred_cols + ["ISO Year", "ISO Week", "ISO_Year", "ISO_Week", "Day", "Day of Week"])
    remaining_cols = [c for c in df.columns if c not in excluded]
    output_cols = ["ISO Year", "ISO Week", "Day", "Day of Week"] + preferred_cols + remaining_cols

    # Required columns per source-of-truth activities_actual file.
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

    if required_columns:
        # Ensure all required columns exist; fill missing ones with empty values.
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

    # Export one CSV per ISO week without aggregation.
    groups = list(df.groupby(["ISO Year", "ISO Week"], sort=True))
    if args.latest and groups:
        groups = [groups[-1]]

    run_ts = datetime.now(timezone.utc)
    run_stamp = run_ts.strftime("%Y%m%d-%H%M%S")

    data_dir = athlete_data_dir(athlete_id)
    latest_dir = athlete_latest_dir(athlete_id)

    last_out_file: Path | None = None
    last_json_file: Path | None = None

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
        last_out_file = out_file
        last_json_file = out_json_file

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
            "trace_upstream": [
                {"artifact": os.path.basename(args.input_csv)}
            ],
        }
        payload = {
            "meta": meta,
            "data": {
                "activities": activities
            },
        }
    if not args.skip_validate:
        validate_or_raise(validator, payload)
        with open(out_json_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

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

    if last_out_file and last_json_file:
        latest_dir.mkdir(parents=True, exist_ok=True)
        latest_csv = latest_dir / "activities_actual.csv"
        latest_json = latest_dir / "activities_actual.json"
        latest_csv.write_bytes(last_out_file.read_bytes())
        latest_json.write_bytes(last_json_file.read_bytes())

        print(f"JSON exported: {last_json_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
