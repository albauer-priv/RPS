"""Mapping from artifact types to schema filenames."""

from __future__ import annotations

from .types import ArtifactType


ARTIFACT_SCHEMA_FILE: dict[ArtifactType, str] = {
    ArtifactType.KPI_PROFILE: "kpi_profile.schema.json",
    ArtifactType.SEASON_SCENARIOS: "season_scenarios.schema.json",
    ArtifactType.SEASON_SCENARIO_SELECTION: "season_scenario_selection.schema.json",
    ArtifactType.MACRO_OVERVIEW: "macro_overview.schema.json",
    ArtifactType.MACRO_MESO_FEED_FORWARD: "macro_meso_feed_forward.schema.json",
    ArtifactType.BLOCK_GOVERNANCE: "block_governance.schema.json",
    ArtifactType.BLOCK_EXECUTION_ARCH: "block_execution_arch.schema.json",
    ArtifactType.BLOCK_EXECUTION_PREVIEW: "block_execution_preview.schema.json",
    ArtifactType.BLOCK_FEED_FORWARD: "block_feed_forward.schema.json",
    ArtifactType.ZONE_MODEL: "zone_model.schema.json",
    ArtifactType.WORKOUTS_PLAN: "workouts_plan.schema.json",
    ArtifactType.INTERVALS_WORKOUTS: "workouts.schema.json",
    ArtifactType.ACTIVITIES_ACTUAL: "activities_actual.schema.json",
    ArtifactType.ACTIVITIES_TREND: "activities_trend.schema.json",
    ArtifactType.DES_ANALYSIS_REPORT: "des_analysis_report.schema.json",
    # Add when schema files are available:
    # ArtifactType.SEASON_BRIEF: "...",
    # ArtifactType.EVENTS: "...",
}
