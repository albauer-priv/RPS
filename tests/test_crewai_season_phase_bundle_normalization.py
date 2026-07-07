from __future__ import annotations

import pytest

from rps.agents.crewai_bundle_normalization import (
    normalize_phase_draft_bundle,
    normalize_season_plan_draft_bundle,
)
from rps.crewai_runtime.guardrails import (
    season_bundle_integrity,
    season_bundle_matches_contract,
    season_phase_load_feasibility,
)
from rps.crewai_runtime.guardrails_context import guardrail_runtime_context
from rps.crewai_runtime.guardrails_phase import (
    phase_bundle_matches_context,
    phase_week_role_load_coherence,
)


def test_season_bundle_integrity_requires_phase_blueprints() -> None:
    failed, message = season_bundle_integrity(
        {
            "event_priority": {},
            "macrocycle": {},
            "phase_blueprints": [],
        }
    )
    ok, payload = season_bundle_integrity(
        {
            "event_priority": {},
            "macrocycle": {},
            "phase_blueprints": [
                {
                    "phase_id": "P01",
                    "iso_week_range": "2026-21--2026-23",
                    "scenario_cadence": "2:1",
                    "cadence_week_roles": ["LOAD_1", "LOAD_2", "DELOAD"],
                }
            ],
        }
    )

    assert failed is False
    assert "at least one phase blueprint" in message
    assert ok is True
    assert payload["phase_blueprints"][0]["scenario_cadence"] == "2:1"

def test_season_bundle_integrity_requires_event_priority_and_macrocycle() -> None:
    ok, message = season_bundle_integrity(
        {
            "macrocycle": {},
            "phase_blueprints": [
                {
                    "phase_id": "P01",
                    "iso_week_range": "2026-21--2026-23",
                    "scenario_cadence": "2:1",
                    "cadence_week_roles": ["LOAD_1", "LOAD_2", "DELOAD"],
                }
            ],
        }
    )
    assert ok is False
    assert "event_priority" in message

    ok, message = season_bundle_integrity(
        {
            "event_priority": {},
            "phase_blueprints": [
                {
                    "phase_id": "P01",
                    "iso_week_range": "2026-21--2026-23",
                    "scenario_cadence": "2:1",
                    "cadence_week_roles": ["LOAD_1", "LOAD_2", "DELOAD"],
                }
            ],
        }
    )
    assert ok is False
    assert "macrocycle" in message

def test_season_phase_load_feasibility_rejects_unavailable_corridor_and_flat_roles() -> None:
    failed, message = season_phase_load_feasibility(
        {
            "phase_blueprints": [
                {
                    "phase_id": "P01",
                    "cycle": "Build",
                    "scenario_cadence": "2:1",
                    "cadence_week_roles": ["LOAD_1", "LOAD_2", "DELOAD"],
                    "load_corridor_max": 12000,
                    "availability_cap_kj": 9000,
                    "load_feasibility_status": "feasible",
                }
            ]
        }
    )

    assert failed is False
    assert "exceeds availability_cap_kj" in message

def test_phase_week_role_load_coherence_rejects_flat_deload() -> None:
    failed, message = phase_week_role_load_coherence(
        {
            "week_blueprints": [
                {"week": "2026-20", "week_role": "LOAD_1", "s5_band_min": 7000, "s5_band_max": 8000},
                {"week": "2026-21", "week_role": "DELOAD", "s5_band_min": 7000, "s5_band_max": 7900},
            ]
        }
    )

    assert failed is False
    assert "must reduce materially" in message

def test_season_bundle_matches_contract_rejects_domains_outside_semantic_profile() -> None:
    with guardrail_runtime_context(
        phase_slot_context={
            "phase_slots": [
                {"phase_id": "P01", "iso_week_range": "2026-21--2026-23", "length_weeks": 3, "phase_intent": "shortened_re_entry"}
            ]
        },
        season_phase_load_context={
            "season_allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
            "phases": [
                {
                    "phase_id": "P01",
                    "phase_intent": "shortened_re_entry",
                    "recommended_phase_corridor": {"min": 7000, "max": 9000},
                    "event_taper_trace": {},
                }
            ],
        },
    ):
        failed, message = season_bundle_matches_contract(
            {
                "event_priority": {},
                "macrocycle": {},
                "season_load_envelope": {"expected_average_weekly_kj_range": {"min": 7000, "max": 9000}},
                "season_semantic_notes": ["Frame the objective against the A event."],
                "phase_blueprints": [
                    {
                        "phase_id": "P01",
                        "iso_week_range": "2026-21--2026-23",
                        "scenario_cadence": "2:1",
                        "phase_type": "BASE",
                        "phase_intent": "shortened_re_entry",
                        "build_subtype": None,
                        "phase_taxonomy_version": "canonical_phase_taxonomy_v1",
                        "load_corridor_min": 7000,
                        "load_corridor_max": 9000,
                        "allowed_domains": ["ENDURANCE", "THRESHOLD"],
                        "forbidden_domains": ["VO2MAX"],
                        "semantic_contract": {
                            "methodology_family": "compressed_reentry",
                            "threshold_role": "forbidden",
                            "event_load_policy": "no_event_load_exception",
                            "taper_policy": "not_applicable",
                            "writer_semantic_notes": ["Keep the phase recovery-protective."],
                        },
                    }
                ],
            }
        )

    assert failed is False
    assert "season_bundle_phase_domains_outside_semantic_contract" in message

