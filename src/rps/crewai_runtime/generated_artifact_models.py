"""Generated CrewAI artifact output models. Do not edit by hand."""

from __future__ import annotations

from typing import Any

from rps.crewai_runtime.models import ArtifactEnvelopeModel
from rps.crewai_runtime.schema_backed_models import JsonSchemaArtifactModel


class ActivitiesActualModel(JsonSchemaArtifactModel):
    """Schema-backed model for `activities_actual.schema.json`."""

    __schema_file__ = "activities_actual.schema.json"


class ActivitiesTrendModel(JsonSchemaArtifactModel):
    """Schema-backed model for `activities_trend.schema.json`."""

    __schema_file__ = "activities_trend.schema.json"


class AdvisoryMemoryInterfaceModel(JsonSchemaArtifactModel):
    """Schema-backed model for `advisory_memory.schema.json`."""

    __schema_file__ = "advisory_memory.schema.json"


class ArtefactEnvelopeModel(JsonSchemaArtifactModel):
    """Schema-backed model for `artefact_envelope.schema.json`."""

    __schema_file__ = "artefact_envelope.schema.json"


class AthleteProfileModel(JsonSchemaArtifactModel):
    """Schema-backed model for `athlete_profile.schema.json`."""

    __schema_file__ = "athlete_profile.schema.json"


class AthleteStateSnapshotModel(JsonSchemaArtifactModel):
    """Schema-backed model for `athlete_state_snapshot.schema.json`."""

    __schema_file__ = "athlete_state_snapshot.schema.json"


class AvailabilityModel(JsonSchemaArtifactModel):
    """Schema-backed model for `availability.schema.json`."""

    __schema_file__ = "availability.schema.json"


class CurrentWeekStatusSnapshotModel(JsonSchemaArtifactModel):
    """Schema-backed model for `current_week_status_snapshot.schema.json`."""

    __schema_file__ = "current_week_status_snapshot.schema.json"


class DESAnalysisReportModel(JsonSchemaArtifactModel):
    """Schema-backed model for `des_analysis_report.schema.json`."""

    __schema_file__ = "des_analysis_report.schema.json"


class HistoricalBaselineModel(JsonSchemaArtifactModel):
    """Schema-backed model for `historical_baseline.schema.json`."""

    __schema_file__ = "historical_baseline.schema.json"


class KPIProfileModel(JsonSchemaArtifactModel):
    """Schema-backed model for `kpi_profile.schema.json`."""

    __schema_file__ = "kpi_profile.schema.json"


class LogisticsModel(JsonSchemaArtifactModel):
    """Schema-backed model for `logistics.schema.json`."""

    __schema_file__ = "logistics.schema.json"


class PhaseFeedForwardModel(JsonSchemaArtifactModel):
    """Schema-backed model for `phase_feed_forward.schema.json`."""

    __schema_file__ = "phase_feed_forward.schema.json"


class PhaseGuardrailsModel(JsonSchemaArtifactModel):
    """Schema-backed model for `phase_guardrails.schema.json`."""

    __schema_file__ = "phase_guardrails.schema.json"


class PhasePreviewModel(JsonSchemaArtifactModel):
    """Schema-backed model for `phase_preview.schema.json`."""

    __schema_file__ = "phase_preview.schema.json"


class PhaseStructureModel(JsonSchemaArtifactModel):
    """Schema-backed model for `phase_structure.schema.json`."""

    __schema_file__ = "phase_structure.schema.json"


class PlanningContextSnapshotModel(JsonSchemaArtifactModel):
    """Schema-backed model for `planning_context_snapshot.schema.json`."""

    __schema_file__ = "planning_context_snapshot.schema.json"


class PlanningEventsModel(JsonSchemaArtifactModel):
    """Schema-backed model for `planning_events.schema.json`."""

    __schema_file__ = "planning_events.schema.json"


class SeasonPhaseFeedForwardModel(JsonSchemaArtifactModel):
    """Schema-backed model for `season_phase_feed_forward.schema.json`."""

    __schema_file__ = "season_phase_feed_forward.schema.json"


class SeasonPlanModel(JsonSchemaArtifactModel):
    """Schema-backed model for `season_plan.schema.json`."""

    __schema_file__ = "season_plan.schema.json"


class SeasonScenarioSelectionModel(JsonSchemaArtifactModel):
    """Schema-backed model for `season_scenario_selection.schema.json`."""

    __schema_file__ = "season_scenario_selection.schema.json"


class SeasonScenariosModel(JsonSchemaArtifactModel):
    """Schema-backed model for `season_scenarios.schema.json`."""

    __schema_file__ = "season_scenarios.schema.json"


class WeekPlanModel(JsonSchemaArtifactModel):
    """Schema-backed model for `week_plan.schema.json`."""

    __schema_file__ = "week_plan.schema.json"


class WellnessModel(JsonSchemaArtifactModel):
    """Schema-backed model for `wellness.schema.json`."""

    __schema_file__ = "wellness.schema.json"


class ZoneModel(JsonSchemaArtifactModel):
    """Schema-backed model for `zone_model.schema.json`."""

    __schema_file__ = "zone_model.schema.json"


