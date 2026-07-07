"""Season-artifact CrewAI guardrails enforcing ADR-035 authority boundaries."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from rps.crewai_runtime.guardrails_context import (
    _GUARDRAIL_CONTEXT,
    GuardrailResult,
    JsonMap,
    current_guardrail_runtime_context,
)
from rps.crewai_runtime.guardrails_utilities import (
    _as_float,
    _as_list,
    _as_map,
    _coerce_mapping,
    _contains_any,
    _future_event_runtime_context,
    _scenario_rationale_text,
    _season_phase_load_context,
    _season_phase_slot_context,
    _string_list,
    canonicalize_season_bundle_shape_aliases,
)
from rps.planning.contracts import (
    blocking_messages,
    validate_season_bundle_review_readiness,
    validate_season_bundle_semantics,
    validate_season_plan_against_phase_load_context,
    validate_season_plan_against_phase_slots,
)
from rps.planning.phase_authority import format_role_week_load_bands, normalize_role_week_load_bands
from rps.workspace.intensity_domains import normalize_intensity_domain_list
from rps.workspace.iso_helpers import IsoWeek, parse_iso_week_range

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


def _next_iso_week(week: IsoWeek) -> IsoWeek:
    monday = date.fromisocalendar(week.year, week.week, 1)
    next_monday = monday + timedelta(days=7)
    iso_year, iso_week, _ = next_monday.isocalendar()
    return IsoWeek(iso_year, iso_week)


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
