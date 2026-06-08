from __future__ import annotations

from pathlib import Path

from rps.agents.output_normalization import (
    extract_planning_events_document,
    injection_mode_for_tasks,
    normalize_phase_guardrails_document,
    normalize_phase_preview_document,
    normalize_phase_structure_document,
    normalize_season_scenarios_document,
    normalize_workout_inline_loop_headers,
    normalize_workout_percent_ranges,
)
from rps.agents.tasks import AgentTask
from rps.workspace.schema_registry import SchemaRegistry, validate_or_raise


def test_normalize_phase_guardrails_recovery_rules_and_band_order() -> None:
    document = {
        "meta": {"artifact_type": "PHASE_GUARDRAILS"},
        "data": {
            "execution_non_negotiables": {"recovery_protection_rules": ["rest day", "sleep"]},
            "load_guardrails": {"weekly_kj_bands": [{"band": {"min": 8000, "max": 6200}}]},
        },
    }

    normalized = normalize_phase_guardrails_document(document)

    assert normalized["data"]["execution_non_negotiables"]["recovery_protection_rules"] == "rest day | sleep"
    assert normalized["data"]["load_guardrails"]["weekly_kj_bands"][0]["band"] == {"min": 6200.0, "max": 8000.0}


def test_normalize_phase_guardrails_projects_season_constraints() -> None:
    document = {
        "meta": {"artifact_type": "PHASE_GUARDRAILS"},
        "data": {
            "phase_summary": {
                "non_negotiables": ["Exact phase range is 2026-21--2026-23."],
                "key_risks_warnings": ["Do not drift into threshold or VO2MAX work."],
            },
            "events_constraints": {"events": []},
            "execution_non_negotiables": {
                "recovery_protection_rules": "Respect locked rest days.",
            },
            "load_guardrails": {"weekly_kj_bands": []},
        },
    }
    season_plan = {
        "data": {
            "global_constraints": {
                "availability_assumptions": [
                    "Weekly availability is bounded by min 10.5 h, typical 14.0 h, max 17.5 h.",
                    "Fixed rest days are Monday and Friday.",
                ],
                "risk_constraints": [
                    "Moderate fatigue accumulation may blunt one or two key weeks if recovery is underestimated.",
                ],
                "planned_event_windows": [
                    "2026-15 B Brevet 200 km Toelzer-Land-Runde",
                    "2026-05-16 (A)",
                ],
                "recovery_protection": {
                    "notes": [
                        "Respect the locked rest days as hard recovery boundaries.",
                        "Use the shortened phases to restore continuity before the full build.",
                    ]
                },
            }
        }
    }

    normalized = normalize_phase_guardrails_document(
        document,
        season_plan_document=season_plan,
    )

    non_negotiables = normalized["data"]["phase_summary"]["non_negotiables"]
    assert "Weekly availability is bounded by min 10.5 h, typical 14.0 h, max 17.5 h." in non_negotiables
    assert "Fixed rest days are Monday and Friday." in non_negotiables
    assert "2026-15 B Brevet 200 km Toelzer-Land-Runde" in non_negotiables
    assert (
        "Moderate fatigue accumulation may blunt one or two key weeks if recovery is underestimated."
        in normalized["data"]["phase_summary"]["key_risks_warnings"]
    )
    recovery_rules = normalized["data"]["execution_non_negotiables"]["recovery_protection_rules"]
    assert "Respect locked rest days." in recovery_rules
    assert "Respect the locked rest days as hard recovery boundaries." in recovery_rules
    assert "Use the shortened phases to restore continuity before the full build." in recovery_rules
    assert normalized["data"]["events_constraints"]["events"] == [
        {
            "date": "2026-05-16",
            "week": "2026-20",
            "type": "A",
            "constraint": "Planned season event window preserved from season_plan: 2026-05-16 (A)",
        }
    ]


