"""Athlete profile parsing and Intervals.icu zone-model construction."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import TypedDict

import pandas as pd
import requests

from rps.data_pipeline.common import (
    record_index_write,
    resolve_schema_dir,
)
from rps.data_pipeline.intervals_api_client import (
    get_athlete,
    get_wellness,
)
from rps.data_pipeline.intervals_date_utils import (
    date_to_iso_week,
    last_iso_week,
)
from rps.data_pipeline.intervals_schema_utils import _canonicalize_pipeline_payload
from rps.workspace.schema_registry import SchemaValidationError, validate_or_raise
from rps.workspace.types import ArtifactType

PERCENT_SCALE_THRESHOLD = 1.5
PERCENT_INTEGER_EPSILON = 1e-6
POWER_ZONE_COUNT = 7
DEFAULT_POWER_ZONE_BOUNDS_PCT = [55, 75, 90, 105, 120, 150, 200]
DEFAULT_SWEET_SPOT_RANGE_PCT = (84, 97)


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


class ZoneModelDefault(TypedDict):
    name: str
    typical_if: float | None
    training_intent: str


class IndexMeta(TypedDict):
    run_id: str
    owner_agent: str
    created_at: str | None
    iso_week: str | None
    iso_week_range: str | None


ZONE_MODEL_DEFAULTS: dict[str, ZoneModelDefault] = {
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


def _as_percent(value: float | int | None) -> float | None:
    if value is None:
        return None
    if value <= PERCENT_SCALE_THRESHOLD:
        return float(value) * 100.0
    return float(value)


def _round_pct(value: float) -> float | int:
    if abs(value - round(value)) < PERCENT_INTEGER_EPSILON:
        return round(value)
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
        if (
            isinstance(weight, (int, float))
            and weight > 0
            and isinstance(day, str)
            and (latest_date is None or day > latest_date)
        ):
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
        bounds = [
            pct
            for val in raw
            if isinstance(val, (int, float))
            for pct in [_as_percent(val)]
            if pct is not None
        ]
        return bounds or None
    return None


def _build_zone_ranges(bounds: list[float]) -> dict[str, tuple[float, float]]:
    if len(bounds) < POWER_ZONE_COUNT:
        bounds = [float(bound) for bound in DEFAULT_POWER_ZONE_BOUNDS_PCT]
    bounds = [float(b) for b in bounds[:POWER_ZONE_COUNT]]
    ranges: dict[str, tuple[float, float]] = {}
    prev = 0.0
    for zone_id, max_pct in zip(["Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7"], bounds, strict=True):
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
    filename = f"zone_model_power_{round(ftp_watts)}W_{valid_from}"

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
                    "min": round(ftp_watts * (min_pct / 100.0)),
                    "max": round(ftp_watts * (max_pct / 100.0)),
                },
                "typical_if": zone_def["typical_if"],
                "training_intent": zone_def["training_intent"],
            }
        )

    return {
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
            "data_confidence": "HIGH",
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
                "ftp_watts": round(ftp_watts),
                "purpose": "Power zone model derived from Intervals.icu sport settings.",
                "filename": filename,
            },
            "zones": zones,
            "examples": [],
            "versioning_usage": [
                "Use this zone model for IF calculations and workout encoding.",
                "Update when FTP changes materially or sportSettings are recalibrated.",
            ],
        },
    }


def write_zone_model(
    *,
    athlete_id: str,
    base_url: str,
    latest_dir: Path,
    skip_validate: bool,
) -> None:
    run_ts = datetime.now(UTC)
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
    validator, payload = _canonicalize_pipeline_payload(
        schema_dir=schema_dir,
        schema_file="zone_model.schema.json",
        artifact_type=ArtifactType.ZONE_MODEL,
        payload=payload,
    )
    if not skip_validate:
        try:
            validate_or_raise(validator, payload)
        except SchemaValidationError as exc:
            print("Schema validation failed for ZONE_MODEL:")
            for err in exc.errors:
                print(f"- {err}")
            raise

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
