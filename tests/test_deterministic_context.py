from types import SimpleNamespace

from rps.planning.deterministic_context import (
    LoadCapacityContext,
    PhaseExecutionContext,
    PhaseExecutionResolution,
    WeekCalendarContext,
    WeekDayContext,
    _resolve_phase_execution_roles,
    build_load_capacity_block,
    build_phase_execution_context,
    build_week_calendar_context,
)
from rps.workspace.iso_helpers import IsoWeek, IsoWeekRange


def test_resolve_phase_execution_roles_prefers_active_slot_values() -> None:
    resolution = _resolve_phase_execution_roles(
        weeks=[IsoWeek(2026, 12), IsoWeek(2026, 13), IsoWeek(2026, 14)],
        active_slot={
            "scenario_cadence": "2:1",
            "cadence_week_roles": ["LOAD_1", "LOAD_2", "DELOAD"],
        },
        phase_raw={},
    )

    assert resolution.scenario_cadence == "2:1"
    assert resolution.cadence_week_roles == ("LOAD_1", "LOAD_2", "DELOAD")
    assert resolution.week_role_by_iso_week == {
        "2026-12": "LOAD_1",
        "2026-13": "LOAD_2",
        "2026-14": "DELOAD",
    }
    assert resolution.blocking_issues == ()
    assert resolution.used_fallbacks == ()


def test_resolve_phase_execution_roles_falls_back_to_phase_raw_and_pattern() -> None:
    resolution = _resolve_phase_execution_roles(
        weeks=[IsoWeek(2026, 12), IsoWeek(2026, 13), IsoWeek(2026, 14)],
        active_slot={},
        phase_raw={"scenario_cadence": "2:1"},
    )

    assert resolution.scenario_cadence == "2:1"
    assert resolution.cadence_week_roles == ("LOAD_1", "LOAD_2", "DELOAD")
    assert resolution.used_fallbacks == (
        "scenario_cadence_from_phase_raw",
        "cadence_week_roles_from_cadence_pattern",
    )
    assert resolution.blocking_issues == ()


def test_resolve_phase_execution_roles_falls_back_to_phase_raw_roles() -> None:
    resolution = _resolve_phase_execution_roles(
        weeks=[IsoWeek(2026, 12), IsoWeek(2026, 13), IsoWeek(2026, 14)],
        active_slot={},
        phase_raw={
            "deload_cadence": "2:1",
            "cadence_week_roles": ["LOAD_1", "LOAD_2", "DELOAD"],
        },
    )

    assert resolution.scenario_cadence == "2:1"
    assert resolution.cadence_week_roles == ("LOAD_1", "LOAD_2", "DELOAD")
    assert resolution.used_fallbacks == (
        "scenario_cadence_from_phase_raw",
        "cadence_week_roles_from_phase_raw",
    )
    assert resolution.blocking_issues == ()


def test_resolve_phase_execution_roles_reports_unsupported_cadence() -> None:
    resolution = _resolve_phase_execution_roles(
        weeks=[IsoWeek(2026, 12), IsoWeek(2026, 13), IsoWeek(2026, 14)],
        active_slot={},
        phase_raw={"scenario_cadence": "9:9"},
    )

    assert resolution.scenario_cadence == "9:9"
    assert resolution.cadence_week_roles == ()
    assert resolution.used_fallbacks == ("scenario_cadence_from_phase_raw",)
    assert resolution.blocking_issues == (
        "phase cadence week roles do not cover every phase week.",
        "scenario cadence is unsupported for deterministic phase roles.",
    )


def test_resolve_phase_execution_roles_reports_role_count_mismatch() -> None:
    resolution = _resolve_phase_execution_roles(
        weeks=[IsoWeek(2026, 12), IsoWeek(2026, 13), IsoWeek(2026, 14)],
        active_slot={
            "scenario_cadence": "2:1",
            "cadence_week_roles": ["LOAD_1", "LOAD_2"],
        },
        phase_raw={},
    )

    assert resolution.scenario_cadence == "2:1"
    assert resolution.cadence_week_roles == ("LOAD_1", "LOAD_2")
    assert resolution.week_role_by_iso_week == {
        "2026-12": "LOAD_1",
        "2026-13": "LOAD_2",
    }
    assert resolution.used_fallbacks == ()
    assert resolution.blocking_issues == (
        "phase cadence week roles do not cover every phase week.",
    )


