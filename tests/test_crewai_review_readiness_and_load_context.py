from __future__ import annotations

from rps.crewai_runtime.guardrails_context import guardrail_runtime_context
from rps.crewai_runtime.guardrails_phase import phase_bundle_review_readiness
from rps.crewai_runtime.guardrails_season import (
    season_bundle_review_readiness,
    season_phase_load_context_match,
    season_scenario_selection_shape,
)
from rps.crewai_runtime.guardrails_week import week_bundle_review_readiness


def test_season_phase_load_context_match_repairs_missing_role_week_notes_before_validation() -> None:
    output = {
        "data": {
            "body_metadata": {"phase_taxonomy_version": "canonical_phase_taxonomy_v1"},
            "season_intent_principles": {"season_objective": "Strong 200 km A-event execution."},
            "phases": [
                {
                    "phase_id": "P01",
                    "iso_week_range": "2026-21--2026-23",
                    "phase_type": "BASE",
                    "phase_intent": "shortened_re_entry",
                    "build_subtype": None,
                    "weekly_load_corridor": {"weekly_kj": {"min": 7800, "max": 9800, "notes": "Base corridor."}},
                    "allowed_forbidden_semantics": {
                        "allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
                        "allowed_load_modalities": ["K3"],
                        "forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
                    },
                    "events_constraints": [],
                }
            ],
            "season_load_envelope": {"expected_average_weekly_kj_range": {"min": 7800, "max": 8600}},
            "assumptions_unknowns": {"assumptions": ["a"], "uncertainties": ["u"], "revisit_items": ["r"]},
            "justification": {"phase_justifications": []},
        }
    }

    with guardrail_runtime_context(
        approved_planning_bundle={
            "phase_blueprints": [
                {
                    "phase_id": "P01",
                    "allowed_load_modalities": ["NONE", "K3"],
                    "role_week_load_bands": [
                        {"week": "2026-21", "role": "LOAD_1", "band": {"min": 7800, "max": 8600}}
                    ],
                }
            ]
        },
        season_phase_load_context={
            "season_allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT"],
            "phases": [
                {
                    "phase_id": "P01",
                    "phase_intent": "shortened_re_entry",
                    "recommended_phase_corridor": {"min": 7800, "max": 9800},
                    "role_week_load_bands": [
                        {"week": "2026-21", "role": "LOAD_1", "band": {"min": 7800, "max": 8600}}
                    ],
                    "event_taper_trace": {"events": []},
                }
            ],
        },
    ):
        ok, repaired = season_phase_load_context_match(output)

    assert ok is True
    notes = repaired["data"]["phases"][0]["weekly_load_corridor"]["weekly_kj"]["notes"]
    assert "Inherited role-week load guardrails" in notes
    assert "2026-21: LOAD_1 7800-8600" in notes
    assert repaired["data"]["phases"][0]["allowed_forbidden_semantics"]["allowed_load_modalities"] == ["NONE", "K3"]

def test_season_phase_load_context_match_clears_stale_event_constraints_and_ignores_narrative_semantics() -> None:
    output = {
        "data": {
            "body_metadata": {"phase_taxonomy_version": "canonical_phase_taxonomy_v1"},
            "season_intent_principles": {"season_objective": "Strong 200 km A-event execution."},
            "phases": [
                {
                    "phase_id": "P01",
                    "iso_week_range": "2026-21--2026-23",
                    "phase_type": "BASE",
                    "phase_intent": "shortened_re_entry",
                    "build_subtype": None,
                    "narrative": "Controlled threshold support stays available in this phase.",
                    "weekly_load_corridor": {"weekly_kj": {"min": 7800, "max": 9800, "notes": "Base corridor."}},
                    "allowed_forbidden_semantics": {
                        "allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
                        "allowed_load_modalities": ["K3"],
                        "forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
                    },
                    "events_constraints": [
                        {
                            "window": "2026-21",
                            "type": "B",
                            "constraint": "No target-week event.",
                        }
                    ],
                }
            ],
            "season_load_envelope": {"expected_average_weekly_kj_range": {"min": 7800, "max": 8600}},
            "assumptions_unknowns": {"assumptions": ["a"], "uncertainties": ["u"], "revisit_items": ["r"]},
            "justification": {"phase_justifications": []},
        }
    }

    with guardrail_runtime_context(
        approved_planning_bundle={
            "phase_blueprints": [
                {
                    "phase_id": "P01",
                    "allowed_load_modalities": ["NONE", "K3"],
                    "role_week_load_bands": [
                        {"week": "2026-21", "role": "LOAD_1", "band": {"min": 7800, "max": 8600}}
                    ],
                }
            ]
        },
        season_phase_load_context={
            "season_allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT"],
            "phases": [
                {
                    "phase_id": "P01",
                    "phase_intent": "shortened_re_entry",
                    "recommended_phase_corridor": {"min": 7800, "max": 9800},
                    "role_week_load_bands": [
                        {"week": "2026-21", "role": "LOAD_1", "band": {"min": 7800, "max": 8600}}
                    ],
                    "event_taper_trace": {"events": []},
                }
            ],
        },
    ):
        ok, repaired = season_phase_load_context_match(output)

    assert ok is True
    assert repaired["data"]["phases"][0]["events_constraints"] == []

