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
    ArtifactType.MACRO_OVERVIEW: ArtifactPathConfig("plans/macro", "macro_overview"),
    ArtifactType.MACRO_MESO_FEED_FORWARD: ArtifactPathConfig("plans/macro", "macro_meso_feed_forward"),
    ArtifactType.BLOCK_GOVERNANCE: ArtifactPathConfig("plans/meso", "block_governance"),
    ArtifactType.BLOCK_EXECUTION_ARCH: ArtifactPathConfig("plans/meso", "block_execution_arch"),
    ArtifactType.BLOCK_EXECUTION_PREVIEW: ArtifactPathConfig("plans/meso", "block_execution_preview"),
    ArtifactType.BLOCK_FEED_FORWARD: ArtifactPathConfig("plans/meso", "block_feed_forward"),
    ArtifactType.ZONE_MODEL: ArtifactPathConfig("plans/meso", "zone_model"),
    ArtifactType.WORKOUTS_PLAN: ArtifactPathConfig("plans/micro", "workouts_plan"),
    ArtifactType.INTERVALS_WORKOUTS: ArtifactPathConfig("exports", "intervals_workouts"),
    ArtifactType.ACTIVITIES_ACTUAL: ArtifactPathConfig("analysis", "activities_actual"),
    ArtifactType.ACTIVITIES_TREND: ArtifactPathConfig("analysis", "activities_trend"),
    ArtifactType.DES_ANALYSIS_REPORT: ArtifactPathConfig("analysis", "des_analysis_report"),
}


def ensure_dir(path: Path) -> None:
    """Create a directory if it does not exist."""
    path.mkdir(parents=True, exist_ok=True)
