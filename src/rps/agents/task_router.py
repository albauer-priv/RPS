"""Rule-based task routing for agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from rps.agents.tasks import AgentTask
from rps.workspace.api import Workspace
from rps.workspace.index_exact import IndexExactQuery
from rps.workspace.season_plan_service import resolve_phase_range_from_season_plan
from rps.workspace.iso_helpers import IsoWeek, envelope_week
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

    def route_season(self, target: IsoWeek) -> List[AgentTask]:
        """Return season-plan tasks required for the target week."""
        tasks: List[AgentTask] = []

        if not self.ctx.workspace.latest_exists(ArtifactType.SEASON_PLAN):
            tasks.append(AgentTask.CREATE_SEASON_PLAN)

        if (
            self.ctx.workspace.latest_exists(ArtifactType.DES_ANALYSIS_REPORT)
            and not self.ctx.workspace.latest_exists(ArtifactType.SEASON_PHASE_FEED_FORWARD)
        ):
            pass

        return tasks

    def route_phase(self, target: IsoWeek) -> List[AgentTask]:
        """Return phase tasks required for the target week."""
        tasks: List[AgentTask] = []

        if not self.ctx.workspace.latest_exists(ArtifactType.SEASON_PLAN):
            return tasks

        season_plan = self.ctx.workspace.get_latest(ArtifactType.SEASON_PLAN)
        phase_range = resolve_phase_range_from_season_plan(season_plan, target, phase_len=4)

        index_query = IndexExactQuery(
            root=self.ctx.workspace.store.root,
            athlete_id=self.ctx.workspace.athlete_id,
        )

        if not index_query.has_exact_range(ArtifactType.PHASE_GUARDRAILS.value, phase_range):
            tasks.append(AgentTask.CREATE_PHASE_GUARDRAILS)

        if not index_query.has_exact_range(ArtifactType.PHASE_STRUCTURE.value, phase_range):
            tasks.append(AgentTask.CREATE_PHASE_STRUCTURE)

        if not self.ctx.workspace.latest_exists(ArtifactType.PHASE_PREVIEW):
            tasks.append(AgentTask.CREATE_PHASE_PREVIEW)

        if self.ctx.workspace.latest_exists(ArtifactType.SEASON_PHASE_FEED_FORWARD):
            tasks.append(AgentTask.CREATE_PHASE_FEED_FORWARD)

        return tasks

    def route_week(self, target: IsoWeek) -> List[AgentTask]:
        """Return week tasks required for the target week."""
        tasks: List[AgentTask] = []

        if not (
            self.ctx.workspace.latest_exists(ArtifactType.PHASE_GUARDRAILS)
            and self.ctx.workspace.latest_exists(ArtifactType.PHASE_STRUCTURE)
        ):
            return tasks

        if self.ctx.workspace.latest_exists(ArtifactType.WEEK_PLAN):
            plan = self.ctx.workspace.get_latest(ArtifactType.WEEK_PLAN)
            week = envelope_week(plan)
            if week and (week.year == target.year and week.week == target.week):
                return tasks

        tasks.append(AgentTask.CREATE_WEEK_PLAN)
        return tasks

    def route_builder(self, _target: IsoWeek) -> List[AgentTask]:
        """Return builder tasks required for the target week."""
        tasks: List[AgentTask] = []

        if not self.ctx.workspace.latest_exists(ArtifactType.WEEK_PLAN):
            return tasks

        tasks.append(AgentTask.CREATE_INTERVALS_WORKOUTS_EXPORT)
        return tasks

    def route_analysis(self, target: IsoWeek) -> List[AgentTask]:
        """Return analysis tasks required for the target week."""
        tasks: List[AgentTask] = []

        required = [
            ArtifactType.ACTIVITIES_ACTUAL,
            ArtifactType.ACTIVITIES_TREND,
            ArtifactType.KPI_PROFILE,
            ArtifactType.SEASON_PLAN,
            ArtifactType.PHASE_GUARDRAILS,
            ArtifactType.PHASE_STRUCTURE,
        ]
        if not all(self.ctx.workspace.latest_exists(item) for item in required):
            return tasks

        if self.ctx.workspace.latest_exists(ArtifactType.DES_ANALYSIS_REPORT):
            report = self.ctx.workspace.get_latest(ArtifactType.DES_ANALYSIS_REPORT)
            week = envelope_week(report)
            if week and (week.year == target.year and week.week == target.week):
                return tasks

        tasks.append(AgentTask.CREATE_DES_ANALYSIS_REPORT)
        return tasks