def test_phase_execution_context_to_payload_projects_public_lists() -> None:
    payload = PhaseExecutionContext(
        target_iso_week="2026-12",
        phase_id="P01",
        phase_index=1,
        phase_iso_week_range="2026-12--2026-14",
        phase_length_weeks=3,
        week_keys=("2026-12", "2026-13", "2026-14"),
        week_index_within_phase=1,
        phase_type="BUILD",
        phase_role="BUILD",
        phase_intent="durability_build",
        build_subtype="durability_build",
        phase_allowed_intensity_domains=("ENDURANCE", "TEMPO"),
        phase_forbidden_intensity_domains=("VO2MAX",),
        phase_allowed_load_modalities=("NONE",),
        phase_role_week_load_bands=({"week": "2026-12", "role": "LOAD_1", "band": {"min": 1, "max": 2}},),
        phase_primary_objective="Build durable load.",
        objective_mismatch_warning=None,
        resolution=PhaseExecutionResolution(
            scenario_cadence="2:1",
            cadence_week_roles=("LOAD_1", "LOAD_2", "DELOAD"),
            week_role_by_iso_week={"2026-12": "LOAD_1", "2026-13": "LOAD_2", "2026-14": "DELOAD"},
            blocking_issues=(),
            used_fallbacks=("scenario_cadence_from_phase_raw",),
        ),
        selected_scenario_contract={"selected_scenario_id": "B"},
        season_phase_slot={"phase_id": "P01"},
        deload_intent=False,
        deload_rationale="planned",
        target_week_s5_band={"min": 10, "max": 20},
        target_week_s5_trace={"source": "test"},
        phase_s5_bands=({"week": "2026-12", "band": {"min": 10, "max": 20}},),
        phase_week_skeleton=({"week": "2026-12", "days": []},),
        fixed_rest_days=("Mon", "Fri"),
        logistics_in_phase=({"date": "2026-03-16", "type": "TRAVEL"},),
        events_in_phase=({"date": "2026-03-17", "type": "B", "name": "Spring 200"},),
    ).to_payload()

    assert payload["week_keys"] == ["2026-12", "2026-13", "2026-14"]
    assert payload["phase_cadence_week_roles"] == ["LOAD_1", "LOAD_2", "DELOAD"]
    assert payload["phase_allowed_intensity_domains"] == ["ENDURANCE", "TEMPO"]
    assert payload["fixed_rest_days"] == ["Mon", "Fri"]
    assert payload["blocking_issues"] == []


