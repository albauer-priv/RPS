"""Workspace artifact types and metadata structures."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Authority(str, Enum):
    """Governance levels for artifacts."""

    BINDING = "Binding"
    STRUCTURAL = "Structural"
    ADVISORY = "Advisory"
    DERIVED = "Derived"
    FACTUAL = "Factual"
    INFORMATIONAL = "Informational"


class ArtifactType(str, Enum):
    """Canonical artifact identifiers used across the workspace."""
    # Inputs
    SEASON_BRIEF = "SEASON_BRIEF"
    EVENTS = "EVENTS"
    KPI_PROFILE = "KPI_PROFILE"
    ATHLETE_PROFILE = "ATHLETE_PROFILE"
    LOGISTICS = "LOGISTICS"
    PLANNING_EVENTS = "PLANNING_EVENTS"
    HISTORICAL_BASELINE = "HISTORICAL_BASELINE"

    # Season planning layer
    SEASON_SCENARIOS = "SEASON_SCENARIOS"
    SEASON_SCENARIO_SELECTION = "SEASON_SCENARIO_SELECTION"
    SEASON_PLAN = "SEASON_PLAN"

    SEASON_PHASE_FEED_FORWARD = "SEASON_PHASE_FEED_FORWARD"

    # Phase layer
    PHASE_GUARDRAILS = "PHASE_GUARDRAILS"
    PHASE_STRUCTURE = "PHASE_STRUCTURE"
    PHASE_PREVIEW = "PHASE_PREVIEW"
    PHASE_FEED_FORWARD = "PHASE_FEED_FORWARD"
    ZONE_MODEL = "ZONE_MODEL"

    # Week layer
    WEEK_PLAN = "WEEK_PLAN"

    # Export payload (raw)
    INTERVALS_WORKOUTS = "INTERVALS_WORKOUTS"

    # Data loop and analysis
    ACTIVITIES_ACTUAL = "ACTIVITIES_ACTUAL"
    ACTIVITIES_TREND = "ACTIVITIES_TREND"
    AVAILABILITY = "AVAILABILITY"
    WELLNESS = "WELLNESS"
    DES_ANALYSIS_REPORT = "DES_ANALYSIS_REPORT"


@dataclass(frozen=True)
class ArtifactMeta:
    """Metadata describing an artifact write."""
    artifact_type: ArtifactType
    athlete_id: str
    version_key: str
    authority: Authority
    producer_agent: str
    run_id: str
    created_at: str
    trace_upstream: list[str]
