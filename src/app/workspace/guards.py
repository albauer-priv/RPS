"""Dependency guard rules for workspace writes."""

from __future__ import annotations

from dataclasses import dataclass

from .types import ArtifactType


class MissingDependenciesError(RuntimeError):
    """Raised when required upstream artifacts are missing."""

    def __init__(self, message: str, missing: list[str]):
        """Initialize with a message and a list of missing artifacts."""
        super().__init__(message)
        self.missing = missing


@dataclass(frozen=True)
class DependencyRule:
    """Defines required latest dependencies for a target artifact type."""

    target: ArtifactType
    requires_latest: tuple[ArtifactType, ...]


DEFAULT_RULES: list[DependencyRule] = [
    DependencyRule(
        target=ArtifactType.WORKOUTS_PLAN,
        requires_latest=(ArtifactType.BLOCK_EXECUTION_ARCH,),
    ),
    DependencyRule(
        target=ArtifactType.INTERVALS_WORKOUTS,
        requires_latest=(ArtifactType.WORKOUTS_PLAN,),
    ),
    DependencyRule(
        target=ArtifactType.DES_ANALYSIS_REPORT,
        requires_latest=(ArtifactType.ACTIVITIES_TREND, ArtifactType.WORKOUTS_PLAN),
    ),
]
