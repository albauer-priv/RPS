from __future__ import annotations

from rps.planning.season_structure import (
    build_cadence_options_context,
    build_phase_slot_context,
    build_planning_horizon_context,
    build_selected_scenario_structure_context,
    render_cadence_options_block,
    render_phase_slot_context_block,
    render_planning_horizon_context_block,
    render_selected_scenario_structure_block,
)
from rps.workspace.iso_helpers import IsoWeek


def test_selected_scenario_structure_context_derives_phase_math() -> None:
    context = build_selected_scenario_structure_context(
        season_scenarios_payload={
            "data": {
                "planning_horizon_weeks": 17,
                "scenarios": [
                    {
                        "scenario_id": "B",
                        "name": "Compact resilient build",
                        "intensity_guidance": {
                            "allowed_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                            "avoid_domains": ["VO2MAX"],
                        },
                        "scenario_guidance": {
                            "deload_cadence": "2:1",
                            "phase_length_weeks": 3,
                            "phase_count_expected": 6,
                            "max_shortened_phases": 2,
                            "shortening_budget_weeks": 1,
                            "phase_plan_summary": {
                                "full_phases": 5,
                                "shortened_phases": [{"len": 2, "count": 1}],
                            },
                            "event_alignment_notes": ["A-event backplanned."],
                            "risk_flags": ["Compressed horizon."],
                        },
                    }
                ],
            }
        },
        selection_payload={"data": {"selected_scenario_id": "B"}},
    )

    assert context["selected_scenario_id"] == "B"
    assert context["deload_cadence"] == "2:1"
    assert context["phase_length_weeks"] == 3
    assert context["phase_count_expected"] == 6
    assert context["full_phases"] == 5
    assert context["reconstructed_horizon_weeks"] == 17
    assert context["consistent_with_horizon"] is True
    assert context["allowed_intensity_domains"] == ["ENDURANCE", "TEMPO", "SWEET_SPOT"]
    assert "VO2MAX" in context["forbidden_intensity_domains"]


def test_selected_scenario_structure_block_renders_planning_reference() -> None:
    block = render_selected_scenario_structure_block(
        {
            "selected_scenario_id": "C",
            "scenario_name": "Reset reload",
            "planning_horizon_weeks": 16,
            "deload_cadence": "2:1:1",
            "phase_length_weeks": 4,
            "phase_count_expected": 4,
            "full_phases": 4,
            "shortening_budget_weeks": 0,
            "max_shortened_phases": 0,
            "reconstructed_horizon_weeks": 16,
            "consistent_with_horizon": True,
            "shortened_phases": [],
            "allowed_intensity_domains": ["ENDURANCE", "TEMPO"],
            "forbidden_intensity_domains": ["SWEET_SPOT", "THRESHOLD", "VO2MAX"],
        }
    )

    assert "**Deterministic Selected Scenario Structure Context**" in block
    assert "deload_cadence: 2:1:1" in block
    assert "phase_length_weeks: 4" in block
    assert "shortened_phases: none" in block
    assert "allowed_intensity_domains: ENDURANCE, TEMPO" in block


def test_planning_horizon_context_uses_latest_abc_event() -> None:
    context = build_planning_horizon_context(
        planning_events_payload={
            "data": {
                "events": [
                    {"type": "B", "event_name": "Spring 200", "date": "2026-03-18"},
                    {"type": "A", "event_name": "Main 400", "date": "2026-05-10"},
                ]
            }
        },
        target_week=IsoWeek(2026, 12),
    )

    assert context["target_week_start_date"] == "2026-03-16"
    assert context["last_event_date"] == "2026-05-10"
    assert context["last_event_iso_week"] == "2026-19"
    assert context["weeks_until_last_event_from_target_week_start"] == 7
    assert context["inclusive_planning_horizon_weeks"] == 8
    assert context["season_iso_week_range"] == "2026-12--2026-19"


def test_planning_horizon_context_block_renders_event_horizon() -> None:
    block = render_planning_horizon_context_block(
        {
            "target_iso_week": "2026-12",
            "target_week_start_date": "2026-03-16",
            "last_event_date": "2026-05-10",
            "last_event_iso_week": "2026-19",
            "last_event_type": "A",
            "last_event_name": "Main 400",
            "weeks_until_last_event_from_target_week_start": 7,
            "inclusive_planning_horizon_weeks": 8,
            "season_iso_week_range": "2026-12--2026-19",
            "temporal_scope": {"from": "2026-03-16", "to": "2026-05-10"},
        }
    )

    assert "**Deterministic Season Scenario Horizon Context**" in block
    assert "last_event_date: 2026-05-10" in block
    assert "inclusive_planning_horizon_weeks: 8" in block


