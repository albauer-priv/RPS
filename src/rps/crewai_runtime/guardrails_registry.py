"""Guardrail registry and task-policy resolution for CrewAI task construction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rps.crewai_runtime.guardrails_context import (
    GuardrailFn,
    JsonMap,
)
from rps.crewai_runtime.guardrails_generic import (
    adjustment_intent_has_preview_message,
    audit_lists_are_lists,
    coach_preview_summary_complete,
    coaching_recommendation_text_present,
    pending_resolution_summary_present,
    typed_output_present,
)
from rps.crewai_runtime.guardrails_phase import (
    phase_bundle_integrity,
    phase_bundle_matches_context,
    phase_bundle_review_readiness,
    phase_execution_context_match,
    phase_s5_band_match,
    phase_week_role_load_coherence,
    phase_weeks_match_range,
)
from rps.crewai_runtime.guardrails_schema import (
    artifact_envelope_basic,
    artifact_meta_data_present,
    artifact_schema_valid,
)
from rps.crewai_runtime.guardrails_season import (
    season_bundle_audit_slot_integrity,
    season_bundle_integrity,
    season_bundle_matches_contract,
    season_bundle_review_readiness,
    season_cycle_ordering,
    season_phase_coverage_and_cadence,
    season_phase_load_context_match,
    season_phase_load_feasibility,
    season_scenario_selection_shape,
    season_scenarios_profile_quality,
    season_scenarios_selection_contract_complete,
    season_writer_bundle_match,
)
from rps.crewai_runtime.guardrails_utilities import (
    _with_guardrail_telemetry,
)
from rps.crewai_runtime.guardrails_week import (
    des_diagnostic_only,
    review_decision_integrity,
    week_active_corridor_match,
    week_agenda_shape_and_calendar_check,
    week_bundle_domain_legality_check,
    week_bundle_integrity,
    week_bundle_matches_context,
    week_bundle_review_readiness,
    week_contract_context_match,
    week_corridor_and_capacity_check,
    week_daily_availability_check,
    week_exportability_check,
    week_phase_role_alignment_check,
    week_recovery_day_load_check,
    week_workout_structure_policy_check,
)


@dataclass(frozen=True)
class TaskExecutionPolicy:
    """Resolved task execution policy merged from config defaults and overrides."""

    output_mode: str
    guardrails: tuple[str, ...]
    guardrail_max_retries: int


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
