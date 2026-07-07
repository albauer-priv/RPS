#!/usr/bin/env python3
"""Fetch Intervals.icu data and compile activities_actual + activities_trend outputs.

This script is the single data-pipeline entrypoint for activities_* artefacts.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TypedDict, cast

import numpy as np
import pandas as pd
from requests.auth import HTTPBasicAuth

from rps.data_pipeline.common import (
    athlete_data_dir,
    athlete_latest_dir,
    athlete_root,
    configure_logging,
    load_env,
    parse_iso_week,
    record_index_write,
    require_env,
    resolve_athlete_id,
    resolve_schema_dir,
)
from rps.data_pipeline.intervals_activities_actual import compile_activities_actual
from rps.data_pipeline.intervals_api_client import (
    session,
)
from rps.data_pipeline.intervals_date_utils import (
    DEFAULT_WEEKS,
    date_to_iso_week,
    iso_week_to_dates,
    parse_args,
    parse_ymd,
    resolve_default_range,
)
from rps.data_pipeline.intervals_export import export_range
from rps.data_pipeline.intervals_formatting import (
    getcol,
    seconds_to_hms,
    standardize_activity_columns,
)
from rps.data_pipeline.intervals_historical_baseline import compile_historical_baseline
from rps.data_pipeline.intervals_json_formatters import (
    normalize_scalar,
    write_parquet_cache,
)
from rps.data_pipeline.intervals_schema_utils import (
    _canonicalize_pipeline_payload,
    _confidence_from_columns,
)
from rps.data_pipeline.intervals_wellness import write_wellness
from rps.data_pipeline.intervals_zone_model import write_zone_model
from rps.workspace.schema_registry import SchemaRegistry, SchemaValidationError, validate_or_raise
from rps.workspace.types import ArtifactType

# === Export configuration ===
SEPARATOR = ";"  # Intervals.icu export
QUOTECHAR = '"'
Z2_MIN_THRESHOLD_MIN = 90
PERCENT_SCALE_THRESHOLD = 1.5
PERCENT_INTEGER_EPSILON = 1e-6
POWER_ZONE_COUNT = 7
MIN_CONSECUTIVE_Z2_DAYS = 2
LONG_RIDE_BASE_MINUTES = 150
LONG_RIDE_BUILD_MINUTES = 180
LONG_RIDE_BREVET_MINUTES = 240
LOW_INTENSITY_FACTOR_THRESHOLD = 0.75
ENDURANCE_INTENSITY_FACTOR_THRESHOLD = 0.80
Z2_SHARE_BASE_THRESHOLD_PCT = 60
Z2_SHARE_BREVET_THRESHOLD_PCT = 70
DRIFT_VALID_Z2_MINUTES = 90
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


def load_kj_plan_by_week(athlete_id: str) -> dict[tuple[int, int], float]:
    """Load planned weekly kJ from week_plan artefacts when available."""
    plan_map: dict[tuple[int, int], float] = {}
    base = athlete_root(athlete_id)
    candidate_dirs = [base / "data" / "plans" / "week", base / "plans" / "week"]
    for plan_dir in candidate_dirs:
        if not plan_dir.exists():
            continue
        for path in sorted(plan_dir.glob("week_plan_*.json")):
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            meta = doc.get("meta", {})
            iso_week = meta.get("iso_week") or path.stem.replace("week_plan_", "")
            parsed = parse_iso_week(iso_week)
            if not parsed:
                continue
            data = doc.get("data", {})
            week_summary = data.get("week_summary", {})
            planned = week_summary.get("planned_weekly_load_kj")
            if planned is None:
                planned = sum(
                    float(day.get("planned_kj") or 0)
                    for day in data.get("agenda", [])
                    if isinstance(day, dict)
                )
            if planned is None:
                continue
            plan_map[(parsed["year"], parsed["week"])] = float(planned)
    return plan_map


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


class IndexMeta(TypedDict):
    run_id: str
    owner_agent: str
    created_at: str | None
    iso_week: str | None
    iso_week_range: str | None


def _power_zone_share_percent(zone_seconds: dict[int, float], *, include_zones: Iterable[int]) -> float:
    """Return the percentage share of selected power zones across Z1..Z7.

    Args:
        zone_seconds: Mapping of zone index -> seconds for zones 1..7.
        include_zones: Zones to include in the numerator.

    Returns:
        Percentage value in the range 0..100 when total zone time is positive,
        otherwise NaN.
    """
    def _clean(value: float | int | None) -> float:
        if value is None:
            return 0.0
        try:
            numeric = float(value)
        except Exception:
            return 0.0
        return 0.0 if math.isnan(numeric) else numeric

    total_seconds = sum(_clean(zone_seconds.get(zone, 0.0)) for zone in range(1, POWER_ZONE_COUNT + 1))
    if total_seconds <= 0:
        return np.nan
    numerator_seconds = sum(_clean(zone_seconds.get(zone, 0.0)) for zone in include_zones)
    return 100.0 * numerator_seconds / total_seconds



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
        fallback_day = datetime.now(UTC).date()
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
        total_minutes = round(seconds / 60.0)
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
        return "" if pd.isna(value) else round(value)

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
        if len(z2_days) < MIN_CONSECUTIVE_Z2_DAYS:
            return 0
        count = 0
        for d1, d2 in zip(z2_days, z2_days[1:], strict=False):
            if (d2 - d1).days == 1:
                count += 1
        return int(count)

    kj_plan_by_week = load_kj_plan_by_week(athlete_id)
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
        vo2_p_sec_raw = sum_seconds(g[col_vo2_power_s]) if col_vo2_power_s else pz_sec_raw[5]
        if col_vo2_hr_s:
            vo2_hr_sec_raw = sum_seconds(g[col_vo2_hr_s])
        else:
            hr_seconds = 0.0
            for z in range(4, 8):
                c = hr_cols[z]
                if c is not None:
                    hr_seconds += sum_seconds(g[c])
            vo2_hr_sec_raw = hr_seconds if hr_seconds > 0 else 0.0
        vo2_eff_sec_raw = max(vo2_p_sec_raw, vo2_hr_sec_raw)

        z2_pct_raw = _power_zone_share_percent(pz_sec_raw, include_zones=(2,))
        z1z2_pct_raw = _power_zone_share_percent(pz_sec_raw, include_zones=(1, 2))
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
        if (yr, wk) in kj_plan_by_week and not pd.isna(kj_sum_raw):
            plan = kj_plan_by_week[(yr, wk)]
            if plan:
                adher = round(100.0 * kj_sum_raw / plan)

        b2b = count_back_to_back_z2_days(g, pz_cols[2])

        weekly_flag_counts = {}
        weekly_flag_any = {}
        flag_counts_json = {}
        flag_any_json = {}
        for c, key in FLAG_COLUMN_KEYS.items():
            if c in flag_columns_present:
                if c == "Flag IF <= 0.75 (bool)" and col_if:
                    mask = (
                        pd.to_numeric(g[col_if], errors="coerce").round(3)
                        <= LOW_INTENSITY_FACTOR_THRESHOLD
                    )
                elif c == "Flag IF <= 0.80 (bool)" and col_if:
                    mask = (
                        pd.to_numeric(g[col_if], errors="coerce").round(3)
                        <= ENDURANCE_INTENSITY_FACTOR_THRESHOLD
                    )
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

        def sum_minutes_where(
            week_frame: pd.DataFrame, mask_col: str, minutes_series: pd.Series
        ) -> float:
            if mask_col not in week_frame.columns or len(minutes_series) == 0:
                return np.nan
            mask = week_frame[mask_col].fillna(False).astype(bool)
            return float(minutes_series.where(mask, 0).sum())

        move_min_150plus = sum_minutes_where(g, "Flag Long Ride >=150min (bool)", move_min_series)
        move_min_180plus = sum_minutes_where(g, "Flag Long Ride >=180min (bool)", move_min_series)
        move_min_240plus = sum_minutes_where(g, "Flag Long Ride >=240min (bool)", move_min_series)
        move_min_des_long_base = sum_minutes_where(
            g, "Flag DES Long Base Candidate (bool)", move_min_series
        )
        move_min_des_long_build = sum_minutes_where(
            g, "Flag DES Long Build Candidate (bool)", move_min_series
        )
        z2_min_des_long_base = sum_minutes_where(
            g, "Flag DES Long Base Candidate (bool)", z2_min_series
        )
        z2_min_des_long_build = sum_minutes_where(
            g, "Flag DES Long Build Candidate (bool)", z2_min_series
        )
        z2_min_150plus = sum_minutes_where(g, "Flag Long Ride >=150min (bool)", z2_min_series)
        z2_min_180plus = sum_minutes_where(g, "Flag Long Ride >=180min (bool)", z2_min_series)
        z2_min_240plus = sum_minutes_where(g, "Flag Long Ride >=240min (bool)", z2_min_series)

        row = {
            "Year": int(yr),
            "ISO Week": int(wk),
            "Period": period,
            "# Activities": len(g),
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
                "activity_count": len(g),
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

    run_ts = datetime.now(UTC)
    run_stamp = run_ts.strftime("%Y%m%d-%H%M%S")

    latest = out[["Year", "ISO Week"]].sort_values(["Year", "ISO Week"]).iloc[-1]
    year = int(latest["Year"])
    week = int(latest["ISO Week"])
    iso_week = f"{week:02d}"

    data_dir = athlete_data_dir(athlete_id)
    latest_dir = athlete_latest_dir(athlete_id)

    logger = logging.getLogger(__name__)
    out_file = data_dir / f"{year:04d}" / iso_week / f"activities_trend_{year}-{iso_week}.csv"
    out_json_file = out_file.with_suffix(".json")
    out_parquet_file = out_file.with_suffix(".parquet")
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
    write_parquet_cache(out, out_parquet_file, logger)

    schema_dir = resolve_schema_dir()
    validator = SchemaRegistry(schema_dir).validator_for("activities_trend.schema.json")

    confidence_cols_trend = [
        "# Activities",
        "Moving Time (h:mm)",
        "Work (kJ)",
        "Load (TSS)",
        "Intensity Factor (IF)",
    ]
    data_confidence = _confidence_from_columns(out, confidence_cols_trend)

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
        "data_confidence": data_confidence,
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
    payload = _canonicalize_pipeline_payload(
        schema_dir=schema_dir,
        schema_file="activities_trend.schema.json",
        artifact_type=ArtifactType.ACTIVITIES_TREND,
        payload=payload,
    )[1]

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
    if out_parquet_file.exists():
        latest_parquet = latest_dir / "activities_trend.parquet"
        latest_parquet.write_bytes(out_parquet_file.read_bytes())

    index_meta = cast(IndexMeta, meta)
    record_index_write(
        athlete_id=athlete_id,
        artifact_type="ACTIVITIES_TREND",
        version_key=version_key,
        path=out_json_file,
        run_id=index_meta["run_id"],
        producer_agent=index_meta["owner_agent"],
        created_at=index_meta["created_at"],
        iso_week=index_meta["iso_week"],
        iso_week_range=index_meta["iso_week_range"],
    )

    print(f"JSON exported: {out_json_file}")


def run_pipeline(args: argparse.Namespace, logger: logging.Logger | None = None) -> int:
    """Run the end-to-end Intervals.icu pipeline."""
    load_env()
    if logger is None:
        logger = configure_logging(Path(__file__).stem)
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
        except ValueError as err:
            raise SystemExit("Invalid date format. Expected YYYY-MM-DD, e.g. --from 2025-10-28") from err
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

    print("[5/6] Compiling activities_trend...")
    logger.info("Stage 5: activities_trend")
    compile_activities_trend(
        athlete_id=athlete_id,
        input_csv=export_csv,
        skip_validate=args.skip_validate,
    )

    print("[6/6] Compiling historical baseline...")
    logger.info("Stage 6: historical_baseline years=%s", args.historical_years)
    compile_historical_baseline(
        athlete_id=athlete_id,
        base_url=base_url,
        historical_years=args.historical_years,
        skip_validate=args.skip_validate,
    )

    logger.info("Pipeline complete latest_dir=%s", latest_dir)
    return 0


def main() -> int:
    args = parse_args()
    return run_pipeline(args)


if __name__ == "__main__":
    raise SystemExit(main())