def test_cadence_options_context_derives_supported_phase_math() -> None:
    context = build_cadence_options_context(
        planning_horizon_context={
            "inclusive_planning_horizon_weeks": 8,
            "season_iso_week_range": "2026-12--2026-19",
        }
    )

    assert context["planning_horizon_weeks"] == 8
    options = {item["deload_cadence"]: item for item in context["options"]}
    assert options["2:1"]["phase_length_weeks"] == 3
    assert options["2:1"]["phase_count_expected"] == 3
    assert options["2:1"]["full_phases"] == 2
    assert options["2:1"]["shortened_phases"] == [{"len": 2, "count": 1}]
    assert options["3:1"]["phase_length_weeks"] == 4
    assert options["3:1"]["phase_count_expected"] == 2
    assert options["3:1"]["full_phases"] == 2


def test_cadence_options_block_renders_phase_counts() -> None:
    block = render_cadence_options_block(
        {
            "planning_horizon_weeks": 8,
            "season_iso_week_range": "2026-12--2026-19",
            "options": [
                {
                    "deload_cadence": "2:1",
                    "phase_length_weeks": 3,
                    "phase_count_expected": 3,
                    "full_phases": 2,
                    "shortening_budget_weeks": 1,
                    "shortened_phases": [{"len": 2, "count": 1}],
                }
            ],
        }
    )

    assert "**Deterministic Cadence Options Context**" in block
    assert "cadence 2:1" in block
    assert "phase_count_expected 3" in block


def test_phase_slot_context_builds_shortened_first_then_full_slots() -> None:
    selected = build_selected_scenario_structure_context(
        season_scenarios_payload={
            "data": {
                "planning_horizon_weeks": 8,
                "scenarios": [
                    {
                        "scenario_id": "A",
                        "name": "Eight week build",
                        "scenario_guidance": {
                            "deload_cadence": "2:1",
                            "phase_length_weeks": 3,
                            "phase_count_expected": 3,
                            "phase_plan_summary": {
                                "full_phases": 2,
                                "shortened_phases": [{"len": 2, "count": 1}],
                            },
                        },
                    }
                ],
            }
        },
        selection_payload={"data": {"selected_scenario_id": "A"}},
    )
    context = build_phase_slot_context(
        selected_structure_context=selected,
        target_week=IsoWeek(2026, 12),
    )

    assert context["covered_weeks"] == 8
    assert context["coverage_matches_horizon"] is True
    assert [slot["phase_id"] for slot in context["phase_slots"]] == ["P01", "P02", "P03"]
    assert context["phase_slots"][0]["iso_week_range"] == "2026-12--2026-13"
    assert context["phase_slots"][0]["is_shortened"] is True
    assert context["phase_slots"][0]["scenario_cadence"] == "2:1"
    assert context["phase_slots"][0]["cadence_week_roles"] == [
        "SHORTENED_RE_ENTRY",
        "SHORTENED_CONSOLIDATION",
    ]
    assert context["phase_slots"][1]["iso_week_range"] == "2026-14--2026-16"
    assert context["phase_slots"][1]["cadence_week_roles"] == ["LOAD_1", "LOAD_2", "DELOAD"]
    assert context["phase_slots"][2]["iso_week_range"] == "2026-17--2026-19"


