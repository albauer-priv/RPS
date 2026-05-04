"""Shared workout validation issue types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkoutValidationIssue:
    """A deterministic validation issue for one workout or workout line."""

    workout_id: str
    message: str
    line: str | None = None
    line_number: int | None = None

    def format(self) -> str:
        """Return a stable human-readable error string."""
        prefix = f"{self.workout_id}: {self.message}"
        if self.line_number is None:
            return prefix
        return f"{prefix} (line {self.line_number}: {self.line or ''})"
