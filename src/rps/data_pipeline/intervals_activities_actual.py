"""Activities-actual weekly schema transformation and artefact writing for Intervals.icu data."""

from __future__ import annotations

import csv
import json
import logging
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, TypedDict, cast

import pandas as pd
from requests.auth import HTTPBasicAuth

from rps.data_pipeline.common import (
    athlete_data_dir,
    athlete_latest_dir,
    load_env,
    record_index_write,
    require_env,
    resolve_schema_dir,
)
from rps.data_pipeline.intervals_api_client import (
    session,
)
from rps.data_pipeline.intervals_export import build_export_dataframe
from rps.data_pipeline.intervals_formatting import (
    apply_rounding_policy,
    apply_unit_conversions,
    standardize_activity_columns,
)
from rps.data_pipeline.intervals_json_formatters import (
    ensure_keys,
    format_date,
    format_datetime,
    format_duration_hms,
    format_int,
    format_number,
    format_string,
    normalize_bool,
    normalize_key,
    normalize_scalar,
    unique_key,
    write_parquet_cache,
)
from rps.data_pipeline.intervals_schema_utils import (
    _canonicalize_pipeline_payload,
    _confidence_from_columns,
)
from rps.workspace.schema_registry import SchemaRegistry, SchemaValidationError, validate_or_raise
from rps.workspace.types import ArtifactType

SEPARATOR = ";"
QUOTECHAR = '"'


class IndexMeta(TypedDict):
    run_id: str
    owner_agent: str
    created_at: str | None
    iso_week: str | None
    iso_week_range: str | None