def test_normalize_season_plan_draft_bundle_overwrites_raw_semantics() -> None:
    draft_bundle = {
        "event_priority": {"primary_a_events": ["A Event"]},
        "macrocycle": {"deload_cadence": "2:1:1"},
        "phase_blueprints": [
            {
                "phase_id": "P01",
                "iso_week_range": "2026-21--2026-23",
                "scenario_cadence": "2:1:1",
                "phase_type": "PREPARATION",
                "phase_intent": "base_preparation",
                "build_subtype": None,
                "allowed_domains": ["ENDURANCE", "THRESHOLD"],
                "role_week_load_bands": ["legacy"],
            }
        ],
    }
    with guardrail_runtime_context(
        selected_scenario_contract={
            "selected_scenario_id": "B",
            "scenario_name": "Balanced build",
            "selection_source": "athlete",
            "selection_rationale": "Controlled progression",
            "load_posture": "balanced_progressive",
            "recovery_margin": "medium",
            "fatigue_exposure": "moderate",
            "specificity_density": "controlled",
            "load_philosophy": "balanced_progressive",
            "risk_profile": "medium",
            "constraint_summary": ["preserve continuity"],
            "event_alignment_notes": ["B rehearsal"],
            "risk_flags": ["stable recovery required"],
            "kpi_guardrail_notes": ["repeatable load"],
            "decision_notes": ["athlete selected B"],
            "season_archetype": "none",
            "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
            "forbidden_intensity_domains": ["VO2MAX"],
            "deload_cadence": "2:1:1",
        },
        phase_slot_context={
            "phase_slots": [
                {"phase_id": "P01", "iso_week_range": "2026-21--2026-23", "length_weeks": 3, "phase_intent": "shortened_re_entry"}
            ]
        },
        season_phase_load_context={
            "selected_scenario_contract": {
                "selected_scenario_id": "B",
                "scenario_name": "Balanced build",
                "selection_source": "athlete",
                "selection_rationale": "Controlled progression",
                "load_posture": "balanced_progressive",
                "recovery_margin": "medium",
                "fatigue_exposure": "moderate",
                "specificity_density": "controlled",
                "load_philosophy": "balanced_progressive",
                "risk_profile": "medium",
                "constraint_summary": ["preserve continuity"],
                "event_alignment_notes": ["B rehearsal"],
                "risk_flags": ["stable recovery required"],
                "kpi_guardrail_notes": ["repeatable load"],
                "decision_notes": ["athlete selected B"],
                "season_archetype": "none",
                "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
                "forbidden_intensity_domains": ["VO2MAX"],
                "deload_cadence": "2:1:1",
            },
            "season_allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
            "phases": [
                {
                    "phase_id": "P01",
                    "iso_week_range": "2026-21--2026-23",
                    "phase_type": "BASE",
                    "phase_intent": "shortened_re_entry",
                    "build_subtype": None,
                    "season_phase_role": "shortened_re_entry",
                    "scenario_cadence": "2:1:1",
                    "cadence_week_roles": ["LOAD_1", "LOAD_2", "MINI_RESET"],
                    "availability_cap_kj": {"typical": 10000, "max": 11000},
                    "baseline_load_kj": 8200,
                    "recommended_phase_corridor": {"min": 7800, "max": 9800},
                    "role_week_load_bands": [
                        {"week": "2026-21", "role": "LOAD_1", "band": {"min": 7800, "max": 8600}},
                    ],
                    "progression_trace": {"source": "deterministic"},
                }
            ],
        }
    ):
        normalized = normalize_season_plan_draft_bundle(draft_bundle)
        ok, _ = season_bundle_matches_contract(normalized)

    blueprint = normalized["phase_blueprints"][0]
    assert blueprint["phase_type"] == "BASE"
    assert blueprint["phase_intent"] == "shortened_re_entry"
    assert blueprint["allowed_domains"] == ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"]
    assert blueprint["allowed_load_modalities"] == ["NONE", "K3"]
    assert "THRESHOLD" in blueprint["forbidden_domains"]
    assert "VO2MAX" in blueprint["forbidden_domains"]
    assert blueprint["phase_taxonomy_version"] == "canonical_phase_taxonomy_v1"
    assert blueprint["role_week_load_bands"] == [
        {"week": "2026-21", "role": "LOAD_1", "band": {"min": 7800, "max": 8600}}
    ]
    assert normalized["season_load_envelope"]["expected_average_weekly_kj_range"] == {"min": 7800, "max": 8600}
    assert normalized["selected_scenario_contract"]["selected_scenario_id"] == "B"
    assert ok is True

