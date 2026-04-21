"""Deterministic validation for planner workout text and export preconditions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TypeAlias

JsonMap: TypeAlias = dict[str, object]

ALLOWED_SECTION_HEADERS = {
    "Warmup",
    "#### Activation",
    "Main Set",
    "#### Add-On",
    "#### Z2 Add-On",
    "Cooldown",
}
LOOP_LINE_RE = re.compile(r"^\d+[xX]$")
DURATION_RE = re.compile(
    r"(?:(?:\d+(?:\.\d+)?(?:s|m|h))|(?:\d+m\d+)|(?:\d+h\d+m))"
)
PERCENT_TARGET_RE = re.compile(r"\d+(?:\.\d+)?%(?:-\d+(?:\.\d+)?%)?")
RAMP_TARGET_RE = re.compile(r"ramp \d+(?:\.\d+)?%(?:-\d+(?:\.\d+)?%)?")
CADENCE_RE = re.compile(r"\d+(?:-\d+)?rpm")
STEP_LINE_RE = re.compile(
    r"^- "
    r"(?:(?P<duration>(?:\d+(?:\.\d+)?(?:s|m|h)|\d+m\d+|\d+h\d+m)) )?"
    r"(?:(?P<ramp>ramp \d+(?:\.\d+)?%(?:-\d+(?:\.\d+)?%)?)|(?P<target>\d+(?:\.\d+)?%(?:-\d+(?:\.\d+)?%)?)) "
    r"(?P<cadence>\d+(?:-\d+)?rpm)"
    r"(?: (?P<flags>intensity=(?:warmup|recovery|interval|cooldown)))?"
    r"$"
)
FORBIDDEN_STEP_TOKENS = (
    "@",
    " cadence",
    " freeride",
    " freeRide",
    "/km",
    "/mi",
    "/100m",
    "/500m",
    " FTP",
    " HR",
    " LTHR",
    " Pace",
)
FORBIDDEN_ZONE_RE = re.compile(r"\b[zZ][1-7]\b")
FORBIDDEN_CLOCK_RE = re.compile(r"\b\d{2}:\d{2}(?::\d{2})?\b")
FORBIDDEN_WATTS_RE = re.compile(r"\b\d+(?:\.\d+)?[wW]\b")


class WorkoutValidationError(ValueError):
    """Raised when workout export preconditions are not satisfied."""


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


def validate_week_plan_exportability(week_plan: JsonMap) -> None:
    """Validate agenda/workout references and each workout text before export."""
    issues = collect_week_plan_export_issues(week_plan)
    if issues:
        raise WorkoutValidationError("; ".join(issue.format() for issue in issues))


def collect_week_plan_export_issues(week_plan: JsonMap) -> list[WorkoutValidationIssue]:
    """Collect deterministic export issues for the given week plan."""
    data = week_plan.get("data")
    if not isinstance(data, dict):
        return [WorkoutValidationIssue("WEEK_PLAN", "missing data object")]

    agenda = data.get("agenda")
    workouts = data.get("workouts")
    if not isinstance(agenda, list) or not isinstance(workouts, list):
        return [WorkoutValidationIssue("WEEK_PLAN", "missing agenda or workouts list")]

    workout_map: dict[str, JsonMap] = {}
    issues: list[WorkoutValidationIssue] = []
    for workout in workouts:
        if not isinstance(workout, dict):
            issues.append(WorkoutValidationIssue("UNKNOWN", "workout entry must be an object"))
            continue
        workout_id = str(workout.get("workout_id") or "").strip()
        if not workout_id:
            issues.append(WorkoutValidationIssue("UNKNOWN", "workout_id missing"))
            continue
        if workout_id in workout_map:
            issues.append(WorkoutValidationIssue(workout_id, "duplicate workout_id"))
            continue
        workout_map[workout_id] = workout

    referenced_ids = [
        str(entry.get("workout_id") or "").strip()
        for entry in agenda
        if isinstance(entry, dict) and entry.get("workout_id") is not None
    ]
    for workout_id in referenced_ids:
        if workout_id not in workout_map:
            issues.append(WorkoutValidationIssue(workout_id, "agenda references missing workout definition"))

    for workout_id in workout_map:
        if workout_id not in referenced_ids:
            issues.append(WorkoutValidationIssue(workout_id, "workout definition is not referenced in agenda"))

    for workout_id in referenced_ids:
        workout = workout_map.get(workout_id)
        if workout is None:
            continue
        issues.extend(validate_workout_definition(workout))

    return issues


def validate_workout_definition(workout: JsonMap) -> list[WorkoutValidationIssue]:
    """Validate one workout object and its workout_text."""
    workout_id = str(workout.get("workout_id") or "UNKNOWN").strip() or "UNKNOWN"
    text = workout.get("workout_text")
    if not isinstance(text, str) or not text.strip():
        return [WorkoutValidationIssue(workout_id, "workout_text missing or empty")]
    return validate_workout_text(workout_id, text)


def validate_workout_text(workout_id: str, text: str) -> list[WorkoutValidationIssue]:
    """Validate workout text against the project subset used for cycling export."""
    issues: list[WorkoutValidationIssue] = []
    seen_structural_line = False
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if stripped in ALLOWED_SECTION_HEADERS:
            seen_structural_line = True
            continue
        if LOOP_LINE_RE.fullmatch(stripped):
            seen_structural_line = True
            continue
        if stripped.startswith("- "):
            seen_structural_line = True
            issues.extend(_validate_step_line(workout_id, stripped, line_number))
            continue
        issues.append(
            WorkoutValidationIssue(
                workout_id,
                "unsupported non-empty line",
                line=stripped,
                line_number=line_number,
            )
        )
    if not seen_structural_line:
        issues.append(WorkoutValidationIssue(workout_id, "workout_text has no sections, loops, or step lines"))
    return issues


def _validate_step_line(workout_id: str, line: str, line_number: int) -> list[WorkoutValidationIssue]:
    """Validate one step line from workout text."""
    issues: list[WorkoutValidationIssue] = []
    lowered = f" {line.lower()} "
    for token in FORBIDDEN_STEP_TOKENS:
        if token.lower() in lowered:
            issues.append(
                WorkoutValidationIssue(
                    workout_id,
                    f"forbidden token in step line: {token.strip()}",
                    line=line,
                    line_number=line_number,
                )
            )
    if FORBIDDEN_ZONE_RE.search(line):
        issues.append(
            WorkoutValidationIssue(
                workout_id,
                "zone shorthand is forbidden in step lines",
                line=line,
                line_number=line_number,
            )
        )
    if FORBIDDEN_CLOCK_RE.search(line):
        issues.append(
            WorkoutValidationIssue(
                workout_id,
                "clock-style duration is forbidden in step lines",
                line=line,
                line_number=line_number,
            )
        )
    if FORBIDDEN_WATTS_RE.search(line):
        issues.append(
            WorkoutValidationIssue(
                workout_id,
                "absolute watts are forbidden in step lines",
                line=line,
                line_number=line_number,
            )
        )

    match = STEP_LINE_RE.fullmatch(line)
    if not match:
        issues.append(
            WorkoutValidationIssue(
                workout_id,
                "step line does not match the cycling workout subset",
                line=line,
                line_number=line_number,
            )
        )
        return issues

    duration = match.group("duration")
    if duration and not DURATION_RE.fullmatch(duration):
        issues.append(
            WorkoutValidationIssue(
                workout_id,
                "invalid duration token",
                line=line,
                line_number=line_number,
            )
        )

    target = match.group("ramp") or match.group("target")
    if target is None:
        issues.append(
            WorkoutValidationIssue(
                workout_id,
                "step line is missing a power target",
                line=line,
                line_number=line_number,
            )
        )
    elif target.startswith("ramp "):
        if not RAMP_TARGET_RE.fullmatch(target):
            issues.append(
                WorkoutValidationIssue(
                    workout_id,
                    "invalid ramp target",
                    line=line,
                    line_number=line_number,
                )
            )
    elif not PERCENT_TARGET_RE.fullmatch(target):
        issues.append(
            WorkoutValidationIssue(
                workout_id,
                "invalid power-percent target",
                line=line,
                line_number=line_number,
            )
        )

    cadence = match.group("cadence")
    if cadence is None or not CADENCE_RE.fullmatch(cadence):
        issues.append(
            WorkoutValidationIssue(
                workout_id,
                "step line is missing valid cadence",
                line=line,
                line_number=line_number,
            )
        )

    return issues
