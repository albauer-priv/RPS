"""Structured workout AST, parsing, and canonical rendering for the cycling subset."""

from __future__ import annotations

from dataclasses import dataclass, field

from rps.agents.output_normalization import (
    normalize_workout_inline_loop_headers,
    normalize_workout_percent_ranges,
)
from rps.workouts.validator import (
    ALLOWED_SECTION_HEADERS,
    LOOP_LINE_RE,
    STEP_LINE_RE,
    validate_workout_text,
)

_SECTION_CANONICAL = {
    "Warmup": "Warmup",
    "Activation": "#### Activation",
    "#### Activation": "#### Activation",
    "Main Set": "Main Set",
    "Add-On": "#### Add-On",
    "#### Add-On": "#### Add-On",
    "Z2 Add-On": "#### Z2 Add-On",
    "#### Z2 Add-On": "#### Z2 Add-On",
    "Cooldown": "Cooldown",
}
_CANONICAL_ORDER = (
    "Warmup",
    "#### Activation",
    "Main Set",
    "#### Add-On",
    "#### Z2 Add-On",
    "Cooldown",
)


@dataclass(frozen=True)
class WorkoutStep:
    """One canonical workout step."""

    duration: str
    target: str
    cadence: str
    flags: str | None = None


@dataclass(frozen=True)
class WorkoutLoop:
    """One single-level loop block."""

    count: int
    steps: tuple[WorkoutStep, ...]


WorkoutBlock = WorkoutStep | WorkoutLoop


@dataclass(frozen=True)
class WorkoutSection:
    """One canonical workout section."""

    name: str
    blocks: tuple[WorkoutBlock, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class WorkoutStructure:
    """Canonical workout AST for the project subset."""

    sections: tuple[WorkoutSection, ...]


def render_workout_structure(structure: WorkoutStructure) -> str:
    """Render a workout AST into canonical subset text."""

    rendered_sections: list[str] = []
    for section in structure.sections:
        lines = [section.name]
        for block in section.blocks:
            if isinstance(block, WorkoutLoop):
                lines.append(f"{block.count}x")
                for step in block.steps:
                    lines.append(_render_step(step))
            else:
                lines.append(_render_step(block))
        rendered_sections.append("\n".join(lines))
    return "\n\n".join(rendered_sections).strip()


def canonicalize_workout_text(text: str, *, context_text: str = "") -> str:
    """Normalize supported shorthand and render the canonical workout subset."""

    prepared = normalize_workout_inline_loop_headers(normalize_workout_percent_ranges(text.strip()))
    structure = parse_workout_text(prepared, context_text=context_text)
    return render_workout_structure(structure)


def parse_workout_text(text: str, *, context_text: str = "") -> WorkoutStructure:
    """Parse canonical subset workout text into a workout AST."""

    prepared = normalize_workout_inline_loop_headers(normalize_workout_percent_ranges(text.strip()))
    issues = validate_workout_text("WORKOUT", prepared, context_text=context_text)
    if issues:
        raise ValueError("; ".join(issue.format() for issue in issues))

    sections: list[WorkoutSection] = []
    current_name: str | None = None
    current_blocks: list[WorkoutBlock] = []
    pending_loop_count: int | None = None
    pending_loop_steps: list[WorkoutStep] = []

    def _flush_loop() -> None:
        nonlocal pending_loop_count, pending_loop_steps, current_blocks
        if pending_loop_count is None:
            return
        current_blocks.append(WorkoutLoop(pending_loop_count, tuple(pending_loop_steps)))
        pending_loop_count = None
        pending_loop_steps = []

    def _flush_section() -> None:
        nonlocal current_name, current_blocks
        _flush_loop()
        if current_name is None:
            return
        sections.append(WorkoutSection(current_name, tuple(current_blocks)))
        current_name = None
        current_blocks = []

    for raw_line in prepared.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            _flush_loop()
            continue
        if stripped in ALLOWED_SECTION_HEADERS:
            _flush_section()
            current_name = _SECTION_CANONICAL[stripped]
            continue
        if LOOP_LINE_RE.fullmatch(stripped):
            _flush_loop()
            pending_loop_count = int(stripped[:-1])
            pending_loop_steps = []
            continue
        match = STEP_LINE_RE.fullmatch(stripped)
        if match is None:
            raise ValueError(f"Unsupported workout line after validation: {stripped}")
        step = WorkoutStep(
            duration=str(match.group("duration")),
            target=str(match.group("ramp") or match.group("target")),
            cadence=str(match.group("cadence")),
            flags=str(match.group("flags")) if match.group("flags") else None,
        )
        if pending_loop_count is not None:
            pending_loop_steps.append(step)
        else:
            current_blocks.append(step)

    _flush_section()
    structure = WorkoutStructure(tuple(section for section in sections if section.blocks))
    _assert_canonical_order(structure)
    return structure


def _assert_canonical_order(structure: WorkoutStructure) -> None:
    order = {name: idx for idx, name in enumerate(_CANONICAL_ORDER)}
    previous = -1
    for section in structure.sections:
        current = order.get(section.name, previous)
        if current < previous:
            raise ValueError("Workout sections are out of canonical order.")
        previous = current


def _render_step(step: WorkoutStep) -> str:
    suffix = f" {step.flags}" if step.flags else ""
    return f"- {step.duration} {step.target} {step.cadence}{suffix}"