def test_season_bundle_matches_contract_accepts_selected_scenario_contract_in_synthetic_candidate() -> None:
    normalized = {
        "event_priority": {"primary_a_events": ["A Event"]},
        "macrocycle": {"deload_cadence": "2:1:1"},
        "season_load_envelope": {"expected_average_weekly_kj_range": {"min": 7800, "max": 8600}},
        "season_semantic_notes": ["Frame the objective against the A event."],
        "phase_blueprints": [
            {
                "phase_id": "P01",
                "iso_week_range": "2026-21--2026-23",
                "scenario_cadence": "2:1:1",
                "phase_type": "BASE",
                "phase_intent": "shortened_re_entry",
                "build_subtype": None,
                "phase_taxonomy_version": "canonical_phase_taxonomy_v1",
                "load_corridor_min": 7800,
                "load_corridor_max": 9800,
                "allowed_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
                "allowed_load_modalities": ["NONE", "K3"],
                "forbidden_domains": ["THRESHOLD", "VO2MAX"],
                "role_week_load_bands": [
                    {"week": "2026-21", "role": "LOAD_1", "band": {"min": 7800, "max": 8600}}
                ],
                "semantic_contract": {
                    "methodology_family": "compressed_reentry",
                    "threshold_role": "forbidden",
                    "event_load_policy": "no_event_load_exception",
                    "taper_policy": "not_applicable",
                    "writer_semantic_notes": ["Keep the phase recovery-protective."],
                },
            }
        ],
        "selected_scenario_contract": {
            "selected_scenario_id": "B",
            "scenario_name": "Balanced build",
            "selection_source": "athlete",
            "selection_rationale": "Controlled progression",
            "load_posture": "balanced_progressive",
            "recovery_margin": "medium",
            "fatigue_exposure": "moderate",
            "specificity_density": "controlled",
            "load_philosophy": "balanced_progressive",
            "risk_profile": "medium",
            "constraint_summary": ["preserve continuity"],
            "event_alignment_notes": ["B rehearsal"],
            "risk_flags": ["stable recovery required"],
            "kpi_guardrail_notes": ["repeatable load"],
            "decision_notes": ["athlete selected B"],
            "season_archetype": "none",
            "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
            "forbidden_intensity_domains": ["VO2MAX"],
            "deload_cadence": "2:1:1",
        },
    }
    with guardrail_runtime_context(
        phase_slot_context={
            "phase_slots": [
                {"phase_id": "P01", "iso_week_range": "2026-21--2026-23", "length_weeks": 3, "phase_intent": "shortened_re_entry"}
            ]
        },
        selected_scenario_contract=normalized["selected_scenario_contract"],
        season_phase_load_context={
            "selected_scenario_contract": normalized["selected_scenario_contract"],
            "season_allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
            "phases": [
                {
                    "phase_id": "P01",
                    "iso_week_range": "2026-21--2026-23",
                    "phase_type": "BASE",
                    "phase_intent": "shortened_re_entry",
                    "build_subtype": None,
                    "season_phase_role": "shortened_re_entry",
                    "scenario_cadence": "2:1:1",
                    "cadence_week_roles": ["LOAD_1", "LOAD_2", "MINI_RESET"],
                    "availability_cap_kj": {"typical": 10000, "max": 11000},
                    "baseline_load_kj": 8200,
                    "recommended_phase_corridor": {"min": 7800, "max": 9800},
                    "role_week_load_bands": [
                        {"week": "2026-21", "role": "LOAD_1", "band": {"min": 7800, "max": 8600}},
                    ],
                    "progression_trace": {"source": "deterministic"},
                    "event_taper_trace": {},
                }
            ],
        },
    ):
        ok, message = season_bundle_matches_contract(normalized)

    assert ok is True, message

def test_normalize_season_plan_draft_bundle_supports_variable_phase_counts() -> None:
    draft_bundle = {
        "event_priority": {"primary_a_events": ["A1", "A2"]},
        "macrocycle": {"deload_cadence": "2:1:1"},
        "phase_blueprints": [
            {"phase_id": f"P0{idx}", "iso_week_range": f"2026-{20 + idx}--2026-{20 + idx}", "scenario_cadence": "2:1:1"}
            for idx in range(1, 7)
        ],
    }
    context_phases = []
    intents = [
        ("BASE", "shortened_re_entry"),
        ("BASE", "general_base"),
        ("BUILD", "durability_build"),
        ("TAPER", "taper_freshening"),
        ("BASE", "shortened_re_entry"),
        ("TAPER", "taper_freshening"),
    ]
    for idx, (phase_type, phase_intent) in enumerate(intents, start=1):
        context_phases.append(
            {
                "phase_id": f"P0{idx}",
                "iso_week_range": f"2026-{20 + idx}--2026-{20 + idx}",
                "phase_type": phase_type,
                "phase_intent": phase_intent,
                "build_subtype": phase_intent if phase_type == "BUILD" else None,
                "season_phase_role": phase_intent,
                "scenario_cadence": "2:1:1",
                "cadence_week_roles": ["LOAD_1"],
                "availability_cap_kj": {"typical": 10000, "max": 11000},
                "baseline_load_kj": 8000 + idx,
                "recommended_phase_corridor": {"min": 7000 + idx, "max": 9000 + idx},
                "role_week_load_bands": [{"week": f"2026-{20 + idx}", "role": "LOAD_1", "band": {"min": 7000 + idx, "max": 9000 + idx}}],
                "progression_trace": {"index": idx},
            }
        )
    with guardrail_runtime_context(
        season_phase_load_context={
            "season_allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
            "phases": context_phases,
        }
    ):
        normalized = normalize_season_plan_draft_bundle(draft_bundle)

    assert len(normalized["phase_blueprints"]) == 6
    assert normalized["phase_blueprints"][2]["build_subtype"] == "durability_build"
    assert normalized["phase_blueprints"][5]["phase_intent"] == "taper_freshening"
    assert normalized["season_load_envelope"]["expected_high_load_weeks_count"] == 0
    assert normalized["season_load_envelope"]["expected_deload_or_low_load_weeks_count"] == 0

