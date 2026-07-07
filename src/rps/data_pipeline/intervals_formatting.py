"""Column formatting, unit conversion, and rounding policy for Intervals.icu export data."""

from __future__ import annotations

import pandas as pd

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


def seconds_to_hms(seconds: float | int | None) -> str:
    """Format seconds as HH:MM:SS, returning empty for missing values."""
    if pd.isna(seconds):
        return ""
    if seconds is None:
        return ""
    total_seconds = round(float(seconds))
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
