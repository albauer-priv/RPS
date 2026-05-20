"""Deterministic week-planning engine with configurable workout families."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from rps.agents.tasks import OUTPUT_SPECS, AgentTask
from rps.crewai_runtime.models import (
    ReplanInstructionModel,
    WeekContextAssessmentModel,
    WeekDayBlueprintModel,
    WeekPlanBundleModel,
    WeekReviewDecisionModel,
    WeekWorkoutBlueprintModel,
)
from rps.planning.contracts import (
    blocking_messages,
    validate_week_plan_against_week_context,
    validate_writer_output_against_blueprints,
)
from rps.planning.deterministic_context import (
    build_load_capacity_block,
    build_week_calendar_context,
)
from rps.planning.load_bands import selected_kpi_rate_band_from_selection
from rps.planning.workout_load import build_workout_load_method_context
from rps.workouts.generator import build_week_plan_document_from_bundle
from rps.workouts.validator import collect_week_plan_export_issues
from rps.workspace.guarded_store import GuardedValidatedStore
from rps.workspace.iso_helpers import IsoWeek
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.season_plan_service import resolve_season_plan_phase_info
from rps.workspace.types import ArtifactType

JsonMap = dict[str, Any]

_DAY_ORDER = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_WEEK_KEY_RE = re.compile(r"\b(?P<year>\d{4})-(?P<week>\d{2})\b")
_YEAR_WEEK_RE = re.compile(r"year=(?P<year>\d{4}),\s*week=(?P<week>\d{1,2})")


@dataclass(frozen=True)
class WeekWorkoutFamily:
    family_id: str
    intensity_domain: str
    load_modality: str
    generator_profile: str
    allowed_day_roles: tuple[str, ...]
    allowed_phase_intents: tuple[str, ...]
    allowed_week_roles: tuple[str, ...]
    tags: frozenset[str]


@dataclass(frozen=True)
class WeekWorkoutFamilyConfig:
    families: dict[str, WeekWorkoutFamily]
    by_phase_intent: dict[str, dict[str, list[str]]]
    by_day_role: dict[str, list[str]]


@dataclass(frozen=True)
class WeekAdjustmentIntent:
    message: str
    target_load_fraction: float
    forced_quality_family: str | None
    preserve_sat_anchor: bool


def execute_week_engine(
    *,
    repo_root: Path,
    schema_dir: Path,
    workspace_root: Path,
    athlete_id: str,
    run_id: str,
    target_year: int,
    target_week: int,
    user_message: str = "",
    preview_only: bool = False,
) -> JsonMap:
    """Run deterministic week planning and optionally persist the result."""

    store = LocalArtifactStore(root=workspace_root)
    season_plan = _load_latest_required(store, athlete_id, ArtifactType.SEASON_PLAN)
    target = IsoWeek(target_year, target_week)
    phase_info = resolve_season_plan_phase_info(season_plan, target)
    if phase_info is None:
        return {"ok": False, "error": f"No season phase found for {target_year:04d}-{target_week:02d}.", "produced": {}}

    phase_range = phase_info.phase_range
    phase_guardrails = _load_version_required(store, athlete_id, ArtifactType.PHASE_GUARDRAILS, phase_range.range_key)
    phase_structure = _load_version_required(store, athlete_id, ArtifactType.PHASE_STRUCTURE, phase_range.range_key)
    availability = _load_latest_optional(store, athlete_id, ArtifactType.AVAILABILITY)
    logistics = _load_latest_optional(store, athlete_id, ArtifactType.LOGISTICS)
    planning_events = _load_latest_optional(store, athlete_id, ArtifactType.PLANNING_EVENTS)
    athlete_profile = _load_latest_optional(store, athlete_id, ArtifactType.ATHLETE_PROFILE)
    wellness = _load_latest_optional(store, athlete_id, ArtifactType.WELLNESS)
    zone_model = _load_latest_optional(store, athlete_id, ArtifactType.ZONE_MODEL)
    kpi_profile = _load_latest_optional(store, athlete_id, ArtifactType.KPI_PROFILE)
    scenario_selection = _load_latest_optional(store, athlete_id, ArtifactType.SEASON_SCENARIO_SELECTION)
    kpi_rate_band = selected_kpi_rate_band_from_selection(scenario_selection if isinstance(scenario_selection, dict) else None)

    load_capacity = build_load_capacity_block(
        target_week=target,
        phase_range=phase_range,
        athlete_profile_payload=athlete_profile or {},
        availability_payload=availability or {},
        logistics_payload=logistics or {},
        zone_model_payload=zone_model or {},
        season_plan_payload=season_plan,
        phase_guardrails_payload=phase_guardrails,
        wellness_payload=wellness or {},
        kpi_profile_payload=kpi_profile or {},
        kpi_rate_band=kpi_rate_band,
    )
    week_calendar = build_week_calendar_context(
        target_week=target,
        phase_info=phase_info,
        phase_range=phase_range,
        availability_payload=availability or {},
        logistics_payload=logistics or {},
        planning_events_payload=planning_events or {},
        phase_guardrails_payload=phase_guardrails,
        phase_structure_payload=phase_structure,
        load_capacity_context=load_capacity.payload,
    )
    load_method = build_workout_load_method_context(
        athlete_profile_payload=athlete_profile or {},
        zone_model_payload=zone_model or {},
        allowed_intensity_domains=list(week_calendar.get("allowed_intensity_domains") or []),
    )
    family_config = load_week_workout_family_config(repo_root)
    adjustment = parse_week_adjustment_intent(user_message)
    planning_bundle = _build_week_plan_bundle(
        week_calendar_context=week_calendar,
        load_method_context=load_method,
        family_config=family_config,
        phase_intent=str(week_calendar.get("phase_intent") or phase_info.phase_intent or ""),
        adjustment=adjustment,
    )
    review_decision = _review_bundle(planning_bundle=planning_bundle, week_calendar_context=week_calendar)
    document = build_week_plan_document_from_bundle(
        planning_bundle=planning_bundle.model_dump(mode="json"),
        week_calendar_context=week_calendar,
        review_decision=review_decision.model_dump(mode="json"),
    )
    details: JsonMap = {
        "planning_bundle": planning_bundle.model_dump(mode="json"),
        "review_decision": review_decision.model_dump(mode="json"),
        "week_calendar_context": week_calendar,
    }
    if review_decision.status != "approved":
        return {
            "ok": False,
            "error": "; ".join(review_decision.blocking_issues) or "Deterministic week review did not approve the candidate.",
            "document": document if preview_only else {},
            "details": details,
            "produced": {},
            "warnings": list(review_decision.warnings),
        }
    if preview_only:
        return {
            "ok": True,
            "artifact_type": ArtifactType.WEEK_PLAN.value,
            "document": document,
            "details": details,
            "warnings": list(review_decision.warnings),
        }

    guarded = GuardedValidatedStore(
        athlete_id=athlete_id,
        schema_dir=schema_dir,
        workspace_root=workspace_root,
    )
    saved = guarded.guard_put_validated(
        output_spec=OUTPUT_SPECS[AgentTask.CREATE_WEEK_PLAN],
        document=document,
        run_id=run_id,
        producer_agent="week_engine",
        update_latest=True,
    )
    return {
        "ok": True,
        "produced": {OUTPUT_SPECS[AgentTask.CREATE_WEEK_PLAN].tool_name: saved},
        "document": document,
        "details": details,
        "warnings": list(review_decision.warnings),
    }


def load_week_workout_family_config(root: Path | str) -> WeekWorkoutFamilyConfig:
    """Load and validate configurable workout families."""

    config_path = Path(root) / "config" / "planning" / "week_workout_families.yaml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("week_workout_families.yaml must contain a top-level mapping.")
    families_raw = data.get("families")
    if not isinstance(families_raw, dict) or not families_raw:
        raise ValueError("week_workout_families.yaml must define at least one family.")
    known_profiles = {
        "duration_first_endurance",
        "controlled_tempo_expansion",
        "tiz_first_sweet_spot",
        "k3_progressive_torque",
    }
    families: dict[str, WeekWorkoutFamily] = {}
    for key, raw in families_raw.items():
        if not isinstance(raw, dict):
            raise ValueError(f"Family '{key}' must be a mapping.")
        family_id = str(raw.get("family_id") or key).strip().upper()
        profile = str(raw.get("generator_profile") or "").strip()
        if profile not in known_profiles:
            raise ValueError(f"Family '{family_id}' references unknown generator_profile '{profile}'.")
        families[family_id] = WeekWorkoutFamily(
            family_id=family_id,
            intensity_domain=str(raw.get("intensity_domain") or "").strip().upper(),
            load_modality=str(raw.get("load_modality") or "NONE").strip().upper(),
            generator_profile=profile,
            allowed_day_roles=tuple(str(item).strip().upper() for item in raw.get("allowed_day_roles") or [] if str(item).strip()),
            allowed_phase_intents=tuple(str(item).strip().lower() for item in raw.get("allowed_phase_intents") or [] if str(item).strip()),
            allowed_week_roles=tuple(str(item).strip().upper() for item in raw.get("allowed_week_roles") or [] if str(item).strip()),
            tags=frozenset(str(item).strip().lower() for item in raw.get("tags") or [] if str(item).strip()),
        )
    policy = data.get("selection_policy") or {}
    if not isinstance(policy, dict):
        raise ValueError("selection_policy must be a mapping.")
    by_phase_intent: dict[str, dict[str, list[str]]] = {}
    phase_raw = policy.get("by_phase_intent") or {}
    if not isinstance(phase_raw, dict):
        raise ValueError("selection_policy.by_phase_intent must be a mapping.")
    for phase_intent, mapping in phase_raw.items():
        if not isinstance(mapping, dict):
            raise ValueError(f"selection policy for phase_intent '{phase_intent}' must be a mapping.")
        by_phase_intent[str(phase_intent).strip().lower()] = {
            str(day_role).strip().upper(): [str(item).strip().upper() for item in items or [] if str(item).strip()]
            for day_role, items in mapping.items()
        }
    by_day_role_raw = policy.get("by_day_role") or {}
    if not isinstance(by_day_role_raw, dict):
        raise ValueError("selection_policy.by_day_role must be a mapping.")
    by_day_role = {
        str(day_role).strip().upper(): [str(item).strip().upper() for item in items or [] if str(item).strip()]
        for day_role, items in by_day_role_raw.items()
    }
    unknown = {
        family_id
        for candidates in by_day_role.values()
        for family_id in candidates
        if family_id not in families
    } | {
        family_id
        for mapping in by_phase_intent.values()
        for candidates in mapping.values()
        for family_id in candidates
        if family_id not in families
    }
    if unknown:
        joined = ", ".join(sorted(unknown))
        raise ValueError(f"selection policy references unknown families: {joined}")
    return WeekWorkoutFamilyConfig(
        families=families,
        by_phase_intent=by_phase_intent,
        by_day_role=by_day_role,
    )


def parse_week_adjustment_intent(message: str) -> WeekAdjustmentIntent:
    """Parse a bounded deterministic week-adjustment intent from free text."""

    cleaned = message.strip()
    lowered = cleaned.lower()
    target_load_fraction = 0.5
    if any(token in lowered for token in ("more load", "increase load", "harder", "more volume")):
        target_load_fraction = 0.7
    elif any(token in lowered for token in ("easier", "reduce load", "less load", "lighter")):
        target_load_fraction = 0.25
    forced_quality_family = None
    if "sweet spot" in lowered:
        forced_quality_family = "SWEET_SPOT_STABILIZATION"
    elif "tempo" in lowered:
        forced_quality_family = "TEMPO_STEADY"
    elif "k3" in lowered or "torque" in lowered:
        forced_quality_family = "K3_SWEET_SPOT"
    preserve_sat_anchor = "preserve sat anchor" in lowered or "keep sat" in lowered or "keep saturday" in lowered
    return WeekAdjustmentIntent(
        message=cleaned,
        target_load_fraction=target_load_fraction,
        forced_quality_family=forced_quality_family,
        preserve_sat_anchor=preserve_sat_anchor or True,
    )


def parse_target_week_from_user_input(user_input: str) -> tuple[int, int]:
    """Extract ISO year/week from the standard week runtime prompts."""

    year_week = _YEAR_WEEK_RE.search(user_input)
    if year_week:
        return int(year_week.group("year")), int(year_week.group("week"))
    iso_matches = _WEEK_KEY_RE.findall(user_input)
    if iso_matches:
        year, week = iso_matches[0]
        return int(year), int(week)
    raise ValueError("Unable to determine target ISO week from user input.")


def extract_message_from_user_input(user_input: str) -> str:
    """Extract the optional bounded week-revision message from the prompt."""

    marker = "Message:"
    if marker not in user_input:
        return ""
    tail = user_input.split(marker, 1)[1]
    first_line = tail.splitlines()[0]
    return first_line.strip()


def _build_week_plan_bundle(
    *,
    week_calendar_context: JsonMap,
    load_method_context: JsonMap,
    family_config: WeekWorkoutFamilyConfig,
    phase_intent: str,
    adjustment: WeekAdjustmentIntent,
) -> WeekPlanBundleModel:
    target_band = _active_band(week_calendar_context)
    target_load = int(round(target_band["min"] + (target_band["max"] - target_band["min"]) * adjustment.target_load_fraction))
    hourly_loads = _hourly_loads(load_method_context)
    day_blueprints = _allocate_day_blueprints(week_calendar_context=week_calendar_context)
    workout_blueprints = _select_workout_blueprints(
        day_blueprints=day_blueprints,
        family_config=family_config,
        week_calendar_context=week_calendar_context,
        phase_intent=phase_intent,
        adjustment=adjustment,
    )
    _reconcile_loads(
        day_blueprints=day_blueprints,
        workout_blueprints=workout_blueprints,
        weekly_target_kj=target_load,
        hourly_loads=hourly_loads,
    )
    context_summary = WeekContextAssessmentModel(
        summary=f"Deterministic week planning for {week_calendar_context.get('target_iso_week')}.",
        key_constraints=[
            f"Active weekly band: {target_band['min']}-{target_band['max']} kJ",
            "Fixed rest days preserved.",
            "Workout families selected from configuration.",
        ],
        completed_vs_planned=[],
        likely_change_request=bool(adjustment.message),
    )
    return WeekPlanBundleModel(
        context_summary=context_summary,
        day_blueprints=day_blueprints,
        workout_blueprints=workout_blueprints,
        constraint_summary=[
            f"Week role: {week_calendar_context.get('phase_week_role')}",
            f"Allowed domains: {', '.join(str(item) for item in week_calendar_context.get('allowed_intensity_domains') or [])}",
        ],
        load_target_summary=[f"Deterministic weekly load target set to {target_load} kJ within the binding active band."],
        revision_summary=([f"Applied bounded adjustment intent: {adjustment.message}"] if adjustment.message else []),
        workout_authoring_summary=["Workout families chosen from configurable registry and rendered deterministically."],
        candidate_document_summary=["Week bundle generated without Week CrewAI planning/review/writer stages."],
    )


def _review_bundle(*, planning_bundle: WeekPlanBundleModel, week_calendar_context: JsonMap) -> WeekReviewDecisionModel:
    document = build_week_plan_document_from_bundle(
        planning_bundle=planning_bundle.model_dump(mode="json"),
        week_calendar_context=week_calendar_context,
        review_decision={},
    )
    issues = validate_week_plan_against_week_context(
        week_plan_payload=document,
        week_calendar_context=week_calendar_context,
    )
    issues.extend(
        validate_writer_output_against_blueprints(
            scope="week",
            artifact_payload=document,
            blueprints=[item.model_dump(mode="json") for item in planning_bundle.day_blueprints],
        )
    )
    export_issues = collect_week_plan_export_issues(document)
    blocking = blocking_messages(issues)
    blocking.extend(issue.format() for issue in export_issues)
    if blocking:
        return WeekReviewDecisionModel(
            status="replan_required",
            blocking_issues=blocking,
            warnings=list(planning_bundle.warnings),
            replan_instructions=[
                ReplanInstructionModel(
                    target_specialists=["week_engine"],
                    issues_to_fix=blocking,
                    must_preserve=[
                        "Fixed rest days",
                        "Allowed intensity domains",
                        "Quality-day cap",
                        "Recovery-aware spacing",
                    ],
                    priority_order=["1) satisfy active weekly band", "2) keep contract legality", "3) keep export-safe syntax"],
                    max_scope_of_change="Adjust deterministic family selection and/or workout durations only.",
                )
            ],
            writer_ready_summary="",
        )
    return WeekReviewDecisionModel(
        status="approved",
        warnings=list(planning_bundle.warnings),
        writer_ready_summary="Deterministic week bundle validated and ready for persistence.",
    )


def _allocate_day_blueprints(*, week_calendar_context: JsonMap) -> list[WeekDayBlueprintModel]:
    phase_intent = str(week_calendar_context.get("phase_intent") or "")
    phase_week_role = str(week_calendar_context.get("phase_week_role") or "")
    allowed_day_roles = {str(item).strip().upper() for item in week_calendar_context.get("allowed_day_roles") or []}
    quality_cap = int(week_calendar_context.get("quality_day_cap") or 0)
    role_is_reset = phase_week_role.upper() in {"DELOAD", "MINI_RESET", "SHORTENED_MINI_RESET"}
    day_rows = [_as_map(item) for item in week_calendar_context.get("day_matrix") or []]
    roles = {
        "Tue": "QUALITY" if quality_cap >= 1 and not role_is_reset else "ENDURANCE",
        "Wed": "RECOVERY" if "RECOVERY" in allowed_day_roles else "ENDURANCE",
        "Thu": "QUALITY" if quality_cap >= 2 and not role_is_reset else "ENDURANCE",
        "Sat": "ENDURANCE",
        "Sun": "ENDURANCE",
    }
    blueprints: list[WeekDayBlueprintModel] = []
    for row in day_rows:
        day = str(row.get("day") or "")
        availability = _as_map(row.get("availability_hours"))
        fixed_rest = bool(row.get("fixed_rest_day"))
        day_role = "REST" if fixed_rest else roles.get(day, "ENDURANCE")
        blueprints.append(
            WeekDayBlueprintModel(
                day=day,  # type: ignore[arg-type]
                date=str(row.get("date") or ""),
                fixed_rest_day=fixed_rest,
                availability_cap_minutes=_availability_cap_minutes(availability),
                phase_role=str(week_calendar_context.get("phase_role") or ""),
                phase_intent=phase_intent,
                phase_week_role=phase_week_role,
                day_role=day_role,
                intended_domain="ENDURANCE" if day_role in {"RECOVERY", "ENDURANCE"} else "TEMPO",
                planned_duration_minutes=0,
                planned_kj=0,
                workout_id=None if fixed_rest else _default_workout_id(week_calendar_context, day, day_role),
                warnings=[],
            )
        )
    return blueprints


def _select_workout_blueprints(
    *,
    day_blueprints: list[WeekDayBlueprintModel],
    family_config: WeekWorkoutFamilyConfig,
    week_calendar_context: JsonMap,
    phase_intent: str,
    adjustment: WeekAdjustmentIntent,
) -> list[WeekWorkoutBlueprintModel]:
    allowed_domains = {str(item).strip().upper() for item in week_calendar_context.get("allowed_intensity_domains") or []}
    allowed_modalities = {str(item).strip().upper() for item in week_calendar_context.get("allowed_load_modalities") or []}
    week_role = str(week_calendar_context.get("phase_week_role") or "").strip().upper()
    workout_blueprints: list[WeekWorkoutBlueprintModel] = []
    quality_index = 0
    for day in day_blueprints:
        if day.fixed_rest_day or not day.workout_id:
            continue
        is_anchor = day.day == "Sat" or (day.day == "Sun" and not adjustment.preserve_sat_anchor)
        family = _pick_family(
            family_config=family_config,
            day_role=day.day_role,
            phase_intent=phase_intent,
            week_role=week_role,
            allowed_domains=allowed_domains,
            allowed_modalities=allowed_modalities,
            is_anchor=is_anchor,
            forced_quality_family=adjustment.forced_quality_family if day.day_role == "QUALITY" and quality_index == 0 else None,
        )
        if day.day_role == "QUALITY":
            quality_index += 1
        workout_blueprints.append(
            WeekWorkoutBlueprintModel(
                workout_id=day.workout_id,
                date=day.date,
                phase_intent=phase_intent,
                day_role=day.day_role,
                intensity_domain=family.intensity_domain,
                workout_family=family.family_id,
                family_variant=family.family_id,
                load_modality=family.load_modality,
                generator_profile=family.generator_profile,
                selection_reason=f"Selected from configurable family policy for {day.day_role}.",
                activation_required="activation_capable" in family.tags,
                low_end_endurance="recovery_like" in family.tags,
                progression_parameters={},
                phase_legality_status="legal",
                planned_duration_minutes=0,
                planned_kj=0,
                required_sections=["Warmup", "Main Set", "Cooldown"],
                exportability_status="pending",
                warnings=[],
            )
        )
    return workout_blueprints


def _reconcile_loads(
    *,
    day_blueprints: list[WeekDayBlueprintModel],
    workout_blueprints: list[WeekWorkoutBlueprintModel],
    weekly_target_kj: int,
    hourly_loads: dict[str, int],
) -> None:
    by_workout = {item.workout_id: item for item in workout_blueprints}
    for day in day_blueprints:
        if day.fixed_rest_day or not day.workout_id:
            continue
        workout = by_workout[day.workout_id]
        base_minutes = _base_minutes(day)
        rate = hourly_loads.get(str(workout.intensity_domain or "ENDURANCE").upper(), hourly_loads.get("ENDURANCE", 600))
        object.__setattr__(day, "planned_duration_minutes", base_minutes)
        object.__setattr__(day, "planned_kj", int(round(base_minutes * rate / 60.0)))
        object.__setattr__(workout, "planned_duration_minutes", day.planned_duration_minutes)
        object.__setattr__(workout, "planned_kj", day.planned_kj)
        object.__setattr__(workout, "exportability_status", "valid")
    total = sum(day.planned_kj for day in day_blueprints)
    candidates = [
        day for day in day_blueprints
        if not day.fixed_rest_day and day.workout_id and (day.availability_cap_minutes or 0) > day.planned_duration_minutes
    ]
    while total < weekly_target_kj and candidates:
        progressed = False
        for day in sorted(candidates, key=_day_extension_priority):
            workout = by_workout.get(day.workout_id or "")
            if workout is None:
                continue
            rate = hourly_loads.get(str(workout.intensity_domain or "ENDURANCE").upper(), hourly_loads.get("ENDURANCE", 600))
            step = 15 if day.day_role == "ENDURANCE" else 10
            cap = day.availability_cap_minutes or day.planned_duration_minutes
            new_minutes = min(cap, day.planned_duration_minutes + step)
            if new_minutes == day.planned_duration_minutes:
                continue
            new_kj = int(round(new_minutes * rate / 60.0))
            if new_kj <= day.planned_kj:
                continue
            total += new_kj - day.planned_kj
            object.__setattr__(day, "planned_duration_minutes", new_minutes)
            object.__setattr__(day, "planned_kj", new_kj)
            object.__setattr__(workout, "planned_duration_minutes", new_minutes)
            object.__setattr__(workout, "planned_kj", new_kj)
            progressed = True
            if total >= weekly_target_kj:
                break
        if not progressed:
            break
    shrink_candidates = [day for day in day_blueprints if not day.fixed_rest_day and day.workout_id]
    while total > weekly_target_kj and shrink_candidates:
        progressed = False
        for day in sorted(shrink_candidates, key=_day_shrink_priority):
            workout = by_workout.get(day.workout_id or "")
            if workout is None:
                continue
            rate = hourly_loads.get(str(workout.intensity_domain or "ENDURANCE").upper(), hourly_loads.get("ENDURANCE", 600))
            step = 10 if day.day_role == "QUALITY" else 15
            minimum = _minimum_minutes(day)
            new_minutes = max(minimum, day.planned_duration_minutes - step)
            if new_minutes == day.planned_duration_minutes:
                continue
            new_kj = int(round(new_minutes * rate / 60.0))
            if new_kj >= day.planned_kj:
                continue
            total -= day.planned_kj - new_kj
            object.__setattr__(day, "planned_duration_minutes", new_minutes)
            object.__setattr__(day, "planned_kj", new_kj)
            object.__setattr__(workout, "planned_duration_minutes", new_minutes)
            object.__setattr__(workout, "planned_kj", new_kj)
            progressed = True
            if total <= weekly_target_kj:
                break
        if not progressed:
            break


def _pick_family(
    *,
    family_config: WeekWorkoutFamilyConfig,
    day_role: str,
    phase_intent: str,
    week_role: str,
    allowed_domains: set[str],
    allowed_modalities: set[str],
    is_anchor: bool,
    forced_quality_family: str | None,
) -> WeekWorkoutFamily:
    if forced_quality_family:
        forced = family_config.families.get(forced_quality_family.upper())
        if forced and _family_is_allowed(forced, day_role, phase_intent, week_role, allowed_domains, allowed_modalities, is_anchor):
            return forced
    role = day_role.upper()
    candidates = list(family_config.by_phase_intent.get(phase_intent.lower(), {}).get(role, []))
    candidates.extend(family_config.by_day_role.get(role, []))
    seen: set[str] = set()
    for family_id in candidates:
        if family_id in seen:
            continue
        seen.add(family_id)
        family = family_config.families[family_id]
        if _family_is_allowed(family, day_role, phase_intent, week_role, allowed_domains, allowed_modalities, is_anchor):
            return family
    raise ValueError(f"No legal workout family available for day_role={day_role}, phase_intent={phase_intent}, week_role={week_role}.")


def _family_is_allowed(
    family: WeekWorkoutFamily,
    day_role: str,
    phase_intent: str,
    week_role: str,
    allowed_domains: set[str],
    allowed_modalities: set[str],
    is_anchor: bool,
) -> bool:
    if family.allowed_day_roles and day_role.upper() not in family.allowed_day_roles:
        return False
    if family.allowed_phase_intents and "*" not in family.allowed_phase_intents and phase_intent.lower() not in family.allowed_phase_intents:
        return False
    if family.allowed_week_roles and "*" not in family.allowed_week_roles and week_role.upper() not in family.allowed_week_roles:
        return False
    if family.intensity_domain.upper() not in allowed_domains:
        return False
    if family.load_modality.upper() not in allowed_modalities:
        return False
    return not (is_anchor and "anchor" not in family.tags and day_role.upper() == "ENDURANCE")


def _base_minutes(day: WeekDayBlueprintModel) -> int:
    cap = day.availability_cap_minutes or 60
    if day.day_role == "QUALITY":
        return min(cap, 110)
    if day.day_role == "RECOVERY":
        return min(cap, 75)
    if day.day == "Sat":
        return min(cap, 210)
    if day.day == "Sun":
        return min(cap, 90)
    return min(cap, 90)


def _day_extension_priority(day: WeekDayBlueprintModel) -> tuple[int, int]:
    priority = {
        "Sat": 0,
        "Sun": 1,
        "Wed": 2,
        "Tue": 3,
        "Thu": 4,
    }.get(day.day, 9)
    return priority, day.planned_duration_minutes


def _day_shrink_priority(day: WeekDayBlueprintModel) -> tuple[int, int]:
    priority = {
        "Thu": 0,
        "Tue": 1,
        "Sun": 2,
        "Wed": 3,
        "Sat": 4,
    }.get(day.day, 9)
    return priority, -day.planned_duration_minutes


def _minimum_minutes(day: WeekDayBlueprintModel) -> int:
    if day.day_role == "QUALITY":
        return 75
    if day.day_role == "RECOVERY":
        return 45
    if day.day == "Sat":
        return 180
    return 60


def _default_workout_id(context: JsonMap, day: str, day_role: str) -> str:
    iso_week = str(context.get("target_iso_week") or "0000-00")
    suffix = {
        "QUALITY": "QUALITY",
        "RECOVERY": "REC",
        "ENDURANCE": "END",
    }.get(day_role.upper(), day_role.upper() or "END")
    return f"{iso_week}-{day.upper()}-{suffix}"


def _hourly_loads(context: JsonMap) -> dict[str, int]:
    result: dict[str, int] = {}
    for row in context.get("domain_hourly_estimates") or []:
        row_map = _as_map(row)
        domain = str(row_map.get("domain") or "").strip().upper()
        governance = int(round(float(row_map.get("governance_load_kj_per_hour") or 0)))
        if domain:
            result[domain] = governance
    return result


def _active_band(context: JsonMap) -> dict[str, int]:
    band = _as_map(context.get("active_weekly_kj_band") or context.get("phase_weekly_kj_band") or context.get("active_s5_band"))
    return {
        "min": int(round(float(band.get("min") or 0))),
        "max": int(round(float(band.get("max") or 0))),
    }


def _availability_cap_minutes(availability: JsonMap) -> int:
    for key in ("max", "typical", "min"):
        value = availability.get(key)
        if isinstance(value, (int, float)) and value > 0:
            return int(round(float(value) * 60))
    return 0


def _load_latest_required(store: LocalArtifactStore, athlete_id: str, artifact_type: ArtifactType) -> JsonMap:
    payload = store.load_latest(athlete_id, artifact_type)
    if not isinstance(payload, dict):
        raise ValueError(f"Missing or invalid latest {artifact_type.value}.")
    return payload


def _load_latest_optional(store: LocalArtifactStore, athlete_id: str, artifact_type: ArtifactType) -> JsonMap | None:
    try:
        payload = store.load_latest(athlete_id, artifact_type)
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _load_version_required(store: LocalArtifactStore, athlete_id: str, artifact_type: ArtifactType, version_key: str) -> JsonMap:
    payload = store.load_version(athlete_id, artifact_type, version_key)
    if not isinstance(payload, dict):
        raise ValueError(f"Missing or invalid {artifact_type.value} {version_key}.")
    return payload


def _as_map(value: object) -> JsonMap:
    return value if isinstance(value, dict) else {}
