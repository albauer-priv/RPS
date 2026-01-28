"""Task definitions and schema bindings for strict agent outputs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from rps.workspace.types import ArtifactType


class AgentTask(str, Enum):
    """Named tasks that an agent can execute."""
    CREATE_SEASON_SCENARIOS = "CREATE_SEASON_SCENARIOS"
    CREATE_SEASON_SCENARIO_SELECTION = "CREATE_SEASON_SCENARIO_SELECTION"
    CREATE_SEASON_PLAN = "CREATE_SEASON_PLAN"
    CREATE_MACRO_MESO_FEED_FORWARD = "CREATE_MACRO_MESO_FEED_FORWARD"

    CREATE_PHASE_GUARDRAILS = "CREATE_PHASE_GUARDRAILS"
    CREATE_PHASE_STRUCTURE = "CREATE_PHASE_STRUCTURE"
    CREATE_PHASE_PREVIEW = "CREATE_PHASE_PREVIEW"
    CREATE_BLOCK_FEED_FORWARD = "CREATE_BLOCK_FEED_FORWARD"
    CREATE_ZONE_MODEL = "CREATE_ZONE_MODEL"

    CREATE_WEEK_PLAN = "CREATE_WEEK_PLAN"

    CREATE_INTERVALS_WORKOUTS_EXPORT = "CREATE_INTERVALS_WORKOUTS_EXPORT"

    CREATE_ACTIVITIES_TREND = "CREATE_ACTIVITIES_TREND"
    CREATE_DES_ANALYSIS_REPORT = "CREATE_DES_ANALYSIS_REPORT"


@dataclass(frozen=True)
class OutputSpec:
    """Defines how a task maps to artifact schema and tool metadata."""
    task: AgentTask
    artifact_type: ArtifactType
    schema_file: str
    tool_name: str
    envelope: bool


OUTPUT_SPECS: dict[AgentTask, OutputSpec] = {
    AgentTask.CREATE_SEASON_SCENARIOS: OutputSpec(
        task=AgentTask.CREATE_SEASON_SCENARIOS,
        artifact_type=ArtifactType.SEASON_SCENARIOS,
        schema_file="season_scenarios.schema.json",
        tool_name="store_season_scenarios",
        envelope=True,
    ),
    AgentTask.CREATE_SEASON_SCENARIO_SELECTION: OutputSpec(
        task=AgentTask.CREATE_SEASON_SCENARIO_SELECTION,
        artifact_type=ArtifactType.SEASON_SCENARIO_SELECTION,
        schema_file="season_scenario_selection.schema.json",
        tool_name="store_season_scenario_selection",
        envelope=True,
    ),
    AgentTask.CREATE_SEASON_PLAN: OutputSpec(
        task=AgentTask.CREATE_SEASON_PLAN,
        artifact_type=ArtifactType.SEASON_PLAN,
        schema_file="season_plan.schema.json",
        tool_name="store_season_plan",
        envelope=True,
    ),
    AgentTask.CREATE_MACRO_MESO_FEED_FORWARD: OutputSpec(
        task=AgentTask.CREATE_MACRO_MESO_FEED_FORWARD,
        artifact_type=ArtifactType.MACRO_MESO_FEED_FORWARD,
        schema_file="macro_meso_feed_forward.schema.json",
        tool_name="store_macro_meso_feed_forward",
        envelope=True,
    ),
    AgentTask.CREATE_PHASE_GUARDRAILS: OutputSpec(
        task=AgentTask.CREATE_PHASE_GUARDRAILS,
        artifact_type=ArtifactType.PHASE_GUARDRAILS,
        schema_file="phase_guardrails.schema.json",
        tool_name="store_phase_guardrails",
        envelope=True,
    ),
    AgentTask.CREATE_PHASE_STRUCTURE: OutputSpec(
        task=AgentTask.CREATE_PHASE_STRUCTURE,
        artifact_type=ArtifactType.PHASE_STRUCTURE,
        schema_file="phase_structure.schema.json",
        tool_name="store_phase_structure",
        envelope=True,
    ),
    AgentTask.CREATE_PHASE_PREVIEW: OutputSpec(
        task=AgentTask.CREATE_PHASE_PREVIEW,
        artifact_type=ArtifactType.PHASE_PREVIEW,
        schema_file="phase_preview.schema.json",
        tool_name="store_phase_preview",
        envelope=True,
    ),
    AgentTask.CREATE_BLOCK_FEED_FORWARD: OutputSpec(
        task=AgentTask.CREATE_BLOCK_FEED_FORWARD,
        artifact_type=ArtifactType.BLOCK_FEED_FORWARD,
        schema_file="block_feed_forward.schema.json",
        tool_name="store_block_feed_forward",
        envelope=True,
    ),
    AgentTask.CREATE_ZONE_MODEL: OutputSpec(
        task=AgentTask.CREATE_ZONE_MODEL,
        artifact_type=ArtifactType.ZONE_MODEL,
        schema_file="zone_model.schema.json",
        tool_name="store_zone_model",
        envelope=True,
    ),
    AgentTask.CREATE_WEEK_PLAN: OutputSpec(
        task=AgentTask.CREATE_WEEK_PLAN,
        artifact_type=ArtifactType.WEEK_PLAN,
        schema_file="week_plan.schema.json",
        tool_name="store_week_plan",
        envelope=True,
    ),
    AgentTask.CREATE_INTERVALS_WORKOUTS_EXPORT: OutputSpec(
        task=AgentTask.CREATE_INTERVALS_WORKOUTS_EXPORT,
        artifact_type=ArtifactType.INTERVALS_WORKOUTS,
        schema_file="workouts.schema.json",
        tool_name="store_intervals_workouts_export",
        envelope=False,
    ),
    AgentTask.CREATE_ACTIVITIES_TREND: OutputSpec(
        task=AgentTask.CREATE_ACTIVITIES_TREND,
        artifact_type=ArtifactType.ACTIVITIES_TREND,
        schema_file="activities_trend.schema.json",
        tool_name="store_activities_trend",
        envelope=True,
    ),
    AgentTask.CREATE_DES_ANALYSIS_REPORT: OutputSpec(
        task=AgentTask.CREATE_DES_ANALYSIS_REPORT,
        artifact_type=ArtifactType.DES_ANALYSIS_REPORT,
        schema_file="des_analysis_report.schema.json",
        tool_name="store_des_analysis_report",
        envelope=True,
    ),
}