def test_build_phase_execution_context_remains_dict_compatible() -> None:
    context = build_phase_execution_context(
        target_week=IsoWeek(2026, 12),
        phase_info=SimpleNamespace(
            phase_id="P01",
            phase_type="BUILD",
            raw={
                "phase_type": "BUILD",
                "phase_intent": "durability_build",
                "build_subtype": "durability_build",
                "allowed_forbidden_semantics": {
                    "allowed_intensity_domains": ["ENDURANCE", "TEMPO"],
                    "forbidden_intensity_domains": ["VO2MAX"],
                    "allowed_load_modalities": ["NONE"],
                },
                "role_week_load_bands": [{"week": "2026-12", "role": "LOAD_1", "band": {"min": 1, "max": 2}}],
                "overview": {"phase_goals": {"primary": "Build durable load."}},
                "deload": False,
                "deload_rationale": "planned",
            },
        ),
        phase_range=IsoWeekRange(start=IsoWeek(2026, 12), end=IsoWeek(2026, 14)),
        season_plan_payload={
            "data": {
                "phases": [{"phase_id": "P01"}],
                "selected_scenario_contract": {"selected_scenario_id": "B", "load_posture": "balanced_progressive"},
                "season_intent_principles": {"season_objective": "Ride 200 km well"},
            }
        },
        phase_slot_context={
            "phase_slots": [
                {
                    "phase_id": "P01",
                    "iso_week_range": "2026-12--2026-14",
                    "scenario_cadence": "2:1",
                    "cadence_week_roles": ["LOAD_1", "LOAD_2", "DELOAD"],
                }
            ]
        },
        availability_payload={"data": {"fixed_rest_days": ["Mon", "Fri"]}},
        logistics_payload={"data": {"events": []}},
        planning_events_payload={"data": {"events": []}},
        load_capacity_context={
            "s5_bands": [
                {"week": "2026-12", "band": {"min": 10, "max": 20}, "trace": {"source": "test"}},
                {"week": "2026-13", "band": {"min": 11, "max": 21}},
                {"week": "2026-14", "band": {"min": 12, "max": 22}},
            ]
        },
    )

    assert isinstance(context, dict)
    assert context["phase_cadence_week_roles"] == ["LOAD_1", "LOAD_2", "DELOAD"]
    assert context["week_role_by_iso_week"] == {
        "2026-12": "LOAD_1",
        "2026-13": "LOAD_2",
        "2026-14": "DELOAD",
    }
    assert context["fixed_rest_days"] == ["Mon", "Fri"]
    assert context["blocking_issues"] == []


def test_week_calendar_context_to_payload_projects_public_lists() -> None:
    payload = WeekCalendarContext(
        target_iso_week="2026-21",
        week_start_date="2026-05-18",
        week_end_date="2026-05-24",
        phase_id="P01",
        phase_iso_week_range="2026-20--2026-22",
        phase_cycle="Build",
        phase_role="Build",
        phase_intent="durability_build",
        phase_week_role="LOAD_2",
        inherited_planning_posture={"selected_scenario_id": "B"},
        phase_role_for_week="LOAD_2",
        phase_week_role_source="PHASE_STRUCTURE.week_skeleton_logic.week_roles",
        day_matrix=(
            WeekDayContext(
                day="Mon",
                date="2026-05-18",
                fixed_rest_day=True,
                availability_min=1,
                availability_typical=2,
                availability_max=3,
                logistics=({"date": "2026-05-18", "type": "TRAVEL"},),
                events=({"date": "2026-05-18", "type": "B", "name": "Spring 200"},),
            ),
        ),
        fixed_rest_days=("Mon", "Fri"),
        active_s5_band={"min": 1000, "max": 2000},
        active_s5_trace={"source": "test"},
        phase_weekly_kj_band={"min": 1000, "max": 2000},
        active_weekly_kj_band={"min": 1000, "max": 2000},
        allowed_day_roles=("REST", "ENDURANCE", "QUALITY"),
        forbidden_day_roles=(),
        allowed_intensity_domains=("ENDURANCE", "TEMPO"),
        forbidden_intensity_domains=("THRESHOLD",),
        allowed_load_modalities=("NONE",),
        quality_day_cap=1,
        target_week_skeleton={"days": []},
        week_skeleton_mandatory_elements={"recovery_opportunities_min": 2},
        event_proximity={"weeks_delta": 0},
    ).to_payload()

    assert payload["fixed_rest_days"] == ["Mon", "Fri"]
    assert payload["allowed_day_roles"] == ["REST", "ENDURANCE", "QUALITY"]
    assert payload["allowed_intensity_domains"] == ["ENDURANCE", "TEMPO"]
    assert payload["day_matrix"][0]["availability_hours"] == {"min": 1, "typical": 2, "max": 3}
    assert payload["day_matrix"][0]["events"] == [{"date": "2026-05-18", "type": "B", "name": "Spring 200"}]