def build_activities_actual_payloads_from_export_frame(
    export_df: pd.DataFrame,
    *,
    source_artifact_name: str,
    skip_validate: bool,
    run_ts: datetime | None = None,
    run_id_prefix: str = "data-pipeline",
) -> list[tuple[str, pd.DataFrame, dict[str, Any]]]:
    """Return week-scoped `ACTIVITIES_ACTUAL` payloads from an exported Intervals dataframe."""

    if export_df.empty:
        return []
    df = export_df.copy()
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
        return []
    run_ts = run_ts or datetime.now(UTC)
    run_stamp = run_ts.strftime("%Y%m%d-%H%M%S")

    schema_dir = resolve_schema_dir()
    validator = SchemaRegistry(schema_dir).validator_for("activities_actual.schema.json")
    results: list[tuple[str, pd.DataFrame, dict[str, Any]]] = []
    for (yr, wk), g in groups:
        g = g.sort_values(dt_col)
        out_df = g[output_cols]

        iso_week = f"{int(wk):02d}"
        required_columns_set = set(required_field_map.values())
        metric_columns = [c for c in out_df.columns if c not in required_columns_set and c not in flag_columns]

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
                    f"Missing required values for {', '.join(missing_fields)} in ISO week {int(yr)}-{iso_week}."
                )

            flags = {flag_key_map[col]: normalize_bool(row.get(col)) for col in flag_columns}
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

        confidence_cols_actual = [
            required_field_map["activity_id"],
            required_field_map["moving_time"],
            required_field_map["distance_km"],
            required_field_map["work_kj"],
            required_field_map["load_tss"],
            required_field_map["normalized_power_w"],
            required_field_map["intensity_factor"],
        ]
        data_confidence = _confidence_from_columns(out_df, confidence_cols_actual)
        version_key = f"{int(yr)}-{iso_week}"
        meta = {
            "artifact_type": "ACTIVITIES_ACTUAL",
            "schema_id": "ActivitiesActualInterface",
            "schema_version": "1.0",
            "version": "1.0",
            "authority": "Binding",
            "owner_agent": "Data-Pipeline",
            "run_id": f"{run_stamp}-{run_id_prefix}-{int(yr)}{iso_week}",
            "created_at": run_ts.isoformat(),
            "data_confidence": data_confidence,
            "iso_week": version_key,
            "iso_week_range": f"{version_key}--{version_key}",
            "temporal_scope": {
                "from": format_date(g["Day"].min()),
                "to": format_date(g["Day"].max()),
            },
            "scope": "Shared",
            "trace_upstream": [
                {
                    "artifact": source_artifact_name,
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
        payload = _canonicalize_pipeline_payload(
            schema_dir=schema_dir,
            schema_file="activities_actual.schema.json",
            artifact_type=ArtifactType.ACTIVITIES_ACTUAL,
            payload=payload,
        )[1]
        if not skip_validate:
            try:
                validate_or_raise(validator, payload)
            except SchemaValidationError as exc:
                print("Schema validation failed for ACTIVITIES_ACTUAL:")
                for err in exc.errors:
                    print(f"- {err}")
                raise
        results.append((version_key, out_df, payload))

    return results


def fetch_current_week_activities_actual_payload(
    *,
    athlete_id: str,
    year: int,
    week: int,
    today: date | None = None,
) -> dict[str, Any] | None:
    """Fetch the current ISO week directly from Intervals.icu and return an in-memory payload."""

    today = today or date.today()
    week_start = date.fromisocalendar(year, week, 1)
    week_end = date.fromisocalendar(year, week, 7)
    if today < week_start:
        return None

    load_env()
    api_key = require_env("API_KEY")
    base_url = require_env("BASE_URL")
    session.auth = HTTPBasicAuth("API_KEY", api_key)
    effective_end = min(today, week_end)
    export_df = build_export_dataframe(
        athlete_id=athlete_id,
        base_url=base_url,
        from_date=week_start,
        to_date=effective_end,
    )
    payloads = build_activities_actual_payloads_from_export_frame(
        export_df,
        source_artifact_name=f"intervals_icu_current_week_{week_start.isoformat()}_{effective_end.isoformat()}.csv",
        skip_validate=True,
        run_id_prefix="current-week-status",
    )
    target_key = f"{year:04d}-{week:02d}"
    for version_key, _, payload in payloads:
        if version_key == target_key:
            return payload
    return None


def compile_activities_actual(
    *,
    athlete_id: str,
    input_csv: Path,
    skip_validate: bool,
) -> None:
    """Compile activities_actual JSON for the latest ISO week in the export."""
    df = pd.read_csv(input_csv, sep=SEPARATOR, quotechar=QUOTECHAR)
    payloads = build_activities_actual_payloads_from_export_frame(
        df,
        source_artifact_name=input_csv.name,
        skip_validate=skip_validate,
    )
    if not payloads:
        raise ValueError("No rows available for activities_actual export.")
    data_dir = athlete_data_dir(athlete_id)
    latest_dir = athlete_latest_dir(athlete_id)

    logger = logging.getLogger(__name__)
    last_out_file: Path | None = None
    last_out_json_file: Path | None = None
    last_out_parquet_file: Path | None = None
    for version_key, out_df, payload in payloads:
        yr_str, iso_week = version_key.split("-", 1)
        yr = int(yr_str)
        out_file = data_dir / f"{int(yr):04d}" / iso_week / f"activities_actual_{int(yr)}-{iso_week}.csv"
        out_json_file = out_file.with_suffix(".json")
        out_parquet_file = out_file.with_suffix(".parquet")
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
        write_parquet_cache(out_df, out_parquet_file, logger)

        with open(out_json_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        last_out_file = out_file
        last_out_json_file = out_json_file
        last_out_parquet_file = out_parquet_file

        index_meta = cast(IndexMeta, payload["meta"])
        record_index_write(
            athlete_id=athlete_id,
            artifact_type="ACTIVITIES_ACTUAL",
            version_key=version_key,
            path=out_json_file,
            run_id=index_meta["run_id"],
            producer_agent=index_meta["owner_agent"],
            created_at=index_meta["created_at"],
            iso_week=index_meta["iso_week"],
        )

        print(f"JSON exported: {out_json_file}")

    if last_out_file and last_out_json_file:
        latest_dir.mkdir(parents=True, exist_ok=True)
        latest_csv = latest_dir / "activities_actual.csv"
        latest_json = latest_dir / "activities_actual.json"
        latest_csv.write_bytes(last_out_file.read_bytes())
        latest_json.write_bytes(last_out_json_file.read_bytes())
        if last_out_parquet_file and last_out_parquet_file.exists():
            latest_parquet = latest_dir / "activities_actual.parquet"
            latest_parquet.write_bytes(last_out_parquet_file.read_bytes())