def test_normalize_phase_structure_projects_constraints_and_guardrails_source() -> None:
    document = {
        "meta": {"artifact_type": "PHASE_STRUCTURE"},
        "data": {
            "upstream_intent": {
                "constraints": ["Do not widen the phase beyond 2026-21--2026-23."],
            },
            "load_ranges": {"source": "Deterministic Load Capacity Context"},
        },
    }
    season_plan = {
        "data": {
            "global_constraints": {
                "availability_assumptions": [
                    "Weekly availability is bounded by min 10.5 h, typical 14.0 h, max 17.5 h.",
                ],
                "risk_constraints": [
                    "Moderate fatigue accumulation may blunt one or two key weeks if recovery is underestimated.",
                ],
                "planned_event_windows": ["2026-15 B Brevet 200 km Toelzer-Land-Runde"],
                "recovery_protection": {
                    "notes": ["Respect the locked rest days as hard recovery boundaries."]
                },
            }
        }
    }
    phase_guardrails = {
        "data": {
            "load_guardrails": {
                "weekly_kj_bands": [
                    {"week": "2026-21", "band": {"min": 7329, "max": 8372, "notes": "x"}}
                ]
            }
        }
    }

    normalized = normalize_phase_structure_document(
        document,
        season_plan_document=season_plan,
        phase_guardrails_document=phase_guardrails,
        phase_guardrails_version_key="2026-21--2026-23__20260520_094539",
    )

    assert normalized["data"]["upstream_intent"]["constraints"] == [
        "Do not widen the phase beyond 2026-21--2026-23.",
        "Weekly availability is bounded by min 10.5 h, typical 14.0 h, max 17.5 h.",
        "Moderate fatigue accumulation may blunt one or two key weeks if recovery is underestimated.",
        "Respect the locked rest days as hard recovery boundaries.",
        "2026-15 B Brevet 200 km Toelzer-Land-Runde",
    ]
    assert normalized["data"]["load_ranges"]["weekly_kj_bands"] == [
        {"week": "2026-21", "band": {"min": 7329, "max": 8372, "notes": "x"}}
    ]
    assert (
        normalized["data"]["load_ranges"]["source"]
        == "phase_guardrails_2026-21--2026-23__20260520_094539.json"
    )


def test_normalize_phase_structure_preserves_exact_phase_legality() -> None:
    document = {
        "meta": {"artifact_type": "PHASE_STRUCTURE", "iso_week_range": "2026-24--2026-25"},
        "data": {
            "structural_phase_elements": {
                "allowed_day_roles": ["REST", "RECOVERY", "ENDURANCE", "QUALITY"],
                "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
                "allowed_load_modalities": ["NONE", "K3"],
            }
        },
    }
    season_plan = {
        "data": {
            "phases": [
                {
                    "iso_week_range": "2026-24--2026-25",
                    "allowed_forbidden_semantics": {
                        "allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
                        "allowed_load_modalities": ["NONE"],
                        "forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
                    }
                }
            ]
        }
    }

    normalized = normalize_phase_structure_document(document, season_plan_document=season_plan)

    assert normalized["data"]["structural_phase_elements"]["allowed_intensity_domains"] == [
        "RECOVERY",
        "ENDURANCE",
        "TEMPO",
        "SWEET_SPOT",
    ]
    assert "NONE" not in normalized["data"]["structural_phase_elements"]["allowed_intensity_domains"]


