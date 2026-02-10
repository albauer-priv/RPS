"""Mapping from artifact types to schema filenames."""

from __future__ import annotations

from .types import ArtifactType


ARTIFACT_SCHEMA_FILE: dict[ArtifactType, str] = {
    ArtifactType.KPI_PROFILE: "kpi_profile.schema.json",
    ArtifactType.ATHLETE_PROFILE: "athlete_profile.schema.json",
    ArtifactType.LOGISTICS: "logistics.schema.json",
    ArtifactType.PLANNING_EVENTS: "planning_events.schema.json",
    ArtifactType.HISTORICAL_BASELINE: "historical_baseline.schema.json",
    ArtifactType.SEASON_SCENARIOS: "season_scenarios.schema.json",
    ArtifactType.SEASON_SCENARIO_SELECTION: "season_scenario_selection.schema.json",
    ArtifactType.SEASON_PLAN: "season_plan.schema.json",
    ArtifactType.SEASON_PHASE_FEED_FORWARD: "season_phase_feed_forward.schema.json",
    ArtifactType.PHASE_GUARDRAILS: "phase_guardrails.schema.json",
    ArtifactType.PHASE_STRUCTURE: "phase_structure.schema.json",
    ArtifactType.PHASE_PREVIEW: "phase_preview.schema.json",
    ArtifactType.PHASE_FEED_FORWARD: "phase_feed_forward.schema.json",
    ArtifactType.ZONE_MODEL: "zone_model.schema.json",
    ArtifactType.WEEK_PLAN: "week_plan.schema.json",
    ArtifactType.INTERVALS_WORKOUTS: "workouts.schema.json",
    ArtifactType.ACTIVITIES_ACTUAL: "activities_actual.schema.json",
    ArtifactType.ACTIVITIES_TREND: "activities_trend.schema.json",
    ArtifactType.AVAILABILITY: "availability.schema.json",
    ArtifactType.WELLNESS: "wellness.schema.json",
    ArtifactType.DES_ANALYSIS_REPORT: "des_analysis_report.schema.json",
    # Add when schema files are available:
}
