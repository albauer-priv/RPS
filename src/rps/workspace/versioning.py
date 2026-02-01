"""Derive version keys from artifact metadata."""

from __future__ import annotations

from typing import Any
import re
import time
from datetime import datetime, timezone

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
                dt = dt.astimezone(timezone.utc)
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

    if "iso_week" in meta:
        wk_key = _coerce_week(meta["iso_week"])
        if wk_key:
            version_key = meta.get("version_key") if isinstance(meta, dict) else None
            if isinstance(version_key, str):
                return normalize_week_version_key(
                    version_key,
                    meta.get("created_at"),
                    artifact_type=artifact_type,
                )
            return normalize_week_version_key(
                wk_key,
                meta.get("created_at"),
                artifact_type=artifact_type,
            )

    if "iso_week_range" in meta:
        range_key = _coerce_range(meta["iso_week_range"])
        if range_key:
            return range_key

    if "temporal_scope" in meta:
        scope = meta["temporal_scope"]
        if isinstance(scope, dict):
            start = scope.get("start") or scope.get("from")
            end = scope.get("end") or scope.get("to")
            if start and end:
                return f"{start}--{end}"

    if "date_range" in meta:
        date_range = meta["date_range"]
        if isinstance(date_range, dict):
            start = date_range.get("start") or date_range.get("from")
            end = date_range.get("end") or date_range.get("to")
            if start and end:
                return f"{start}--{end}"
        elif isinstance(date_range, str):
            return date_range

    return "unversioned"
