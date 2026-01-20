"""Derive version keys from artifact metadata."""

from __future__ import annotations

from typing import Any


def _week_key(year: int, week: int) -> str:
    """Format an ISO week as YYYY-WW."""
    return f"{year:04d}-{week:02d}"


def _coerce_week(value: Any) -> str | None:
    """Return a week key from a string or {year, week} mapping."""
    if isinstance(value, str):
        return value
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


def derive_version_key_from_envelope(envelope: dict[str, Any]) -> str:
    """Derive a version key using known metadata fields."""
    meta = envelope.get("meta", {})

    if "iso_week" in meta:
        wk_key = _coerce_week(meta["iso_week"])
        if wk_key:
            return wk_key

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
