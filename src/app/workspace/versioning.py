"""Derive version keys from artifact metadata."""

from __future__ import annotations

from typing import Any


def _week_key(year: int, week: int) -> str:
    """Format an ISO week as YYYY-WW."""
    return f"{year:04d}-{week:02d}"


def derive_version_key_from_envelope(envelope: dict[str, Any]) -> str:
    """Derive a version key using known metadata fields."""
    meta = envelope.get("meta", {})

    if "iso_week" in meta:
        wk = meta["iso_week"]
        return _week_key(int(wk["year"]), int(wk["week"]))

    if "iso_week_range" in meta:
        range_spec = meta["iso_week_range"]
        start = range_spec["start"]
        end = range_spec["end"]
        return f"{_week_key(int(start['year']), int(start['week']))}--{_week_key(int(end['year']), int(end['week']))}"

    if "temporal_scope" in meta:
        scope = meta["temporal_scope"]
        return f"{scope['start']}--{scope['end']}"

    if "date_range" in meta:
        date_range = meta["date_range"]
        return f"{date_range['start']}--{date_range['end']}"

    return "unversioned"
