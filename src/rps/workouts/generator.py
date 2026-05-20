"""Deterministic workout and week-plan generation from structured week blueprints."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from rps.crewai_runtime.models import WeekPlanBundleModel, WeekWorkoutBlueprintModel
from rps.workouts.structured import (
    WorkoutLoop,
    WorkoutSection,
    WorkoutStep,
    WorkoutStructure,
    render_workout_structure,
)
from rps.workspace.intensity_domains import normalize_intensity_domain

JsonMap = dict[str, Any]
_DAY_ORDER = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


@dataclass(frozen=True)
class WorkoutBlueprintRenderSpec:
    """Resolved rendering spec for deterministic workout generation."""

    workout_id: str
    date: str
    day_role: str
    intensity_domain: str
    workout_family: str
    planned_duration_minutes: int
    planned_kj: int
    phase_intent: str | None
    load_modality: str
    low_end_endurance: bool
    activation_required: bool


def build_week_plan_document_from_bundle(
    *,
    planning_bundle: JsonMap,
    week_calendar_context: JsonMap | None = None,
    review_decision: JsonMap | None = None,
) -> JsonMap:
    """Build a deterministic WEEK_PLAN envelope from an approved planning bundle."""

    bundle_model = WeekPlanBundleModel.model_validate(planning_bundle)
    context = week_calendar_context or {}
    corridor = _active_weekly_band(context)
    agenda = _build_agenda(bundle_model)
    workouts = _build_workouts(bundle_model)
    week_objective = _week_objective(bundle_model, context)
    notes = _week_notes(bundle_model, context, review_decision or {})
    iso_week = str(context.get("target_iso_week") or "")
    week_start = str(context.get("week_start_date") or _day_date(bundle_model, "Mon") or "")
    week_end = str(context.get("week_end_date") or _day_date(bundle_model, "Sun") or "")
    planned_total = sum(int(row.get("planned_kj") or 0) for row in agenda)
    return {
        "meta": {
            "artifact_type": "WEEK_PLAN",
            "schema_id": "WeekPlanInterface",
            "schema_version": "1.2",
            "version": "1.0",
            "authority": "Binding",
            "owner_agent": "Week-Artifact-Writer",
            "run_id": "",
            "created_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "scope": "Week",
            "iso_week": iso_week,
            "iso_week_range": f"{iso_week}--{iso_week}" if iso_week else "",
            "temporal_scope": {"from": week_start, "to": week_end},
            "trace_upstream": [],
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "HIGH",
            "notes": "Deterministic week-plan workout generation applied.",
        },
        "data": {
            "week_summary": {
                "week_objective": week_objective,
                "weekly_load_corridor_kj": corridor,
                "planned_weekly_load_kj": planned_total,
                "notes": notes,
            },
            "agenda": agenda,
            "workouts": workouts,
        },
    }


def canonicalize_workout_entry(workout: JsonMap) -> JsonMap:
    """Return one workout entry with canonical subset text."""

    from rps.workouts.structured import canonicalize_workout_text

    normalized = dict(workout)
    text = str(normalized.get("workout_text") or "").strip()
    if text:
        context_text = " ".join(str(normalized.get(key) or "") for key in ("title", "notes"))
        normalized["workout_text"] = canonicalize_workout_text(text, context_text=context_text)
    return normalized


def _build_agenda(bundle: WeekPlanBundleModel) -> list[JsonMap]:
    blueprints = {item.day: item for item in bundle.day_blueprints}
    agenda: list[JsonMap] = []
    for day in _DAY_ORDER:
        item = blueprints.get(day)
        if item is None:
            raise ValueError(f"Missing day blueprint for {day}.")
        agenda.append(
            {
                "day": item.day,
                "date": item.date,
                "day_role": _canonical_day_role(item.day_role),
                "planned_duration": _minutes_to_hhmm(item.planned_duration_minutes),
                "planned_kj": int(item.planned_kj),
                "workout_id": item.workout_id,
            }
        )
    return agenda


def _build_workouts(bundle: WeekPlanBundleModel) -> list[JsonMap]:
    day_index = {item.day: idx for idx, item in enumerate(bundle.day_blueprints)}
    workout_day = {item.workout_id: item.day for item in bundle.day_blueprints if item.workout_id}
    ordered_blueprints = sorted(
        bundle.workout_blueprints,
        key=lambda item: day_index.get(workout_day.get(item.workout_id, ""), 99),
    )
    workouts: list[JsonMap] = []
    for blueprint in ordered_blueprints:
        spec = _resolve_render_spec(blueprint)
        structure = _generate_workout_structure(spec)
        workouts.append(
            {
                "workout_id": spec.workout_id,
                "title": _title_for_spec(spec),
                "notes": _notes_for_spec(spec),
                "date": spec.date,
                "start": "00:00",
                "duration": _minutes_to_hhmmss(spec.planned_duration_minutes),
                "workout_text": render_workout_structure(structure),
            }
        )
    return workouts


def _resolve_render_spec(blueprint: WeekWorkoutBlueprintModel) -> WorkoutBlueprintRenderSpec:
    domain = normalize_intensity_domain(blueprint.intensity_domain) or _domain_from_day_role(blueprint.day_role)
    family = str(blueprint.workout_family or domain or "ENDURANCE").strip().upper().replace(" ", "_")
    load_modality = "K3" if "K3" in family or "K3" in blueprint.workout_id.upper() else "NONE"
    if load_modality == "K3":
        family = "K3"
        domain = "ENDURANCE" if domain == "ENDURANCE" else domain
    low_end_endurance = (
        family in {"RECOVERY", "ENDURANCE_LOW"}
        or blueprint.day_role.upper() == "RECOVERY"
        or "EASY" in blueprint.workout_id.upper()
    )
    activation_required = domain == "SWEET_SPOT"
    if family not in {"ENDURANCE", "RECOVERY", "ENDURANCE_LOW", "ENDURANCE_HIGH", "TEMPO", "SWEET_SPOT", "K3"}:
        family = domain or "ENDURANCE"
    return WorkoutBlueprintRenderSpec(
        workout_id=blueprint.workout_id,
        date=blueprint.date,
        day_role=blueprint.day_role,
        intensity_domain=domain or "ENDURANCE",
        workout_family=family,
        planned_duration_minutes=max(int(blueprint.planned_duration_minutes), 20),
        planned_kj=int(blueprint.planned_kj),
        phase_intent=blueprint.phase_intent,
        load_modality=load_modality,
        low_end_endurance=low_end_endurance,
        activation_required=activation_required,
    )


def _generate_workout_structure(spec: WorkoutBlueprintRenderSpec) -> WorkoutStructure:
    if spec.workout_family == "K3":
        return _generate_k3(spec)
    if spec.intensity_domain == "SWEET_SPOT":
        return _generate_sweet_spot(spec)
    if spec.intensity_domain == "TEMPO":
        return _generate_tempo(spec)
    if spec.intensity_domain == "ENDURANCE":
        return _generate_endurance(spec)
    raise ValueError(f"Unsupported workout blueprint family/domain for {spec.workout_id}: {spec.workout_family}/{spec.intensity_domain}")


def _generate_endurance(spec: WorkoutBlueprintRenderSpec) -> WorkoutStructure:
    low_end = spec.low_end_endurance
    warm = 6 if low_end and spec.planned_duration_minutes <= 75 else 8 if spec.planned_duration_minutes < 180 else 10
    cool = 6 if low_end and spec.planned_duration_minutes <= 75 else 8 if spec.planned_duration_minutes < 180 else 10
    main = max(spec.planned_duration_minutes - warm - cool, 10)
    warm_target = "ramp 50%-60%" if low_end else "ramp 50%-65%"
    main_target = "60%-65%" if low_end else "68%-72%"
    cool_target = "ramp 55%-45%" if low_end else "ramp 60%-45%"
    return WorkoutStructure(
        sections=(
            WorkoutSection("Warmup", (WorkoutStep(f"{warm}m", warm_target, "85-90rpm"),)),
            WorkoutSection("Main Set", (WorkoutStep(_minutes_token(main), main_target, "85-90rpm"),)),
            WorkoutSection("Cooldown", (WorkoutStep(f"{cool}m", cool_target, "80-85rpm"),)),
        )
    )


def _generate_tempo(spec: WorkoutBlueprintRenderSpec) -> WorkoutStructure:
    warm = 8
    cool = 8
    main = max(spec.planned_duration_minutes - warm - cool, 10)
    return WorkoutStructure(
        sections=(
            WorkoutSection("Warmup", (WorkoutStep("8m", "ramp 50%-70%", "85-90rpm"),)),
            WorkoutSection("Main Set", (WorkoutStep(_minutes_token(main), "80%-83%", "85-90rpm"),)),
            WorkoutSection("Cooldown", (WorkoutStep("8m", "ramp 60%-45%", "80-85rpm"),)),
        )
    )


def _generate_sweet_spot(spec: WorkoutBlueprintRenderSpec) -> WorkoutStructure:
    warm = 8
    activation = 3
    cool = 8
    main = max(spec.planned_duration_minutes - warm - activation - cool, 12)
    loops, work_minutes, remainder = _interval_layout(total_minutes=main, recovery_minutes=3, preferred_work_minutes=12)
    blocks: list[WorkoutLoop | WorkoutStep] = [
        WorkoutLoop(
            loops,
            (
                WorkoutStep(f"{work_minutes}m", "88%-90%", "85-90rpm"),
                WorkoutStep("3m", "60%", "85rpm"),
            ),
        )
    ]
    if remainder > 0:
        blocks.append(WorkoutStep(_minutes_token(remainder), "68%-72%", "85-90rpm"))
    return WorkoutStructure(
        sections=(
            WorkoutSection("Warmup", (WorkoutStep("8m", "ramp 50%-70%", "85-90rpm"),)),
            WorkoutSection(
                "#### Activation",
                (
                    WorkoutLoop(
                        3,
                        (
                            WorkoutStep("20s", "120%", "95rpm"),
                            WorkoutStep("40s", "60%", "85rpm"),
                        ),
                    ),
                ),
            ),
            WorkoutSection("Main Set", tuple(blocks)),
            WorkoutSection("Cooldown", (WorkoutStep("8m", "ramp 60%-45%", "80-85rpm"),)),
        )
    )


def _generate_k3(spec: WorkoutBlueprintRenderSpec) -> WorkoutStructure:
    warm = 8
    cool = 8
    main = max(spec.planned_duration_minutes - warm - cool, 18)
    loops, work_minutes, remainder = _interval_layout(total_minutes=main, recovery_minutes=3, preferred_work_minutes=8)
    blocks: list[WorkoutLoop | WorkoutStep] = [
        WorkoutLoop(
            loops,
            (
                WorkoutStep(f"{work_minutes}m", "85%-88%", "50-60rpm"),
                WorkoutStep("3m", "60%", "85rpm"),
            ),
        )
    ]
    if remainder > 0:
        blocks.append(WorkoutStep(_minutes_token(remainder), "68%-72%", "85-90rpm"))
    return WorkoutStructure(
        sections=(
            WorkoutSection("Warmup", (WorkoutStep("8m", "ramp 50%-70%", "85-90rpm"),)),
            WorkoutSection("Main Set", tuple(blocks)),
            WorkoutSection("Cooldown", (WorkoutStep("8m", "ramp 60%-45%", "80-85rpm"),)),
        )
    )


def _interval_layout(*, total_minutes: int, recovery_minutes: int, preferred_work_minutes: int) -> tuple[int, int, int]:
    loops = max(1, min(4, total_minutes // max(preferred_work_minutes + recovery_minutes, 1)))
    work = max(6, (total_minutes // loops) - recovery_minutes)
    used = loops * (work + recovery_minutes)
    remainder = max(total_minutes - used, 0)
    return loops, work, remainder


def _title_for_spec(spec: WorkoutBlueprintRenderSpec) -> str:
    phase_prefix = _phase_prefix(spec.phase_intent)
    if spec.workout_family == "K3":
        return f"{phase_prefix} K3 Strength Endurance".strip()
    if spec.intensity_domain == "SWEET_SPOT":
        return f"{phase_prefix} Sweet Spot".strip()
    if spec.intensity_domain == "TEMPO":
        return f"{phase_prefix} Tempo".strip()
    if spec.low_end_endurance:
        return "Low-End Endurance Support"
    if spec.planned_duration_minutes >= 180:
        return "Long Endurance Anchor"
    return "Aerobic Endurance Support"


def _notes_for_spec(spec: WorkoutBlueprintRenderSpec) -> str:
    if spec.workout_family == "K3":
        return "Deterministic K3 workout generated from the approved week blueprint."
    if spec.intensity_domain == "SWEET_SPOT":
        return "Deterministic Sweet Spot workout generated from the approved week blueprint."
    if spec.intensity_domain == "TEMPO":
        return "Deterministic Tempo workout generated from the approved week blueprint."
    if spec.low_end_endurance:
        return "Deterministic low-end Endurance workout generated from the approved week blueprint."
    return "Deterministic Endurance workout generated from the approved week blueprint."


def _week_objective(bundle: WeekPlanBundleModel, context: JsonMap) -> str:
    if bundle.load_target_summary:
        return str(bundle.load_target_summary[0]).strip()
    if bundle.revision_summary:
        return str(bundle.revision_summary[0]).strip()
    phase_week_role = str(context.get("phase_week_role") or context.get("phase_role_for_week") or "Week")
    return f"{phase_week_role.replace('_', ' ').title()} week generated from approved day and workout blueprints."


def _week_notes(bundle: WeekPlanBundleModel, context: JsonMap, review_decision: JsonMap) -> str:
    fixed_rest = ", ".join(str(item) for item in context.get("fixed_rest_days") or [])
    quality_days = sum(1 for item in bundle.day_blueprints if str(item.day_role).upper() == "QUALITY")
    warnings = list(bundle.warnings) + list(review_decision.get("warnings") or [])
    parts = []
    if fixed_rest:
        parts.append(f"Fixed rest days: {fixed_rest}.")
    parts.append(f"Quality days: {quality_days}.")
    if warnings:
        parts.append("Warnings: " + " | ".join(str(item).strip() for item in warnings if str(item).strip()))
    return " ".join(parts).strip()


def _active_weekly_band(context: JsonMap) -> JsonMap:
    band = context.get("active_weekly_kj_band") or context.get("phase_weekly_kj_band") or context.get("active_s5_band") or {}
    if not isinstance(band, dict):
        return {"min": 0, "max": 0, "notes": ""}
    minimum = int(round(float(band.get("min") or 0)))
    maximum = int(round(float(band.get("max") or 0)))
    return {"min": minimum, "max": maximum, "notes": str(band.get("notes") or "")}


def _day_date(bundle: WeekPlanBundleModel, day: str) -> str | None:
    for item in bundle.day_blueprints:
        if item.day == day:
            return item.date
    return None


def _domain_from_day_role(day_role: str) -> str:
    role = str(day_role or "").upper()
    if role == "QUALITY":
        return "TEMPO"
    if role == "RECOVERY":
        return "ENDURANCE"
    return "ENDURANCE"


def _canonical_day_role(day_role: str) -> str:
    role = str(day_role or "").upper()
    if role == "LONG":
        return "ENDURANCE"
    return role or "ENDURANCE"


def _phase_prefix(phase_intent: str | None) -> str:
    if not phase_intent:
        return "Controlled"
    rendered = str(phase_intent).strip().replace("_", " ")
    return rendered.title()


def _minutes_to_hhmm(total_minutes: int) -> str:
    hours, minutes = divmod(max(int(total_minutes), 0), 60)
    return f"{hours:02d}:{minutes:02d}"


def _minutes_to_hhmmss(total_minutes: int) -> str:
    return f"{_minutes_to_hhmm(total_minutes)}:00"


def _minutes_token(total_minutes: int) -> str:
    total_minutes = max(int(total_minutes), 1)
    hours, minutes = divmod(total_minutes, 60)
    if hours and minutes:
        return f"{hours}h{minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"
