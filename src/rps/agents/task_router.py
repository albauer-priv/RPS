"""Rule-based task routing for agents."""

from __future__ import annotations

from dataclasses import dataclass

from rps.agents.tasks import AgentTask
from rps.workspace.api import Workspace
from rps.workspace.index_exact import IndexExactQuery
from rps.workspace.iso_helpers import IsoWeek
from rps.workspace.season_plan_service import resolve_phase_range_from_season_plan
from rps.workspace.types import ArtifactType


@dataclass
class RouterContext:
    """Context for routing decisions."""
    workspace: Workspace


class AgentTaskRouter:
    """Routes tasks for each agent based on workspace state."""

    def __init__(self, ctx: RouterContext):
        """Initialize with routing context."""
        self.ctx = ctx

    def _week_version_exists(self, artifact_type: ArtifactType, target: IsoWeek) -> bool:
        """Return whether a week-scoped artefact exists for the target ISO week."""
        version_key = f"{target.year:04d}-{target.week:02d}"
        resolved = self.ctx.workspace.store.resolve_week_version_key(
            self.ctx.workspace.athlete_id,
            artifact_type,
            version_key,
        )
        return bool(resolved)

    def route_season(self, target: IsoWeek) -> list[AgentTask]:
        """Return season-plan tasks required for the target week."""
        tasks: list[AgentTask] = []

        if not self.ctx.workspace.latest_exists(ArtifactType.SEASON_PLAN):
            tasks.append(AgentTask.CREATE_SEASON_PLAN)

        if (
            self.ctx.workspace.latest_exists(ArtifactType.DES_ANALYSIS_REPORT)
            and not self.ctx.workspace.latest_exists(ArtifactType.SEASON_PHASE_FEED_FORWARD)
        ):
            pass

        return tasks

    def route_phase(self, target: IsoWeek) -> list[AgentTask]:
        """Return phase tasks required for the target week."""
        tasks: list[AgentTask] = []

        if not self.ctx.workspace.latest_exists(ArtifactType.SEASON_PLAN):
            return tasks

        season_plan = self.ctx.workspace.get_latest(ArtifactType.SEASON_PLAN)
        if not isinstance(season_plan, dict):
            return tasks
        phase_range = resolve_phase_range_from_season_plan(season_plan, target, phase_len=4)

        index_query = IndexExactQuery(
            root=self.ctx.workspace.store.root,
            athlete_id=self.ctx.workspace.athlete_id,
        )

        if not index_query.has_exact_range(ArtifactType.PHASE_GUARDRAILS.value, phase_range):
            tasks.append(AgentTask.CREATE_PHASE_GUARDRAILS)

        if not index_query.has_exact_range(ArtifactType.PHASE_STRUCTURE.value, phase_range):
            tasks.append(AgentTask.CREATE_PHASE_STRUCTURE)

        if not index_query.has_exact_range(ArtifactType.PHASE_PREVIEW.value, phase_range):
            tasks.append(AgentTask.CREATE_PHASE_PREVIEW)

        if self._week_version_exists(ArtifactType.SEASON_PHASE_FEED_FORWARD, target):
            tasks.append(AgentTask.CREATE_PHASE_FEED_FORWARD)

        return tasks

    def route_week(self, target: IsoWeek) -> list[AgentTask]:
        """Return week tasks required for the target week."""
        tasks: list[AgentTask] = []

        if not self.ctx.workspace.latest_exists(ArtifactType.SEASON_PLAN):
            return tasks

        season_plan = self.ctx.workspace.get_latest(ArtifactType.SEASON_PLAN)
        if not isinstance(season_plan, dict):
            return tasks

        phase_range = resolve_phase_range_from_season_plan(season_plan, target, phase_len=4)
        index_query = IndexExactQuery(
            root=self.ctx.workspace.store.root,
            athlete_id=self.ctx.workspace.athlete_id,
        )
        if not (
            index_query.has_exact_range(ArtifactType.PHASE_GUARDRAILS.value, phase_range)
            and index_query.has_exact_range(ArtifactType.PHASE_STRUCTURE.value, phase_range)
        ):
            return tasks

        if self._week_version_exists(ArtifactType.WEEK_PLAN, target):
            return tasks

        tasks.append(AgentTask.CREATE_WEEK_PLAN)
        return tasks

    def route_workout_export(self, target: IsoWeek) -> list[AgentTask]:
        """Return workout-export tasks required for the target week."""
        tasks: list[AgentTask] = []

        if not self._week_version_exists(ArtifactType.WEEK_PLAN, target):
            return tasks

        tasks.append(AgentTask.BUILD_WORKOUT_EXPORT)
        return tasks

    def route_analysis(self, target: IsoWeek) -> list[AgentTask]:
        """Return analysis tasks required for the target week."""
        tasks: list[AgentTask] = []

        required = [
            ArtifactType.KPI_PROFILE,
            ArtifactType.SEASON_PLAN,
        ]
        if not all(self.ctx.workspace.latest_exists(item) for item in required):
            return tasks
        if not (
            self._week_version_exists(ArtifactType.ACTIVITIES_ACTUAL, target)
            and self._week_version_exists(ArtifactType.ACTIVITIES_TREND, target)
        ):
            return tasks

        if self._week_version_exists(ArtifactType.DES_ANALYSIS_REPORT, target):
            return tasks

        tasks.append(AgentTask.CREATE_DES_ANALYSIS_REPORT)
        return tasks
