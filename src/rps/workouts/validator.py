"""Deterministic validation for planner workout text and export preconditions."""

from __future__ import annotations

import re
from typing import TypeAlias

from rps.workouts.issues import WorkoutValidationIssue

JsonMap: TypeAlias = dict[str, object]

ALLOWED_SECTION_HEADERS = {
    "Warmup",
    "Activation",
    "#### Activation",
    "Main Set",
    "Add-On",
    "#### Add-On",
    "Z2 Add-On",
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
    r"(?P<duration>(?:\d+(?:\.\d+)?(?:s|m|h)|\d+m\d+|\d+h\d+m)) "
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
from rps.workouts.week_plan_consistency import collect_week_plan_consistency_issues

SECTION_ORDER = {
    "Warmup": 1,
    "Activation": 2,
    "Main Set": 3,
    "Add-On": 4,
    "Z2 Add-On": 4,
    "Cooldown": 5,
}
ACTIVATION_REQUIRED_DOMAINS = {"VO2MAX", "THRESHOLD", "SWEET_SPOT"}


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

    issues.extend(collect_week_plan_consistency_issues(week_plan))

    return issues


def validate_workout_definition(workout: JsonMap) -> list[WorkoutValidationIssue]:
    """Validate one workout object and its workout_text."""
    workout_id = str(workout.get("workout_id") or "UNKNOWN").strip() or "UNKNOWN"
    text = workout.get("workout_text")
    if not isinstance(text, str) or not text.strip():
        return [WorkoutValidationIssue(workout_id, "workout_text missing or empty")]
    context_text = " ".join(
        str(workout.get(key) or "")
        for key in ("title", "notes")
    )
    return validate_workout_text(workout_id, text, context_text=context_text)


def validate_workout_text(workout_id: str, text: str, *, context_text: str = "") -> list[WorkoutValidationIssue]:
    """Validate workout text against the project subset used for cycling export."""
    issues: list[WorkoutValidationIssue] = []
    seen_structural_line = False
    seen_sections: list[tuple[str, int]] = []
    last_section_order = 0
    active_loop = False
    active_loop_line: int | None = None
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            active_loop = False
            active_loop_line = None
            continue
        if stripped in ALLOWED_SECTION_HEADERS:
            seen_structural_line = True
            section = _normalize_section_header(stripped)
            section_order = SECTION_ORDER.get(section, 0)
            if section_order < last_section_order:
                issues.append(
                    WorkoutValidationIssue(
                        workout_id,
                        "workout sections are out of policy order",
                        line=stripped,
                        line_number=line_number,
                    )
                )
            last_section_order = max(last_section_order, section_order)
            seen_sections.append((section, line_number))
            active_loop = False
            active_loop_line = None
            continue
        if LOOP_LINE_RE.fullmatch(stripped):
            seen_structural_line = True
            if active_loop:
                issues.append(
                    WorkoutValidationIssue(
                        workout_id,
                        "nested or adjacent loop declarations are forbidden",
                        line=stripped,
                        line_number=line_number,
                    )
                )
            active_loop = True
            active_loop_line = line_number
            continue
        if stripped.startswith("- "):
            seen_structural_line = True
            issues.extend(_validate_step_line(workout_id, stripped, line_number))
            active_loop = False
            active_loop_line = None
            continue
        if active_loop:
            issues.append(
                WorkoutValidationIssue(
                    workout_id,
                    "loop declaration must be followed by workout step lines only",
                    line=stripped,
                    line_number=active_loop_line or line_number,
                )
            )
        active_loop = False
        active_loop_line = None
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
    section_names = [section for section, _line_number in seen_sections]
    for required in ("Warmup", "Main Set", "Cooldown"):
        if required not in section_names:
            issues.append(WorkoutValidationIssue(workout_id, f"workout_text missing required section: {required}"))
    if _activation_required(context_text) and "Activation" not in section_names:
        issues.append(
            WorkoutValidationIssue(
                workout_id,
                "Activation section is required for VO2MAX, THRESHOLD, or SWEET_SPOT workouts",
            )
        )
    return issues


def _normalize_section_header(header: str) -> str:
    return header.removeprefix("#### ").strip()


def _activation_required(context_text: str) -> bool:
    haystack = context_text.upper().replace(" ", "_")
    return any(domain in haystack for domain in ACTIVATION_REQUIRED_DOMAINS)


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
    if duration is None:
        issues.append(
            WorkoutValidationIssue(
                workout_id,
                "step line is missing a duration",
                line=line,
                line_number=line_number,
            )
        )
    elif not DURATION_RE.fullmatch(duration):
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
