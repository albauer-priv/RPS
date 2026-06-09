"""Deterministic workout and week-plan generation from structured week blueprints."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from rps.crewai_runtime.models import WeekPlanBundleModel, WeekWorkoutBlueprintModel
from rps.planning.deterministic_context import build_effective_week_constraints_block
from rps.workouts.protocol_solver import solve_protocol_workout
from rps.workouts.structured import render_workout_structure
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
    family_variant: str | None
    protocol_type: str | None
    protocol_variant: str | None
    planned_duration_minutes: int
    planned_kj: int
    target_kj: int | None
    primary_tiz_target_min: int | None
    phase_intent: str | None
    load_modality: str
    generator_profile: str | None
    addon_policy: str | None
    low_end_endurance: bool
    activation_required: bool
    progression_parameters: JsonMap
    progression_state: JsonMap


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
    notes = _week_notes(bundle_model, context, review_decision or {})
    iso_week = str(context.get("target_iso_week") or "")
    week_start = str(context.get("week_start_date") or _day_date(bundle_model, "Mon") or "")
    week_end = str(context.get("week_end_date") or _day_date(bundle_model, "Sun") or "")
    planned_total = sum(int(row.get("planned_kj") or 0) for row in agenda)
    effective_constraints = build_effective_week_constraints_block(context)
    trace_upstream = list(context.get("trace_upstream") or []) if isinstance(context.get("trace_upstream"), list) else []
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
            "trace_upstream": trace_upstream,
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "HIGH",
            "notes": "Deterministic protocol-driven week-plan workout generation applied.",
        },
        "data": {
            "inherited_planning_posture": (
                context.get("inherited_planning_posture", {})
                if isinstance(context.get("inherited_planning_posture"), dict)
                else {}
            ),
            "effective_week_constraints": effective_constraints,
            "week_summary": {
                "week_objective": _week_objective(bundle_model, context, planned_total=planned_total),
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
        solved = solve_protocol_workout(spec)
        workouts.append(
            {
                "workout_id": spec.workout_id,
                "title": solved.title,
                "notes": solved.notes,
                "date": spec.date,
                "start": "00:00",
                "duration": _minutes_to_hhmmss(spec.planned_duration_minutes),
                "workout_text": render_workout_structure(solved.structure),
            }
        )
    return workouts


def _resolve_render_spec(blueprint: WeekWorkoutBlueprintModel) -> WorkoutBlueprintRenderSpec:
    domain = normalize_intensity_domain(blueprint.intensity_domain) or _domain_from_day_role(blueprint.day_role)
    family = str(blueprint.workout_family or domain or "ENDURANCE").strip().upper().replace(" ", "_")
    load_modality = "K3" if "K3" in family or "K3" in blueprint.workout_id.upper() else str(blueprint.load_modality or "NONE")
    if load_modality == "K3":
        family = "K3"
        domain = "ENDURANCE" if domain == "ENDURANCE" else domain
    low_end_endurance = (
        family in {"RECOVERY", "ENDURANCE_LOW"}
        or blueprint.day_role.upper() == "RECOVERY"
        or "EASY" in blueprint.workout_id.upper()
        or bool(blueprint.low_end_endurance)
    )
    activation_required = bool(blueprint.activation_required) or domain == "SWEET_SPOT"
    return WorkoutBlueprintRenderSpec(
        workout_id=blueprint.workout_id,
        date=blueprint.date,
        day_role=blueprint.day_role,
        intensity_domain=domain or "ENDURANCE",
        workout_family=family,
        family_variant=str(blueprint.family_variant or blueprint.workout_family or "").strip() or None,
        protocol_type=str(blueprint.protocol_type or blueprint.generator_profile or "").strip().upper() or None,
        protocol_variant=str(blueprint.protocol_variant or blueprint.family_variant or blueprint.workout_family or "").strip().upper() or None,
        planned_duration_minutes=max(int(blueprint.planned_duration_minutes), 20),
        planned_kj=int(blueprint.planned_kj),
        target_kj=int(blueprint.target_kj) if blueprint.target_kj is not None else None,
        primary_tiz_target_min=int(blueprint.primary_tiz_target_min) if blueprint.primary_tiz_target_min is not None else None,
        phase_intent=blueprint.phase_intent,
        load_modality=str(load_modality).strip().upper(),
        generator_profile=str(blueprint.generator_profile or "").strip() or None,
        addon_policy=str(blueprint.addon_policy or "").strip().upper() or None,
        low_end_endurance=low_end_endurance,
        activation_required=activation_required,
        progression_parameters=dict(blueprint.progression_parameters),
        progression_state=dict(blueprint.progression_state),
    )


def _week_objective(bundle: WeekPlanBundleModel, context: JsonMap, *, planned_total: int) -> str:
    band = _active_weekly_band(context)
    phase_week_role = str(context.get("phase_week_role") or context.get("phase_role_for_week") or "Week").replace("_", " ").title()
    phase_intent = str(context.get("phase_intent") or "").replace("_", " ").strip()
    if band.get("min") or band.get("max"):
        intent_prefix = f"{phase_intent} " if phase_intent else ""
        return (
            f"{intent_prefix}{phase_week_role} planned at {int(planned_total)} kJ "
            f"inside the binding {int(band.get('min') or 0)}-{int(band.get('max') or 0)} kJ band."
        )
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


def _minutes_to_hhmm(total_minutes: int) -> str:
    hours, minutes = divmod(max(int(total_minutes), 0), 60)
    return f"{hours:02d}:{minutes:02d}"


def _minutes_to_hhmmss(total_minutes: int) -> str:
    return f"{_minutes_to_hhmm(total_minutes)}:00"