def test_build_week_calendar_context_remains_dict_compatible() -> None:
    phase_info = SimpleNamespace(phase_id="P01", phase_type="Build", raw={"cycle": "Build"})
    context = build_week_calendar_context(
        target_week=IsoWeek(2026, 21),
        phase_info=phase_info,
        phase_range=IsoWeekRange(start=IsoWeek(2026, 20), end=IsoWeek(2026, 22)),
        availability_payload={
            "data": {
                "fixed_rest_days": ["Mon", "Fri"],
                "availability_table": [
                    {"weekday": "Mon", "hours_min": 1, "hours_typical": 2, "hours_max": 3},
                ],
            }
        },
        logistics_payload={"data": {"events": [{"date": "2026-05-18", "event_type": "TRAVEL", "description": "Trip"}]}},
        planning_events_payload={"data": {"events": [{"date": "2026-05-18", "type": "B", "event_name": "Spring 200"}]}},
        phase_structure_payload={
            "data": {
                "execution_principles": {"phase_role": "Build"},
                "week_skeleton_logic": {
                    "week_roles": {
                        "week_roles": [
                            {"week": "2026-20", "role": "LOAD_1"},
                            {"week": "2026-21", "role": "LOAD_2"},
                            {"week": "2026-22", "role": "DELOAD"},
                        ]
                    },
                    "mandatory_elements": {"recovery_opportunities_min": 2},
                },
                "inherited_scenario_contract": {"selected_scenario_id": "B"},
            }
        },
        phase_guardrails_payload={
            "data": {
                "load_guardrails": {
                    "weekly_kj_bands": [{"week": "2026-21", "band": {"min": 1000, "max": 2000}}]
                },
                "allowed_forbidden_semantics": {
                    "allowed_day_roles": ["REST", "ENDURANCE", "QUALITY"],
                    "forbidden_day_roles": [],
                    "allowed_intensity_domains": ["ENDURANCE", "TEMPO"],
                    "forbidden_intensity_domains": ["THRESHOLD"],
                    "allowed_load_modalities": ["NONE"],
                    "quality_density": {"max_quality_days_per_week": 1},
                },
                "inherited_scenario_contract": {"selected_scenario_id": "B"},
            }
        },
        load_capacity_context={
            "s5_bands": [{"week": "2026-21", "band": {"min": 1200, "max": 2200}, "trace": {"source": "test"}}]
        },
    )

    assert isinstance(context, dict)
    assert context["phase_week_role"] == "LOAD_2"
    assert context["phase_week_role_source"] == "PHASE_STRUCTURE.week_skeleton_logic.week_roles"
    assert context["active_weekly_kj_band"] == {"min": 1000, "max": 2000}
    assert context["quality_day_cap"] == 1
    assert context["fixed_rest_days"] == ["Mon", "Fri"]
    assert context["day_matrix"][0]["day"] == "Mon"


def test_load_capacity_context_to_payload_detaches_nested_payload() -> None:
    original = {
        "allowed_intensity_domains": ["ENDURANCE", "TEMPO"],
        "s5_bands": [{"week": "2026-20", "band": {"min": 1000, "max": 2000}}],
        "warnings": ["none"],
    }

    payload = LoadCapacityContext(payload=original).to_payload()

    assert payload == original
    assert payload is not original
    assert payload["allowed_intensity_domains"] is not original["allowed_intensity_domains"]
    assert payload["s5_bands"] is not original["s5_bands"]


def test_build_load_capacity_block_remains_payload_compatible() -> None:
    block = build_load_capacity_block(
        target_week=IsoWeek(2026, 20),
        athlete_profile_payload={"data": {"profile": {"endurance_anchor_w": 204, "body_mass_kg": 75}}},
        availability_payload={"data": {"weekly_hours": {"min": 6, "typical": 8, "max": 10}}},
        zone_model_payload={"data": {"model_metadata": {"ftp_watts": 300}, "zones": [{"zone_id": "Z2", "typical_if": 0.66}]}},
        season_allowed_intensity_domains=["ENDURANCE", "TEMPO"],
    )

    assert block.name == "load_capacity"
    assert block.title == "Deterministic Load Capacity Context"
    assert isinstance(block.payload, dict)
    assert block.payload["allowed_intensity_domains"] == ["ENDURANCE", "TEMPO"]
    assert block.payload["availability_load_capacity_kj"]["max"] > block.payload["availability_load_capacity_kj"]["min"]