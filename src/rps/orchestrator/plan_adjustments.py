"""Input-driven plan adjustment suggestion logic."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType

logger = logging.getLogger(__name__)

JsonMap = dict[str, object]

# (input_artifact_type, input_label, plan_artifact_type, plan_label, scope)
INPUT_PLAN_DEPS: list[tuple[ArtifactType, str, ArtifactType, str, str]] = [
    (ArtifactType.ATHLETE_PROFILE, "About You & Goals", ArtifactType.SEASON_PLAN, "Season Plan", "Season Plan"),
    (ArtifactType.PLANNING_EVENTS, "Events", ArtifactType.SEASON_PLAN, "Season Plan", "Season Plan"),
    (ArtifactType.AVAILABILITY, "Availability", ArtifactType.PHASE_GUARDRAILS, "Phase", "Phase"),
    (ArtifactType.LOGISTICS, "Logistics", ArtifactType.WEEK_PLAN, "Week Plan", "Week Plan"),
]

SCOPE_PRIORITY: dict[str, int] = {"Season Plan": 3, "Phase": 2, "Week Plan": 1}


@dataclass(frozen=True)
class AdjustmentSuggestion:
    input_label: str
    input_artifact_type: ArtifactType
    input_created_at: str
    plan_label: str
    plan_artifact_type: ArtifactType
    plan_created_at: str
    scope: str


def _parse_dt(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        v = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(v)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except ValueError:
        return None


def _latest_created_at(index: JsonMap, artifact_type: ArtifactType) -> str | None:
    artefacts = index.get("artefacts")
    if not isinstance(artefacts, dict):
        return None
    entry = artefacts.get(artifact_type.value)
    if not isinstance(entry, dict):
        return None
    latest = entry.get("latest")
    if not isinstance(latest, dict):
        return None
    value = latest.get("created_at")
    return value if isinstance(value, str) else None


def get_adjustment_suggestions(
    index: JsonMap,
    store: LocalArtifactStore,
    athlete_id: str,
) -> list[AdjustmentSuggestion]:
    """Return suggestions for plan scopes whose inputs are newer than the plan artifact."""
    suggestions: list[AdjustmentSuggestion] = []
    seen_scopes: dict[str, AdjustmentSuggestion] = {}

    for input_type, input_label, plan_type, plan_label, scope in INPUT_PLAN_DEPS:
        if not store.latest_exists(athlete_id, input_type):
            continue
        if not store.latest_exists(athlete_id, plan_type):
            continue
        input_ts_str = _latest_created_at(index, input_type)
        plan_ts_str = _latest_created_at(index, plan_type)
        if not input_ts_str or not plan_ts_str:
            continue
        input_dt = _parse_dt(input_ts_str)
        plan_dt = _parse_dt(plan_ts_str)
        if input_dt is None or plan_dt is None:
            continue
        if input_dt <= plan_dt:
            continue
        suggestion = AdjustmentSuggestion(
            input_label=input_label,
            input_artifact_type=input_type,
            input_created_at=input_ts_str,
            plan_label=plan_label,
            plan_artifact_type=plan_type,
            plan_created_at=plan_ts_str,
            scope=scope,
        )
        logger.debug(
            "Adjustment suggestion: input=%s (%s) > plan=%s (%s) → scope=%s",
            input_label, input_ts_str, plan_label, plan_ts_str, scope,
        )
        existing = seen_scopes.get(scope)
        if existing is None:
            seen_scopes[scope] = suggestion
        else:
            existing_dt = _parse_dt(existing.input_created_at)
            if existing_dt is None or input_dt > existing_dt:
                seen_scopes[scope] = suggestion

    suggestions = list(seen_scopes.values())
    suggestions.sort(key=lambda s: SCOPE_PRIORITY.get(s.scope, 0), reverse=True)
    return suggestions
