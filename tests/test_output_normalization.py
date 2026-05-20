from __future__ import annotations

from pathlib import Path

from rps.agents.output_normalization import (
    extract_planning_events_document,
    injection_mode_for_tasks,
    normalize_phase_guardrails_document,
    normalize_season_scenarios_document,
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
