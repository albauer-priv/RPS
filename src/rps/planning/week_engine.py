"""Deterministic week-planning engine with configurable workout protocols."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
    resolve_effective_allowed_modalities,
)
from rps.planning.load_bands import selected_kpi_rate_band_from_selection
from rps.planning.week_protocols import (
    WeekWorkoutProtocol,
    WeekWorkoutProtocolConfig,
    load_week_workout_protocol_config,
    protocol_is_allowed,
)
from rps.planning.week_selection_rules import (
    WeekWorkoutSelectionRuleConfig,
    load_week_workout_selection_rule_config,
)
from rps.planning.week_selector import (
    build_source_versions_map,
    build_trace_upstream,
    persist_selection_audit,
    select_workouts_for_week,
)
from rps.planning.workout_load import build_workout_load_method_context
from rps.workouts.generator import build_week_plan_document_from_bundle
from rps.workouts.progression_history import (
    extract_progression_signatures_from_week_plan,
    match_progression_signature,
)
from rps.workouts.validator import collect_week_plan_export_issues
from rps.workspace.guarded_store import GuardedValidatedStore
from rps.workspace.iso_helpers import IsoWeek, previous_iso_week
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.season_plan_service import resolve_season_plan_phase_info
from rps.workspace.types import ArtifactType

JsonMap = dict[str, Any]

_DAY_ORDER = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_WEEK_KEY_RE = re.compile(r"\b(?P<year>\d{4})-(?P<week>\d{2})\b")
_YEAR_WEEK_RE = re.compile(r"year=(?P<year>\d{4}),\s*week=(?P<week>\d{1,2})")

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
    phase_preview = _load_version_required(store, athlete_id, ArtifactType.PHASE_PREVIEW, phase_range.range_key)
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
    effective_modalities, week_context_warnings = resolve_effective_allowed_modalities(
        week_calendar_context=week_calendar,
        phase_structure_payload=phase_structure,
    )
    week_calendar["allowed_load_modalities"] = effective_modalities
    week_calendar["trace_upstream"] = build_trace_upstream(
        [
            (ArtifactType.PHASE_GUARDRAILS, phase_guardrails),
            (ArtifactType.PHASE_STRUCTURE, phase_structure),
        ]
    )
    load_method = build_workout_load_method_context(
        athlete_profile_payload=athlete_profile or {},
        zone_model_payload=zone_model or {},
        allowed_intensity_domains=list(week_calendar.get("allowed_intensity_domains") or []),
    )
    week_calendar["phase_type"] = str(phase_info.phase_type or week_calendar.get("phase_cycle") or "")
    week_calendar["season_archetype"] = str(load_capacity.payload.get("season_archetype") or "")
    protocol_config = load_week_workout_protocol_config(repo_root)
    selection_rule_config = load_week_workout_selection_rule_config(repo_root)
    progression_history = _load_prior_progression_signatures(store=store, athlete_id=athlete_id, target_week=target)
    adjustment = parse_week_adjustment_intent(user_message)
    planning_bundle, selection_audit = _build_week_plan_bundle(
        athlete_id=athlete_id,
        week_calendar_context=week_calendar,
        load_method_context=load_method,
        protocol_config=protocol_config,
        selection_rule_config=selection_rule_config,
        progression_history=progression_history,
        phase_preview_payload=phase_preview,
        phase_intent=str(week_calendar.get("phase_intent") or phase_info.phase_intent or ""),
        phase_type=str(phase_info.phase_type or week_calendar.get("phase_cycle") or ""),
        season_archetype=str(load_capacity.payload.get("season_archetype") or ""),
        adjustment=adjustment,
        initial_warnings=week_context_warnings,
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
            "details": {**details, "selection_audit": selection_audit},
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
    trace_upstream = build_trace_upstream(
        [
            (ArtifactType.PHASE_GUARDRAILS, phase_guardrails),
            (ArtifactType.PHASE_STRUCTURE, phase_structure),
        ]
    )
    previous_payload = _load_previous_week_plan_payload(store=store, athlete_id=athlete_id, target_week=target)
    if previous_payload:
        trace_upstream.extend(build_trace_upstream([(ArtifactType.WEEK_PLAN, previous_payload)]))
    source_versions = build_source_versions_map(
        [
            ("season_plan", season_plan),
            ("phase_guardrails", phase_guardrails),
            ("phase_structure", phase_structure),
            ("phase_preview", phase_preview),
            ("previous_week_plan", previous_payload or {}),
        ]
    )
    audit_json_path, audit_csv_path = persist_selection_audit(
        workspace_root=workspace_root,
        schema_dir=schema_dir,
        athlete_id=athlete_id,
        version_key=f"{target_year:04d}-{target_week:02d}",
        run_id=run_id,
        target_week_start=str(week_calendar.get("week_start_date") or ""),
        target_week_end=str(week_calendar.get("week_end_date") or ""),
        payload=selection_audit,
        trace_upstream=trace_upstream,
        source_versions=source_versions,
    )
    return {
        "ok": True,
        "produced": {
            OUTPUT_SPECS[AgentTask.CREATE_WEEK_PLAN].tool_name: saved,
            ArtifactType.WEEK_WORKOUT_SELECTION_AUDIT.value: {
                "path": audit_json_path,
                "csv_path": audit_csv_path,
            },
        },
        "document": document,
        "details": {**details, "selection_audit": selection_audit},
        "warnings": list(review_decision.warnings),
    }


def load_week_workout_family_config(root: Path | str) -> WeekWorkoutProtocolConfig:
    """Backward-compatible wrapper for the protocol config loader."""

    return load_week_workout_protocol_config(root)


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
        forced_quality_family = "SWEET_SPOT_CLASSIC_INTERVALS"
    elif "tempo" in lowered:
        forced_quality_family = "TEMPO_CLASSIC_INTERVALS"
    elif "k3" in lowered or "torque" in lowered:
        forced_quality_family = "K3_CLASSIC_INTERVALS"
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
    athlete_id: str,
    week_calendar_context: JsonMap,
    load_method_context: JsonMap,
    protocol_config: WeekWorkoutProtocolConfig,
    selection_rule_config: WeekWorkoutSelectionRuleConfig,
    progression_history: list[JsonMap],
    phase_preview_payload: JsonMap,
    phase_intent: str,
    phase_type: str,
    season_archetype: str,
    adjustment: WeekAdjustmentIntent,
    initial_warnings: list[str],
) -> tuple[WeekPlanBundleModel, JsonMap]:
    target_band = _active_band(week_calendar_context)
    target_load = int(round(target_band["min"] + (target_band["max"] - target_band["min"]) * adjustment.target_load_fraction))
    hourly_loads = _hourly_loads(load_method_context)
    day_blueprints, allocation_warnings = _allocate_day_blueprints(week_calendar_context=week_calendar_context)
    workout_blueprints, selection_warnings, selection_audit = select_workouts_for_week(
        athlete_id=athlete_id,
        target_iso_week=str(week_calendar_context.get("target_iso_week") or ""),
        day_blueprints=day_blueprints,
        protocol_config=protocol_config,
        selection_rules=selection_rule_config,
        progression_history=progression_history,
        week_calendar_context=week_calendar_context,
        phase_preview_payload=phase_preview_payload,
        phase_intent=phase_intent,
        phase_type=phase_type,
        season_archetype=season_archetype,
        forced_quality_family=adjustment.forced_quality_family,
        preserve_sat_anchor=adjustment.preserve_sat_anchor,
    )
    _reconcile_loads(
        day_blueprints=day_blueprints,
        workout_blueprints=workout_blueprints,
        weekly_target_kj=target_load,
        hourly_loads=hourly_loads,
    )
    shaping_warnings = _apply_shortened_reentry_quality_shaping(
        workout_blueprints=workout_blueprints,
        phase_intent=phase_intent,
    )
    preview_warnings = _collect_phase_preview_alignment_warnings(
        workout_blueprints=workout_blueprints,
        phase_preview_payload=phase_preview_payload,
        target_week=str(week_calendar_context.get("target_iso_week") or ""),
    )
    context_summary = WeekContextAssessmentModel(
        summary=f"Deterministic week planning for {week_calendar_context.get('target_iso_week')}.",
        key_constraints=[
            f"Active weekly band: {target_band['min']}-{target_band['max']} kJ",
            "Fixed rest days preserved.",
            "Workout protocols selected from configuration.",
            "Previous week progression state is reused when a matching protocol signature exists.",
        ],
        completed_vs_planned=[],
        likely_change_request=bool(adjustment.message),
    )
    bundle = WeekPlanBundleModel(
        context_summary=context_summary,
        day_blueprints=day_blueprints,
        workout_blueprints=workout_blueprints,
        constraint_summary=[
            f"Week role: {week_calendar_context.get('phase_week_role')}",
            f"Allowed domains: {', '.join(str(item) for item in week_calendar_context.get('allowed_intensity_domains') or [])}",
        ],
        load_target_summary=[f"Deterministic weekly load target set to {target_load} kJ within the binding active band."],
        revision_summary=([f"Applied bounded adjustment intent: {adjustment.message}"] if adjustment.message else []),
        workout_authoring_summary=["Workout protocols chosen from configurable registry and rendered deterministically."],
        candidate_document_summary=["Week bundle generated without Week CrewAI planning/review/writer stages."],
        warnings=[*initial_warnings, *allocation_warnings, *selection_warnings, *shaping_warnings, *preview_warnings],
    )
    return bundle, selection_audit.payload


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
                    max_scope_of_change="Adjust deterministic protocol selection, progression, add-on composition, and/or workout durations only.",
                )
            ],
            writer_ready_summary="",
        )
    return WeekReviewDecisionModel(
        status="approved",
        warnings=list(planning_bundle.warnings),
        writer_ready_summary="Deterministic week bundle validated and ready for persistence.",
    )


def _allocate_day_blueprints(*, week_calendar_context: JsonMap) -> tuple[list[WeekDayBlueprintModel], list[str]]:
    phase_intent = str(week_calendar_context.get("phase_intent") or "")
    phase_week_role = str(week_calendar_context.get("phase_week_role") or "")
    allowed_day_roles = {str(item).strip().upper() for item in week_calendar_context.get("allowed_day_roles") or []}
    quality_cap = int(week_calendar_context.get("quality_day_cap") or 0)
    role_is_reset = phase_week_role.upper() in {"DELOAD", "MINI_RESET", "SHORTENED_MINI_RESET"}
    reentry_is_conservative = phase_intent == "shortened_re_entry" or phase_week_role.upper() == "SHORTENED_RE_ENTRY"
    day_rows = [_as_map(item) for item in week_calendar_context.get("day_matrix") or []]
    target_week_skeleton = _as_map(week_calendar_context.get("target_week_skeleton"))
    target_week_days = target_week_skeleton.get("days")
    skeleton_days = {
        str(_as_map(day).get("day_of_week") or "").strip(): _as_map(day)
        for day in (target_week_days if isinstance(target_week_days, list) else [])
        if str(_as_map(day).get("day_of_week") or "").strip()
    }
    roles = {
        "Tue": "QUALITY" if quality_cap >= 1 and not role_is_reset else "ENDURANCE",
        "Wed": "RECOVERY" if "RECOVERY" in allowed_day_roles else "ENDURANCE",
        "Thu": "ENDURANCE" if reentry_is_conservative else ("QUALITY" if quality_cap >= 2 and not role_is_reset else "ENDURANCE"),
        "Sat": "ENDURANCE",
        "Sun": "ENDURANCE",
    }
    warnings: list[str] = []
    if reentry_is_conservative and quality_cap >= 2 and not role_is_reset:
        warnings.append(
            "reentry_week_shape: shortened_re_entry defaults to one true quality day; Thu is assigned ENDURANCE support unless a higher-demand override is introduced."
        )
    blueprints: list[WeekDayBlueprintModel] = []
    for row in day_rows:
        day = str(row.get("day") or "")
        availability = _as_map(row.get("availability_hours"))
        fixed_rest = bool(row.get("fixed_rest_day"))
        skeleton_day = skeleton_days.get(day)
        day_role = str(skeleton_day.get("day_role") or "").strip() if skeleton_day else ""
        if not day_role:
            day_role = "REST" if fixed_rest else roles.get(day, "ENDURANCE")
        intended_domain = str(skeleton_day.get("intensity_domain") or "").strip() if skeleton_day else ""
        if not intended_domain:
            intended_domain = "ENDURANCE" if day_role in {"RECOVERY", "ENDURANCE"} else "TEMPO"
        blueprints.append(
            WeekDayBlueprintModel(
                day=day,
                date=str(row.get("date") or ""),
                fixed_rest_day=fixed_rest,
                availability_cap_minutes=_availability_cap_minutes(availability),
                phase_role=str(week_calendar_context.get("phase_role") or ""),
                phase_intent=phase_intent,
                phase_week_role=phase_week_role,
                day_role=day_role,
                intended_domain=intended_domain,
                planned_duration_minutes=0,
                planned_kj=0,
                workout_id=None if fixed_rest else _default_workout_id(week_calendar_context, day, day_role),
                warnings=[],
            )
        )
    return blueprints, warnings


def _select_workout_blueprints(
    *,
    day_blueprints: list[WeekDayBlueprintModel],
    protocol_config: WeekWorkoutProtocolConfig,
    progression_history: list[JsonMap],
    week_calendar_context: JsonMap,
    phase_preview_payload: JsonMap,
    phase_intent: str,
    adjustment: WeekAdjustmentIntent,
) -> tuple[list[WeekWorkoutBlueprintModel], list[str]]:
    allowed_domains = {str(item).strip().upper() for item in week_calendar_context.get("allowed_intensity_domains") or []}
    allowed_modalities = {str(item).strip().upper() for item in week_calendar_context.get("allowed_load_modalities") or []}
    week_role = str(week_calendar_context.get("phase_week_role") or "").strip().upper()
    true_quality_cap = int(week_calendar_context.get("quality_day_cap") or 0)
    true_quality_used = 0
    workout_blueprints: list[WeekWorkoutBlueprintModel] = []
    warnings: list[str] = []
    quality_index = 0
    selected_quality_variants: list[str] = []
    preview_hints = _phase_preview_hints(
        phase_preview_payload=phase_preview_payload,
        target_week=str(week_calendar_context.get("target_iso_week") or ""),
    )
    for day in day_blueprints:
        if day.fixed_rest_day or not day.workout_id:
            continue
        is_anchor = day.day == "Sat" or (day.day == "Sun" and not adjustment.preserve_sat_anchor)
        preview_hint = preview_hints.get(day.day) or {}
        preferred_domain = (
            str(day.intended_domain or "").strip().upper()
            or str(preview_hint.get("intensity_domain") or "").strip().upper()
            or None
        )
        protocol = _pick_protocol(
            protocol_config=protocol_config,
            day_role=day.day_role,
            phase_intent=phase_intent,
            week_role=week_role,
            allowed_domains=allowed_domains,
            allowed_modalities=allowed_modalities,
            is_anchor=is_anchor,
            forced_quality_family=adjustment.forced_quality_family if day.day_role == "QUALITY" and quality_index == 0 else None,
            remaining_true_quality_budget=max(true_quality_cap - true_quality_used, 0),
            preferred_domain=preferred_domain,
            avoid_protocol_variants=set(selected_quality_variants) if day.day_role == "QUALITY" and quality_index > 0 and phase_intent.startswith("shortened_") else set(),
        )
        if day.day_role == "QUALITY":
            quality_index += 1
            selected_quality_variants.append(protocol.protocol_variant)
        if str(protocol.parameters.get("quality_cost") or "endurance_only").strip().lower() == "true_quality":
            true_quality_used += 1
        previous_signature = match_progression_signature(
            signatures=progression_history,
            protocol_type=protocol.protocol_type,
            protocol_variant=protocol.protocol_variant,
            workout_family=protocol.intensity_domain,
            day_role=day.day_role,
        )
        progression_parameters = dict(protocol.parameters)
        addon_policy = protocol_config.addon_policies.get(protocol.addon_policy)
        if addon_policy is not None and addon_policy.policy_id != "NONE":
            progression_parameters.update(
                {
                    "addon_target_domain": addon_policy.target_domain,
                    "addon_target": addon_policy.target,
                    "addon_cadence": addon_policy.cadence,
                    "addon_min_block_minutes": addon_policy.min_block_minutes,
                    "addon_max_block_minutes": addon_policy.max_block_minutes,
                    "addon_step_minutes": addon_policy.step_minutes,
                    "addon_max_share_of_session": addon_policy.max_share_of_session,
                }
            )
        workout_blueprints.append(
            WeekWorkoutBlueprintModel(
                workout_id=day.workout_id,
                date=day.date,
                phase_intent=phase_intent,
                day_role=day.day_role,
                intensity_domain=protocol.intensity_domain,
                workout_family=protocol.intensity_domain,
                family_variant=protocol.protocol_variant,
                protocol_type=protocol.protocol_type,
                protocol_variant=protocol.protocol_variant,
                load_modality=protocol.load_modality,
                generator_profile=protocol.protocol_type,
                addon_policy=protocol.addon_policy,
                target_kj=0,
                progression_state={
                    "primary_axis": protocol.primary_axis,
                    "secondary_axis": protocol.secondary_axis,
                    "progression_priority": list(protocol.parameters.get("progression_priority") or []),
                    "redistribution_rule": protocol.redistribution_rule,
                    "count_tiz_as": str(protocol.parameters.get("count_tiz_as") or "full_work"),
                    "quality_cost": str(protocol.parameters.get("quality_cost") or "endurance_only"),
                    "previous_signature": dict(previous_signature) if previous_signature else {},
                },
                selection_reason=(
                    f"Selected protocol {protocol.protocol_id} for {day.day_role}."
                    + (f" Prior progression signature matched {previous_signature.get('protocol_variant_guess')}." if previous_signature else "")
                ),
                activation_required="activation_capable" in protocol.tags,
                low_end_endurance="recovery_like" in protocol.tags,
                progression_parameters=progression_parameters,
                phase_legality_status="legal",
                planned_duration_minutes=0,
                planned_kj=0,
                required_sections=["Warmup", "Main Set", "Cooldown"],
                exportability_status="pending",
                warnings=[],
            )
        )
    if selected_quality_variants.count("TEMPO_CLASSIC") > 1 and phase_intent == "shortened_re_entry":
        warnings.append("week_quality_monotony: shortened_re_entry resolved to repeated TEMPO_CLASSIC; second quality session will be damped.")
    return workout_blueprints, warnings


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
        object.__setattr__(workout, "target_kj", day.planned_kj)
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
            object.__setattr__(workout, "target_kj", new_kj)
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
            object.__setattr__(workout, "target_kj", new_kj)
            progressed = True
            if total <= weekly_target_kj:
                break
        if not progressed:
            break
    for day in day_blueprints:
        if day.fixed_rest_day or not day.workout_id:
            continue
        workout = by_workout.get(day.workout_id or "")
        if workout is None:
            continue
        primary_tiz = _estimate_primary_tiz_minutes(workout=workout, session_minutes=day.planned_duration_minutes)
        object.__setattr__(workout, "primary_tiz_target_min", primary_tiz)


def _pick_protocol(
    *,
    protocol_config: WeekWorkoutProtocolConfig,
    day_role: str,
    phase_intent: str,
    week_role: str,
    allowed_domains: set[str],
    allowed_modalities: set[str],
    is_anchor: bool,
    forced_quality_family: str | None,
    remaining_true_quality_budget: int,
    preferred_domain: str | None,
    avoid_protocol_variants: set[str],
) -> WeekWorkoutProtocol:
    if forced_quality_family:
        forced = protocol_config.protocols.get(forced_quality_family.upper())
        if forced and protocol_is_allowed(
            forced,
            day_role=day_role,
            phase_intent=phase_intent,
            week_role=week_role,
            allowed_domains=allowed_domains,
            allowed_modalities=allowed_modalities,
            is_anchor=is_anchor,
        ) and _quality_budget_allows(protocol=forced, remaining_true_quality_budget=remaining_true_quality_budget):
            return forced
    role = day_role.upper()
    candidates = list(protocol_config.by_phase_intent.get(phase_intent.lower(), {}).get(role, []))
    candidates.extend(protocol_config.by_day_role.get(role, []))
    legal_candidates: list[WeekWorkoutProtocol] = []
    seen: set[str] = set()
    for protocol_id in candidates:
        if protocol_id in seen:
            continue
        seen.add(protocol_id)
        protocol = protocol_config.protocols[protocol_id]
        if protocol_is_allowed(
            protocol,
            day_role=day_role,
            phase_intent=phase_intent,
            week_role=week_role,
            allowed_domains=allowed_domains,
            allowed_modalities=allowed_modalities,
            is_anchor=is_anchor,
        ) and _quality_budget_allows(protocol=protocol, remaining_true_quality_budget=remaining_true_quality_budget):
            legal_candidates.append(protocol)
    if preferred_domain:
        preferred_candidates = [item for item in legal_candidates if item.intensity_domain == preferred_domain]
        if preferred_candidates:
            legal_candidates = preferred_candidates
    if avoid_protocol_variants:
        non_duplicate_candidates = [item for item in legal_candidates if item.protocol_variant not in avoid_protocol_variants]
        if non_duplicate_candidates:
            legal_candidates = non_duplicate_candidates
    if legal_candidates:
        return legal_candidates[0]
    raise ValueError(f"No legal workout protocol available for day_role={day_role}, phase_intent={phase_intent}, week_role={week_role}.")


def _quality_budget_allows(*, protocol: WeekWorkoutProtocol, remaining_true_quality_budget: int) -> bool:
    quality_cost = str(protocol.parameters.get("quality_cost") or "endurance_only").strip().lower()
    if quality_cost != "true_quality":
        return True
    return remaining_true_quality_budget > 0


def _phase_preview_hints(*, phase_preview_payload: JsonMap, target_week: str) -> dict[str, JsonMap]:
    data = _as_map(phase_preview_payload.get("data"))
    for week in data.get("weekly_agenda_preview") or []:
        week_map = _as_map(week)
        if str(week_map.get("week") or "").strip() != target_week:
            continue
        return {
            str(_as_map(item).get("day_of_week") or "").strip(): _as_map(item)
            for item in week_map.get("days") or []
            if str(_as_map(item).get("day_of_week") or "").strip()
        }
    return {}


def _apply_shortened_reentry_quality_shaping(*, workout_blueprints: list[WeekWorkoutBlueprintModel], phase_intent: str) -> list[str]:
    if phase_intent != "shortened_re_entry":
        return []
    warnings: list[str] = []
    quality_workouts = [item for item in workout_blueprints if item.day_role == "QUALITY"]
    first_tempo_seen = False
    for workout in quality_workouts:
        if str(workout.protocol_variant or "").upper() != "TEMPO_CLASSIC":
            continue
        if not first_tempo_seen:
            first_tempo_seen = True
            continue
        params = dict(workout.progression_parameters)
        params["work_target"] = "80%-85%"
        object.__setattr__(workout, "progression_parameters", params)
        if workout.primary_tiz_target_min is not None:
            object.__setattr__(workout, "primary_tiz_target_min", min(int(workout.primary_tiz_target_min), 45))
        object.__setattr__(
            workout,
            "selection_reason",
            f"{workout.selection_reason or ''} Re-entry shaping damped repeated Tempo Classic quality stimulus.",
        )
        workout.warnings.append("reentry_shaping: repeated Tempo Classic quality day damped to a lighter stabilization dose.")
        warnings.append(f"reentry_shaping:{workout.workout_id}: repeated Tempo Classic quality day damped.")
    return warnings


def _collect_phase_preview_alignment_warnings(
    *,
    workout_blueprints: list[WeekWorkoutBlueprintModel],
    phase_preview_payload: JsonMap,
    target_week: str,
) -> list[str]:
    preview_hints = _phase_preview_hints(phase_preview_payload=phase_preview_payload, target_week=target_week)
    warnings: list[str] = []
    for workout in workout_blueprints:
        day = workout.workout_id.split("-")[2].title()[:3] if "-" in workout.workout_id else ""
        hint = preview_hints.get(day)
        if not hint:
            continue
        hinted_domain = str(hint.get("intensity_domain") or "").strip().upper()
        hinted_modality = str(hint.get("load_modality") or "").strip().upper()
        actual_domain = str(workout.intensity_domain or "").strip().upper()
        actual_modality = str(workout.load_modality or "").strip().upper()
        if hinted_domain and hinted_domain not in {"NONE", "RECOVERY"} and hinted_domain != actual_domain:
            warnings.append(f"phase_preview_alignment:{workout.workout_id}: preview suggested domain {hinted_domain}, generated {actual_domain}.")
        if hinted_modality and hinted_modality not in {"", "NONE"} and hinted_modality != actual_modality:
            warnings.append(f"phase_preview_alignment:{workout.workout_id}: preview suggested modality {hinted_modality}, generated {actual_modality}.")
    return warnings


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


def _estimate_primary_tiz_minutes(*, workout: WeekWorkoutBlueprintModel, session_minutes: int) -> int:
    params = dict(workout.progression_parameters)
    tiz_min = int(params.get("tiz_min_minutes") or 0)
    tiz_max = int(params.get("tiz_max_minutes") or 0)
    tiz_standard_cap = int(params.get("tiz_standard_cap_minutes") or 0)
    tiz_hard_cap = int(params.get("tiz_hard_cap_minutes") or 0)
    count_tiz_as = str(params.get("count_tiz_as") or "full_work").strip().lower()
    protocol_type = str(workout.protocol_type or "").upper()
    warm = int(params.get("warmup_minutes") or 0)
    cool = int(params.get("cooldown_minutes") or 0)
    activation_minutes = 3 if str(params.get("activation_profile") or "").strip() else 0
    available = max(session_minutes - warm - cool - activation_minutes, 0)
    default_upper = tiz_standard_cap or tiz_hard_cap or tiz_max or available
    if protocol_type == "LONG_STEADY":
        return max(min(available, default_upper, tiz_hard_cap or available, tiz_max or available), tiz_min or 0)
    if protocol_type == "FATIGUE_FINISH":
        finish_min = int(params.get("finish_min_minutes") or 20)
        finish_max = int(params.get("finish_max_minutes") or finish_min)
        late_standard = int(params.get("late_finish_standard_cap_minutes") or 0)
        late_hard = int(params.get("late_finish_hard_cap_minutes") or 0)
        finish_available = max(session_minutes - int(params.get("preload_min_minutes") or 120), 0)
        capped = min(finish_available, finish_max, late_standard or finish_max, late_hard or finish_max)
        return min(max(finish_min, capped), late_hard or finish_max)
    if count_tiz_as == "on_time":
        return max(min(available, default_upper, tiz_hard_cap or available, tiz_max or available), tiz_min or 0)
    return max(min(available, default_upper, tiz_hard_cap or available, tiz_max or available), tiz_min or 0)


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


def _load_prior_progression_signatures(*, store: LocalArtifactStore, athlete_id: str, target_week: IsoWeek) -> list[JsonMap]:
    previous = previous_iso_week(target_week)
    previous_key = f"{previous.year:04d}-{previous.week:02d}"
    resolved = store.resolve_week_version_key(athlete_id, ArtifactType.WEEK_PLAN, previous_key)
    if not resolved:
        return []
    try:
        payload = store.load_version(athlete_id, ArtifactType.WEEK_PLAN, resolved)
    except Exception:
        return []
    if not isinstance(payload, dict):
        return []
    return extract_progression_signatures_from_week_plan(payload)


def _load_previous_week_plan_payload(*, store: LocalArtifactStore, athlete_id: str, target_week: IsoWeek) -> JsonMap | None:
    previous = previous_iso_week(target_week)
    previous_key = f"{previous.year:04d}-{previous.week:02d}"
    resolved = store.resolve_week_version_key(athlete_id, ArtifactType.WEEK_PLAN, previous_key)
    if not resolved:
        return None
    try:
        payload = store.load_version(athlete_id, ArtifactType.WEEK_PLAN, resolved)
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _as_map(value: object) -> JsonMap:
    return value if isinstance(value, dict) else {}
