"""Workspace filesystem layout helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .types import ArtifactType


@dataclass(frozen=True)
class ArtifactPathConfig:
    """Controls where a given artifact type is stored within a workspace."""

    folder: str
    filename_prefix: str


ARTIFACT_PATHS: dict[ArtifactType, ArtifactPathConfig] = {
    ArtifactType.KPI_PROFILE: ArtifactPathConfig("inputs", "kpi_profile"),
    ArtifactType.ATHLETE_PROFILE: ArtifactPathConfig("inputs", "athlete_profile"),
    ArtifactType.LOGISTICS: ArtifactPathConfig("inputs", "logistics"),
    ArtifactType.PLANNING_EVENTS: ArtifactPathConfig("inputs", "planning_events"),
    ArtifactType.HISTORICAL_BASELINE: ArtifactPathConfig("data/analysis", "historical_baseline"),
    ArtifactType.SEASON_SCENARIOS: ArtifactPathConfig("data/plans/season", "season_scenarios"),
    ArtifactType.SEASON_SCENARIO_SELECTION: ArtifactPathConfig("data/plans/season", "season_scenario_selection"),
    ArtifactType.SEASON_PLAN: ArtifactPathConfig("data/plans/season", "season_plan"),
    ArtifactType.SEASON_PHASE_FEED_FORWARD: ArtifactPathConfig("data/plans/season", "season_phase_feed_forward"),
    ArtifactType.PHASE_GUARDRAILS: ArtifactPathConfig("data/plans/phase", "phase_guardrails"),
    ArtifactType.PHASE_STRUCTURE: ArtifactPathConfig("data/plans/phase", "phase_structure"),
    ArtifactType.PHASE_PREVIEW: ArtifactPathConfig("data/plans/phase", "phase_preview"),
    ArtifactType.PHASE_FEED_FORWARD: ArtifactPathConfig("data/plans/phase", "phase_feed_forward"),
    ArtifactType.ZONE_MODEL: ArtifactPathConfig("data/plans/phase", "zone_model"),
    ArtifactType.WEEK_PLAN: ArtifactPathConfig("data/plans/week", "week_plan"),
    ArtifactType.INTERVALS_WORKOUTS: ArtifactPathConfig("data/exports", "workouts"),
    ArtifactType.ACTIVITIES_ACTUAL: ArtifactPathConfig("data/analysis", "activities_actual"),
    ArtifactType.ACTIVITIES_TREND: ArtifactPathConfig("data/analysis", "activities_trend"),
    ArtifactType.AVAILABILITY: ArtifactPathConfig("inputs", "availability"),
    ArtifactType.WELLNESS: ArtifactPathConfig("data/analysis", "wellness"),
    ArtifactType.DES_ANALYSIS_REPORT: ArtifactPathConfig("data/analysis", "des_analysis_report"),
}


def ensure_dir(path: Path) -> None:
    """Create a directory if it does not exist."""
    path.mkdir(parents=True, exist_ok=True)
