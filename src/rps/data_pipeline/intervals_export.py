"""Export DataFrame building and CSV writing for Intervals.icu activities."""

from __future__ import annotations

import csv
from datetime import date
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd

from rps.data_pipeline.common import (
    athlete_data_dir,
    athlete_latest_dir,
)
from rps.data_pipeline.intervals_api_client import (
    get_activities,
    get_activity_detail,
    get_power_curves_csv,
)
from rps.data_pipeline.intervals_date_utils import (
    date_to_iso_week,
)
from rps.data_pipeline.intervals_formatting import (
    apply_rounding_policy,
    build_export_rename_map,
)

SEPARATOR = ";"
QUOTECHAR = '"'
LONG_RIDE_BASE_MINUTES = 150
LONG_RIDE_BUILD_MINUTES = 180
LONG_RIDE_BREVET_MINUTES = 240
LOW_INTENSITY_FACTOR_THRESHOLD = 0.75
ENDURANCE_INTENSITY_FACTOR_THRESHOLD = 0.80
Z2_SHARE_BASE_THRESHOLD_PCT = 60
Z2_SHARE_BREVET_THRESHOLD_PCT = 70
DRIFT_VALID_Z2_MINUTES = 90

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


def build_export_dataframe(
    *,
    athlete_id: str,
    base_url: str,
    from_date: date,
    to_date: date,
) -> pd.DataFrame:
    """Return the normalized Intervals export dataframe for a date range."""
    activities = get_activities(athlete_id, base_url, from_date, to_date)
    activities = [a for a in activities if a.get("type") in {"Ride", "VirtualRide"}]
    if not activities:
        return pd.DataFrame()

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
        if not isinstance(aid, (str, int)):
            continue
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
    df["Power TiZ Share Z2 (%)"] = ((df["Power TiZ Z2 (s)"] / pz_total.where(pz_total != 0)) * 100.0).round(1)

    move_min = df["Moving Time (s)"] / 60.0
    z2_min = df["Power TiZ Z2 (s)"] / 60.0
    z2_share = df["Power TiZ Share Z2 (%)"]
    if_val = df["Intensity Factor (IF)"]

    df["Flag Long Ride >=150min (bool)"] = move_min >= LONG_RIDE_BASE_MINUTES
    df["Flag Long Ride >=180min (bool)"] = move_min >= LONG_RIDE_BUILD_MINUTES
    df["Flag Long Ride >=240min (bool)"] = move_min >= LONG_RIDE_BREVET_MINUTES
    df["Flag IF <= 0.75 (bool)"] = if_val <= LOW_INTENSITY_FACTOR_THRESHOLD
    df["Flag IF <= 0.80 (bool)"] = if_val <= ENDURANCE_INTENSITY_FACTOR_THRESHOLD
    df["Flag Z2 Share >= 60% (bool)"] = z2_share >= Z2_SHARE_BASE_THRESHOLD_PCT
    df["Flag Z2 Share >= 70% (bool)"] = z2_share >= Z2_SHARE_BREVET_THRESHOLD_PCT
    df["Flag Drift Valid (Z2 >= 90min) (bool)"] = z2_min >= DRIFT_VALID_Z2_MINUTES
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

    return df


def export_range(
    *,
    athlete_id: str,
    base_url: str,
    from_date: date,
    to_date: date,
) -> Path:
    """Export activities for a date range and write CSV outputs."""
    print(f"Range: {from_date} to {to_date}")

    df = build_export_dataframe(
        athlete_id=athlete_id,
        base_url=base_url,
        from_date=from_date,
        to_date=to_date,
    )
    if df.empty:
        raise ValueError("No Ride or VirtualRide activities found for the requested range.")

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
