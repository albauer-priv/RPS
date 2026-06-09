from typing import Any

from rps.planning.season_selection_binding import (
    REASON_SCENARIOS_MISSING,
    REASON_SELECTED_SCENARIO_CONTRACT_INCOMPLETE,
    REASON_SELECTED_SCENARIO_STRUCTURE_MISSING,
    REASON_SELECTED_SCENARIO_UNRESOLVED,
    REASON_SELECTION_MISSING,
    REASON_SELECTION_STALE,
    resolve_bound_season_selection,
)

JsonMap = dict[str, Any]


def _scenario_payload(*, version_key: str = "2026-22__20260528_084859") -> JsonMap:
    return {
        "meta": {
            "artifact_type": "SEASON_SCENARIOS",
            "version_key": version_key,
            "run_id": "scenarios-run",
        },
        "data": {
            "planning_horizon_weeks": 16,
            "scenarios": [
                {
                    "scenario_id": "B",
                    "name": "Balanced build",
                    "load_philosophy": "balanced_progressive",
                    "risk_profile": "medium",
                    "best_suited_if": "Stable recovery and repeatable load.",
                    "key_differences": "Balances progression and freshness.",
                    "main_payoff": "Repeatable progression",
                    "main_cost": "Less conservative than scenario A",
                    "scenario_guidance": {
                        "recovery_margin": "medium",
                        "fatigue_exposure": "moderate",
                        "specificity_density": "controlled",
                        "constraint_summary": ["Preserve continuity and legal domains."],
                        "event_alignment_notes": ["B-event rehearsal stays inside build."],
                        "risk_flags": ["Needs stable recovery."],
                        "kpi_guardrail_notes": ["Stay repeatable."],
                        "decision_notes": ["Chosen for balanced progression."],
                        "deload_cadence": "2:1:1",
                        "phase_length_weeks": 4,
                        "phase_count_expected": 4,
                        "phase_plan_summary": {"full_phases": 4, "shortened_phases": []},
                        "max_shortened_phases": 0,
                        "shortening_budget_weeks": 0,
                        "intensity_guidance": {
                            "allowed_domains": ["ENDURANCE", "TEMPO"],
                            "avoid_domains": ["VO2MAX"],
                        },
                    },
                }
            ],
        },
    }


def _selection_payload(*, version_key: str = "2026-22__20260528_084939", scenarios_version_key: str) -> JsonMap:
    return {
        "meta": {
            "artifact_type": "SEASON_SCENARIO_SELECTION",
            "version_key": version_key,
            "run_id": "selection-run",
            "trace_upstream": [
                {
                    "artifact": "SEASON_SCENARIOS",
                    "version": scenarios_version_key,
                    "version_key": scenarios_version_key,
                    "run_id": "scenarios-run",
                }
            ],
        },
        "data": {
            "season_scenarios_ref": scenarios_version_key,
            "selected_scenario_id": "B",
            "selection_source": "user",
            "selection_rationale": "Balanced choice",
            "notes": ["Selected in UI."],
            "kpi_moving_time_rate_guidance_selection": None,
        },
    }


def test_resolve_bound_season_selection_success() -> None:
    scenarios = _scenario_payload()
    selection = _selection_payload(scenarios_version_key=str(scenarios["meta"]["version_key"]))

    result = resolve_bound_season_selection(
        season_scenarios_payload=scenarios,
        selection_payload=selection,
    )

    assert result["ok"] is True
    assert result["reason_code"] == "ready"
    assert result["selected_scenario_id"] == "B"
    assert result["selected_scenario_contract"]["load_posture"] == "balanced_progressive"
    assert result["selected_scenario_contract"]["constraint_summary"] == ["Preserve continuity and legal domains."]


def test_resolve_bound_season_selection_missing_selection() -> None:
    result = resolve_bound_season_selection(
        season_scenarios_payload=_scenario_payload(),
        selection_payload={},
    )

    assert result["ok"] is False
    assert result["reason_code"] == REASON_SELECTION_MISSING


def test_resolve_bound_season_selection_missing_scenarios() -> None:
    result = resolve_bound_season_selection(
        season_scenarios_payload={},
        selection_payload=_selection_payload(scenarios_version_key="2026-22__20260528_084859"),
    )

    assert result["ok"] is False
    assert result["reason_code"] == REASON_SCENARIOS_MISSING


def test_resolve_bound_season_selection_detects_stale_selection() -> None:
    result = resolve_bound_season_selection(
        season_scenarios_payload=_scenario_payload(version_key="2026-22__new"),
        selection_payload=_selection_payload(scenarios_version_key="2026-22__old"),
    )

    assert result["ok"] is False
    assert result["reason_code"] == REASON_SELECTION_STALE


def test_resolve_bound_season_selection_detects_unresolved_selected_scenario() -> None:
    scenarios = _scenario_payload()
    selection = _selection_payload(scenarios_version_key=str(scenarios["meta"]["version_key"]))
    selection["data"]["selected_scenario_id"] = "C"

    result = resolve_bound_season_selection(
        season_scenarios_payload=scenarios,
        selection_payload=selection,
    )

    assert result["ok"] is False
    assert result["reason_code"] == REASON_SELECTED_SCENARIO_UNRESOLVED


def test_resolve_bound_season_selection_detects_incomplete_contract() -> None:
    scenarios = _scenario_payload()
    scenario = scenarios["data"]["scenarios"][0]
    scenario["scenario_guidance"].pop("constraint_summary")
    selection = _selection_payload(scenarios_version_key=str(scenarios["meta"]["version_key"]))

    result = resolve_bound_season_selection(
        season_scenarios_payload=scenarios,
        selection_payload=selection,
    )

    assert result["ok"] is False
    assert result["reason_code"] == REASON_SELECTED_SCENARIO_CONTRACT_INCOMPLETE
    assert "constraint_summary" in str(result["reason_message"])


def test_resolve_bound_season_selection_detects_missing_structure() -> None:
    scenarios = _scenario_payload()
    scenario = scenarios["data"]["scenarios"][0]
    scenario["scenario_guidance"].pop("deload_cadence")
    selection = _selection_payload(scenarios_version_key=str(scenarios["meta"]["version_key"]))

    result = resolve_bound_season_selection(
        season_scenarios_payload=scenarios,
        selection_payload=selection,
    )

    assert result["ok"] is False
    assert result["reason_code"] == REASON_SELECTED_SCENARIO_STRUCTURE_MISSING