def test_normalize_season_plan_draft_bundle_derives_envelope_counts_when_missing() -> None:
    draft_bundle = {
        "event_priority": {"primary_a_events": ["A1"]},
        "macrocycle": {"deload_cadence": "2:1:1"},
        "season_load_envelope": {"expected_average_weekly_kj_range": {"min": 1, "max": 2}},
        "phase_blueprints": [
            {
                "phase_id": "P01",
                "iso_week_range": "2026-21--2026-23",
                "scenario_cadence": "2:1:1",
                "cadence_week_roles": [
                    "SHORTENED_RE_ENTRY",
                    "SHORTENED_CONSOLIDATION",
                    "SHORTENED_MINI_RESET",
                ],
                "role_week_load_bands": [
                    {"week": "2026-21", "role": "SHORTENED_RE_ENTRY", "band": {"min": 7800, "max": 8200}},
                    {"week": "2026-22", "role": "SHORTENED_CONSOLIDATION", "band": {"min": 8000, "max": 8400}},
                    {"week": "2026-23", "role": "SHORTENED_MINI_RESET", "band": {"min": 7600, "max": 8000}},
                ],
            },
            {
                "phase_id": "P02",
                "iso_week_range": "2026-24--2026-27",
                "scenario_cadence": "2:1:1",
                "cadence_week_roles": ["LOAD_1", "LOAD_2", "MINI_RESET", "RELOAD"],
                "role_week_load_bands": [
                    {"week": "2026-24", "role": "LOAD_1", "band": {"min": 9000, "max": 9800}},
                    {"week": "2026-25", "role": "LOAD_2", "band": {"min": 9400, "max": 10200}},
                    {"week": "2026-26", "role": "MINI_RESET", "band": {"min": 8200, "max": 9000}},
                    {"week": "2026-27", "role": "RELOAD", "band": {"min": 9300, "max": 10100}},
                ],
            },
        ],
    }
    with guardrail_runtime_context(
        season_phase_load_context={
            "season_allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
            "phases": [
                {
                    "phase_id": "P01",
                    "iso_week_range": "2026-21--2026-23",
                    "phase_type": "BASE",
                    "phase_intent": "shortened_re_entry",
                    "build_subtype": None,
                    "season_phase_role": "shortened_re_entry",
                    "scenario_cadence": "2:1:1",
                    "cadence_week_roles": ["SHORTENED_RE_ENTRY", "SHORTENED_CONSOLIDATION", "SHORTENED_MINI_RESET"],
                    "availability_cap_kj": {"typical": 10000, "max": 11000},
                    "baseline_load_kj": 8200,
                    "recommended_phase_corridor": {"min": 7800, "max": 9800},
                    "role_week_load_bands": [
                        {"week": "2026-21", "role": "SHORTENED_RE_ENTRY", "band": {"min": 7800, "max": 8200}},
                        {"week": "2026-22", "role": "SHORTENED_CONSOLIDATION", "band": {"min": 8000, "max": 8400}},
                        {"week": "2026-23", "role": "SHORTENED_MINI_RESET", "band": {"min": 7600, "max": 8000}},
                    ],
                    "progression_trace": {"source": "deterministic"},
                },
                {
                    "phase_id": "P02",
                    "iso_week_range": "2026-24--2026-27",
                    "phase_type": "BUILD",
                    "phase_intent": "durability_build",
                    "build_subtype": "durability_build",
                    "season_phase_role": "durability_build",
                    "scenario_cadence": "2:1:1",
                    "cadence_week_roles": ["LOAD_1", "LOAD_2", "MINI_RESET", "RELOAD"],
                    "availability_cap_kj": {"typical": 12000, "max": 13000},
                    "baseline_load_kj": 9200,
                    "recommended_phase_corridor": {"min": 9000, "max": 12000},
                    "role_week_load_bands": [
                        {"week": "2026-24", "role": "LOAD_1", "band": {"min": 9000, "max": 9800}},
                        {"week": "2026-25", "role": "LOAD_2", "band": {"min": 9400, "max": 10200}},
                        {"week": "2026-26", "role": "MINI_RESET", "band": {"min": 8200, "max": 9000}},
                        {"week": "2026-27", "role": "RELOAD", "band": {"min": 9300, "max": 10100}},
                    ],
                    "progression_trace": {"source": "deterministic"},
                },
            ],
        }
    ):
        normalized = normalize_season_plan_draft_bundle(draft_bundle)

    envelope = normalized["season_load_envelope"]
    assert envelope["expected_high_load_weeks_count"] == 2
    assert envelope["expected_deload_or_low_load_weeks_count"] == 3

