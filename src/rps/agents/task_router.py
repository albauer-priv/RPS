"""Rule-based task routing for agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from rps.agents.tasks import AgentTask
from rps.workspace.api import Workspace
from rps.workspace.index_exact import IndexExactQuery
from rps.workspace.macro_phase_service import resolve_block_range_from_macro
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

    def route_macro(self, target: IsoWeek) -> List[AgentTask]:
        """Return macro tasks required for the target week."""
        tasks: List[AgentTask] = []

        if not self.ctx.workspace.latest_exists(ArtifactType.MACRO_OVERVIEW):
            tasks.append(AgentTask.CREATE_MACRO_OVERVIEW)

        if (
            self.ctx.workspace.latest_exists(ArtifactType.DES_ANALYSIS_REPORT)
            and not self.ctx.workspace.latest_exists(ArtifactType.MACRO_MESO_FEED_FORWARD)
        ):
            pass

        return tasks

    def route_meso(self, target: IsoWeek) -> List[AgentTask]:
        """Return meso tasks required for the target week."""
        tasks: List[AgentTask] = []

        if not self.ctx.workspace.latest_exists(ArtifactType.MACRO_OVERVIEW):
            return tasks

        macro = self.ctx.workspace.get_latest(ArtifactType.MACRO_OVERVIEW)
        block_range = resolve_block_range_from_macro(macro, target, block_len=4)

        index_query = IndexExactQuery(
            root=self.ctx.workspace.store.root,
            athlete_id=self.ctx.workspace.athlete_id,
        )

        if not index_query.has_exact_range(ArtifactType.BLOCK_GOVERNANCE.value, block_range):
            tasks.append(AgentTask.CREATE_BLOCK_GOVERNANCE)

        if not index_query.has_exact_range(ArtifactType.BLOCK_EXECUTION_ARCH.value, block_range):
            tasks.append(AgentTask.CREATE_BLOCK_EXECUTION_ARCH)

        if not self.ctx.workspace.latest_exists(ArtifactType.BLOCK_EXECUTION_PREVIEW):
            tasks.append(AgentTask.CREATE_BLOCK_EXECUTION_PREVIEW)

        if self.ctx.workspace.latest_exists(ArtifactType.MACRO_MESO_FEED_FORWARD):
            tasks.append(AgentTask.CREATE_BLOCK_FEED_FORWARD)

        return tasks

    def route_micro(self, target: IsoWeek) -> List[AgentTask]:
        """Return micro tasks required for the target week."""
        tasks: List[AgentTask] = []

        if not (
            self.ctx.workspace.latest_exists(ArtifactType.BLOCK_GOVERNANCE)
            and self.ctx.workspace.latest_exists(ArtifactType.BLOCK_EXECUTION_ARCH)
        ):
            return tasks

        if self.ctx.workspace.latest_exists(ArtifactType.WORKOUTS_PLAN):
            plan = self.ctx.workspace.get_latest(ArtifactType.WORKOUTS_PLAN)
            week = envelope_week(plan)
            if week and (week.year == target.year and week.week == target.week):
                return tasks

        tasks.append(AgentTask.CREATE_WORKOUTS_PLAN)
        return tasks

    def route_builder(self, _target: IsoWeek) -> List[AgentTask]:
        """Return builder tasks required for the target week."""
        tasks: List[AgentTask] = []

        if not self.ctx.workspace.latest_exists(ArtifactType.WORKOUTS_PLAN):
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
            ArtifactType.MACRO_OVERVIEW,
            ArtifactType.BLOCK_GOVERNANCE,
            ArtifactType.BLOCK_EXECUTION_ARCH,
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
