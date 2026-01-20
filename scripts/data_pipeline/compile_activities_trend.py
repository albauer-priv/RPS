#!/usr/bin/env python3
"""Aggregate Intervals.icu exports into weekly activities_trend artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sys
import warnings

import numpy as np
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
# Assumes Intervals.icu CSV exports using semicolon separators and quoted fields.
SEPARATOR = ";"  # Intervals.icu export
QUOTECHAR = '"'
# Used for the back-to-back Z2 definition (minutes per day).
Z2_MIN_THRESHOLD_MIN = 90
# Optional plan targets per ISO week for adherence calculation.
TSS_PLAN_BY_WEEK: dict[tuple[int, int], int] = {}

# Required columns per source-of-truth activities_trend file (order matters).
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

EXPECTED_TREND_KEYS = {
    "year",
    "iso_week",
    "period",
    "weekly_aggregates",
    "intensity_load_metrics",
    "power_tiz",
    "hr_tiz",
    "optional_tiz",
    "distribution_metrics",
    "peak_metrics",
    "flag_counts",
    "flag_any",
    "metrics",
}
EXPECTED_WEEKLY_AGG_KEYS = {
    "activity_count",
    "moving_time",
    "distance_km",
    "load_tss",
    "work_kj",
}
EXPECTED_INTENSITY_KEYS = {
    "normalized_power_w",
    "intensity_factor",
    "decoupling_percent",
    "durability_index",
    "efficiency_factor",
    "functional_intensity_ratio",
    "ftp_estimated_w",
    "vo2_ftp",
}
EXPECTED_TIZ_KEYS = {"z1", "z2", "z3", "z4", "z5", "z6", "z7"}
EXPECTED_OPTIONAL_TIZ_KEYS = {
    "sweet_spot",
    "vo2max_power",
    "vo2max_hr",
    "vo2max_tiz_efficiency",
}
EXPECTED_DISTRIBUTION_KEYS = {
    "adherence_percent",
    "z1_z2_time_percent",
    "z5_time_percent",
    "z2_share_power_percent",
    "back_to_back_z2_days_count",
}
EXPECTED_PEAK_KEYS = {
    "mmp_60s",
    "mmp_180s",
    "mmp_300s",
    "mmp_600s",
    "mmp_1200s",
    "mmp_1800s",
    "mmp_3600s",
    "mmp_5400s",
    "mmp_7200s",
    "mmp_9000s",
    "mmp_10800s",
    "mmp_14400s",
    "mmp_18000s",
    "mmp_21600s",
}
EXPECTED_FLAG_KEYS = set(FLAG_COLUMN_KEYS.values())
EXPECTED_METRICS_KEYS = {
    "tsb_today",
    "weekly_moving_time_total_min",
    "weekly_z2_time_total_min",
    "weekly_z2_share",
    "weekly_moving_time_max_min",
    "weekly_z2_time_max_min",
    "weekly_moving_time_150min_sum_min",
    "weekly_moving_time_180min_sum_min",
    "weekly_moving_time_240min_sum_min",
    "weekly_z2_time_150min_sum_min",
    "weekly_z2_time_180min_sum_min",
    "weekly_z2_time_240min_sum_min",
    "weekly_moving_time_des_base_sum_min",
    "weekly_moving_time_des_build_sum_min",
    "weekly_z2_time_des_base_sum_min",
    "weekly_z2_time_des_build_sum_min",
}


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the trend compiler."""
    parser = argparse.ArgumentParser(
        description="Aggregates an Intervals.icu CSV into an activities trend CSV."
    )
    parser.add_argument("input_csv", help="Path to the input CSV")
    parser.add_argument(
        "--skip-validate",
        action="store_true",
        help="Skip JSON schema validation before writing output",
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


def sum_seconds(series: pd.Series) -> float:
    """Sum seconds from a series, coercing NaN to zero."""
    return pd.to_numeric(series, errors="coerce").fillna(0).sum()


def sum_seconds_to_min_raw(series: pd.Series) -> float:
    """Sum seconds and return minutes as a float."""
    return sum_seconds(series) / 60.0


def sum_seconds_to_hmm(seconds: float) -> str:
    """Convert seconds to H:MM (minutes)."""
    total_minutes = int(round(seconds / 60.0))
    h = total_minutes // 60
    m = total_minutes % 60
    return f"{h:02d}:{m:02d}"


def seconds_to_hms(seconds: float) -> str:
    """Convert seconds to HH:MM:SS string."""
    if pd.isna(seconds):
        return ""
    total_seconds = int(round(seconds))
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def sum_m_to_km_raw(series: pd.Series) -> float:
    """Sum meters and convert to kilometers."""
    return pd.to_numeric(series, errors="coerce").fillna(0).sum() / 1000.0


def sum_j_to_kj_raw(series: pd.Series) -> float:
    """Sum joules and convert to kilojoules."""
    return pd.to_numeric(series, errors="coerce").fillna(0).sum() / 1000.0


def avg(series: pd.Series) -> float:
    """Return the mean of a series or NaN if empty."""
    v = pd.to_numeric(series, errors="coerce").dropna()
    if not len(v):
        return np.nan
    return float(v.mean())


def last(series: pd.Series) -> float:
    """Return the last non-null value in a series or NaN if empty."""
    v = pd.to_numeric(series, errors="coerce").dropna()
    if not len(v):
        return np.nan
    return v.iloc[-1]


def fmt_int(value: float) -> int | str:
    """Format numeric values as integers or empty strings."""
    return "" if pd.isna(value) else int(round(value))


def fmt_dec(value: float, nd: int) -> float | str:
    """Format numeric values with decimals or empty strings."""
    return "" if pd.isna(value) else round(float(value), nd)


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


def normalize_scalar(value):
    """Normalize pandas scalars into native Python values."""
    if pd.isna(value):
        return None
    if isinstance(value, str) and not value.strip():
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def num_or_none(value):
    """Normalize values into floats or None."""
    value = normalize_scalar(value)
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def int_or_none(value):
    """Normalize values into integers or None."""
    value = normalize_scalar(value)
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def duration_hm_from_seconds(seconds: float) -> str | None:
    """Convert seconds to HH:MM (hours:minutes) for trend output."""
    if pd.isna(seconds):
        return None
    return sum_seconds_to_hmm(seconds)


def duration_hms_from_seconds(seconds: float) -> str | None:
    """Convert seconds to HH:MM:SS for trend output."""
    if pd.isna(seconds):
        return None
    return seconds_to_hms(seconds)


def count_back_to_back_z2_days(g_week: pd.DataFrame, z2_col: str | None) -> int | float:
    """Count consecutive calendar days with >= threshold minutes of Z2."""
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


def main() -> int:
    """Compile weekly activities_trend CSV + JSON artifacts."""
    warn_msg = (
        "DEPRECATED: scripts/data_pipeline/compile_activities_trend.py is superseded by "
        "scripts/data_pipeline/get_intervals_data.py. Please migrate to the new script."
    )
    print(warn_msg, file=sys.stderr)
    warnings.warn(warn_msg, DeprecationWarning, stacklevel=2)

    load_env()
    args = parse_args()
    athlete_id = args.athlete or resolve_athlete_id()
    schema_dir = resolve_schema_dir()
    validator = SchemaRegistry(schema_dir).validator_for("activities_trend.schema.json")

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

    # ISO calendar + day stamp
    iso = df[dt_col].dt.isocalendar()
    df["ISO_Year"] = iso.year.astype(int)
    df["ISO_Week"] = iso.week.astype(int)
    df["Day"] = df[dt_col].dt.floor("D")

    # Column mapping (Intervals.icu naming)
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

    # Power zones + sweet spot
    pz_cols = {z: getcol(cols, f"Power TiZ Z{z} (s)") for z in range(1, 8)}
    col_sst_s = getcol(cols, "Sweet Spot TiZ (s)")

    # HR TiZ (optional)
    hr_cols = {z: getcol(cols, f"HR TiZ Z{z} (s)") for z in range(1, 8)}

    # PDC
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

    # VO2Max TiZ Eff (optional)
    col_vo2_eff_s = getcol(cols, "VO2Max TiZ Eff (s)")
    col_vo2_power_s = getcol(cols, "VO2Max Power TiZ (s)")
    col_vo2_hr_s = getcol(cols, "VO2Max HR TiZ (s)")

    # Derived metrics (optional)
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

    # Aggregation
    rows = []
    weekly_trends_json = []
    for (yr, wk), g in df.groupby(["ISO_Year", "ISO_Week"], sort=True):
        # Period (Mon-Sun) from min/max date in group
        start = g[dt_col].min().date()
        end = g[dt_col].max().date()
        period = f"{start}-{end}"

        # Sums/averages (raw)
        move_seconds = sum_seconds(g[col_move_s]) if col_move_s else np.nan
        dist_km_raw = sum_m_to_km_raw(g[col_dist_m]) if col_dist_m else np.nan
        tss_sum_raw = pd.to_numeric(g[col_tss], errors="coerce").fillna(0).sum() if col_tss else np.nan
        kj_sum_raw = sum_j_to_kj_raw(g[col_work_j]) if col_work_j else np.nan
        np_mean_raw = avg(g[col_np]) if col_np else np.nan
        if_mean_raw = avg(g[col_if]) if col_if else np.nan
        dec_mean_raw = avg(g[col_decoup]) if col_decoup else np.nan
        # DI uses decoupling: 1 - (|Pa:Hr| / 100).
        di_val_raw = (1 - abs(dec_mean_raw) / 100.0) if (dec_mean_raw == dec_mean_raw) else np.nan
        ef_mean_raw = avg(g[col_ef]) if col_ef else np.nan
        tsb_last_raw = last(g[col_tsb]) if col_tsb else np.nan
        move_min_series = (
            pd.to_numeric(g[col_move_s], errors="coerce") / 60.0 if col_move_s else pd.Series(dtype="float64")
        )

        # Power zones (seconds) and totals (raw)
        pz_sec_raw = {z: (sum_seconds(g[pz_cols[z]]) if pz_cols[z] else 0.0) for z in range(1, 8)}
        pz_min_raw = {z: (pz_sec_raw[z] / 60.0) for z in range(1, 8)}
        pz_sum = sum(pz_min_raw.values())
        hr_sec_raw = {z: (sum_seconds(g[hr_cols[z]]) if hr_cols[z] else 0.0) for z in range(1, 8)}
        z2_min_series = (
            pd.to_numeric(g[pz_cols[2]], errors="coerce") / 60.0 if pz_cols[2] else pd.Series(dtype="float64")
        )

        # Z2/SST/VO2
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

        # Percentages
        z2_pct_raw = (100.0 * pz_min_raw[2] / pz_sum) if pz_sum > 0 else np.nan
        z1z2_pct_raw = (100.0 * (pz_min_raw[1] + pz_min_raw[2]) / pz_sum) if pz_sum > 0 else np.nan
        z5_pct_raw = (100.0 * pz_min_raw[5] / pz_sum) if pz_sum > 0 else np.nan

        # PDC and FIR
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

        # Adherence (if plan is available)
        adher = None
        if (yr, wk) in TSS_PLAN_BY_WEEK and not pd.isna(tss_sum_raw):
            plan = TSS_PLAN_BY_WEEK[(yr, wk)]
            if plan:
                adher = int(round(100.0 * tss_sum_raw / plan))

        # Back-to-back
        b2b = count_back_to_back_z2_days(g, pz_cols[2])

        # Weekly flag aggregates (counts, any, minutes under flags)
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
            """Sum minutes for rows where a boolean mask column is True."""
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

        # Output row
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
                "distance_km": num_or_none(dist_km_raw),
                "load_tss": num_or_none(tss_sum_raw),
                "work_kj": num_or_none(kj_sum_raw),
            },
            "intensity_load_metrics": {
                "normalized_power_w": num_or_none(np_mean_raw),
                "intensity_factor": num_or_none(if_mean_raw),
                "decoupling_percent": num_or_none(dec_mean_raw),
                "durability_index": num_or_none(di_val_raw),
                "efficiency_factor": num_or_none(ef_mean_raw),
                "functional_intensity_ratio": num_or_none(fir),
                "ftp_estimated_w": num_or_none(ftp_est_mean_raw),
                "vo2_ftp": num_or_none(vo2_ftp_ratio),
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
            "adherence_percent": num_or_none(adher),
            "z1_z2_time_percent": num_or_none(z1z2_pct_raw),
            "z5_time_percent": num_or_none(z5_pct_raw),
            "z2_share_power_percent": num_or_none(z2_pct_raw),
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
            peak_metrics[key] = num_or_none(mmp_out_raw[duration])
        trend_entry["peak_metrics"] = peak_metrics

        trend_entry["flag_counts"] = flag_counts_json
        trend_entry["flag_any"] = flag_any_json

        metrics = {
            "tsb_today": num_or_none(tsb_last_raw),
            "weekly_moving_time_total_min": int_or_none(move_min_total),
            "weekly_z2_time_total_min": int_or_none(z2_min_total),
            "weekly_z2_share": num_or_none(weekly_z2_share_pct),
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

        context_label = f"ISO week {int(yr)}-{wk:02d}"
        ensure_keys("trend_entry", set(trend_entry.keys()), EXPECTED_TREND_KEYS, context_label)
        ensure_keys("weekly_aggregates", set(trend_entry["weekly_aggregates"].keys()), EXPECTED_WEEKLY_AGG_KEYS, context_label)
        ensure_keys(
            "intensity_load_metrics",
            set(trend_entry["intensity_load_metrics"].keys()),
            EXPECTED_INTENSITY_KEYS,
            context_label,
        )
        ensure_keys("power_tiz", set(trend_entry["power_tiz"].keys()), EXPECTED_TIZ_KEYS, context_label)
        ensure_keys("hr_tiz", set(trend_entry["hr_tiz"].keys()), EXPECTED_TIZ_KEYS, context_label)
        ensure_keys("optional_tiz", set(trend_entry["optional_tiz"].keys()), EXPECTED_OPTIONAL_TIZ_KEYS, context_label)
        ensure_keys(
            "distribution_metrics",
            set(trend_entry["distribution_metrics"].keys()),
            EXPECTED_DISTRIBUTION_KEYS,
            context_label,
        )
        ensure_keys("peak_metrics", set(trend_entry["peak_metrics"].keys()), EXPECTED_PEAK_KEYS, context_label)
        ensure_keys("flag_counts", set(trend_entry["flag_counts"].keys()), EXPECTED_FLAG_KEYS, context_label)
        ensure_keys("flag_any", set(trend_entry["flag_any"].keys()), EXPECTED_FLAG_KEYS, context_label)
        ensure_keys("metrics", set(trend_entry["metrics"].keys()), EXPECTED_METRICS_KEYS, context_label)

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

    version_key = f"{year}-{iso_week}"
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
        "trace_upstream": [
            {"artifact": os.path.basename(args.input_csv)}
        ],
    }
    payload = {
        "meta": meta,
        "data": {
            "weekly_trends": weekly_trends_json,
        },
    }
    if not args.skip_validate:
        validate_or_raise(validator, payload)
    with open(out_json_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    record_index_write(
        athlete_id=athlete_id,
        artifact_type="ACTIVITIES_TREND",
        version_key=version_key,
        path=out_json_file,
        run_id=meta["run_id"],
        producer_agent=meta["owner_agent"],
        created_at=meta["created_at"],
        iso_week=meta["iso_week"],
    )

    latest_csv = latest_dir / "activities_trend.csv"
    latest_json = latest_dir / "activities_trend.json"
    latest_csv.write_bytes(out_file.read_bytes())
    latest_json.write_bytes(out_json_file.read_bytes())

    print(f"JSON exported: {out_json_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