def test_normalize_season_plan_draft_bundle_canonicalizes_invalid_deterministic_phase_type() -> None:
    draft_bundle = {
        "event_priority": {"primary_a_events": ["A1"]},
        "macrocycle": {"deload_cadence": "2:1:1"},
        "phase_blueprints": [
            {
                "phase_id": "P02",
                "iso_week_range": "2026-24--2026-25",
                "scenario_cadence": "2:1:1",
                "cadence_week_roles": ["SHORTENED_RE_ENTRY", "SHORTENED_CONSOLIDATION"],
                "role_week_load_bands": [
                    {"week": "2026-24", "role": "SHORTENED_RE_ENTRY", "band": {"min": 7800, "max": 8200}},
                    {"week": "2026-25", "role": "SHORTENED_CONSOLIDATION", "band": {"min": 8000, "max": 8400}},
                ],
            }
        ],
    }
    with guardrail_runtime_context(
        season_phase_load_context={
            "season_allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
            "phases": [
                {
                    "phase_id": "P02",
                    "iso_week_range": "2026-24--2026-25",
                    "phase_type": "PREPARATION",
                    "phase_intent": "general_base",
                    "build_subtype": None,
                    "season_phase_role": "general_base",
                    "scenario_cadence": "2:1:1",
                    "cadence_week_roles": ["LOAD_1", "LOAD_2"],
                    "availability_cap_kj": {"typical": 10000, "max": 11000},
                    "baseline_load_kj": 8200,
                    "recommended_phase_corridor": {"min": 7800, "max": 9800},
                    "role_week_load_bands": [
                        {"week": "2026-24", "role": "SHORTENED_RE_ENTRY", "band": {"min": 7800, "max": 8200}},
                        {"week": "2026-25", "role": "SHORTENED_CONSOLIDATION", "band": {"min": 8000, "max": 8400}},
                    ],
                    "progression_trace": {"source": "deterministic"},
                }
            ],
        }
    ):
        normalized = normalize_season_plan_draft_bundle(draft_bundle)
        ok, message = season_bundle_matches_contract(normalized)

    blueprint = normalized["phase_blueprints"][0]
    assert blueprint["phase_type"] == "BASE"
    assert blueprint["phase_intent"] == "general_base"
    assert any("canonicalized phase_type" in warning for warning in blueprint["warnings"])
    assert ok is True, message

def test_normalize_season_plan_draft_bundle_strips_blueprint_forbidden_domain_narrative() -> None:
    draft_bundle = {
        "event_priority": {"primary_a_events": ["A1"]},
        "macrocycle": {"deload_cadence": "2:1:1"},
        "phase_blueprints": [
            {
                "phase_id": "P02",
                "iso_week_range": "2026-24--2026-25",
                "scenario_cadence": "2:1:1",
                "narrative": "Controlled THRESHOLD support appears inside this base block.",
                "overview": {
                    "metabolic_focus": "THRESHOLD-led base support.",
                    "expected_adaptations": ["THRESHOLD maintenance for base support."],
                    "non_negotiables": ["THRESHOLD remains secondary in this block."],
                },
                "structural_emphasis": {"typical_focus": "threshold-led continuity."},
            }
        ],
    }
    with guardrail_runtime_context(
        season_phase_load_context={
            "season_allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
            "phases": [
                {
                    "phase_id": "P02",
                    "iso_week_range": "2026-24--2026-25",
                    "phase_type": "BASE",
                    "phase_intent": "general_base",
                    "build_subtype": None,
                    "season_phase_role": "general_base",
                    "scenario_cadence": "2:1:1",
                    "cadence_week_roles": ["LOAD_1", "LOAD_2"],
                    "availability_cap_kj": {"typical": 10000, "max": 11000},
                    "baseline_load_kj": 8200,
                    "recommended_phase_corridor": {"min": 7800, "max": 9800},
                    "role_week_load_bands": [],
                    "progression_trace": {"source": "deterministic"},
                }
            ],
        }
    ):
        normalized = normalize_season_plan_draft_bundle(draft_bundle)

    blueprint = normalized["phase_blueprints"][0]
    assert blueprint["narrative"] == (
        "Base work consolidates durable aerobic support through endurance-led work with controlled tempo and sweet spot support."
    )
    assert blueprint["overview"]["metabolic_focus"] == (
        "Aerobic base support through endurance-led work with controlled tempo and sweet spot support."
    )
    assert blueprint["overview"]["expected_adaptations"] == [
        "Improved aerobic support and sustainable routine through endurance-led work with controlled tempo and sweet spot support."
    ]
    assert "THRESHOLD remains forbidden in this phase identity." in blueprint["overview"]["non_negotiables"]
    assert "VO2MAX remains forbidden in this phase identity." in blueprint["overview"]["non_negotiables"]
    assert blueprint["structural_emphasis"]["typical_focus"] == (
        "Sustainable base loading, continuity, and durable routine-building."
    )
    assert blueprint["forbidden_domains"] == ["THRESHOLD", "VO2MAX"]

