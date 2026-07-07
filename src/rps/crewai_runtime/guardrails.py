"""Guardrail registry and helpers for CrewAI task construction."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, cast

from rps.crewai_runtime.guardrails_context import (
    _GUARDRAIL_CONTEXT,
    GuardrailFn,
    GuardrailResult,
    JsonMap,
    current_guardrail_runtime_context,
)
from rps.crewai_runtime.guardrails_generic import (
    adjustment_intent_has_preview_message,
    audit_lists_are_lists,
    coach_preview_summary_complete,
    coaching_recommendation_text_present,
    pending_resolution_summary_present,
    typed_output_present,
)
from rps.crewai_runtime.guardrails_schema import (
    artifact_envelope_basic,
    artifact_meta_data_present,
    artifact_schema_valid,
)
from rps.crewai_runtime.guardrails_utilities import (
    _active_weekly_band_from_context,
    _as_float,
    _as_list,
    _as_map,
    _coerce_mapping,
    _contains_any,
    _future_event_runtime_context,
    _phase_execution_context,
    _scenario_rationale_text,
    _season_phase_load_context,
    _season_phase_slot_context,
    _string_list,
    _week_calendar_context,
    _with_guardrail_telemetry,
    canonicalize_season_bundle_shape_aliases,
)
from rps.planning.contracts import (
    blocking_messages,
    validate_phase_against_execution_context,
    validate_phase_bundle_review_readiness,
    validate_phase_s5_bands_against_context,
    validate_season_bundle_review_readiness,
    validate_season_bundle_semantics,
    validate_season_plan_against_phase_load_context,
    validate_season_plan_against_phase_slots,
    validate_week_bundle_review_readiness,
    validate_week_plan_against_week_context,
)
from rps.planning.phase_authority import format_role_week_load_bands, normalize_role_week_load_bands
from rps.workspace.intensity_domains import normalize_intensity_domain_list
from rps.workspace.iso_helpers import IsoWeek, parse_iso_week, parse_iso_week_range


@dataclass(frozen=True)
class TaskExecutionPolicy:
    """Resolved task execution policy merged from config defaults and overrides."""

    output_mode: str
    guardrails: tuple[str, ...]
    guardrail_max_retries: int


_SUPPORTED_SCENARIO_CADENCES = {"2:1", "3:1", "2:1:1"}
_CADENCE_TOKENS = ("2:1", "3:1", "2:1:1", "cadence")
_SHARED_CADENCE_MARKERS = (
    "shared cadence",
    "same cadence",
    "cadence held constant",
    "keep cadence constant",
    "cadence remains constant",
    "cadence is intentionally held constant",
    "cadence is intentionally shared",
    "intentionally held constant",
    "intentionally shared",
)
_DIFFERENTIATION_MARKERS = (
    "load philosophy",
    "specificity",
    "fatigue",
    "recovery margin",
    "recovery tolerance",
    "risk posture",
    "risk profile",
    "intensity permissions",
    "density",
)
_SCENARIO_SELECTION_POSITIVE_MARKERS = (
    "stable recovery",
    "uncertain recovery",
    "continuity priority",
    "continuity",
    "recoverability",
    "load tolerance",
    "fatigue exposure tolerance",
    "travel",
    "logistics",
    "lower recovery margin",
    "recovery margin",
)
_SCENARIO_SELECTION_NEGATIVE_MARKERS = (
    "fatigue risk",
    "recovery slip",
    "continuity break",
    "travel disruption",
    "logistics disruption",
    "insufficient tolerance",
    "under-deliver",
    "too conservative",
    "too aggressive",
    "overload risk",
)
_DOMAIN_ELIGIBILITY_MARKERS = (
    "eligibility",
    "eligible",
    "later assignment",
    "not every phase",
    "does not authorize every domain",
    "not phase-wide authorization",
)
_DOMAIN_AUTHORIZATION_MARKERS = (
    "every phase",
    "all phases",
    "blanket legality",
    "globally authorized",
    "phase-wide authorization",
)
_OBJECTIVE_RESOLUTION_MARKERS = (
    "objective reconciled",
    "primary event target now replaced",
    "final event hierarchy resolved here",
    "objective mismatch resolved",
)
_VO2_RATIONALE_MARKER_GROUPS = (
    ("sparse", "occasional", "limited"),
    ("ceiling-support", "fresh-only", "fresh"),
    ("not primary identity",),
    ("specificity-under-fatigue", "density", "event simulation", "load posture"),
)
_ARCHETYPE_REQUIRED_MARKER_GROUPS = (
    ("ceiling support", "early ceiling", "early vo2 support"),
    ("sufficient runway", "enough runway", "adequate runway"),
    ("later durability", "later specificity", "durability preserved", "specificity preserved"),
    ("recovery tolerance supports it", "recovery tolerance", "recovery supports it"),
)


def phase_bundle_integrity(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Phase bundle must decode to an object.")
    required = ("phase_range", "week_blueprints", "guardrails", "structure", "preview", "constraint_audit", "load_governance_audit")
    missing = [field for field in required if field not in mapping]
    if missing:
        return (False, f"Phase bundle missing required keys: {', '.join(missing)}")
    week_blueprints = mapping.get("week_blueprints")
    if not isinstance(week_blueprints, list) or not week_blueprints:
        return (False, "Phase bundle must include at least one week blueprint.")
    return (True, mapping)


def phase_bundle_matches_context(result: Any) -> GuardrailResult:
    """Validate internal Phase bundle week blueprints against execution context."""

    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Phase bundle must decode to an object.")
    context = _phase_execution_context()
    if not context:
        return (True, mapping)
    blueprints = [_as_map(item) for item in _as_list(mapping.get("week_blueprints"))]
    if not blueprints:
        return (False, "Phase bundle must include week_blueprints for contract validation.")
    inherited_contract = _as_map(context.get("inherited_scenario_contract"))
    phase_payload = {
        "data": {
            "load_ranges": {
                "weekly_kj_bands": [
                    {
                        "week": item.get("week"),
                        "band": {"min": item.get("s5_band_min"), "max": item.get("s5_band_max")},
                    }
                    for item in blueprints
                ]
            },
            "week_skeleton_logic": {
                "week_roles": {
                    "week_roles": [
                        {"week": item.get("week"), "role": item.get("week_role")}
                        for item in blueprints
                    ]
                }
            },
        }
    }
    if inherited_contract:
        phase_payload["data"]["inherited_scenario_contract"] = inherited_contract
        if _as_map(_as_map(phase_payload.get("data")).get("inherited_scenario_contract")) != inherited_contract:
            return (False, "Synthetic Phase candidate missing deterministic inherited_scenario_contract.")
    issues = validate_phase_against_execution_context(
        phase_payload=phase_payload,
        phase_execution_context=context,
    )
    messages = blocking_messages(issues)
    if messages:
        return (False, "; ".join(messages[:5]))
    return (True, mapping)


def season_bundle_integrity(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Season bundle must decode to an object.")
    required = ("event_priority", "macrocycle", "phase_blueprints")
    missing = [field for field in required if field not in mapping]
    if missing:
        return (False, f"Season bundle missing required keys: {', '.join(missing)}")
    blueprints = mapping.get("phase_blueprints")
    if not isinstance(blueprints, list) or not blueprints:
        return (False, "Season bundle must include at least one phase blueprint.")
    for blueprint in blueprints:
        if not isinstance(blueprint, dict):
            continue
        if not str(blueprint.get("phase_id") or "").strip():
            return (False, "Season bundle phase blueprints must include phase_id.")
        if not str(blueprint.get("iso_week_range") or "").strip():
            return (False, "Season bundle phase blueprints must include iso_week_range.")
        if not str(blueprint.get("scenario_cadence") or "").strip():
            return (False, "Season bundle phase blueprints must include scenario_cadence.")
    return (True, mapping)


def season_bundle_audit_slot_integrity(result: Any) -> GuardrailResult:
    """Ensure Season bundle audit slots keep canonical audit-object shapes."""

    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Season bundle must decode to an object.")
    normalized = canonicalize_season_bundle_shape_aliases(mapping)
    constraint_keys = {"blocking_issues", "warnings", "recommended_adjustments", "applied_sources"}
    governance_keys = {
        "blocking_issues",
        "warnings",
        "recommended_adjustments",
        "cadence_authority_preserved",
        "durability_first_respected",
    }
    for item in _as_list(normalized.get("constraints")):
        if not isinstance(item, dict):
            return (False, "Season constraints[] entries must be canonical audit objects.")
        keys = {str(key).strip() for key in item.keys() if str(key).strip()}
        if not keys <= constraint_keys:
            return (False, "Season constraints[] entries must be canonical audit objects, not finding rows.")
    for item in _as_list(normalized.get("load_governance")):
        if not isinstance(item, dict):
            return (False, "Season load_governance[] entries must be canonical audit objects.")
        keys = {str(key).strip() for key in item.keys() if str(key).strip()}
        if not keys <= governance_keys:
            return (False, "Season load_governance[] entries must be canonical audit objects, not finding rows.")
    return (True, normalized)


def season_bundle_matches_contract(result: Any) -> GuardrailResult:
    """Validate internal Season bundle phase blueprints against deterministic context."""

    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Season bundle must decode to an object.")
    issues = validate_season_bundle_semantics(season_bundle_payload=mapping)
    messages = blocking_messages(issues)
    if messages:
        return (False, "; ".join(messages[:5]))
    phase_slot_context = _season_phase_slot_context()
    if not phase_slot_context:
        return (True, mapping)
    blueprints = [_as_map(item) for item in _as_list(mapping.get("phase_blueprints"))]
    season_phase_load_context = _season_phase_load_context()
    context_by_phase_id = {
        str(_as_map(item).get("phase_id") or ""): _as_map(item)
        for item in _as_list(_as_map(season_phase_load_context).get("phases"))
        if str(_as_map(item).get("phase_id") or "").strip()
    }
    candidate: dict[str, object] = {
        "season_allowed_domains": season_phase_load_context.get("season_allowed_intensity_domains") if season_phase_load_context else [],
        "season_load_envelope": mapping.get("season_load_envelope"),
        "season_semantic_notes": mapping.get("season_semantic_notes"),
        "data": {
            "body_metadata": {
                "phase_taxonomy_version": next(
                    (
                        str(_as_map(item).get("phase_taxonomy_version"))
                        for item in blueprints
                        if str(_as_map(item).get("phase_taxonomy_version") or "").strip()
                    ),
                    "",
                )
            },
            "phases": [
                {
                    "phase_id": item.get("phase_id"),
                    "iso_week_range": item.get("iso_week_range"),
                    "phase_type": item.get("phase_type") or item.get("cycle"),
                    "phase_intent": item.get("phase_intent"),
                    "build_subtype": item.get("build_subtype"),
                    "weekly_load_corridor": {
                        "weekly_kj": {
                            "min": item.get("load_corridor_min"),
                            "max": item.get("load_corridor_max"),
                            "notes": (
                                "Inherited role-week load guardrails (season-level, not week prescriptions): "
                                + "; ".join(format_role_week_load_bands(item.get("role_week_load_bands")))
                                + "."
                            )
                            if format_role_week_load_bands(item.get("role_week_load_bands"))
                            else ""
                        }
                    },
                    "role_week_load_bands": normalize_role_week_load_bands(item.get("role_week_load_bands")),
                    "allowed_forbidden_semantics": {
                        "allowed_intensity_domains": item.get("allowed_domains") or [],
                        "allowed_load_modalities": item.get("allowed_load_modalities") or [],
                        "forbidden_intensity_domains": item.get("forbidden_domains") or [],
                    },
                    "events_constraints": [
                        {
                            "window": str(_as_map(event).get("date") or _as_map(event).get("week") or "").strip(),
                            "type": str(_as_map(event).get("type") or "").strip().upper(),
                            "constraint": "deterministic contract event",
                        }
                        for event in _as_list(_as_map(_as_map(context_by_phase_id.get(str(item.get('phase_id') or ''))).get("event_taper_trace")).get("events"))
                        if str(_as_map(event).get("date") or _as_map(event).get("week") or "").strip()
                    ],
                }
                for item in blueprints
            ],
            "season_load_envelope": mapping.get("season_load_envelope"),
        }
    }
    selected_contract = _as_map(season_phase_load_context.get("selected_scenario_contract"))
    if selected_contract:
        candidate_data = _as_map(candidate.get("data"))
        candidate_data["selected_scenario_contract"] = selected_contract
        candidate["data"] = candidate_data
        if _as_map(candidate_data.get("selected_scenario_contract")) != selected_contract:
            return (False, "Synthetic Season candidate missing deterministic selected_scenario_contract.")
    issues = validate_season_plan_against_phase_slots(
        season_plan_payload=candidate,
        phase_slot_context=phase_slot_context,
    )
    messages = blocking_messages(issues)
    if messages:
        return (False, "; ".join(messages[:5]))
    if season_phase_load_context:
        issues = validate_season_plan_against_phase_load_context(
            season_plan_payload=candidate,
            season_phase_load_context=season_phase_load_context,
        )
        messages = blocking_messages(issues)
        if messages:
            return (False, "; ".join(messages[:5]))
    return (True, mapping)


def season_bundle_review_readiness(result: Any) -> GuardrailResult:
    """Ensure a normalized season bundle is review-ready before review runs."""

    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Season bundle must decode to an object.")
    issues = validate_season_bundle_review_readiness(season_bundle_payload=mapping)
    messages = blocking_messages(issues)
    if messages:
        return (False, "; ".join(messages[:5]))
    return (True, mapping)


def season_writer_bundle_match(result: Any) -> GuardrailResult:
    """Validate that the final Season Plan copied bundle-owned semantics exactly."""

    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Season output must decode to an object.")
    approved_bundle = _as_map(_GUARDRAIL_CONTEXT.get({}).get("approved_planning_bundle"))
    selected_scenario_contract = _as_map(_GUARDRAIL_CONTEXT.get({}).get("selected_scenario_contract"))
    if not approved_bundle:
        return (True, mapping)
    data = _as_map(mapping.get("data"))
    mapping["data"] = data
    body_metadata = _as_map(data.get("body_metadata"))
    data["body_metadata"] = body_metadata
    phase_taxonomy_version = str(body_metadata.get("phase_taxonomy_version") or "").strip()
    bundle_version = str(
        next(
            (
                _as_map(item).get("phase_taxonomy_version")
                for item in _as_list(approved_bundle.get("phase_blueprints"))
                if str(_as_map(item).get("phase_taxonomy_version") or "").strip()
            ),
            "",
        )
        or ""
    ).strip()
    if bundle_version:
        body_metadata["phase_taxonomy_version"] = bundle_version
        phase_taxonomy_version = bundle_version
    if bundle_version and phase_taxonomy_version != bundle_version:
        return (
            False,
            f"Season body_metadata.phase_taxonomy_version is {phase_taxonomy_version!r}, expected {bundle_version!r} from the approved bundle.",
        )
    approved_envelope = _as_map(approved_bundle.get("season_load_envelope"))
    if approved_envelope:
        data["season_load_envelope"] = approved_envelope
    if _as_map(data.get("season_load_envelope")) != approved_envelope:
        return (False, "Season output season_load_envelope must match the approved bundle exactly.")
    if selected_scenario_contract:
        data["selected_scenario_contract"] = selected_scenario_contract
    if selected_scenario_contract and _as_map(data.get("selected_scenario_contract")) != selected_scenario_contract:
        return (False, "Season output selected_scenario_contract must match the derived selected scenario contract exactly.")
    approved_by_phase = {
        str(_as_map(item).get("phase_id") or ""): _as_map(item)
        for item in _as_list(approved_bundle.get("phase_blueprints"))
    }
    for phase in _as_list(data.get("phases")):
        phase_map = _as_map(phase)
        phase_id = str(phase_map.get("phase_id") or "")
        approved = approved_by_phase.get(phase_id)
        if not approved:
            continue
        for field in ("phase_type", "phase_intent", "build_subtype"):
            phase_map[field] = approved.get(field)
        for field in ("phase_type", "phase_intent", "build_subtype"):
            if phase_map.get(field) != approved.get(field):
                return (
                    False,
                    f"Season phase {phase_id} field {field} must match the approved bundle value {approved.get(field)!r}.",
                )
        semantics = _as_map(phase_map.get("allowed_forbidden_semantics"))
        phase_map["allowed_forbidden_semantics"] = semantics
        semantics["allowed_intensity_domains"] = list(approved.get("allowed_domains") or [])
        approved_modalities = [str(item).strip().upper() for item in approved.get("allowed_load_modalities") or [] if str(item).strip()]
        if approved_modalities:
            semantics["allowed_load_modalities"] = approved_modalities
        semantics["forbidden_intensity_domains"] = list(approved.get("forbidden_domains") or [])
        if normalize_intensity_domain_list(semantics.get("allowed_intensity_domains")) != normalize_intensity_domain_list(approved.get("allowed_domains")):
            return (
                False,
                f"Season phase {phase_id} allowed_intensity_domains must match the approved bundle exactly.",
            )
        if approved_modalities and [str(item).strip().upper() for item in semantics.get("allowed_load_modalities") or [] if str(item).strip()] != approved_modalities:
            return (
                False,
                f"Season phase {phase_id} allowed_load_modalities must match the approved bundle exactly.",
            )
        if normalize_intensity_domain_list(semantics.get("forbidden_intensity_domains")) != normalize_intensity_domain_list(approved.get("forbidden_domains")):
            return (
                False,
                f"Season phase {phase_id} forbidden_intensity_domains must match the approved bundle exactly.",
            )
    return (True, mapping)


def season_phase_load_feasibility(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Season bundle must decode to an object.")
    blueprints = mapping.get("phase_blueprints")
    if not isinstance(blueprints, list) or not blueprints:
        return (True, mapping)
    corridor_max_values: list[float] = []
    role_signatures: set[tuple[str, ...]] = set()
    phase_types: set[str] = set()
    for blueprint in blueprints:
        if not isinstance(blueprint, dict):
            continue
        phase_id = str(blueprint.get("phase_id") or "unknown")
        max_value = _as_float(blueprint.get("load_corridor_max"))
        availability_cap = _as_float(blueprint.get("availability_cap_kj"))
        status = str(blueprint.get("load_feasibility_status") or "").lower()
        if max_value is not None:
            corridor_max_values.append(max_value)
        phase_type = str(blueprint.get("phase_type") or blueprint.get("cycle") or "")
        if phase_type:
            phase_types.add(phase_type)
        roles = tuple(str(item) for item in blueprint.get("cadence_week_roles") or [] if str(item).strip())
        if roles:
            role_signatures.add(roles)
        if max_value is not None and availability_cap is not None and max_value > availability_cap and "exception" not in status:
            return (
                False,
                f"Season phase {phase_id} load_corridor_max {max_value:g} exceeds availability_cap_kj {availability_cap:g}.",
            )
        if phase_type == "PEAK" and max_value is not None:
            build_max_candidates = [
                _as_float(item.get("load_corridor_max"))
                for item in blueprints
                if isinstance(item, dict) and (item.get("phase_type") or item.get("cycle")) == "BUILD"
            ]
            build_max: list[float] = [item for item in build_max_candidates if item is not None]
            if build_max and max_value >= max(build_max):
                return (False, f"Season Peak phase {phase_id} must show load reduction versus Build phases.")
    if (
        len(set(corridor_max_values)) == 1
        and len(corridor_max_values) > 2
        and role_signatures
        and len(phase_types) > 1
    ):
        return (False, "Season phase corridors are flat across phases despite cadence/phase-role load semantics.")
    return (True, mapping)


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


def season_scenario_selection_shape(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Scenario selection output must decode to an object.")
    meta = mapping.get("meta")
    data = mapping.get("data")
    if not isinstance(meta, dict) or not isinstance(data, dict):
        return (False, "Scenario selection must include meta and data objects.")
    if meta.get("artifact_type") != "SEASON_SCENARIO_SELECTION":
        return (False, "Scenario selection meta.artifact_type must be SEASON_SCENARIO_SELECTION.")
    if data.get("selected_scenario_id") not in {"A", "B", "C"}:
        return (False, "Scenario selection selected_scenario_id must be A, B, or C.")
    if not isinstance(data.get("season_scenarios_ref"), str) or not data.get("season_scenarios_ref"):
        return (False, "Scenario selection must include season_scenarios_ref.")
    forbidden_keys = {"phases", "agenda", "workouts", "weekly_kj_bands"}
    if any(key in data for key in forbidden_keys):
        return (False, "Scenario selection must not contain season, phase, week, or workout planning payloads.")
    return (True, mapping)


def season_scenarios_profile_quality(result: Any) -> GuardrailResult:
    """Check that season scenarios differ by exposure/risk profile, not only syntax."""

    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Season scenarios output must decode to an object.")
    meta = _as_map(mapping.get("meta"))
    data = _as_map(mapping.get("data"))
    if meta.get("artifact_type") != "SEASON_SCENARIOS":
        return (False, "Season scenarios meta.artifact_type must be SEASON_SCENARIOS.")
    scenarios = [_as_map(item) for item in _as_list(data.get("scenarios"))]
    if len(scenarios) != 3:
        return (False, "Season scenarios must include exactly three scenarios.")

    seen_ids: set[str] = set()
    signatures: set[tuple[str, str, str, tuple[str, ...]]] = set()
    by_id: dict[str, JsonMap] = {}
    cadence_by_id: dict[str, str] = {}
    rationale_by_id: dict[str, str] = {}
    global_notes_text = " ".join(_string_list(data.get("notes"))).lower()
    if not _contains_any(global_notes_text, _DOMAIN_ELIGIBILITY_MARKERS):
        return (False, "Season scenarios must state that allowed_domains are eligibility only, not phase-wide authorization.")
    if _contains_any(global_notes_text, _DOMAIN_AUTHORIZATION_MARKERS) and not _contains_any(global_notes_text, _DOMAIN_ELIGIBILITY_MARKERS):
        return (False, "Season scenarios must not describe allowed_domains as blanket legality for all phases.")
    if _contains_any(global_notes_text, _OBJECTIVE_RESOLUTION_MARKERS):
        return (False, "Scenario layer must not claim that objective mismatch is already resolved.")

    event_context = _future_event_runtime_context()
    future_events = [event for event in _as_list(event_context.get("future_events")) if isinstance(event, dict)]
    all_events = [event for event in _as_list(event_context.get("all_events")) if isinstance(event, dict)]
    future_event_dates = {str(event.get("date") or "").strip().lower() for event in future_events if str(event.get("date") or "").strip()}
    historical_events = [
        event
        for event in all_events
        if str(event.get("date") or "").strip() and str(event.get("date") or "").strip().lower() not in future_event_dates
    ]
    has_event_context = bool(future_events or all_events)
    future_type_counts = {
        event_type: sum(1 for event in future_events if str(event.get("type") or "").strip().upper() == event_type)
        for event_type in ("A", "B", "C")
    }

    for scenario in scenarios:
        scenario_id = str(scenario.get("scenario_id") or "").strip().upper()
        if scenario_id not in {"A", "B", "C"}:
            return (False, "Season scenarios must contain only scenario ids A, B, and C.")
        seen_ids.add(scenario_id)
        by_id[scenario_id] = scenario
        best_suited_if = str(scenario.get("best_suited_if") or "").strip().lower()
        if not best_suited_if or not _contains_any(best_suited_if, _SCENARIO_SELECTION_POSITIVE_MARKERS):
            return (False, f"Scenario {scenario_id} must include a meaningful best_suited_if selection gate.")
        guidance = _as_map(scenario.get("scenario_guidance"))
        risk_flags_text = " ".join(_string_list(guidance.get("risk_flags"))).lower()
        if not risk_flags_text or not _contains_any(risk_flags_text, _SCENARIO_SELECTION_NEGATIVE_MARKERS):
            return (False, f"Scenario {scenario_id} must include concrete caution markers in risk_flags.")
        cadence = str(guidance.get("deload_cadence") or "").strip()
        if cadence not in _SUPPORTED_SCENARIO_CADENCES:
            return (False, f"Scenario {scenario_id} must include supported deload_cadence (`2:1`, `3:1`, or `2:1:1`).")
        cadence_by_id[scenario_id] = cadence
        rationale_text = _scenario_rationale_text(guidance)
        rationale_by_id[scenario_id] = rationale_text
        if not any(token in rationale_text for token in _CADENCE_TOKENS) or cadence not in rationale_text:
            return (False, f"Scenario {scenario_id} cadence is present but not explained in decision/risk fields.")
        event_text = " ".join(
            [
                " ".join(_string_list(guidance.get("event_alignment_notes"))),
                " ".join(_string_list(guidance.get("decision_notes"))),
                " ".join(_string_list(guidance.get("risk_flags"))),
                global_notes_text,
            ]
        ).lower()
        if has_event_context:
            for event in historical_events:
                event_name = str(event.get("event_name") or "").strip().lower()
                event_date = str(event.get("date") or "").strip().lower()
                if ((event_name and event_name in event_text) or (event_date and event_date in event_text)) and _contains_any(
                    event_text, ("rehearsal", "anchor", "peak", "cluster")
                ):
                    return (False, "Season scenarios must not describe pre-horizon events as active rehearsal/anchor/peak logic.")
            if "b-event cluster" in event_text and future_type_counts["B"] < 2:
                return (False, "Cluster wording requires multiple relevant in-horizon events.")
            if "peak cluster" in event_text and future_type_counts["A"] < 2:
                return (False, "Cluster wording requires multiple relevant in-horizon events.")
            if (
                "event cluster" in event_text
                or (" cluster" in event_text and not any(token in event_text for token in ("historical context", "cluster-member")))
            ) and sum(future_type_counts.values()) < 2:
                return (False, "Cluster wording requires multiple relevant in-horizon events.")
        intensity = _as_map(guidance.get("intensity_guidance"))
        allowed_domains = [str(item).strip().upper() for item in _as_list(intensity.get("allowed_domains")) if str(item).strip()]
        if "ENDURANCE" not in allowed_domains:
            return (False, f"Scenario {scenario_id} must include ENDURANCE in allowed_domains.")
        load_philosophy = str(scenario.get("load_philosophy") or "").strip().lower()
        risk_profile = str(scenario.get("risk_profile") or "").strip().lower()
        key_diff = str(scenario.get("key_differences") or "").strip().lower()
        signatures.add((load_philosophy, risk_profile, key_diff, tuple(allowed_domains)))
    if seen_ids != {"A", "B", "C"}:
        return (False, "Season scenarios must include scenario ids A, B, and C exactly once.")
    if len(signatures) < 3:
        return (False, "Season scenarios must differ materially in load/risk/specificity profile; cosmetic low/mid/high variants are not enough.")
    unique_cadences = set(cadence_by_id.values())
    if len(unique_cadences) == 1:
        shared_rationale = " ".join(rationale_by_id.values())
        has_shared_cadence_rationale = any(marker in shared_rationale for marker in _SHARED_CADENCE_MARKERS) and any(
            marker in shared_rationale for marker in _DIFFERENTIATION_MARKERS
        )
        recommendation_context = _as_map(current_guardrail_runtime_context().get("season_scenario_recommendation_context"))
        recommended_cadence = str(recommendation_context.get("recommended_cadence") or "").strip()
        if not has_shared_cadence_rationale and recommended_cadence and next(iter(unique_cadences)) == recommended_cadence:
            return (False, "Recommendation-default cadence was mirrored across all scenarios without scenario differentiation.")
        if not has_shared_cadence_rationale:
            return (False, "Season scenarios collapse cadence across A/B/C without explicit justification.")

    scenario_c = by_id["C"]
    guidance_c = _as_map(scenario_c.get("scenario_guidance"))
    intensity_c = _as_map(guidance_c.get("intensity_guidance"))
    allowed_c = {str(item).strip().upper() for item in _as_list(intensity_c.get("allowed_domains")) if str(item).strip()}
    season_archetype = str(guidance_c.get("season_archetype") or "").strip()
    archetype_rationale = " ".join(_string_list(guidance_c.get("season_archetype_rationale"))).lower()
    if season_archetype == "ceiling_first_durability":
        decision_text = " ".join(_string_list(guidance_c.get("decision_notes"))).lower()
        joined_text = f"{archetype_rationale} {decision_text}"
        if not all(any(marker in joined_text for marker in group) for group in _ARCHETYPE_REQUIRED_MARKER_GROUPS):
            return (False, "Scenario C may use ceiling_first_durability only with explicit rationale and preserved runway.")
    if allowed_c == {"ENDURANCE"}:
        return (False, "Scenario C must express ambitious specificity beyond ENDURANCE-only semantics.")
    c_story = " ".join(
        [
            str(scenario_c.get("load_philosophy") or ""),
            str(scenario_c.get("risk_profile") or ""),
            str(scenario_c.get("key_differences") or ""),
            " ".join(str(item) for item in _as_list(guidance_c.get("decision_notes"))),
            " ".join(str(item) for item in _as_list(guidance_c.get("constraint_summary"))),
            " ".join(str(item) for item in _as_list(guidance_c.get("kpi_guardrail_notes"))),
        ]
    ).lower()
    if not any(marker in c_story for marker in ("back-to-back", "b2b", "hard-late", "event simulation", "specificity", "fatigue")):
        return (False, "Scenario C must describe higher specificity or fatigue exposure, not only a larger kJ envelope.")
    if "VO2MAX" in allowed_c:
        if not all(any(marker in c_story for marker in group) for group in _VO2_RATIONALE_MARKER_GROUPS):
            return (False, "Scenario C may allow VO2MAX only with explicit sparse ceiling-support rationale.")
    return (True, mapping)


def season_scenarios_selection_contract_complete(result: Any) -> GuardrailResult:
    """Require each scenario to emit complete operational posture for selection binding."""

    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Season scenarios output must decode to an object.")
    meta = _as_map(mapping.get("meta"))
    data = _as_map(mapping.get("data"))
    if meta.get("artifact_type") != "SEASON_SCENARIOS":
        return (False, "Season scenarios meta.artifact_type must be SEASON_SCENARIOS.")
    scenarios = [_as_map(item) for item in _as_list(data.get("scenarios"))]
    if len(scenarios) != 3:
        return (False, "Season scenarios must include exactly three scenarios.")

    required_string_fields = ("recovery_margin", "fatigue_exposure", "specificity_density")
    required_list_fields = (
        "constraint_summary",
        "event_alignment_notes",
        "risk_flags",
        "kpi_guardrail_notes",
        "decision_notes",
    )
    for scenario in scenarios:
        scenario_id = str(scenario.get("scenario_id") or "").strip().upper() or "?"
        guidance = _as_map(scenario.get("scenario_guidance"))
        for field in required_string_fields:
            if not str(guidance.get(field) or "").strip():
                return (False, f"Scenario {scenario_id} must include non-empty scenario_guidance.{field}.")
        for field in required_list_fields:
            value = guidance.get(field)
            if not isinstance(value, list):
                return (False, f"Scenario {scenario_id} must include scenario_guidance.{field} as a string array.")
            items = _string_list(value)
            if field == "constraint_summary" and not items:
                return (False, f"Scenario {scenario_id} must include non-empty scenario_guidance.constraint_summary.")
    return (True, mapping)


def season_phase_coverage_and_cadence(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Season output must decode to an object.")
    phase_slot_context = _season_phase_slot_context()
    if phase_slot_context:
        issues = validate_season_plan_against_phase_slots(
            season_plan_payload=mapping,
            phase_slot_context=phase_slot_context,
        )
        messages = blocking_messages(issues)
        if messages:
            return (False, "; ".join(messages[:5]))
    candidate_document = mapping.get("candidate_document")
    candidate_map = candidate_document if isinstance(candidate_document, dict) else {}
    data = mapping.get("data") if "data" in mapping else candidate_map.get("data")
    if not isinstance(data, dict):
        return (True, mapping)
    phases = data.get("phases")
    if not isinstance(phases, list) or not phases:
        return (False, "Season plan must include at least one phase.")
    seen_ranges: set[str] = set()
    parsed_ranges = []
    for idx, phase in enumerate(phases):
        if not isinstance(phase, dict):
            return (False, f"Season phase {idx} must be an object.")
        range_key = phase.get("iso_week_range")
        if not isinstance(range_key, str) or not range_key:
            return (False, f"Season phase {idx} missing iso_week_range.")
        if range_key in seen_ranges:
            return (False, f"Duplicate season phase iso_week_range: {range_key}.")
        seen_ranges.add(range_key)
        parsed = parse_iso_week_range(range_key)
        if parsed is None:
            return (False, f"Season phase {idx} has invalid iso_week_range: {range_key}.")
        parsed_ranges.append((range_key, parsed))
        if not isinstance(phase.get("deload"), bool):
            return (False, f"Season phase {range_key} must include boolean deload.")
        rationale = phase.get("deload_rationale")
        if phase.get("deload") is True and (not isinstance(rationale, str) or not rationale.strip()):
            return (False, f"Season phase {range_key} deload requires non-empty deload_rationale.")
    for previous, current in zip(parsed_ranges, parsed_ranges[1:], strict=False):
        previous_range = previous[1]
        current_range = current[1]
        expected_next = _next_iso_week(previous_range.end)
        if current_range.start != expected_next:
            return (
                False,
                "Season phases must be continuous and non-overlapping; "
                f"{current[0]} should start at {expected_next.year:04d}-{expected_next.week:02d}.",
            )
    return (True, mapping)


def season_phase_load_context_match(result: Any) -> GuardrailResult:
    """Validate Season Plan corridors against deterministic season phase load context."""

    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Season output must decode to an object.")
    mapping = _repair_season_plan_for_contract_validation(mapping)
    context = _season_phase_load_context()
    if not context:
        return (True, mapping)
    issues = validate_season_plan_against_phase_load_context(
        season_plan_payload=mapping,
        season_phase_load_context=context,
        include_narrative_semantics=False,
    )
    messages = blocking_messages(issues)
    if messages:
        return (False, "; ".join(messages[:5]))
    return (True, mapping)


def season_cycle_ordering(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Season output must decode to an object.")
    candidate_document = mapping.get("candidate_document")
    candidate_map = candidate_document if isinstance(candidate_document, dict) else {}
    data = mapping.get("data") if "data" in mapping else candidate_map.get("data")
    if not isinstance(data, dict):
        return (True, mapping)
    phases = data.get("phases")
    if not isinstance(phases, list):
        return (True, mapping)
    allowed = {"TRANSITION", "PREPARATION", "BASE", "BUILD", "PEAK", "TAPER", "RACE"}
    for phase in phases:
        if not isinstance(phase, dict):
            continue
        phase_type = phase.get("phase_type") or phase.get("cycle")
        if phase_type not in allowed:
            return (False, f"Season phase phase_type must be one of {sorted(allowed)}; got {phase_type!r}.")
    return (True, mapping)


def phase_s5_band_match(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Phase guardrails output must decode to an object.")
    context = _phase_execution_context()
    if context:
        issues = validate_phase_s5_bands_against_context(
            phase_payload=mapping,
            phase_execution_context=context,
        )
        messages = blocking_messages(issues)
        if messages:
            return (False, "; ".join(messages[:5]))
        return (True, mapping)
    data = mapping.get("data")
    if not isinstance(data, dict):
        return (True, mapping)
    load_guardrails = data.get("load_guardrails")
    if not isinstance(load_guardrails, dict):
        return (True, mapping)
    bands = load_guardrails.get("weekly_kj_bands")
    if not isinstance(bands, list) or not bands:
        return (False, "Phase guardrails must include weekly_kj_bands.")
    for entry in bands:
        if not isinstance(entry, dict):
            return (False, "Each weekly_kj_bands entry must be an object.")
        band = entry.get("band")
        if not isinstance(band, dict):
            return (False, "Each weekly_kj_bands entry must include band object.")
        min_value = band.get("min")
        max_value = band.get("max")
        if not isinstance(min_value, (int, float)) or not isinstance(max_value, (int, float)):
            return (False, "Each weekly_kj_bands band must include numeric min and max.")
        if float(min_value) > float(max_value):
            return (False, "weekly_kj_bands min must not exceed max.")
        expected = _extract_expected_s5_band(str(band.get("notes") or ""))
        if expected and (round(float(min_value)) != expected[0] or round(float(max_value)) != expected[1]):
            return (
                False,
                f"weekly_kj_bands[{entry.get('week')}] does not match deterministic S5 band {expected[0]}-{expected[1]}.",
            )
    return (True, mapping)


def phase_bundle_review_readiness(result: Any) -> GuardrailResult:
    """Ensure a normalized phase bundle is review-ready before review runs."""

    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Phase bundle must decode to an object.")
    issues = validate_phase_bundle_review_readiness(phase_bundle_payload=mapping)
    messages = blocking_messages(issues)
    if messages:
        return (False, "; ".join(messages[:5]))
    return (True, mapping)


def phase_execution_context_match(result: Any) -> GuardrailResult:
    """Validate Phase artifact structure and bands against phase execution context."""

    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Phase output must decode to an object.")
    context = _phase_execution_context()
    if not context:
        return (True, mapping)
    issues = validate_phase_against_execution_context(
        phase_payload=mapping,
        phase_execution_context=context,
    )
    messages = blocking_messages(issues)
    if messages:
        return (False, "; ".join(messages[:5]))
    return (True, mapping)


def phase_weeks_match_range(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Phase structure output must decode to an object.")
    meta = mapping.get("meta")
    data = mapping.get("data")
    if not isinstance(meta, dict) or not isinstance(data, dict):
        return (True, mapping)
    phase_range = parse_iso_week_range(meta.get("iso_week_range"))
    if phase_range is None:
        return (True, mapping)
    expected_weeks = [_iso_week_key(week) for week in _weeks_in_range(phase_range)]
    observed_weeks: set[str] = set()
    load_ranges = data.get("load_ranges")
    if isinstance(load_ranges, dict):
        for entry in load_ranges.get("weekly_kj_bands") or []:
            if isinstance(entry, dict):
                week_key = _coerce_week_key(entry.get("week"))
                if week_key:
                    observed_weeks.add(week_key)
    skeleton = data.get("week_skeleton_logic")
    if isinstance(skeleton, dict):
        roles = skeleton.get("week_roles")
        roles_map = roles if isinstance(roles, dict) else {}
        for entry in roles_map.get("week_roles") or []:
            if isinstance(entry, dict):
                week_key = _coerce_week_key(entry.get("week"))
                if week_key:
                    observed_weeks.add(week_key)
    if not observed_weeks:
        return (True, mapping)
    expected_set = set(expected_weeks)
    missing = [week for week in expected_weeks if week not in observed_weeks]
    extra = sorted(observed_weeks - expected_set)
    if missing or extra:
        return (
            False,
            "Phase structure weeks must match meta.iso_week_range exactly; "
            f"missing={missing or []}, extra={extra or []}.",
        )
    return (True, mapping)


def phase_week_role_load_coherence(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Phase output must decode to an object.")
    if "week_blueprints" in mapping:
        blueprints = mapping.get("week_blueprints")
        if not isinstance(blueprints, list) or not blueprints:
            return (False, "Phase week_blueprints must be non-empty.")
        ok, message = _check_role_band_sequence(
            [
                {
                    "week": item.get("week"),
                    "role": item.get("week_role"),
                    "min": item.get("s5_band_min"),
                    "max": item.get("s5_band_max"),
                    "notes": " ".join(str(warn) for warn in item.get("warnings") or []),
                }
                for item in blueprints
                if isinstance(item, dict)
            ]
        )
        return (ok, mapping if ok else message)
    data = mapping.get("data")
    if not isinstance(data, dict):
        return (True, mapping)
    bands_by_week: dict[str, JsonMap] = {}
    load_ranges = data.get("load_ranges")
    if isinstance(load_ranges, dict):
        for entry in load_ranges.get("weekly_kj_bands") or []:
            if not isinstance(entry, dict):
                continue
            week = _coerce_week_key(entry.get("week"))
            band = entry.get("band")
            if week and isinstance(band, dict):
                bands_by_week[week] = band
    skeleton = data.get("week_skeleton_logic")
    roles_map = skeleton.get("week_roles") if isinstance(skeleton, dict) else {}
    role_entries = roles_map.get("week_roles") if isinstance(roles_map, dict) else []
    sequence = []
    for entry in role_entries or []:
        if not isinstance(entry, dict):
            continue
        week = _coerce_week_key(entry.get("week"))
        band = bands_by_week.get(week or "")
        if not week or not band:
            continue
        sequence.append(
            {
                "week": week,
                "role": entry.get("role"),
                "min": band.get("min"),
                "max": band.get("max"),
                "notes": band.get("notes"),
            }
        )
    if not sequence:
        return (True, mapping)
    ok, message = _check_role_band_sequence(sequence)
    return (ok, mapping if ok else message)


def _extract_expected_s5_band(notes: str) -> tuple[int, int] | None:
    match = re.search(r"S5(?: deterministic)? band(?: is|=|:)?\s*(\d+)\s*(?:-|/|to)\s*(\d+)", notes, re.I)
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)))


def _check_role_band_sequence(sequence: list[JsonMap]) -> GuardrailResult:
    previous_load_max: float | None = None
    previous_load_role = ""
    for entry in sequence:
        role = str(entry.get("role") or "").upper()
        max_value = _as_float(entry.get("max"))
        notes = str(entry.get("notes") or "").lower()
        if max_value is None:
            continue
        fallback_allows_flat = "fallback_level 4" in notes or "fallback_level 5" in notes or "s5 fallback" in notes
        if role in {"DELOAD", "MINI_RESET", "SHORTENED_MINI_RESET"} and previous_load_max is not None:
            required_factor = 0.92 if role in {"MINI_RESET", "SHORTENED_MINI_RESET"} else 0.82
            if max_value >= previous_load_max * required_factor and not fallback_allows_flat:
                return (
                    False,
                    f"{entry.get('week')} {role} band must reduce materially versus prior load role {previous_load_role}.",
                )
        if role in {"RELOAD", "SHORTENED_RELOAD"} and previous_load_max is not None:
            if max_value > previous_load_max * 1.13 and not fallback_allows_flat:
                return (False, f"{entry.get('week')} {role} band reload exceeds progressive-overload bounds.")
        if role.startswith("LOAD") or role in {"RELOAD", "SHORTENED_CONSOLIDATION", "SHORTENED_RELOAD"}:
            previous_load_max = max_value
            previous_load_role = role
    return (True, sequence)


def _iso_week_key(week: IsoWeek) -> str:
    return f"{week.year:04d}-{week.week:02d}"


def _next_iso_week(week: IsoWeek) -> IsoWeek:
    monday = date.fromisocalendar(week.year, week.week, 1)
    next_monday = monday + timedelta(days=7)
    iso_year, iso_week, _ = next_monday.isocalendar()
    return IsoWeek(iso_year, iso_week)


def _weeks_in_range(range_spec) -> list[IsoWeek]:
    cursor = date.fromisocalendar(range_spec.start.year, range_spec.start.week, 1)
    end = date.fromisocalendar(range_spec.end.year, range_spec.end.week, 1)
    weeks: list[IsoWeek] = []
    while cursor <= end:
        iso_year, iso_week, _ = cursor.isocalendar()
        weeks.append(IsoWeek(iso_year, iso_week))
        cursor += timedelta(days=7)
    return weeks


def _coerce_week_key(value: Any) -> str | None:
    week = parse_iso_week(value)
    if week is None:
        return None
    return _iso_week_key(week)


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


def _repair_season_plan_for_contract_validation(mapping: JsonMap) -> JsonMap:
    """Apply minimal code-owned season repairs before final contract validation."""

    repaired = dict(mapping)
    data = _as_map(repaired.get("data"))
    repaired["data"] = data
    phases = [_as_map(item) for item in _as_list(data.get("phases"))]
    approved_bundle = _as_map(_GUARDRAIL_CONTEXT.get({}).get("approved_planning_bundle"))
    approved_by_phase = {
        str(_as_map(item).get("phase_id") or ""): _as_map(item)
        for item in _as_list(approved_bundle.get("phase_blueprints"))
        if str(_as_map(item).get("phase_id") or "").strip()
    }
    season_phase_load_context = _season_phase_load_context()
    context_by_phase = {
        str(_as_map(item).get("phase_id") or ""): _as_map(item)
        for item in _as_list(_as_map(season_phase_load_context).get("phases"))
        if str(_as_map(item).get("phase_id") or "").strip()
    }
    for phase in phases:
        phase_id = str(phase.get("phase_id") or "").strip()
        approved = approved_by_phase.get(phase_id, {})
        context_phase = context_by_phase.get(phase_id, {})
        semantics = _as_map(phase.get("allowed_forbidden_semantics"))
        phase["allowed_forbidden_semantics"] = semantics
        approved_modalities = [
            str(item).strip().upper()
            for item in approved.get("allowed_load_modalities") or []
            if str(item).strip()
        ]
        if approved_modalities:
            semantics["allowed_load_modalities"] = approved_modalities
        structured_role_week_load_bands = normalize_role_week_load_bands(approved.get("role_week_load_bands"))
        if not structured_role_week_load_bands:
            structured_role_week_load_bands = normalize_role_week_load_bands(
                context_phase.get("role_week_load_bands")
            )
        role_week_load_bands = format_role_week_load_bands(structured_role_week_load_bands)
        if structured_role_week_load_bands:
            phase["role_week_load_bands"] = structured_role_week_load_bands
        weekly_kj = _as_map(_as_map(phase.get("weekly_load_corridor")).get("weekly_kj"))
        if role_week_load_bands and weekly_kj is not None:
            note = (
                "Inherited role-week load guardrails (season-level, not week prescriptions): "
                + "; ".join(role_week_load_bands)
                + "."
            )
            existing = str(weekly_kj.get("notes") or "").strip()
            if note not in existing:
                weekly_kj["notes"] = f"{existing} {note}".strip() if existing else note
        if context_phase:
            events = [
                {
                    "window": str(_as_map(event).get("date") or _as_map(event).get("week") or "").strip(),
                    "type": str(_as_map(event).get("type") or "").strip().upper(),
                    "constraint": "deterministic contract event",
                }
                for event in _as_list(_as_map(context_phase.get("event_taper_trace")).get("events"))
                if str(_as_map(event).get("date") or _as_map(event).get("week") or "").strip()
            ]
            phase["events_constraints"] = events
    data["phases"] = phases
    return repaired


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


REGISTRY: dict[str, GuardrailFn] = {
    "typed_output_present": typed_output_present,
    "coaching_recommendation_text_present": coaching_recommendation_text_present,
    "adjustment_intent_has_preview_message": adjustment_intent_has_preview_message,
    "coach_preview_summary_complete": coach_preview_summary_complete,
    "pending_resolution_summary_present": pending_resolution_summary_present,
    "audit_lists_are_lists": audit_lists_are_lists,
    "phase_bundle_integrity": phase_bundle_integrity,
    "phase_bundle_matches_context": phase_bundle_matches_context,
    "phase_week_role_load_coherence": phase_week_role_load_coherence,
    "phase_bundle_review_readiness": phase_bundle_review_readiness,
    "season_bundle_integrity": season_bundle_integrity,
    "season_bundle_audit_slot_integrity": season_bundle_audit_slot_integrity,
    "season_bundle_matches_contract": season_bundle_matches_contract,
    "season_phase_load_feasibility": season_phase_load_feasibility,
    "season_bundle_review_readiness": season_bundle_review_readiness,
    "week_bundle_integrity": week_bundle_integrity,
    "week_bundle_matches_context": week_bundle_matches_context,
    "week_bundle_domain_legality_check": week_bundle_domain_legality_check,
    "week_bundle_review_readiness": week_bundle_review_readiness,
    "review_decision_integrity": review_decision_integrity,
    "artifact_envelope_basic": artifact_envelope_basic,
    "artifact_meta_data_present": artifact_meta_data_present,
    "artifact_schema_valid": artifact_schema_valid,
    "season_scenarios_profile_quality": season_scenarios_profile_quality,
    "season_scenarios_selection_contract_complete": season_scenarios_selection_contract_complete,
    "season_scenario_selection_shape": season_scenario_selection_shape,
    "season_phase_coverage_and_cadence": season_phase_coverage_and_cadence,
    "season_phase_load_context_match": season_phase_load_context_match,
    "season_writer_bundle_match": season_writer_bundle_match,
    "season_cycle_ordering": season_cycle_ordering,
    "phase_s5_band_match": phase_s5_band_match,
    "phase_execution_context_match": phase_execution_context_match,
    "phase_weeks_match_range": phase_weeks_match_range,
    "week_corridor_and_capacity_check": week_corridor_and_capacity_check,
    "week_active_corridor_match": week_active_corridor_match,
    "week_recovery_day_load_check": week_recovery_day_load_check,
    "week_agenda_shape_and_calendar_check": week_agenda_shape_and_calendar_check,
    "week_daily_availability_check": week_daily_availability_check,
    "week_phase_role_alignment_check": week_phase_role_alignment_check,
    "week_contract_context_match": week_contract_context_match,
    "week_workout_structure_policy_check": week_workout_structure_policy_check,
    "week_exportability_check": week_exportability_check,
    "des_diagnostic_only": des_diagnostic_only,
}


def resolve_guardrail(name: str) -> GuardrailFn:
    """Return a registered guardrail callable by symbolic name."""

    try:
        return REGISTRY[name]
    except KeyError as exc:  # pragma: no cover - config validation catches this in tests
        raise ValueError(f"Unknown CrewAI guardrail: {name}") from exc


def resolve_task_policy(task_blueprint: Any, task_policies: JsonMap) -> TaskExecutionPolicy:
    """Resolve the merged task execution policy from config defaults and overrides."""

    defaults = task_policies.get("defaults") or {}
    kind_defaults = defaults.get(task_blueprint.config.get("kind") or "") or {}
    task_overrides = (task_policies.get("tasks") or {}).get(task_blueprint.name) or {}

    output_mode = str(task_overrides.get("output_mode") or kind_defaults.get("output_mode") or "pydantic")
    guardrails_raw = task_overrides.get("guardrails")
    if guardrails_raw is None:
        guardrails_raw = kind_defaults.get("guardrails") or []
    guardrails = tuple(str(item) for item in guardrails_raw)
    guardrail_max_retries = int(
        task_overrides.get("guardrail_max_retries")
        or kind_defaults.get("guardrail_max_retries")
        or 3
    )
    return TaskExecutionPolicy(
        output_mode=output_mode,
        guardrails=guardrails,
        guardrail_max_retries=guardrail_max_retries,
    )


def build_task_guardrail_kwargs(task_blueprint: Any, task_policies: JsonMap) -> JsonMap:
    """Return CrewAI Task kwargs for guardrails and output-mode policy."""

    policy = resolve_task_policy(task_blueprint, task_policies)
    kwargs: JsonMap = {"guardrail_max_retries": policy.guardrail_max_retries}
    if policy.guardrails:
        guardrail_fns = [
            _with_guardrail_telemetry(task_blueprint.name, name, resolve_guardrail(name))
            for name in policy.guardrails
        ]
        if len(guardrail_fns) == 1:
            kwargs["guardrail"] = guardrail_fns[0]
        else:
            kwargs["guardrails"] = guardrail_fns
    kwargs["_resolved_output_mode"] = policy.output_mode
    return kwargs