ARTIFACT_MODEL_BY_SCHEMA_FILE: dict[str, type[JsonSchemaArtifactModel]] = {
    "activities_actual.schema.json": ActivitiesActualModel,
    "activities_trend.schema.json": ActivitiesTrendModel,
    "advisory_memory.schema.json": AdvisoryMemoryInterfaceModel,
    "artefact_envelope.schema.json": ArtefactEnvelopeModel,
    "athlete_profile.schema.json": AthleteProfileModel,
    "athlete_state_snapshot.schema.json": AthleteStateSnapshotModel,
    "availability.schema.json": AvailabilityModel,
    "current_week_status_snapshot.schema.json": CurrentWeekStatusSnapshotModel,
    "des_analysis_report.schema.json": DESAnalysisReportModel,
    "historical_baseline.schema.json": HistoricalBaselineModel,
    "kpi_profile.schema.json": KPIProfileModel,
    "logistics.schema.json": LogisticsModel,
    "phase_feed_forward.schema.json": PhaseFeedForwardModel,
    "phase_guardrails.schema.json": PhaseGuardrailsModel,
    "phase_preview.schema.json": PhasePreviewModel,
    "phase_structure.schema.json": PhaseStructureModel,
    "planning_context_snapshot.schema.json": PlanningContextSnapshotModel,
    "planning_events.schema.json": PlanningEventsModel,
    "season_phase_feed_forward.schema.json": SeasonPhaseFeedForwardModel,
    "season_plan.schema.json": SeasonPlanModel,
    "season_scenario_selection.schema.json": SeasonScenarioSelectionModel,
    "season_scenarios.schema.json": SeasonScenariosModel,
    "week_plan.schema.json": WeekPlanModel,
    "wellness.schema.json": WellnessModel,
    "zone_model.schema.json": ZoneModel,
}

ARTIFACT_MODEL_BY_TYPE: dict[str, type[JsonSchemaArtifactModel]] = {
    "ACTIVITIES_ACTUAL": ActivitiesActualModel,
    "ACTIVITIES_TREND": ActivitiesTrendModel,
    "ADVISORY_MEMORY": AdvisoryMemoryInterfaceModel,
    "ATHLETE_PROFILE": AthleteProfileModel,
    "ATHLETE_STATE_SNAPSHOT": AthleteStateSnapshotModel,
    "AVAILABILITY": AvailabilityModel,
    "CURRENT_WEEK_STATUS_SNAPSHOT": CurrentWeekStatusSnapshotModel,
    "DES_ANALYSIS_REPORT": DESAnalysisReportModel,
    "HISTORICAL_BASELINE": HistoricalBaselineModel,
    "KPI_PROFILE": KPIProfileModel,
    "LOGISTICS": LogisticsModel,
    "PHASE_FEED_FORWARD": PhaseFeedForwardModel,
    "PHASE_GUARDRAILS": PhaseGuardrailsModel,
    "PHASE_PREVIEW": PhasePreviewModel,
    "PHASE_STRUCTURE": PhaseStructureModel,
    "PLANNING_CONTEXT_SNAPSHOT": PlanningContextSnapshotModel,
    "PLANNING_EVENTS": PlanningEventsModel,
    "SEASON_PHASE_FEED_FORWARD": SeasonPhaseFeedForwardModel,
    "SEASON_PLAN": SeasonPlanModel,
    "SEASON_SCENARIO_SELECTION": SeasonScenarioSelectionModel,
    "SEASON_SCENARIOS": SeasonScenariosModel,
    "WEEK_PLAN": WeekPlanModel,
    "WELLNESS": WellnessModel,
    "ZONE_MODEL": ZoneModel,
}

ARTIFACT_MODEL_BY_TASK_NAME: dict[str, type[JsonSchemaArtifactModel]] = {
    "des_analysis_report": DESAnalysisReportModel,
    "phase_feed_forward": PhaseFeedForwardModel,
    "phase_guardrails": PhaseGuardrailsModel,
    "phase_preview": PhasePreviewModel,
    "phase_structure": PhaseStructureModel,
    "season_phase_feed_forward": SeasonPhaseFeedForwardModel,
    "season_plan": SeasonPlanModel,
    "season_scenario_selection": SeasonScenarioSelectionModel,
    "season_scenarios": SeasonScenariosModel,
    "week_plan": WeekPlanModel,
}

def artifact_model_for_schema_file(schema_file: str | None) -> type[Any]:
    """Return the generated artifact model for a schema file, or the generic fallback."""

    if schema_file and schema_file in ARTIFACT_MODEL_BY_SCHEMA_FILE:
        return ARTIFACT_MODEL_BY_SCHEMA_FILE[schema_file]
    return ArtifactEnvelopeModel


def artifact_model_for_task_name(task_name: str | None) -> type[Any]:
    """Return the generated artifact model for a CrewAI task name, or the generic fallback."""

    if task_name and task_name in ARTIFACT_MODEL_BY_TASK_NAME:
        return ARTIFACT_MODEL_BY_TASK_NAME[task_name]
    return ArtifactEnvelopeModel