def test_normalize_phase_draft_bundle_overwrites_top_level_semantics_and_week_contracts() -> None:
    draft_bundle = {
        "phase_range": "2026-21--2026-23",
        "phase_type": "PREPARATION",
        "phase_intent": "base_preparation",
        "week_blueprints": [
            {"week": "2026-21", "week_role": "LOAD_2", "s5_band_min": 7000, "s5_band_max": 9000},
        ],
        "guardrails": {"phase_summary": {}, "inherited_scenario_contract": {"selected_scenario_id": "C"}},
        "structure": {"upstream_intent": {}, "inherited_scenario_contract": {"selected_scenario_id": "A"}},
        "preview": {"phase_intent_summary": {}, "inherited_scenario_contract": {"selected_scenario_id": "D"}},
        "constraint_audit": {"blocking_issues": [], "warnings": [], "recommended_adjustments": [], "applied_sources": []},
        "load_governance_audit": {"blocking_issues": [], "warnings": [], "recommended_adjustments": [], "cadence_authority_preserved": True, "durability_first_respected": True},
        "decision_summary": {"cadence_application_notes": [], "override_rationale": []},
    }
    with guardrail_runtime_context(
        phase_execution_context={
            "phase_id": "P01",
            "phase_iso_week_range": "2026-21--2026-23",
            "phase_type": "BASE",
            "phase_role": "BASE",
            "phase_intent": "shortened_re_entry",
            "build_subtype": None,
            "inherited_scenario_contract": {"selected_scenario_id": "B", "load_posture": "balanced_progressive"},
            "week_role_by_iso_week": {"2026-21": "LOAD_1"},
            "phase_s5_bands": [{"week": "2026-21", "band": {"min": 7800, "max": 8600}}],
        }
    ):
        normalized = normalize_phase_draft_bundle(draft_bundle)

    assert normalized["phase_id"] == "P01"
    assert normalized["phase_type"] == "BASE"
    assert normalized["phase_intent"] == "shortened_re_entry"
    assert normalized["inherited_scenario_contract"]["selected_scenario_id"] == "B"
    assert normalized["guardrails"]["inherited_scenario_contract"]["selected_scenario_id"] == "B"
    assert normalized["structure"]["inherited_scenario_contract"]["selected_scenario_id"] == "B"
    assert normalized["preview"]["inherited_scenario_contract"]["selected_scenario_id"] == "B"
    assert normalized["guardrails"]["phase_intent"] == "shortened_re_entry"
    assert normalized["structure"]["phase_intent"] == "shortened_re_entry"
    assert normalized["preview"]["phase_intent"] == "shortened_re_entry"
    assert normalized["week_blueprints"][0]["week_role"] == "LOAD_1"
    assert normalized["week_blueprints"][0]["s5_band_min"] == 7800
    assert normalized["week_blueprints"][0]["s5_band_max"] == 8600

def test_normalize_phase_draft_bundle_rewrites_nested_narrative_phase_intents() -> None:
    draft_bundle = {
        "phase_range": "2026-24--2026-25",
        "phase_type": "BASE",
        "phase_intent": "wrong",
        "week_blueprints": [
            {"week": "2026-24", "week_role": "LOAD_2", "s5_band_min": 7000, "s5_band_max": 9000},
        ],
        "guardrails": {
            "phase_intent": "Re-establish stable training continuity under moderated load.",
            "phase_summary": {"primary_objective": "Rebuild load tolerance."},
        },
        "structure": {
            "phase_intent": "Controlled re-entry narrative",
            "upstream_intent": {"phase_intent": "shortened_re_entry"},
        },
        "preview": {
            "phase_intent": "Keep the weeks feeling stable and aerobic.",
            "phase_intent_summary": {"phase_intent": "shortened_re_entry"},
        },
        "constraint_audit": {"blocking_issues": [], "warnings": [], "recommended_adjustments": [], "applied_sources": []},
        "load_governance_audit": {"blocking_issues": [], "warnings": [], "recommended_adjustments": [], "cadence_authority_preserved": True, "durability_first_respected": True},
        "decision_summary": {"cadence_application_notes": [], "override_rationale": []},
    }
    with guardrail_runtime_context(
        phase_execution_context={
            "phase_id": "P01",
            "phase_iso_week_range": "2026-24--2026-25",
            "phase_type": "BASE",
            "phase_role": "BASE",
            "phase_intent": "shortened_re_entry",
            "build_subtype": None,
            "inherited_scenario_contract": {"selected_scenario_id": "B"},
            "week_role_by_iso_week": {"2026-24": "SHORTENED_RE_ENTRY"},
            "phase_s5_bands": [{"week": "2026-24", "band": {"min": 7893, "max": 10148}}],
        }
    ):
        normalized = normalize_phase_draft_bundle(draft_bundle)

    assert normalized["phase_intent"] == "shortened_re_entry"
    assert normalized["guardrails"]["phase_intent"] == "shortened_re_entry"
    assert normalized["structure"]["phase_intent"] == "shortened_re_entry"
    assert normalized["preview"]["phase_intent"] == "shortened_re_entry"
    assert normalized["week_blueprints"][0]["phase_intent"] == "shortened_re_entry"

