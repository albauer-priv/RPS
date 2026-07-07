"""Week-artifact CrewAI guardrails enforcing ADR-035 authority boundaries."""

from __future__ import annotations

import re
from typing import Any, cast

from rps.crewai_runtime.guardrails_context import _GUARDRAIL_CONTEXT, GuardrailResult, JsonMap
from rps.crewai_runtime.guardrails_utilities import (
    _active_weekly_band_from_context,
    _as_float,
    _as_list,
    _as_map,
    _coerce_mapping,
    _week_calendar_context,
)
from rps.planning.contracts import (
    blocking_messages,
    validate_week_bundle_review_readiness,
    validate_week_plan_against_week_context,
)
from rps.workspace.iso_helpers import IsoWeek, parse_iso_week


def week_bundle_integrity(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Week bundle must decode to an object.")
    required = ("context_summary", "constraint_summary", "load_target_summary", "revision_summary")
    missing = [field for field in required if field not in mapping]
    if missing:
        return (False, f"Week bundle missing required keys: {', '.join(missing)}")
    day_blueprints = mapping.get("day_blueprints")
    workout_blueprints = mapping.get("workout_blueprints")
    if not isinstance(day_blueprints, list) or len(day_blueprints) != 7:
        return (False, "Week bundle day_blueprints must contain exactly seven Mon-Sun day blueprints.")
    observed_days = [str(_as_map(item).get("day") or "") for item in day_blueprints]
    if observed_days != ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
        return (False, "Week bundle day_blueprints must be ordered Mon, Tue, Wed, Thu, Fri, Sat, Sun.")
    if not isinstance(workout_blueprints, list):
        return (False, "Week bundle workout_blueprints must be a list.")
    for blueprint in workout_blueprints:
        if not isinstance(blueprint, dict):
            continue
        if not str(blueprint.get("intensity_domain") or "").strip():
            return (False, "Week bundle workout blueprints must include intensity_domain.")
        if not str(blueprint.get("workout_family") or "").strip():
            return (False, "Week bundle workout blueprints must include workout_family.")
    return (True, mapping)


def week_bundle_matches_context(result: Any) -> GuardrailResult:
    """Validate internal Week bundle day blueprints against active calendar context."""

    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Week bundle must decode to an object.")
    context = _week_calendar_context()
    if not context:
        return (True, mapping)
    blueprints = [_as_map(item) for item in _as_list(mapping.get("day_blueprints"))]
    if not blueprints:
        return (False, "Week bundle must include day_blueprints for contract validation.")
    expected_days = [_as_map(item) for item in _as_list(context.get("day_matrix"))]
    for idx, expected in enumerate(expected_days):
        if idx >= len(blueprints):
            return (False, f"Week bundle missing day blueprint for {expected.get('day')} {expected.get('date')}.")
        observed = blueprints[idx]
        if observed.get("day") != expected.get("day") or observed.get("date") != expected.get("date"):
            return (
                False,
                "Week bundle day_blueprints must match active week calendar; "
                f"row {idx + 1} got {observed.get('day')} {observed.get('date')}, "
                f"expected {expected.get('day')} {expected.get('date')}.",
            )
        if expected.get("fixed_rest_day") is True:
            planned_duration = _as_float(observed.get("planned_duration_minutes")) or 0.0
            planned_kj = _as_float(observed.get("planned_kj")) or 0.0
            if planned_duration > 0 or planned_kj > 0 or observed.get("workout_id"):
                return (
                    False,
                    f"Week bundle fixed rest day {expected.get('day')} must carry no duration, load, or workout.",
                )
    return (True, mapping)


def _normalized_domain_token(value: Any) -> str:
    return str(value or "").upper().replace(" ", "_").replace("-", "_").strip("_")


def week_bundle_domain_legality_messages(
    mapping: JsonMap,
    *,
    week_calendar_context: JsonMap | None = None,
) -> list[str]:
    """Return semantic workout-domain legality issues for an internal week bundle."""

    context = week_calendar_context or _week_calendar_context()
    if not context or not isinstance(mapping, dict):
        return []
    workout_blueprints = [_as_map(item) for item in _as_list(mapping.get("workout_blueprints"))]
    if not workout_blueprints:
        return []
    allowed_domains = {
        _normalized_domain_token(item)
        for item in _as_list(context.get("allowed_intensity_domains"))
        if str(item).strip()
    }
    forbidden_domains = {
        _normalized_domain_token(item)
        for item in _as_list(context.get("forbidden_intensity_domains"))
        if str(item).strip()
    }
    issues: list[str] = []
    forbidden_family_hits: dict[str, list[str]] = {}
    forbidden_domain_hits: dict[str, list[str]] = {}
    missing_fields: list[str] = []
    illegal_status_ids: list[str] = []
    outside_allowance: dict[str, list[str]] = {}
    for blueprint in workout_blueprints:
        workout_id = str(blueprint.get("workout_id") or "<unknown>")
        declared_domain = _normalized_domain_token(blueprint.get("intensity_domain"))
        declared_family = _normalized_domain_token(blueprint.get("workout_family"))
        legality_status = str(blueprint.get("phase_legality_status") or "").strip().lower()
        if not declared_domain:
            missing_fields.append(f"{workout_id}: missing intensity_domain")
        if not declared_family:
            missing_fields.append(f"{workout_id}: missing workout_family")
        if legality_status == "illegal":
            illegal_status_ids.append(workout_id)
        if declared_domain in forbidden_domains:
            forbidden_domain_hits.setdefault(declared_domain, []).append(workout_id)
        if allowed_domains and declared_domain and declared_domain not in allowed_domains and declared_domain not in {"NONE"}:
            outside_allowance.setdefault(declared_domain, []).append(workout_id)
        if declared_family in forbidden_domains:
            forbidden_family_hits.setdefault(declared_family, []).append(workout_id)
    if missing_fields:
        issues.append("Week workout blueprints missing canonical legality fields: " + ", ".join(missing_fields))
    if illegal_status_ids:
        issues.append("Week workout blueprints already marked phase-illegal: " + ", ".join(sorted(illegal_status_ids)))
    if forbidden_domain_hits:
        rendered = ", ".join(f"{domain} ({', '.join(sorted(ids))})" for domain, ids in sorted(forbidden_domain_hits.items()))
        issues.append(f"Week workout blueprints declare forbidden intensity domains: {rendered}.")
    if forbidden_family_hits:
        rendered = ", ".join(f"{family} ({', '.join(sorted(ids))})" for family, ids in sorted(forbidden_family_hits.items()))
        issues.append(f"Week workout blueprints declare forbidden workout families: {rendered}.")
    if outside_allowance:
        rendered = ", ".join(f"{domain} ({', '.join(sorted(ids))})" for domain, ids in sorted(outside_allowance.items()))
        issues.append(f"Week workout blueprints declare domains outside phase allowance: {rendered}.")
    return issues


def week_bundle_domain_legality_check(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Week bundle must decode to an object.")
    issues = week_bundle_domain_legality_messages(mapping)
    if issues:
        return (False, "; ".join(issues[:5]))
    return (True, mapping)


def week_bundle_review_readiness(result: Any) -> GuardrailResult:
    """Ensure a week bundle is review-ready before review runs."""

    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Week bundle must decode to an object.")
    issues = validate_week_bundle_review_readiness(week_bundle_payload=mapping)
    messages = blocking_messages(issues)
    if messages:
        return (False, "; ".join(messages[:5]))
    return (True, mapping)


def review_decision_integrity(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Review decision must decode to an object.")
    status = mapping.get("status")
    if status not in {"approved", "replan_required", "rejected"}:
        return (False, "Review decision status must be approved, replan_required, or rejected.")
    for field in ("blocking_issues", "warnings", "replan_instructions"):
        if field in mapping and not isinstance(mapping[field], list):
            return (False, f"Review decision field '{field}' must be a list.")
    if not isinstance(mapping.get("writer_ready_summary"), str):
        return (False, "Review decision must include writer_ready_summary string.")
    blocking_issues = [str(item).strip() for item in mapping.get("blocking_issues") or [] if str(item).strip()]
    replan_instructions = mapping.get("replan_instructions") or []
    writer_ready_summary = str(mapping.get("writer_ready_summary") or "").strip()
    if status == "approved":
        if blocking_issues:
            return (False, "Approved review decision must not include blocking_issues.")
        if replan_instructions:
            return (False, "Approved review decision must not include replan_instructions.")
        if not writer_ready_summary:
            return (False, "Approved review decision must include non-empty writer_ready_summary.")
    if status == "replan_required" and not replan_instructions:
        return (False, "replan_required review decision must include replan_instructions.")
    return (True, mapping)


def week_corridor_and_capacity_check(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Week plan output must decode to an object.")
    data = mapping.get("data")
    if not isinstance(data, dict):
        return (True, mapping)
    summary = data.get("week_summary")
    if not isinstance(summary, dict):
        return (True, mapping)
    planned = summary.get("planned_weekly_load_kj")
    corridor = summary.get("weekly_load_corridor_kj") or summary.get("weekly_load_corridor")
    if not isinstance(planned, (int, float)) or not isinstance(corridor, dict):
        return (True, mapping)
    min_value = corridor.get("min")
    max_value = corridor.get("max")
    if isinstance(min_value, (int, float)) and float(planned) < float(min_value):
        return (False, "Week planned_weekly_load_kj is below weekly load corridor.")
    if isinstance(max_value, (int, float)) and float(planned) > float(max_value):
        return (False, "Week planned_weekly_load_kj exceeds weekly load corridor.")
    return (True, mapping)


def week_active_corridor_match(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Week plan output must decode to an object.")
    active_band = _active_weekly_band_from_context()
    if not active_band:
        return (True, mapping)
    data = mapping.get("data")
    if not isinstance(data, dict):
        return (True, mapping)
    summary = data.get("week_summary")
    if not isinstance(summary, dict):
        return (True, mapping)
    corridor = summary.get("weekly_load_corridor_kj") or summary.get("weekly_load_corridor")
    if not isinstance(corridor, dict):
        return (False, "Week summary must include weekly_load_corridor_kj matching active Phase/S5 band.")
    observed_min = _as_float(corridor.get("min"))
    observed_max = _as_float(corridor.get("max"))
    expected_min = _as_float(active_band.get("min"))
    expected_max = _as_float(active_band.get("max"))
    if None in {observed_min, observed_max, expected_min, expected_max}:
        return (True, mapping)
    if abs(cast(float, observed_min) - cast(float, expected_min)) > 0.001 or abs(cast(float, observed_max) - cast(float, expected_max)) > 0.001:
        return (
            False,
            "Week weekly_load_corridor_kj must exactly mirror active Phase/S5 band "
            f"{expected_min:g}-{expected_max:g}; got {observed_min:g}-{observed_max:g}.",
        )
    planned = _as_float(summary.get("planned_weekly_load_kj"))
    if planned is not None and planned < cast(float, expected_min):
        return (False, "Week planned_weekly_load_kj is below active Phase/S5 weekly band.")
    if planned is not None and planned > cast(float, expected_max):
        return (False, "Week planned_weekly_load_kj exceeds active Phase/S5 weekly band.")
    return (True, mapping)


def week_recovery_day_load_check(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Week plan output must decode to an object.")
    data = mapping.get("data")
    if not isinstance(data, dict):
        return (True, mapping)
    for entry in data.get("agenda") or []:
        if not isinstance(entry, dict):
            continue
        role = str(entry.get("day_role") or "").upper()
        planned = entry.get("planned_kj")
        workout_id = entry.get("workout_id")
        planned_value = float(planned) if isinstance(planned, (int, float)) else 0.0
        if role in {"REST", "OFF_BIKE"} and (planned_value > 0 or workout_id):
            return (False, f"{role} day {entry.get('day')} must not carry planned load or a workout_id.")
    return (True, mapping)


def week_agenda_shape_and_calendar_check(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Week plan output must decode to an object.")
    data = mapping.get("data")
    if not isinstance(data, dict):
        return (True, mapping)
    agenda = data.get("agenda")
    if not isinstance(agenda, list):
        return (False, "Week plan agenda must be a list.")
    target_week = _target_week_from_context_or_meta(mapping)
    if target_week is None:
        return (True, mapping)
    try:
        from rps.planning.week_availability import validate_week_plan_daily_availability

        issues = validate_week_plan_daily_availability(
            week_plan_payload=mapping,
            availability_payload={},
            target_week=target_week,
        )
    except Exception as exc:
        return (False, f"Week agenda calendar check failed: {exc}")
    if issues:
        return (False, "; ".join(issue.format() for issue in issues[:5]))
    return (True, mapping)


def week_daily_availability_check(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Week plan output must decode to an object.")
    context = _GUARDRAIL_CONTEXT.get({})
    availability_payload = context.get("availability_payload")
    if not isinstance(availability_payload, dict):
        return (True, mapping)
    target_week = context.get("target_week")
    if isinstance(target_week, dict):
        year = target_week.get("year")
        week = target_week.get("week")
        target_week = IsoWeek(int(year), int(week)) if isinstance(year, int) and isinstance(week, int) else None
    try:
        from rps.planning.week_availability import validate_week_plan_daily_availability

        issues = validate_week_plan_daily_availability(
            week_plan_payload=mapping,
            availability_payload=availability_payload,
            target_week=target_week if isinstance(target_week, IsoWeek) else None,
        )
    except Exception as exc:
        return (False, f"Week daily availability check failed: {exc}")
    if issues:
        return (False, "; ".join(issue.format() for issue in issues[:5]))
    return (True, mapping)


def week_phase_role_alignment_check(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Week plan output must decode to an object.")
    context = _week_calendar_context()
    if not context:
        return (True, mapping)
    data = mapping.get("data")
    if not isinstance(data, dict):
        return (True, mapping)
    approved_bundle = _as_map(_GUARDRAIL_CONTEXT.get({}).get("approved_planning_bundle"))
    if approved_bundle:
        bundle_issues = week_bundle_domain_legality_messages(
            approved_bundle,
            week_calendar_context=context,
        )
        if bundle_issues:
            return (False, "; ".join(bundle_issues[:5]))
    agenda = [entry for entry in _as_list(data.get("agenda")) if isinstance(entry, dict)]
    allowed_roles = {str(item).upper() for item in _as_list(context.get("allowed_day_roles")) if str(item).strip()}
    forbidden_roles = {str(item).upper() for item in _as_list(context.get("forbidden_day_roles")) if str(item).strip()}
    quality_count = 0
    for entry in agenda:
        role = str(entry.get("day_role") or "").upper()
        if role == "QUALITY":
            quality_count += 1
        if allowed_roles and role not in allowed_roles:
            return (False, f"Week agenda day {entry.get('day')} uses day_role {role}, outside allowed phase roles {sorted(allowed_roles)}.")
        if role in forbidden_roles:
            return (False, f"Week agenda day {entry.get('day')} uses forbidden phase day_role {role}.")
    cap = _as_float(context.get("quality_day_cap"))
    if cap is not None and quality_count > int(cap):
        return (False, f"Week agenda has {quality_count} QUALITY days, exceeding phase quality_day_cap {int(cap)}.")
    week_role = str(context.get("phase_week_role") or context.get("phase_role_for_week") or "").upper()
    if week_role in {"DELOAD", "MINI_RESET", "SHORTENED_MINI_RESET"} and quality_count > 0:
        return (False, f"{week_role} week must not schedule QUALITY days.")
    forbidden_domains = {str(item).upper().replace(" ", "_") for item in _as_list(context.get("forbidden_intensity_domains"))}
    allowed_domains = {str(item).upper().replace(" ", "_") for item in _as_list(context.get("allowed_intensity_domains"))}
    domain_hits = _workout_domain_hits(data)
    domain_sources = _workout_domain_sources(data)
    if approved_bundle:
        blueprint_by_workout_id = {
            str(_as_map(item).get("workout_id") or ""): _as_map(item)
            for item in _as_list(approved_bundle.get("workout_blueprints"))
            if str(_as_map(item).get("workout_id") or "").strip()
        }
        for workout in _as_list(data.get("workouts")):
            workout_map = _as_map(workout)
            workout_id = str(workout_map.get("workout_id") or "")
            blueprint = blueprint_by_workout_id.get(workout_id)
            if not blueprint:
                continue
            declared_domain = _normalized_domain_token(blueprint.get("intensity_domain"))
            declared_family = _normalized_domain_token(blueprint.get("workout_family"))
            workout_hits = _workout_domain_hits({"workouts": [workout_map]})
            explicit_forbidden = sorted((workout_hits & forbidden_domains) - {declared_domain, declared_family})
            if explicit_forbidden:
                rendered = ", ".join(explicit_forbidden)
                return (
                    False,
                    f"Week workout blueprint/text mismatch for {workout_id}: declared "
                    f"{declared_domain or '<missing>'}/{declared_family or '<missing>'}, "
                    f"but final workout content signals forbidden domains {rendered}.",
                )
    if forbidden_domains:
        forbidden_used = sorted(domain_hits & forbidden_domains)
        if forbidden_used:
            details = []
            for domain in forbidden_used:
                workout_ids = sorted(domain_sources.get(domain, set()))
                if workout_ids:
                    details.append(f"{domain} ({', '.join(workout_ids)})")
                else:
                    details.append(domain)
            return (False, f"Week workouts use forbidden phase intensity domains: {', '.join(details)}.")
    if allowed_domains:
        domain_outside = sorted(domain_hits - allowed_domains - {"NONE", "RECOVERY", "ENDURANCE"})
        if domain_outside:
            details = []
            for domain in domain_outside:
                workout_ids = sorted(domain_sources.get(domain, set()))
                if workout_ids:
                    details.append(f"{domain} ({', '.join(workout_ids)})")
                else:
                    details.append(domain)
            return (False, f"Week workouts use intensity domains outside phase allowance: {', '.join(details)}.")
    return (True, mapping)


def week_contract_context_match(result: Any) -> GuardrailResult:
    """Validate Week Plan against active deterministic week context."""

    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Week plan output must decode to an object.")
    context = _week_calendar_context()
    if not context:
        return (True, mapping)
    issues = validate_week_plan_against_week_context(
        week_plan_payload=mapping,
        week_calendar_context=context,
    )
    messages = blocking_messages(issues)
    if messages:
        return (False, "; ".join(messages[:5]))
    return (True, mapping)


def week_exportability_check(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Week plan output must decode to an object.")
    try:
        from rps.workouts.validator import collect_week_plan_export_issues

        issues = collect_week_plan_export_issues(mapping)
    except Exception as exc:
        return (False, f"Week exportability check failed: {exc}")
    if issues:
        return (False, "; ".join(issue.format() for issue in issues[:5]))
    return (True, mapping)


def week_workout_structure_policy_check(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Week plan output must decode to an object.")
    try:
        from rps.workouts.validator import collect_week_plan_export_issues

        issues = collect_week_plan_export_issues(mapping)
    except Exception as exc:
        return (False, f"Week workout structure check failed: {exc}")
    if issues:
        return (False, "; ".join(issue.format() for issue in issues[:5]))
    return (True, mapping)


def _target_week_from_context_or_meta(mapping: JsonMap) -> IsoWeek | None:
    context = _GUARDRAIL_CONTEXT.get({})
    target_week = context.get("target_week")
    if isinstance(target_week, IsoWeek):
        return target_week
    if isinstance(target_week, dict):
        year = target_week.get("year")
        week = target_week.get("week")
        if isinstance(year, int) and isinstance(week, int):
            return IsoWeek(year, week)
    return parse_iso_week(_as_map(mapping.get("meta")).get("iso_week"))


def _workout_domain_hits(data: JsonMap) -> set[str]:
    return set(_workout_domain_sources(data))


def _workout_domain_sources(data: JsonMap) -> dict[str, set[str]]:
    sources: dict[str, set[str]] = {}
    for workout in _as_list(data.get("workouts")):
        workout_map = _as_map(workout)
        workout_id = str(workout_map.get("workout_id") or "<unknown>")
        for domain in _derived_workout_domains(workout_map):
            sources.setdefault(domain, set()).add(workout_id)
    return sources


def _derived_workout_domains(workout: JsonMap) -> set[str]:
    text = str(workout.get("workout_text") or "").strip()
    if not text:
        return set()
    try:
        from rps.workouts.structured import parse_workout_text

        structure = parse_workout_text(
            text,
            context_text=" ".join(str(workout.get(field) or "") for field in ("title", "notes")),
        )
    except Exception:
        haystack = text.upper().replace(" ", "_").replace("-", "_")
        domains = {"ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD", "VO2MAX"}
        return {domain for domain in domains if domain in haystack}

    step_targets: list[float] = []
    has_activation = False
    low_cadence = False
    for section in structure.sections:
        if section.name == "#### Activation":
            has_activation = True
        for block in section.blocks:
            steps = block.steps if hasattr(block, "steps") else (block,)
            for step in steps:
                target = str(step.target)
                low, high = _percent_bounds(target)
                step_targets.extend([low, high])
                cadence = str(step.cadence)
                if cadence.endswith("rpm") and cadence.split("rpm", 1)[0].startswith("50"):
                    low_cadence = True
    if not step_targets:
        return set()
    max_target = max(step_targets)
    if low_cadence and max_target >= 84.0:
        return {"ENDURANCE"}
    if max_target >= 96.0:
        return {"THRESHOLD"}
    if max_target >= 88.0 and has_activation:
        return {"SWEET_SPOT"}
    if max_target >= 76.0:
        return {"TEMPO"}
    return {"ENDURANCE"}


def _percent_bounds(target: str) -> tuple[float, float]:
    rendered = str(target).replace("ramp ", "")
    values = [float(item[:-1]) for item in re.findall(r"\d+(?:\.\d+)?%", rendered)]
    if not values:
        return 0.0, 0.0
    if len(values) == 1:
        return values[0], values[0]
    return min(values), max(values)


def des_diagnostic_only(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "DES report output must decode to an object.")
    data = mapping.get("data")
    if not isinstance(data, dict):
        return (True, mapping)
    recommendation = data.get("recommendation")
    if not isinstance(recommendation, dict):
        return (True, mapping)
    if recommendation.get("type") not in (None, "advisory"):
        return (False, "DES recommendation type must remain advisory.")
    if recommendation.get("scope") not in (None, "Season-Planner"):
        return (False, "DES recommendation scope must remain Season-Planner.")
    explicitly_not = recommendation.get("explicitly_not")
    if isinstance(explicitly_not, list):
        missing = {"direct_phase_change", "weekly_intervention"} - {str(item) for item in explicitly_not}
        if missing:
            return (False, "DES recommendation must explicitly exclude direct_phase_change and weekly_intervention.")
    return (True, mapping)
