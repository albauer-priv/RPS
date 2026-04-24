from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime

from rps.workspace.iso_helpers import IsoWeek, next_iso_week, parse_iso_week, parse_iso_week_range
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType


def iter_weeks_in_range(range_spec) -> list[IsoWeek]:
    """Return all ISO week objects covered by a parsed ISO week range."""
    if not range_spec:
        return []
    weeks = []
    current = range_spec.start
    while True:
        weeks.append(current)
        if current == range_spec.end:
            break
        current = next_iso_week(current)
    return weeks


def normalize_iso_label(label: str) -> str | None:
    """Normalize week labels to the canonical ``YYYY-Www`` form."""
    if not label:
        return None
    candidate = label
    if "-W" in candidate:
        candidate = candidate.replace("-W", "-")
    week = parse_iso_week(candidate)
    if not week:
        return None
    return f"{week.year}-W{week.week:02d}"


def normalize_corridor(corridor: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    """Normalize corridor week keys to canonical ISO labels."""
    normalized: dict[str, dict[str, float]] = {}
    for key, value in corridor.items():
        label = normalize_iso_label(str(key))
        if not label:
            continue
        normalized[label] = value
    return normalized


def normalize_scalar_series(series: dict[str, float]) -> dict[str, float]:
    """Normalize scalar series week keys to canonical ISO labels."""
    normalized: dict[str, float] = {}
    for key, value in series.items():
        label = normalize_iso_label(str(key))
        if not label:
            continue
        normalized[label] = value
    return normalized


def sorted_labels(*series_maps: Mapping[str, object]) -> list[str]:
    """Return sorted week labels from all provided series/corridor mappings."""
    labels: set[str] = set()
    for series in series_maps:
        for key in series.keys():
            label = normalize_iso_label(str(key))
            if label:
                labels.add(label)
    return sorted(
        labels,
        key=lambda label: (
            int(label.split("-W")[0]),
            int(label.split("-W")[1]),
        ),
    )


def label_order(label: str) -> tuple[int, int] | None:
    """Return sortable ``(year, week)`` tuple for a week label."""
    normalized = normalize_iso_label(label)
    if not normalized:
        return None
    year_str, week_str = normalized.split("-W")
    return int(year_str), int(week_str)


def _parse_created_at(value: object) -> datetime:
    """Return an aware UTC timestamp for artefact ordering."""
    if not isinstance(value, str) or not value.strip():
        return datetime.min.replace(tzinfo=UTC)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return datetime.min.replace(tzinfo=UTC)


def season_corridor_by_week(store: LocalArtifactStore, athlete_id: str) -> dict[str, dict[str, float]]:
    """Build season load corridors keyed by ISO week."""
    if not store.latest_exists(athlete_id, ArtifactType.SEASON_PLAN):
        return {}
    payload = store.load_latest(athlete_id, ArtifactType.SEASON_PLAN)
    if not isinstance(payload, dict):
        return {}
    phases = (payload.get("data") or {}).get("phases", []) or []
    corridors: dict[str, dict[str, float]] = {}
    for phase in phases:
        iso_range = phase.get("iso_week_range")
        weekly_kj = (phase.get("weekly_load_corridor") or {}).get("weekly_kj") or {}
        minimum = weekly_kj.get("min")
        maximum = weekly_kj.get("max")
        range_spec = parse_iso_week_range(iso_range)
        if not range_spec and isinstance(iso_range, str) and "--" in iso_range:
            start, end = iso_range.split("--", maxsplit=1)
            start_label = normalize_iso_label(start.strip())
            end_label = normalize_iso_label(end.strip())
            if start_label and end_label:
                range_spec = parse_iso_week_range(f"{start_label}--{end_label}")
        if minimum is None or maximum is None or not range_spec:
            continue
        for week in iter_weeks_in_range(range_spec):
            label = f"{week.year}-W{week.week:02d}"
            corridors[label] = {"min": minimum, "max": maximum}
    return corridors


def phase_guardrails_by_week(store: LocalArtifactStore, athlete_id: str) -> dict[str, dict[str, float]]:
    """Build per-week phase corridors from the latest guardrails version touching each week."""
    corridors: dict[str, tuple[datetime, dict[str, float]]] = {}
    for version in store.list_versions(athlete_id, ArtifactType.PHASE_GUARDRAILS):
        payload = store.load_version(athlete_id, ArtifactType.PHASE_GUARDRAILS, version)
        if not isinstance(payload, dict):
            continue
        meta = payload.get("meta") or {}
        created_at = _parse_created_at(meta.get("created_at"))
        bands = (payload.get("data") or {}).get("load_guardrails", {}).get("weekly_kj_bands", []) or []
        for band in bands:
            week = band.get("week")
            limits = band.get("band") or {}
            minimum = limits.get("min")
            maximum = limits.get("max")
            if not week or minimum is None or maximum is None:
                continue
            label = str(week)
            existing = corridors.get(label)
            if existing is None or created_at >= existing[0]:
                corridors[label] = (created_at, {"min": minimum, "max": maximum})
    return {label: values for label, (_created_at, values) in corridors.items()}


def _latest_week_plan_payloads_by_week(
    store: LocalArtifactStore,
    athlete_id: str,
) -> dict[str, dict[str, object]]:
    """Return the latest stored week-plan payload per ISO week."""
    latest_payloads: dict[str, tuple[datetime, dict[str, object]]] = {}
    for version in store.list_versions(athlete_id, ArtifactType.WEEK_PLAN):
        payload = store.load_version(athlete_id, ArtifactType.WEEK_PLAN, version)
        if not isinstance(payload, dict):
            continue
        meta = payload.get("meta") or {}
        normalized = normalize_iso_label(str(meta.get("iso_week") or ""))
        if not normalized:
            continue
        created_at = _parse_created_at(meta.get("created_at"))
        existing = latest_payloads.get(normalized)
        if existing is None or created_at >= existing[0]:
            latest_payloads[normalized] = (created_at, payload)
    return {label: payload for label, (_created_at, payload) in latest_payloads.items()}


def week_plan_corridor_by_week(store: LocalArtifactStore, athlete_id: str) -> dict[str, dict[str, float]]:
    """Build per-week week-plan corridors from the latest stored week plan per week."""
    corridors: dict[str, dict[str, float]] = {}
    for label, payload in _latest_week_plan_payloads_by_week(store, athlete_id).items():
        corridor = (payload.get("data") or {}).get("week_summary", {}).get("weekly_load_corridor_kj") or {}
        minimum = corridor.get("min")
        maximum = corridor.get("max")
        if minimum is None or maximum is None:
            continue
        corridors[label] = {"min": minimum, "max": maximum}
    return corridors


def planned_weekly_kj_by_week(store: LocalArtifactStore, athlete_id: str) -> dict[str, float]:
    """Build per-week planned kJ values from the latest stored week plan per week."""
    planned: dict[str, float] = {}
    for normalized, payload in _latest_week_plan_payloads_by_week(store, athlete_id).items():
        summary = (payload.get("data") or {}).get("week_summary") or {}
        value = summary.get("planned_weekly_load_kj")
        if value is None:
            continue
        planned[normalized] = float(value)
    return planned