def test_normalize_phase_draft_bundle_overwrites_nested_inherited_scenario_contracts() -> None:
    expected_contract = {
        "selected_scenario_id": "B",
        "constraint_summary": [
            "Indoor trainer availability supports continuity when travel or weather reduces outdoor options."
        ],
        "risk_flags": ["Preserve recovery margin through controlled progression."],
    }
    draft_bundle = {
        "phase_range": "2026-24--2026-25",
        "phase_type": "BASE",
        "phase_intent": "wrong",
        "week_blueprints": [
            {"week": "2026-24", "week_role": "LOAD_2", "s5_band_min": 7000, "s5_band_max": 9000},
        ],
        "guardrails": {
            "phase_summary": {"primary_objective": "Rebuild load tolerance."},
            "inherited_scenario_contract": {
                "selected_scenario_id": "B",
                "constraint_summary": [
                    "Indoor trainer availability supports continuity when travel or weather reduces outdoor work."
                ],
            },
        },
        "structure": {
            "upstream_intent": {"phase_intent": "shortened_re_entry"},
            "inherited_scenario_contract": {
                "selected_scenario_id": "B",
                "constraint_summary": ["Paraphrased constraint summary"],
            },
        },
        "preview": {
            "phase_intent_summary": {"phase_intent": "shortened_re_entry"},
            "inherited_scenario_contract": {
                "selected_scenario_id": "B",
                "risk_flags": ["Paraphrased risk flag"],
            },
        },
        "constraint_audit": {"blocking_issues": [], "warnings": [], "recommended_adjustments": [], "applied_sources": []},
        "load_governance_audit": {"blocking_issues": [], "warnings": [], "recommended_adjustments": [], "cadence_authority_preserved": True, "durability_first_respected": True},
        "decision_summary": {"cadence_application_notes": [], "override_rationale": []},
    }
    with guardrail_runtime_context(
        phase_execution_context={
            "phase_id": "P01",
            "phase_iso_week_range": "2026-24--2026-25",
            "phase_type": "BASE",
            "phase_role": "BASE",
            "phase_intent": "shortened_re_entry",
            "build_subtype": None,
            "inherited_scenario_contract": expected_contract,
            "week_role_by_iso_week": {"2026-24": "SHORTENED_RE_ENTRY"},
            "phase_s5_bands": [{"week": "2026-24", "band": {"min": 7893, "max": 10148}}],
        }
    ):
        normalized = normalize_phase_draft_bundle(draft_bundle)

    assert normalized["inherited_scenario_contract"] == expected_contract
    assert normalized["guardrails"]["inherited_scenario_contract"] == expected_contract
    assert normalized["structure"]["inherited_scenario_contract"] == expected_contract
    assert normalized["preview"]["inherited_scenario_contract"] == expected_contract

def test_normalize_phase_draft_bundle_canonicalizes_structure_constraints_before_writer_handoff() -> None:
    draft_bundle = {
        "phase_range": "2026-24--2026-25",
        "phase_type": "BASE",
        "phase_intent": "wrong",
        "week_blueprints": [{"week": "2026-24", "week_role": "LOAD_2", "s5_band_min": 7000, "s5_band_max": 9000}],
        "guardrails": {"phase_summary": {"primary_objective": "Rebuild load tolerance."}},
        "structure": {
            "upstream_intent": {
                "constraints": [
                    "Weekday training must fit compact Tue-Thu windows, with longer work shifting to the weekend.",
                    "Weekday training has to fit into compact Tue-Thu windows, with longer work shifting to the weekend.",
                    "Use the injected role-week banding exactly.",
                    "Fixed no-ride days are preserved across the season.",
                ]
            }
        },
        "preview": {"phase_intent_summary": {"phase_intent": "shortened_re_entry"}},
        "constraint_audit": {"blocking_issues": [], "warnings": [], "recommended_adjustments": [], "applied_sources": []},
        "load_governance_audit": {"blocking_issues": [], "warnings": [], "recommended_adjustments": [], "cadence_authority_preserved": True, "durability_first_respected": True},
        "decision_summary": {"cadence_application_notes": [], "override_rationale": []},
    }
    season_plan_document = {
        "document": {
            "data": {
                "global_constraints": {
                    "availability_assumptions": [
                        "Weekday training has to fit into compact Tue-Thu windows, with longer work shifting to the weekend.",
                        "Fixed rest days are Monday and Friday.",
                    ],
                    "risk_constraints": [],
                    "planned_event_windows": [],
                    "recovery_protection": {"notes": []},
                }
            }
        }
    }
    with guardrail_runtime_context(
        phase_execution_context={
            "phase_id": "P01",
            "phase_iso_week_range": "2026-24--2026-25",
            "phase_type": "BASE",
            "phase_role": "BASE",
            "phase_intent": "shortened_re_entry",
            "build_subtype": None,
            "inherited_scenario_contract": {"selected_scenario_id": "B"},
            "week_role_by_iso_week": {"2026-24": "SHORTENED_RE_ENTRY"},
            "phase_s5_bands": [{"week": "2026-24", "band": {"min": 7893, "max": 10148}}],
        },
        loaded_inputs={"season_plan": season_plan_document},
    ):
        normalized = normalize_phase_draft_bundle(draft_bundle)

    assert normalized["structure"]["upstream_intent"]["constraints"] == [
        "Weekday training has to fit into compact Tue-Thu windows, with longer work shifting to the weekend.",
        "Fixed rest days are Monday and Friday.",
    ]

