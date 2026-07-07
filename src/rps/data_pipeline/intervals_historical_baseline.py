"""Historical baseline aggregation from Intervals.icu activities."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import Any, TypedDict, cast

from rps.data_pipeline.common import (
    athlete_data_dir,
    athlete_latest_dir,
    record_index_write,
    resolve_schema_dir,
)
from rps.data_pipeline.intervals_api_client import (
    get_activities,
    get_activity_detail,
)
from rps.data_pipeline.intervals_schema_utils import _canonicalize_pipeline_payload
from rps.workspace.schema_registry import validate_or_raise
from rps.workspace.types import ArtifactType


class IndexMeta(TypedDict):
    run_id: str
    owner_agent: str
    created_at: str | None
    iso_week: str | None
    iso_week_range: str | None


def _aggregate_yearly_activity_summary(
    *,
    athlete_id: str,
    base_url: str,
    year: int,
) -> dict[str, float]:
    from_date = date(year, 1, 1)
    to_date = date(year, 12, 31)
    activities = get_activities(athlete_id, base_url, from_date, to_date)
    activities = [a for a in activities if a.get("type") in {"Ride", "VirtualRide"}]
    total_seconds = 0.0
    total_km = 0.0
    total_kj = 0.0
    for activity in activities:
        total_seconds += float(activity.get("moving_time") or 0.0)
        total_km += float(activity.get("distance") or 0.0) / 1000.0
        activity_id = activity.get("id")
        if not isinstance(activity_id, (str, int)):
            continue
        detail = get_activity_detail(base_url, activity_id)
        joules = detail.get("icu_joules") or 0.0
        total_kj += float(joules) / 1000.0
    return {
        "activities": float(len(activities)),
        "moving_time_seconds": total_seconds,
        "distance_km": total_km,
        "work_kj": total_kj,
    }


def compile_historical_baseline(
    *,
    athlete_id: str,
    base_url: str,
    historical_years: int,
    skip_validate: bool,
) -> None:
    """Compile Historical Baseline + yearly summaries from Intervals data."""
    if historical_years <= 0:
        return

    today = date.today()
    years = list(range(today.year - historical_years + 1, today.year + 1))
    yearly_summary = []
    total_kj = 0.0
    total_seconds = 0.0
    total_activities = 0
    for year in years:
        summary = _aggregate_yearly_activity_summary(
            athlete_id=athlete_id,
            base_url=base_url,
            year=year,
        )
        if summary["activities"] == 0:
            continue
        total_kj += summary["work_kj"]
        total_seconds += summary["moving_time_seconds"]
        total_activities += int(summary["activities"])
        yearly_summary.append(
            {
                "year": year,
                "activities": int(summary["activities"]),
                "moving_time_seconds": summary["moving_time_seconds"],
                "distance_km": round(summary["distance_km"], 1),
                "work_kj": round(summary["work_kj"], 1),
                "kj_per_activity": round(
                    summary["work_kj"] / summary["activities"], 1
                )
                if summary["activities"] > 0
                else 0.0,
                "kj_per_hour": round(
                    summary["work_kj"] / (summary["moving_time_seconds"] / 3600.0), 1
                )
                if summary["moving_time_seconds"] > 0
                else 0.0,
            }
        )

    if not yearly_summary:
        raise ValueError("No yearly activities found for historical baseline.")

    avg_kj_year = total_kj / len(yearly_summary)
    avg_kj_activity = total_kj / total_activities if total_activities > 0 else 0.0
    avg_kj_hour = total_kj / (total_seconds / 3600.0) if total_seconds > 0 else 0.0

    run_ts = datetime.now(UTC)
    version_key = run_ts.strftime("%Y%m%d_%H%M%S")
    run_id = f"intervals_historical_baseline_{run_ts.strftime('%Y%m%dT%H%M%SZ')}"

    payload = {
        "meta": {
            "artifact_type": "HISTORICAL_BASELINE",
            "schema_id": "HistoricalBaselineInterface",
            "schema_version": "1.2",
            "version": "1.2",
            "authority": "Derived",
            "owner_agent": "Intervals-Pipeline",
            "run_id": run_id,
            "created_at": run_ts.isoformat(),
            "scope": "Athlete",
            "data_confidence": "MEDIUM",
            "trace_upstream": [
                {
                    "artifact": "intervals_icu_activity",
                    "version": "1.0",
                    "run_id": athlete_id,
                }
            ],
            "notes": "Yearly aggregates derived from full-year Intervals activity fetches.",
        },
        "data": {
            "metrics": {
                "kj_per_year": round(avg_kj_year, 2),
                "kj_per_activity": round(avg_kj_activity, 2),
                "kj_per_hour": round(avg_kj_hour, 2),
                "long_ride_tolerance_kj": 0.0,
            },
            "yearly_summary": yearly_summary,
            "source": {
                "source_type": "intervals",
                "range": f"{len(yearly_summary)} years",
            },
        },
    }

    schema_dir = resolve_schema_dir()
    validator, payload = _canonicalize_pipeline_payload(
        schema_dir=schema_dir,
        schema_file="historical_baseline.schema.json",
        artifact_type=ArtifactType.HISTORICAL_BASELINE,
        payload=payload,
    )
    if not skip_validate:
        validate_or_raise(validator, payload)

    data_dir = athlete_data_dir(athlete_id) / "analysis"
    data_dir.mkdir(parents=True, exist_ok=True)
    out_file = data_dir / f"historical_baseline_{version_key}.json"
    out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    latest_dir = athlete_latest_dir(athlete_id)
    latest_dir.mkdir(parents=True, exist_ok=True)
    latest_file = latest_dir / "historical_baseline.json"
    latest_file.write_bytes(out_file.read_bytes())

    payload_meta = cast(dict[str, Any], payload["meta"])
    record_index_write(
        athlete_id=athlete_id,
        artifact_type="HISTORICAL_BASELINE",
        version_key=version_key,
        path=out_file,
        run_id=run_id,
        producer_agent=str(payload_meta["owner_agent"]),
        created_at=cast(str | None, payload_meta["created_at"]),
        iso_week=None,
        iso_week_range=None,
    )

    print(f"Historical baseline written: {out_file}")
