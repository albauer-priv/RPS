"""Derive version keys from artifact metadata."""

from __future__ import annotations

import re
import time
from datetime import UTC, datetime
from typing import Any

from rps.workspace.types import ArtifactType


def _week_key(year: int, week: int) -> str:
    """Format an ISO week as YYYY-WW."""
    return f"{year:04d}-{week:02d}"


_WEEK_KEY_RE = re.compile(r"^\d{4}-\d{2}$")
_WEEK_TIMESTAMP_RE = re.compile(r"^\d{8}_\d{6}$")

WEEK_SCOPED_ARTIFACTS = {
    ArtifactType.WEEK_PLAN,
    ArtifactType.INTERVALS_WORKOUTS,
    ArtifactType.DES_ANALYSIS_REPORT,
    ArtifactType.SEASON_SCENARIOS,
    ArtifactType.SEASON_SCENARIO_SELECTION,
    ArtifactType.SEASON_PLAN,
}

RANGE_SCOPED_ARTIFACTS = {
    ArtifactType.PHASE_GUARDRAILS,
    ArtifactType.PHASE_STRUCTURE,
    ArtifactType.PHASE_PREVIEW,
}


def _normalize_week_key(value: str) -> str | None:
    """Return YYYY-WW from a key that may include a timestamp suffix."""
    base = value.split("__", 1)[0]
    if _WEEK_KEY_RE.match(base):
        return base
    return None


def _format_timestamp(created_at: str | None = None) -> str:
    """Return a timestamp string for version keys."""
    if created_at:
        try:
            value = created_at.replace("Z", "+00:00")
            dt = datetime.fromisoformat(value)
            if dt.tzinfo:
                dt = dt.astimezone(UTC)
            return dt.strftime("%Y%m%d_%H%M%S")
        except ValueError:
            pass
    return time.strftime("%Y%m%d_%H%M%S", time.gmtime())


def normalize_week_version_key(
    value: str,
    created_at: str | None = None,
    *,
    artifact_type: ArtifactType | None = None,
) -> str:
    """Ensure a week version key includes a timestamp suffix when required."""
    base = _normalize_week_key(value)
    if not base:
        return value
    if "__" in value:
        return value
    if artifact_type is not None and artifact_type not in WEEK_SCOPED_ARTIFACTS:
        return value
    return f"{base}__{_format_timestamp(created_at)}"


def normalize_range_version_key(
    value: str,
    created_at: str | None = None,
    *,
    artifact_type: ArtifactType | None = None,
) -> str:
    """Ensure a range version key includes a timestamp suffix when required."""
    if "--" not in value:
        return value
    if "__" in value:
        return value
    if artifact_type is not None and artifact_type not in RANGE_SCOPED_ARTIFACTS:
        return value
    return f"{value}__{_format_timestamp(created_at)}"


def normalize_version_key(
    value: str,
    created_at: str | None = None,
    *,
    artifact_type: ArtifactType | None = None,
) -> str:
    """Normalize a version key for week or range scoped artifacts."""
    if "--" in value:
        return normalize_range_version_key(value, created_at, artifact_type=artifact_type)
    return normalize_week_version_key(value, created_at, artifact_type=artifact_type)


def split_week_version_key(value: str) -> tuple[str | None, str | None]:
    """Split a week version key into (base, timestamp)."""
    base = _normalize_week_key(value)
    if not base:
        return None, None
    if "__" not in value:
        return base, None
    suffix = value.split("__", 1)[1]
    if _WEEK_TIMESTAMP_RE.match(suffix):
        return base, suffix
    return base, None


def split_range_version_key(value: str) -> tuple[str | None, str | None]:
    """Split a range version key into (base, timestamp)."""
    if "--" not in value:
        return None, None
    base = value.split("__", 1)[0]
    if "__" not in value:
        return base, None
    suffix = value.split("__", 1)[1]
    if _WEEK_TIMESTAMP_RE.match(suffix):
        return base, suffix
    return base, None