def test_normalize_phase_draft_bundle_raises_when_canonical_phase_intent_missing() -> None:
    draft_bundle = {
        "phase_range": "2026-24--2026-25",
        "guardrails": {"phase_summary": {"primary_objective": "Rebuild load tolerance."}},
        "structure": {"upstream_intent": {"phase_intent": "shortened_re_entry"}},
        "preview": {"phase_intent_summary": {"phase_intent": "shortened_re_entry"}},
        "constraint_audit": {"blocking_issues": [], "warnings": [], "recommended_adjustments": [], "applied_sources": []},
        "load_governance_audit": {"blocking_issues": [], "warnings": [], "recommended_adjustments": [], "cadence_authority_preserved": True, "durability_first_respected": True},
        "decision_summary": {"cadence_application_notes": [], "override_rationale": []},
    }
    with guardrail_runtime_context(
        phase_execution_context={
            "phase_id": "P01",
            "phase_iso_week_range": "2026-24--2026-25",
            "phase_type": "BASE",
            "phase_role": "BASE",
            "phase_intent": "",
        }
    ):
        with pytest.raises(RuntimeError, match="phase_execution_context\\.phase_intent"):
            normalize_phase_draft_bundle(draft_bundle)

def test_normalize_phase_draft_bundle_raises_when_inherited_scenario_contract_missing() -> None:
    draft_bundle = {
        "phase_range": "2026-24--2026-25",
        "guardrails": {"phase_summary": {"primary_objective": "Rebuild load tolerance."}},
        "structure": {"upstream_intent": {"phase_intent": "shortened_re_entry"}},
        "preview": {"phase_intent_summary": {"phase_intent": "shortened_re_entry"}},
        "constraint_audit": {"blocking_issues": [], "warnings": [], "recommended_adjustments": [], "applied_sources": []},
        "load_governance_audit": {"blocking_issues": [], "warnings": [], "recommended_adjustments": [], "cadence_authority_preserved": True, "durability_first_respected": True},
        "decision_summary": {"cadence_application_notes": [], "override_rationale": []},
    }
    with guardrail_runtime_context(
        phase_execution_context={
            "phase_id": "P01",
            "phase_iso_week_range": "2026-24--2026-25",
            "phase_type": "BASE",
            "phase_role": "BASE",
            "phase_intent": "shortened_re_entry",
        }
    ):
        with pytest.raises(RuntimeError, match="inherited_scenario_contract"):
            normalize_phase_draft_bundle(draft_bundle)

def test_phase_bundle_matches_context_accepts_inherited_scenario_contract_in_synthetic_candidate() -> None:
    draft_bundle = {
        "phase_range": "2026-21--2026-23",
        "phase_type": "PREPARATION",
        "phase_intent": "base_preparation",
        "week_blueprints": [
            {"week": "2026-21", "week_role": "LOAD_2", "s5_band_min": 7000, "s5_band_max": 9000},
        ],
        "guardrails": {"phase_summary": {}},
        "structure": {"upstream_intent": {}},
        "preview": {"phase_intent_summary": {}},
        "constraint_audit": {"blocking_issues": [], "warnings": [], "recommended_adjustments": [], "applied_sources": []},
        "load_governance_audit": {"blocking_issues": [], "warnings": [], "recommended_adjustments": [], "cadence_authority_preserved": True, "durability_first_respected": True},
        "decision_summary": {"cadence_application_notes": [], "override_rationale": []},
    }
    with guardrail_runtime_context(
        phase_execution_context={
            "phase_id": "P01",
            "phase_iso_week_range": "2026-21--2026-23",
            "phase_type": "BASE",
            "phase_role": "BASE",
            "phase_intent": "shortened_re_entry",
            "build_subtype": None,
            "inherited_scenario_contract": {"selected_scenario_id": "B", "load_posture": "balanced_progressive"},
            "week_role_by_iso_week": {"2026-21": "LOAD_1"},
            "phase_s5_bands": [{"week": "2026-21", "band": {"min": 7800, "max": 8600}}],
        }
    ):
        normalized = normalize_phase_draft_bundle(draft_bundle)
        ok, message = phase_bundle_matches_context(normalized)

    assert normalized["inherited_scenario_contract"]["selected_scenario_id"] == "B"
    assert ok is True, message

def test_phase_bundle_matches_context_does_not_require_missing_authority_contract() -> None:
    mapping = {
        "week_blueprints": [
            {"week": "2026-21", "week_role": "LOAD_1", "s5_band_min": 7800, "s5_band_max": 8600},
        ]
    }
    with guardrail_runtime_context(
        phase_execution_context={
            "week_role_by_iso_week": {"2026-21": "LOAD_1"},
            "phase_s5_bands": [{"week": "2026-21", "band": {"min": 7800, "max": 8600}}],
        }
    ):
        ok, message = phase_bundle_matches_context(mapping)

    assert ok is True, message
