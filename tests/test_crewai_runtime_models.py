from __future__ import annotations

import pytest
from pydantic import ValidationError

from rps.crewai_runtime.models import (
    PhaseGuardrailsPayloadModel,
    PhaseStructurePayloadModel,
    SeasonEventAnchorModel,
    SeasonMacrocycleDraftModel,
    SeasonPlanBundleModel,
    SelectedScenarioContractModel,
)


def _full_selected_scenario_contract() -> dict[str, object]:
    return {
        "selected_scenario_id": "B",
        "scenario_name": "Balanced build, controlled pressure",
        "selection_source": "user",
        "selection_rationale": "",
        "load_posture": "Moderate-to-progressive load with planned resets.",
        "recovery_margin": "Moderate recovery margin.",
        "fatigue_exposure": "Moderate fatigue exposure.",
        "specificity_density": "Moderate-to-high specificity density.",
        "load_philosophy": "Moderate-to-progressive load with planned resets.",
        "risk_profile": "Moderate risk option.",
        "best_suited_if": "Stable recovery supports systematic progression.",
        "key_differences": "More progression than A, more control than C.",
        "main_payoff": "Best balance of adaptation and control.",
        "main_cost": "More accumulated fatigue than A.",
        "constraint_summary": [
            "Fixed rest days are Monday and Friday.",
            "Weekly availability is typical 14.0 h.",
        ],
        "event_alignment_notes": [
            "Matches the horizon well.",
            "B events remain rehearsal markers.",
        ],
        "risk_flags": [
            "Becomes less forgiving if continuity breaks.",
            "Can under-deliver if resets are ignored.",
        ],
        "kpi_guardrail_notes": [
            "Keep progression inside KPI limits.",
        ],
        "decision_notes": [
            "This is the middle path.",
        ],
        "season_archetype": "none",
        "allowed_intensity_domains": [
            "NONE",
            "RECOVERY",
            "ENDURANCE",
            "TEMPO",
            "SWEET_SPOT",
            "THRESHOLD",
            "VO2MAX",
        ],
        "forbidden_intensity_domains": [],
        "deload_cadence": "2:1:1",
        "phase_length_weeks": 4,
        "phase_count_expected": 4,
        "full_phases": 4,
        "shortened_phases": [],
        "max_shortened_phases": 0,
        "shortening_budget_weeks": 0,
    }


def test_selected_scenario_contract_model_accepts_canonical_full_contract() -> None:
    model = SelectedScenarioContractModel(**_full_selected_scenario_contract())

    assert model.selected_scenario_id == "B"
    assert model.constraint_summary == [
        "Fixed rest days are Monday and Friday.",
        "Weekly availability is typical 14.0 h.",
    ]
    assert model.shortened_phases == []


def test_selected_scenario_contract_model_rejects_string_list_drift() -> None:
    payload = _full_selected_scenario_contract()
    payload["constraint_summary"] = "Fixed rest days are Monday and Friday."

    with pytest.raises(ValidationError) as exc_info:
        SelectedScenarioContractModel(**payload)

    assert "constraint_summary" in str(exc_info.value)


def test_season_and_phase_runtime_models_accept_full_selected_contract() -> None:
    contract = _full_selected_scenario_contract()

    season_bundle = SeasonPlanBundleModel(
        selected_scenario_contract=contract,
        event_priority=SeasonEventAnchorModel(),
        macrocycle=SeasonMacrocycleDraftModel(),
    )
    phase_guardrails = PhaseGuardrailsPayloadModel(inherited_scenario_contract=contract)
    phase_structure = PhaseStructurePayloadModel(inherited_scenario_contract=contract)

    assert season_bundle.selected_scenario_contract is not None
    assert season_bundle.selected_scenario_contract.main_payoff == "Best balance of adaptation and control."
    assert phase_guardrails.inherited_scenario_contract is not None
    assert phase_guardrails.inherited_scenario_contract.phase_count_expected == 4
    assert phase_structure.inherited_scenario_contract is not None
    assert phase_structure.inherited_scenario_contract.allowed_intensity_domains[-1] == "VO2MAX"


def test_phase_runtime_models_accept_structured_phase_payload_sections() -> None:
    guardrails = PhaseGuardrailsPayloadModel(
        phase_summary={"primary_objective": "Rebuild load tolerance."},
        load_guardrails={"weekly_kj_bands": [{"week": "2026-24", "band": {"min": 7893, "max": 10148}}]},
        allowed_forbidden_semantics={"allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO"]},
        events_constraints={"events": []},
        execution_non_negotiables={"no_catch_up_rule": "No catch-up load."},
    )
    structure = PhaseStructurePayloadModel(
        upstream_intent={"phase_intent": "shortened_re_entry"},
        load_ranges={"source": "phase_guardrails_2026-24--2026-25__20260609_070439.json"},
        execution_principles={"load_intensity_handling": {"max_quality_days_per_week": 1}},
        structural_phase_elements={"allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO"]},
        week_skeleton_logic={"week_roles": {"week_roles": [{"week": "2026-24", "role": "SHORTENED_RE_ENTRY"}]}},
        adaptation_rules=["Reduce quality before load."],
    )

    assert guardrails.phase_summary.primary_objective == "Rebuild load tolerance."
    assert structure.upstream_intent.phase_intent == "shortened_re_entry"