def test_normalize_phase_preview_repairs_traceability_rest_days_and_quality_cap() -> None:
    document = {
        "meta": {"artifact_type": "PHASE_PREVIEW"},
        "data": {
            "traceability": {"derived_from": ["Season plan version 2026-21__20260520_084154"]},
            "weekly_agenda_preview": [
                {
                    "week": "2026-22",
                    "days": [
                        {"day_of_week": "Mon", "day_role": "REST", "intensity_domain": "TEMPO", "load_modality": "K3", "notes": "wrong"},
                        {"day_of_week": "Tue", "day_role": "QUALITY", "intensity_domain": "ENDURANCE", "load_modality": "NONE", "notes": "ok"},
                        {"day_of_week": "Wed", "day_role": "QUALITY", "intensity_domain": "TEMPO", "load_modality": "NONE", "notes": "ok"},
                        {"day_of_week": "Thu", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE", "notes": "ok"},
                        {"day_of_week": "Fri", "day_role": "REST", "intensity_domain": "SWEET_SPOT", "load_modality": "K3", "notes": "wrong"},
                        {"day_of_week": "Sat", "day_role": "QUALITY", "intensity_domain": "SWEET_SPOT", "load_modality": "NONE", "notes": "excess"},
                        {"day_of_week": "Sun", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE", "notes": "ok"},
                    ],
                }
            ],
        },
    }
    phase_structure = {
        "data": {
            "structural_phase_elements": {
                "allowed_day_roles": ["REST", "RECOVERY", "ENDURANCE", "QUALITY"],
                "allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
                "allowed_load_modalities": ["NONE"],
            },
            "execution_principles": {
                "load_intensity_handling": {"max_quality_days_per_week": 2},
                "recovery_protection": {"fixed_non_training_days": ["Mon", "Fri"]},
            },
        }
    }

    normalized = normalize_phase_preview_document(
        document,
        phase_structure_document=phase_structure,
        phase_structure_version_key="2026-21--2026-23__20260520_112942",
    )

    assert (
        "phase_structure_2026-21--2026-23__20260520_112942.json"
        in normalized["data"]["traceability"]["derived_from"]
    )
    days = normalized["data"]["weekly_agenda_preview"][0]["days"]
    assert days[0]["intensity_domain"] == "NONE"
    assert days[0]["load_modality"] == "NONE"
    assert days[4]["intensity_domain"] == "NONE"
    assert days[4]["load_modality"] == "NONE"
    assert days[5]["day_role"] == "ENDURANCE"
    assert days[5]["intensity_domain"] == "ENDURANCE"
    assert "inherited_scenario_contract" not in normalized["data"]


def test_extract_planning_events_document_parses_workspace_payload() -> None:
    payload = {"ok": True, "content": '{"data":{"events":[{"type":"A","date":"2026-05-10"}]}}'}
    parsed = extract_planning_events_document(payload)
    assert parsed == {"data": {"events": [{"type": "A", "date": "2026-05-10"}]}}


def test_normalize_season_scenarios_derives_horizon_from_events() -> None:
    document = {
        "meta": {"artifact_type": "SEASON_SCENARIOS", "iso_week": "2026-19", "trace_events": [], "trace_data": []},
        "data": {
            "planning_horizon_weeks": 1,
            "scenarios": [
                {
                    "scenario_id": "S1",
                    "scenario_guidance": {"deload_cadence": "3:1", "intensity_guidance": {"allowed_domains": ["ENDURANCE"], "avoid_domains": ["NONE", "THRESHOLD"]}},
                }
            ],
        },
    }
    events = {"data": {"events": [{"type": "A", "date": "2026-06-14"}]}}

    normalized = normalize_season_scenarios_document(document, planning_events_document=events)

    assert normalized["meta"]["iso_week_range"] == "2026-19--2026-24"
    assert normalized["data"]["planning_horizon_weeks"] == 6
    guidance = normalized["data"]["scenarios"][0]["scenario_guidance"]
    assert guidance["intensity_guidance"]["allowed_domains"] == ["ENDURANCE"]
    assert guidance["intensity_guidance"]["avoid_domains"] == ["THRESHOLD"]


def test_normalize_season_scenarios_repairs_agent_payload_for_schema() -> None:
    def _scenario(scenario_id: str, cadence: str) -> dict[str, object]:
        return {
            "scenario_id": scenario_id,
            "name": f"Scenario {scenario_id}",
            "core_idea": "Build durable readiness.",
            "load_philosophy": "Progress conservatively.",
            "risk_profile": "Moderate risk.",
            "key_differences": ["Uses deterministic cadence math.", "Keeps recovery explicit."],
            "best_suited_if": "The athlete wants reliable completion.",
            "typical_week_feel": "Structured but manageable.",
            "main_payoff": "More reliable execution.",
            "main_cost": "Less upside than the riskiest option.",
            "what_gets_prioritized": "Consistency and durability.",
            "what_gets_de_emphasized": "Unnecessary high-intensity escalation.",
            "scenario_guidance": {
                "recovery_margin": "medium",
                "fatigue_exposure": "moderate",
                "specificity_density": "controlled",
                "deload_cadence": cadence,
                "phase_length_weeks": 99,
                "event_alignment_notes": "Aligns to the target event.",
                "risk_flags": ["Watch cumulative fatigue."],
                "fixed_rest_days": ["Mon", "Fri"],
                "constraint_summary": ["Respect fixed rest days."],
                "kpi_guardrail_notes": ["Stay in sustainable endurance bands."],
                "decision_notes": ["Use as default if risk control matters."],
                "intensity_guidance": {
                    "allowed_domains": ["ENDURANCE", "TEMPO"],
                    "avoid_domains": ["NONE", "THRESHOLD"],
                },
                "assumptions": ["Availability is stable."],
                "unknowns": ["Late travel unknown."],
            },
        }

    document = {
        "meta": {
            "artifact_type": "SEASON_SCENARIOS",
            "schema_id": "Wrong",
            "schema_version": "2026-20",
            "version": "2026-20_A01",
            "authority": "Binding",
            "owner_agent": "Season-Planner",
            "run_id": "season_scenarios_2026-20_A01",
            "created_at": "2026-05-17T16:07:25Z",
            "scope": "Athlete: i150546",
            "iso_week": "2026-20",
            "iso_week_range": "2026-20--2026-37",
            "temporal_scope": {"from": "2026-05-11", "to": "2026-09-13"},
            "trace_upstream": [
                "athlete_profile.ui_athlete_profile_20260315T091949Z",
                "planning_events.ui_planning_events_20260504T094650Z",
                "athlete_state_snapshot_2026-20__20260517_160725.json",
            ],
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "UNKNOWN",
            "notes": [],
        },
        "data": {
            "kpi_profile_ref": "kpi_profile.latest",
            "athlete_profile_ref": "athlete_profile.ui_athlete_profile_20260315T091949Z",
            "planning_horizon_weeks": 18,
            "notes": "Agent emitted a scalar note.",
            "scenarios": [_scenario("A", "2:1"), _scenario("B", "3:1"), _scenario("C", "2:1:1")],
        },
    }

    normalized = normalize_season_scenarios_document(document)

    assert normalized["meta"]["version"] == "1.0"
    assert normalized["meta"]["scope"] == "Season"
    assert normalized["meta"]["schema_id"] == "SeasonScenariosInterface"
    assert normalized["meta"]["schema_version"] == "1.0"
    assert normalized["meta"]["authority"] == "Informational"
    assert normalized["meta"]["owner_agent"] == "Season-Scenario-Agent"
    assert all(isinstance(entry, dict) for entry in normalized["meta"]["trace_upstream"])
    assert isinstance(normalized["data"]["notes"], list)
    assert all(isinstance(scenario["key_differences"], str) for scenario in normalized["data"]["scenarios"])
    assert all(isinstance(scenario["typical_week_feel"], str) for scenario in normalized["data"]["scenarios"])
    assert all(isinstance(scenario["main_payoff"], str) for scenario in normalized["data"]["scenarios"])

    registry = SchemaRegistry(Path("specs/schemas"))
    validate_or_raise(registry.validator_for("season_scenarios.schema.json"), normalized)


def test_injection_mode_for_tasks_is_single_mode_only() -> None:
    assert injection_mode_for_tasks([AgentTask.CREATE_PHASE_GUARDRAILS]) == "phase_guardrails"
    assert injection_mode_for_tasks([AgentTask.CREATE_PHASE_GUARDRAILS, AgentTask.CREATE_WEEK_PLAN]) is None


def test_normalize_workout_percent_ranges_repairs_missing_middle_percent() -> None:
    assert normalize_workout_percent_ranges("- 3h44m 68-72% 85-90rpm") == "- 3h44m 68%-72% 85-90rpm"


def test_normalize_workout_inline_loop_headers_splits_inline_repeat_step() -> None:
    assert normalize_workout_inline_loop_headers("- 3x 12m 80%-84% 88-94rpm") == "3x\n- 12m 80%-84% 88-94rpm"


def test_normalize_workout_inline_loop_headers_preserves_non_loop_step() -> None:
    text = "- 12m 80%-84% 88-94rpm"
    assert normalize_workout_inline_loop_headers(text) == text
