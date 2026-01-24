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
    ArtifactType.SEASON_BRIEF: ArtifactPathConfig("inputs", "season_brief"),
    ArtifactType.EVENTS: ArtifactPathConfig("inputs", "events"),
    ArtifactType.KPI_PROFILE: ArtifactPathConfig("inputs", "kpi_profile"),
    ArtifactType.SEASON_SCENARIOS: ArtifactPathConfig("data/plans/macro", "season_scenarios"),
    ArtifactType.SEASON_SCENARIO_SELECTION: ArtifactPathConfig("data/plans/macro", "season_scenario_selection"),
    ArtifactType.MACRO_OVERVIEW: ArtifactPathConfig("data/plans/macro", "macro_overview"),
    ArtifactType.MACRO_MESO_FEED_FORWARD: ArtifactPathConfig("data/plans/macro", "macro_meso_feed_forward"),
    ArtifactType.BLOCK_GOVERNANCE: ArtifactPathConfig("data/plans/meso", "block_governance"),
    ArtifactType.BLOCK_EXECUTION_ARCH: ArtifactPathConfig("data/plans/meso", "block_execution_arch"),
    ArtifactType.BLOCK_EXECUTION_PREVIEW: ArtifactPathConfig("data/plans/meso", "block_execution_preview"),
    ArtifactType.BLOCK_FEED_FORWARD: ArtifactPathConfig("data/plans/meso", "block_feed_forward"),
    ArtifactType.ZONE_MODEL: ArtifactPathConfig("data/plans/meso", "zone_model"),
    ArtifactType.WORKOUTS_PLAN: ArtifactPathConfig("data/plans/micro", "workouts_plan"),
    ArtifactType.INTERVALS_WORKOUTS: ArtifactPathConfig("data/exports", "intervals_workouts"),
    ArtifactType.ACTIVITIES_ACTUAL: ArtifactPathConfig("data/analysis", "activities_actual"),
    ArtifactType.ACTIVITIES_TREND: ArtifactPathConfig("data/analysis", "activities_trend"),
    ArtifactType.AVAILABILITY: ArtifactPathConfig("data/analysis", "availability"),
    ArtifactType.WELLNESS: ArtifactPathConfig("data/analysis", "wellness"),
    ArtifactType.DES_ANALYSIS_REPORT: ArtifactPathConfig("data/analysis", "des_analysis_report"),
}


def ensure_dir(path: Path) -> None:
    """Create a directory if it does not exist."""
    path.mkdir(parents=True, exist_ok=True)
