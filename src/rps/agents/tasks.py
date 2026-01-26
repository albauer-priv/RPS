"""Task definitions and schema bindings for strict agent outputs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from rps.workspace.types import ArtifactType


class AgentTask(str, Enum):
    """Named tasks that an agent can execute."""
    CREATE_SEASON_SCENARIOS = "CREATE_SEASON_SCENARIOS"
    CREATE_SEASON_SCENARIO_SELECTION = "CREATE_SEASON_SCENARIO_SELECTION"
    CREATE_MACRO_OVERVIEW = "CREATE_MACRO_OVERVIEW"
    CREATE_MACRO_MESO_FEED_FORWARD = "CREATE_MACRO_MESO_FEED_FORWARD"

    CREATE_BLOCK_GOVERNANCE = "CREATE_BLOCK_GOVERNANCE"
    CREATE_BLOCK_EXECUTION_ARCH = "CREATE_BLOCK_EXECUTION_ARCH"
    CREATE_BLOCK_EXECUTION_PREVIEW = "CREATE_BLOCK_EXECUTION_PREVIEW"
    CREATE_BLOCK_FEED_FORWARD = "CREATE_BLOCK_FEED_FORWARD"
    CREATE_ZONE_MODEL = "CREATE_ZONE_MODEL"

    CREATE_WORKOUTS_PLAN = "CREATE_WORKOUTS_PLAN"

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
    AgentTask.CREATE_MACRO_OVERVIEW: OutputSpec(
        task=AgentTask.CREATE_MACRO_OVERVIEW,
        artifact_type=ArtifactType.MACRO_OVERVIEW,
        schema_file="macro_overview.schema.json",
        tool_name="store_macro_overview",
        envelope=True,
    ),
    AgentTask.CREATE_MACRO_MESO_FEED_FORWARD: OutputSpec(
        task=AgentTask.CREATE_MACRO_MESO_FEED_FORWARD,
        artifact_type=ArtifactType.MACRO_MESO_FEED_FORWARD,
        schema_file="macro_meso_feed_forward.schema.json",
        tool_name="store_macro_meso_feed_forward",
        envelope=True,
    ),
    AgentTask.CREATE_BLOCK_GOVERNANCE: OutputSpec(
        task=AgentTask.CREATE_BLOCK_GOVERNANCE,
        artifact_type=ArtifactType.BLOCK_GOVERNANCE,
        schema_file="block_governance.schema.json",
        tool_name="store_block_governance",
        envelope=True,
    ),
    AgentTask.CREATE_BLOCK_EXECUTION_ARCH: OutputSpec(
        task=AgentTask.CREATE_BLOCK_EXECUTION_ARCH,
        artifact_type=ArtifactType.BLOCK_EXECUTION_ARCH,
        schema_file="block_execution_arch.schema.json",
        tool_name="store_block_execution_arch",
        envelope=True,
    ),
    AgentTask.CREATE_BLOCK_EXECUTION_PREVIEW: OutputSpec(
        task=AgentTask.CREATE_BLOCK_EXECUTION_PREVIEW,
        artifact_type=ArtifactType.BLOCK_EXECUTION_PREVIEW,
        schema_file="block_execution_preview.schema.json",
        tool_name="store_block_execution_preview",
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
    AgentTask.CREATE_WORKOUTS_PLAN: OutputSpec(
        task=AgentTask.CREATE_WORKOUTS_PLAN,
        artifact_type=ArtifactType.WORKOUTS_PLAN,
        schema_file="workouts_plan.schema.json",
        tool_name="store_workouts_plan",
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
