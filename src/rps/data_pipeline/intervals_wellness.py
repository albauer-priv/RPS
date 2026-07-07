"""Intervals.icu wellness data fetching and artefact writing."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import cast

from rps.data_pipeline.common import (
    athlete_data_dir,
    athlete_latest_dir,
    record_index_write,
    resolve_schema_dir,
)
from rps.data_pipeline.intervals_api_client import (
    get_athlete,
    get_wellness,
)
from rps.data_pipeline.intervals_date_utils import (
    date_to_iso_week,
)
from rps.data_pipeline.intervals_schema_utils import _canonicalize_pipeline_payload
from rps.data_pipeline.intervals_zone_model import (
    IndexMeta,
    _extract_latest_weight_from_wellness,
    _extract_weight_kg,
    _num_or_none,
    _parse_date,
    normalize_scalar,
)
from rps.workspace.schema_registry import validate_or_raise
from rps.workspace.types import ArtifactType


def write_wellness(
    *,
    athlete_id: str,
    base_url: str,
    from_date: date,
    to_date: date,
    skip_validate: bool,
) -> None:
    run_ts = datetime.now(UTC)
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
    # Extend validity to end of calendar year so future planning can reuse body_mass_kg.
    # Use Dec 28 to anchor the final ISO week of the year.
    year_end = date(end_day.year, 12, 31)
    year_end_iso_anchor = date(end_day.year, 12, 28)
    valid_end_week = f"{date_to_iso_week(year_end_iso_anchor)[0]}-{date_to_iso_week(year_end_iso_anchor)[1]:02d}"
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
        "iso_week_range": f"{start_week}--{valid_end_week}",
        "data_confidence": "HIGH",
        "temporal_scope": {
            "from": start_day.isoformat(),
            "to": year_end.isoformat(),
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
        "notes": (
            "Derived from Intervals.icu wellness export. "
            "Temporal scope extends to calendar year end to allow planning with "
            "the latest body_mass_kg even when no future wellness entries exist."
        ),
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
    validator, payload = _canonicalize_pipeline_payload(
        schema_dir=schema_dir,
        schema_file="wellness.schema.json",
        artifact_type=ArtifactType.WELLNESS,
        payload=payload,
    )
    if not skip_validate:
        validate_or_raise(validator, payload)

    data_dir = athlete_data_dir(athlete_id)
    latest_dir = athlete_latest_dir(athlete_id)
    end_week_year, end_week_number = end_week.split("-", 1)
    out_dir = data_dir / end_week_year / end_week_number
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"wellness_{end_week}.json"

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    latest_dir.mkdir(parents=True, exist_ok=True)
    latest_file = latest_dir / "wellness.json"
    latest_file.write_bytes(out_file.read_bytes())

    index_meta = cast(IndexMeta, meta)
    record_index_write(
        athlete_id=athlete_id,
        artifact_type="WELLNESS",
        version_key=version_key,
        path=out_file,
        run_id=index_meta["run_id"],
        producer_agent=index_meta["owner_agent"],
        created_at=index_meta["created_at"],
        iso_week=index_meta["iso_week"],
        iso_week_range=index_meta["iso_week_range"],
    )

    print(f"Wellness written: {out_file}")