def test_phase_slot_context_derives_roles_from_selected_scenario_cadence() -> None:
    selected = build_selected_scenario_structure_context(
        season_scenarios_payload={
            "data": {
                "planning_horizon_weeks": 17,
                "scenarios": [
                    {
                        "scenario_id": "B",
                        "name": "Balanced inherited cadence",
                        "scenario_guidance": {
                            "deload_cadence": "2:1:1",
                            "phase_length_weeks": 4,
                            "phase_count_expected": 5,
                            "phase_plan_summary": {
                                "full_phases": 3,
                                "shortened_phases": [
                                    {"len": 3, "count": 1},
                                    {"len": 2, "count": 1},
                                ],
                            },
                        },
                    }
                ],
            }
        },
        selection_payload={"data": {"selected_scenario_id": "B"}},
    )

    context = build_phase_slot_context(
        selected_structure_context=selected,
        target_week=IsoWeek(2026, 21),
    )

    assert context["deload_cadence"] == "2:1:1"
    assert context["coverage_matches_horizon"] is True
    assert [slot["length_weeks"] for slot in context["phase_slots"]] == [3, 2, 4, 4, 4]
    assert context["phase_slots"][0]["cadence_week_roles"] == [
        "SHORTENED_RE_ENTRY",
        "SHORTENED_CONSOLIDATION",
        "SHORTENED_MINI_RESET",
    ]
    assert context["phase_slots"][1]["cadence_week_roles"] == [
        "SHORTENED_RE_ENTRY",
        "SHORTENED_CONSOLIDATION",
    ]
    assert context["phase_slots"][2]["cadence_week_roles"] == ["LOAD_1", "LOAD_2", "MINI_RESET", "RELOAD"]


def test_i150546_kw21_scenario_b_slots_keep_selected_scenario_authority() -> None:
    selected = build_selected_scenario_structure_context(
        season_scenarios_payload={
            "data": {
                "planning_horizon_weeks": 17,
                "scenarios": [
                    {
                        "scenario_id": "B",
                        "name": "Balanced Brevet-Specific Progression",
                        "scenario_guidance": {
                            "deload_cadence": "2:1:1",
                            "phase_length_weeks": 4,
                            "phase_count_expected": 5,
                            "shortening_budget_weeks": 3,
                            "phase_plan_summary": {
                                "full_phases": 3,
                                "shortened_phases": [
                                    {"len": 3, "count": 1},
                                    {"len": 2, "count": 1},
                                ],
                            },
                        },
                    }
                ],
            }
        },
        selection_payload={"data": {"selected_scenario_id": "B"}},
    )

    context = build_phase_slot_context(
        selected_structure_context=selected,
        target_week=IsoWeek(2026, 21),
    )

    assert context["deload_cadence"] == "2:1:1"
    assert context["phase_count_expected"] == 5
    assert [slot["iso_week_range"] for slot in context["phase_slots"]] == [
        "2026-21--2026-23",
        "2026-24--2026-25",
        "2026-26--2026-29",
        "2026-30--2026-33",
        "2026-34--2026-37",
    ]
    assert context["phase_slots"][-1]["cadence_week_roles"] == ["LOAD_1", "LOAD_2", "MINI_RESET", "RELOAD"]


def test_phase_slot_context_flags_inconsistent_selected_scenario_cadence() -> None:
    context = build_phase_slot_context(
        selected_structure_context={
            "selected_scenario_id": "B",
            "planning_horizon_weeks": 3,
            "deload_cadence": "2:1:1",
            "phase_length_weeks": 3,
            "phase_count_expected": 1,
            "full_phases": 1,
            "shortened_phases": [],
        },
        target_week=IsoWeek(2026, 21),
    )

    assert context["blocking_issues"] == [
        "Selected scenario phase_length_weeks does not match its inherited deload_cadence."
    ]


def test_phase_slot_context_block_renders_required_slots() -> None:
    block = render_phase_slot_context_block(
        {
            "selected_scenario_id": "A",
            "planning_horizon_weeks": 8,
            "deload_cadence": "2:1",
            "phase_length_weeks": 3,
            "phase_count_expected": 3,
            "covered_weeks": 8,
            "coverage_matches_horizon": True,
            "phase_slots": [
                {
                    "phase_id": "P01",
                    "iso_week_range": "2026-12--2026-13",
                    "length_weeks": 2,
                    "is_shortened": True,
                    "scenario_cadence": "2:1",
                    "cadence_week_roles": ["SHORTENED_RE_ENTRY", "SHORTENED_CONSOLIDATION"],
                    "week_keys": ["2026-12", "2026-13"],
                }
            ],
        }
    )

    assert "**Deterministic Season Phase Slot Context**" in block
    assert "P01: 2026-12--2026-13" in block
    assert "scenario_cadence 2:1" in block
    assert "cadence_week_roles SHORTENED_RE_ENTRY, SHORTENED_CONSOLIDATION" in block