def _coerce_week(value: Any) -> str | None:
    """Return a week key from a string or {year, week} mapping."""
    if isinstance(value, str):
        return _normalize_week_key(value) or value
    if isinstance(value, dict) and "year" in value and "week" in value:
        return _week_key(int(value["year"]), int(value["week"]))
    return None


def _coerce_range(value: Any) -> str | None:
    """Return a range key from a string or {start/end} mapping."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        start = value.get("start") or value.get("from")
        end = value.get("end") or value.get("to")
        if start is None or end is None:
            return None
        start_key = _coerce_week(start) or (start if isinstance(start, str) else None)
        end_key = _coerce_week(end) or (end if isinstance(end, str) else None)
        if start_key and end_key:
            return f"{start_key}--{end_key}"
    return None


def derive_version_key_from_envelope(
    envelope: dict[str, Any],
    artifact_type: ArtifactType | None = None,
) -> str:
    """Derive a version key using known metadata fields."""
    meta = envelope.get("meta", {})
    range_key = _version_key_from_iso_week_range(meta, artifact_type)
    if range_key:
        return range_key
    week_key = _version_key_from_iso_week(meta, artifact_type)
    if week_key:
        return week_key
    temporal_key = _version_key_from_temporal_scope(meta, artifact_type)
    if temporal_key:
        return temporal_key
    date_range_key = _version_key_from_date_range(meta, artifact_type)
    if date_range_key:
        return date_range_key
    return "unversioned"


def _version_key_from_iso_week_range(
    meta: object,
    artifact_type: ArtifactType | None,
) -> str | None:
    if not isinstance(meta, dict) or "iso_week_range" not in meta:
        return None
    if artifact_type is not None and artifact_type not in RANGE_SCOPED_ARTIFACTS:
        return None
    range_key = _coerce_range(meta["iso_week_range"])
    if not range_key:
        return None
    return normalize_version_key(
        range_key,
        meta.get("created_at"),
        artifact_type=artifact_type,
    )


def _version_key_from_iso_week(
    meta: object,
    artifact_type: ArtifactType | None,
) -> str | None:
    if not isinstance(meta, dict) or "iso_week" not in meta:
        return None
    wk_key = _coerce_week(meta["iso_week"])
    if not wk_key:
        return None
    version_key = meta.get("version_key")
    if isinstance(version_key, str):
        normalized_version_key = normalize_version_key(
            version_key,
            meta.get("created_at"),
            artifact_type=artifact_type,
        )
        normalized_base, _ = split_week_version_key(normalized_version_key)
        if normalized_base == wk_key:
            if artifact_type in WEEK_SCOPED_ARTIFACTS:
                return normalize_version_key(
                    wk_key,
                    meta.get("created_at"),
                    artifact_type=artifact_type,
                )
            return normalized_version_key
    return normalize_version_key(
        wk_key,
        meta.get("created_at"),
        artifact_type=artifact_type,
    )


def _version_key_from_temporal_scope(
    meta: object,
    artifact_type: ArtifactType | None,
) -> str | None:
    if not isinstance(meta, dict):
        return None
    scope = meta.get("temporal_scope")
    if not isinstance(scope, dict):
        return None
    start = scope.get("start") or scope.get("from")
    end = scope.get("end") or scope.get("to")
    if not (start and end):
        return None
    return normalize_version_key(
        f"{start}--{end}",
        meta.get("created_at"),
        artifact_type=artifact_type,
    )


def _version_key_from_date_range(
    meta: object,
    artifact_type: ArtifactType | None,
) -> str | None:
    if not isinstance(meta, dict) or "date_range" not in meta:
        return None
    date_range = meta["date_range"]
    if isinstance(date_range, dict):
        start = date_range.get("start") or date_range.get("from")
        end = date_range.get("end") or date_range.get("to")
        if start and end:
            return f"{start}--{end}"
        return None
    if isinstance(date_range, str):
        return normalize_version_key(
            date_range,
            meta.get("created_at"),
            artifact_type=artifact_type,
        )
    return None