def test_season_bundle_review_readiness_rejects_phantom_event_placeholders() -> None:
    for placeholder in (
        "No target-week event.",
        "No logistics exception.",
        "No event-driven load exception.",
    ):
        ok, message = season_bundle_review_readiness(
            {
                "event_priority": {},
                "macrocycle": {},
                "phase_blueprints": [
                    {
                        "phase_id": "P01",
                        "iso_week_range": "2026-21--2026-23",
                        "scenario_cadence": "2:1",
                        "event_constraints": [placeholder],
                    }
                ],
            }
        )

        assert ok is False
        assert "synthetic no-event semantics" in message

def test_phase_bundle_review_readiness_rejects_unready_bundle() -> None:
    ok, message = phase_bundle_review_readiness(
        {
            "phase_intent": "general_base",
            "guardrails": {"phase_intent": "general_base", "phase_summary": {}},
            "structure": {"phase_intent": "specificity_build"},
            "preview": {"phase_intent": "general_base", "phase_intent_summary": {}},
            "constraint_audit": {"blocking_issues": []},
            "load_governance_audit": {"blocking_issues": []},
        }
    )

    assert ok is False
    assert "does not match bundle phase_intent" in message or "must provide guardrails.phase_summary" in message

def test_phase_bundle_review_readiness_accepts_normalized_nested_phase_intents() -> None:
    ok, payload = phase_bundle_review_readiness(
        {
            "phase_intent": "shortened_re_entry",
            "guardrails": {"phase_intent": "shortened_re_entry", "phase_summary": {"primary_objective": "Rebuild load tolerance."}},
            "structure": {"phase_intent": "shortened_re_entry"},
            "preview": {"phase_intent": "shortened_re_entry", "phase_intent_summary": {"phase_intent": "shortened_re_entry"}},
            "constraint_audit": {"blocking_issues": []},
            "load_governance_audit": {"blocking_issues": []},
        }
    )

    assert ok is True
    assert payload["phase_intent"] == "shortened_re_entry"

def test_week_bundle_review_readiness_rejects_loaded_fixed_rest_day() -> None:
    ok, message = week_bundle_review_readiness(
        {
            "day_blueprints": [
                {
                    "day": "Mon",
                    "date": "2026-05-11",
                    "fixed_rest_day": True,
                    "planned_duration_minutes": 45,
                    "planned_kj": 250,
                    "workout_id": "W1",
                }
            ],
            "workout_blueprints": [],
        }
    )

    assert ok is False
    assert "Fixed rest day still carries duration" in message

def test_scenario_selection_guardrail_accepts_only_selection_shape() -> None:
    ok, payload = season_scenario_selection_shape(
        {
            "meta": {"artifact_type": "SEASON_SCENARIO_SELECTION", "schema_id": "SeasonScenarioSelectionInterface"},
            "data": {"selected_scenario_id": "B", "season_scenarios_ref": "season_scenarios/latest.json"},
        }
    )
    failed, message = season_scenario_selection_shape(
        {
            "meta": {"artifact_type": "SEASON_SCENARIO_SELECTION", "schema_id": "SeasonScenarioSelectionInterface"},
            "data": {
                "selected_scenario_id": "B",
                "season_scenarios_ref": "season_scenarios/latest.json",
                "weekly_kj_bands": [],
            },
        }
    )

    assert ok is True
    assert payload["data"]["selected_scenario_id"] == "B"
    assert failed is False
    assert "must not contain" in message
