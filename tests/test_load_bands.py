from __future__ import annotations

import pytest

from rps.planning.load_bands import (
    DEFAULT_IF_REF_LOAD,
    LoadBandError,
    NumberBand,
    build_load_capacity_context,
    build_season_phase_load_context,
    calculate_availability_feasible_band,
    calculate_kpi_capacity_band,
    calculate_progression_band,
    calculate_role_progression_band,
    derive_phase_s5_band,
    resolve_if_ref_load,
    selected_kpi_rate_band_from_selection,
)
from rps.workspace.iso_helpers import IsoWeek, IsoWeekRange


def _zone_model(ftp: float | None = 300.0, typical_if: float | None = 0.66) -> dict:
    metadata = {} if ftp is None else {"ftp_watts": ftp}
    zones = [] if typical_if is None else [{"zone_id": "Z2", "typical_if": typical_if}]
    return {"data": {"model_metadata": metadata, "zones": zones}}


def _rich_zone_model(ftp: float = 300.0) -> dict:
    return {
        "data": {
            "model_metadata": {"ftp_watts": ftp},
            "zones": [
                {"zone_id": "Z2", "typical_if": 0.68},
                {"zone_id": "Z3", "typical_if": 0.83},
                {"zone_id": "SS", "typical_if": 0.92},
                {"zone_id": "Z4", "typical_if": 0.98},
            ],
        }
    }


def test_resolve_if_ref_load_prefers_athlete_anchor() -> None:
    profile = {"data": {"profile": {"endurance_anchor_w": 210}}}

    resolved = resolve_if_ref_load(athlete_profile_payload=profile, zone_model_payload=_zone_model(300))

    assert resolved.source == "ATHLETE_PROFILE_ANCHOR"
    assert resolved.value == pytest.approx(0.70)


def test_resolve_if_ref_load_uses_zone_model_then_constant_fallback() -> None:
    zone_resolved = resolve_if_ref_load(zone_model_payload=_zone_model(300, 0.64))
    const_resolved = resolve_if_ref_load(zone_model_payload=_zone_model(None, None))

    assert zone_resolved.source == "ZONEMODEL_ENDURANCE_TYPICAL"
    assert zone_resolved.value == pytest.approx(0.64)
    assert const_resolved.source == "FALLBACK_CONST"
    assert const_resolved.value == DEFAULT_IF_REF_LOAD


def test_availability_feasible_band_uses_time_ftp_and_domains() -> None:
    band = calculate_availability_feasible_band(
        availability_hours=10,
        ftp_watts=300,
        allowed_intensity_domains=["ENDURANCE", "TEMPO"],
        if_ref_load=0.68,
        utilization_min=0.5,
        utilization_max=1.0,
    )

    assert band.min > 0
    assert band.max > band.min


def test_kpi_capacity_band_requires_body_mass_when_kpi_active() -> None:
    kpi_rate = {"kj_per_kg_per_hour": {"min": 8, "max": 12}}

    band = calculate_kpi_capacity_band(
        kpi_rate_band=kpi_rate,
        body_mass_kg=75,
        availability_hours=10,
        if_ref_load=0.68,
    )

    assert band.min == pytest.approx(6000)
    assert band.max == pytest.approx(9000)
    with pytest.raises(LoadBandError, match="missing_body_mass_for_kpi_rate"):
        calculate_kpi_capacity_band(
            kpi_rate_band=kpi_rate,
            body_mass_kg=None,
            availability_hours=10,
            if_ref_load=0.68,
        )


def test_progression_band_applies_increase_and_decrease_caps() -> None:
    band = calculate_progression_band(previous_load_kj=1000, max_weekly_increase_pct=0.10, max_weekly_decrease_pct=0.20)

    assert band is not None
    assert band.min == pytest.approx(800)
    assert band.max == pytest.approx(1100)


def test_role_progression_modulates_by_phase_role() -> None:
    base_load_2 = calculate_role_progression_band(
        baseline_load_kj=1000,
        week_role="LOAD_2",
        phase_role="Base",
        scenario_cadence="2:1",
    )
    build_load_2 = calculate_role_progression_band(
        baseline_load_kj=1000,
        week_role="LOAD_2",
        phase_role="Build",
        scenario_cadence="2:1",
    )
    peak_load_2 = calculate_role_progression_band(
        baseline_load_kj=1000,
        week_role="LOAD_2",
        phase_role="Peak",
        scenario_cadence="2:1",
    )
    deload = calculate_role_progression_band(
        baseline_load_kj=1000,
        week_role="DELOAD",
        phase_role="Build",
        scenario_cadence="2:1",
    )
    mini_reset = calculate_role_progression_band(
        baseline_load_kj=1000,
        week_role="MINI_RESET",
        phase_role="Build",
        scenario_cadence="2:1:1",
    )
    reload = calculate_role_progression_band(
        baseline_load_kj=1000,
        week_role="RELOAD",
        phase_role="Build",
        scenario_cadence="2:1:1",
    )

    assert base_load_2 is not None
    assert build_load_2 is not None
    assert peak_load_2 is not None
    assert deload is not None
    assert mini_reset is not None
    assert reload is not None
    assert base_load_2.max < build_load_2.max
    assert peak_load_2.max < build_load_2.min
    assert deload.max < build_load_2.min
    assert mini_reset.max < build_load_2.min
    assert reload.max <= build_load_2.max + 10


def test_s5_normal_intersection_and_level_1_drop_progression() -> None:
    normal = derive_phase_s5_band(
        season_band=NumberBand(1000, 2000),
        feasible_band=NumberBand(900, 2100),
        progression_band=NumberBand(1200, 1800),
    )
    level_1 = derive_phase_s5_band(
        season_band=NumberBand(1000, 2000),
        feasible_band=NumberBand(900, 2100),
        progression_band=NumberBand(2500, 3000),
    )

    assert normal.trace["fallback_level"] == 0
    assert normal.band.as_dict() == {"min": 1200.0, "max": 1800.0}
    assert level_1.trace["fallback_level"] == 1
    assert level_1.band.as_dict() == {"min": 1000.0, "max": 2000.0}


def test_s5_level_2_kpi_escalation_and_level_3_override() -> None:
    level_2 = derive_phase_s5_band(
        season_band=NumberBand(1000, 2000),
        feasible_band=NumberBand(900, 2100),
        kpi_band=NumberBand(100, 500),
        kpi_selector_used="LOW",
        kpi_escalation_bands={"MID": NumberBand(1200, 1600)},
    )
    level_3 = derive_phase_s5_band(
        season_band=NumberBand(1000, 2000),
        feasible_band=NumberBand(900, 2100),
        kpi_band=NumberBand(100, 500),
        kpi_utilization_override_band=NumberBand(1100, 1500),
    )

    assert level_2.trace["fallback_level"] == 2
    assert level_2.trace["kpi_rate_band_selector_used"] == "MID"
    assert level_2.band.as_dict() == {"min": 1200.0, "max": 1600.0}
    assert level_3.trace["fallback_level"] == 3
    assert level_3.band.as_dict() == {"min": 1100.0, "max": 1500.0}


def test_s5_level_4_degenerate_and_level_5_season_infeasible() -> None:
    level_4 = derive_phase_s5_band(
        season_band=NumberBand(2000, 1000),
        feasible_band=NumberBand(900, 2100),
    )
    level_5 = derive_phase_s5_band(
        season_band=NumberBand(100, 200),
        feasible_band=NumberBand(900, 2100),
    )

    assert level_4.trace["fallback_level"] == 4
    assert level_4.band.as_dict() == {"min": 2100.0, "max": 2100.0}
    assert level_5.trace["fallback_level"] == 5
    assert level_5.band.as_dict() == {"min": 900.0, "max": 900.0}


def test_load_band_stops_for_invalid_required_inputs() -> None:
    with pytest.raises(LoadBandError, match="missing_or_invalid_ftp"):
        calculate_availability_feasible_band(
            availability_hours=10,
            ftp_watts=0,
            allowed_intensity_domains=["ENDURANCE"],
            if_ref_load=0.68,
        )
    with pytest.raises(LoadBandError, match="negative_availability"):
        calculate_availability_feasible_band(
            availability_hours=-1,
            ftp_watts=300,
            allowed_intensity_domains=["ENDURANCE"],
            if_ref_load=0.68,
        )
    with pytest.raises(LoadBandError, match="missing_allowed_intensity_domains"):
        calculate_availability_feasible_band(
            availability_hours=10,
            ftp_watts=300,
            allowed_intensity_domains=[],
            if_ref_load=0.68,
        )


def test_build_load_capacity_context_injects_s5_and_logistics_constraints() -> None:
    context = build_load_capacity_context(
        target_week=IsoWeek(2026, 20),
        phase_range=IsoWeekRange(start=IsoWeek(2026, 20), end=IsoWeek(2026, 21)),
        athlete_profile_payload={"data": {"profile": {"endurance_anchor_w": 204, "body_mass_kg": 75}}},
        availability_payload={"data": {"weekly_hours": {"min": 6, "typical": 8, "max": 10}}},
        logistics_payload={
            "data": {
                "events": [
                    {
                        "date": "2026-05-12",
                        "event_type": "travel",
                        "impact": "AVAILABILITY",
                        "description": "late return",
                    }
                ]
            }
        },
        zone_model_payload=_zone_model(300, 0.66),
        season_plan_payload={
            "data": {
                "phases": [
                    {
                        "iso_week_range": "2026-20--2026-21",
                        "weekly_load_corridor": {"weekly_kj": {"min": 2000, "max": 6000}},
                        "allowed_forbidden_semantics": {"allowed_intensity_domains": ["ENDURANCE"]},
                    }
                ]
            }
        },
    )

    assert context["availability_load_capacity_kj"]["max"] > context["availability_load_capacity_kj"]["min"]
    assert len(context["s5_bands"]) == 2
    assert context["s5_bands"][0]["band"]["min"] >= 0
    assert context["logistics_constraints"]


def test_build_load_capacity_context_uses_selected_scenario_domains_for_season_path() -> None:
    context = build_load_capacity_context(
        target_week=IsoWeek(2026, 20),
        athlete_profile_payload={"data": {"profile": {"endurance_anchor_w": 204, "body_mass_kg": 75}}},
        availability_payload={"data": {"weekly_hours": {"min": 6, "typical": 8, "max": 10}}},
        zone_model_payload=_zone_model(300, 0.66),
        season_allowed_intensity_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
    )

    assert context["allowed_intensity_domains"] == ["ENDURANCE", "TEMPO", "SWEET_SPOT"]
    assert context["availability_load_capacity_kj"]["max"] > context["availability_load_capacity_kj"]["min"]


def test_build_load_capacity_context_uses_representative_typical_capacity_not_domain_ceiling() -> None:
    context = build_load_capacity_context(
        target_week=IsoWeek(2026, 20),
        athlete_profile_payload={"data": {"profile": {"endurance_anchor_w": 204, "body_mass_kg": 75}}},
        availability_payload={"data": {"weekly_hours": {"min": 10.5, "typical": 14.0, "max": 17.5}}},
        zone_model_payload=_rich_zone_model(300),
        season_allowed_intensity_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
    )

    capacity = context["availability_load_capacity_kj"]
    assert capacity["typical"] < capacity["max"]
    assert capacity["representative_if"] == pytest.approx(0.83)
    assert capacity["ceiling_if"] == pytest.approx(0.98)


def test_build_load_capacity_context_no_longer_silently_defaults_to_endurance() -> None:
    context = build_load_capacity_context(
        target_week=IsoWeek(2026, 20),
        athlete_profile_payload={"data": {"profile": {"endurance_anchor_w": 204, "body_mass_kg": 75}}},
        availability_payload={"data": {"weekly_hours": {"min": 6, "typical": 8, "max": 10}}},
        zone_model_payload=_zone_model(300, 0.66),
    )

    assert context["allowed_intensity_domains"] == []
    assert context["availability_load_capacity_kj"] is None
    assert "missing_allowed_intensity_domains" in context["warnings"]


def test_build_load_capacity_context_uses_role_aware_s5_overlay() -> None:
    context = build_load_capacity_context(
        target_week=IsoWeek(2026, 20),
        phase_range=IsoWeekRange(start=IsoWeek(2026, 20), end=IsoWeek(2026, 22)),
        athlete_profile_payload={"data": {"profile": {"endurance_anchor_w": 204, "body_mass_kg": 75}}},
        availability_payload={"data": {"weekly_hours": {"min": 6, "typical": 10, "max": 12}}},
        zone_model_payload=_zone_model(300, 0.66),
        season_plan_payload={
            "data": {
                "phases": [
                    {
                        "iso_week_range": "2026-20--2026-22",
                        "weekly_load_corridor": {"weekly_kj": {"min": 500, "max": 9000}},
                        "allowed_forbidden_semantics": {"allowed_intensity_domains": ["ENDURANCE"]},
                    }
                ]
            }
        },
        baseline_load_kj=5000,
        week_role_by_week={"2026-20": "LOAD_1", "2026-21": "LOAD_2", "2026-22": "DELOAD"},
        phase_role_by_week={"2026-20": "Build", "2026-21": "Build", "2026-22": "Build"},
        scenario_cadence="2:1",
    )

    bands = {entry["week"]: entry["band"] for entry in context["s5_bands"]}
    traces = {entry["week"]: entry["trace"] for entry in context["s5_bands"]}

    assert bands["2026-21"]["max"] > bands["2026-20"]["max"]
    assert bands["2026-22"]["max"] < bands["2026-21"]["max"]
    assert traces["2026-22"]["week_role"] == "DELOAD"
    assert traces["2026-22"]["role_progression_band"]["max"] < traces["2026-21"]["role_progression_band"]["max"]


def test_build_load_capacity_context_preserves_shortened_mini_reset_reduction_for_recovery_sensitive_intent() -> None:
    context = build_load_capacity_context(
        target_week=IsoWeek(2026, 21),
        phase_range=IsoWeekRange(start=IsoWeek(2026, 21), end=IsoWeek(2026, 23)),
        athlete_profile_payload={"data": {"profile": {"endurance_anchor_w": 210, "body_mass_kg": 92}}},
        availability_payload={"data": {"weekly_hours": {"min": 10.5, "typical": 14.0, "max": 17.5}}},
        zone_model_payload=_rich_zone_model(300),
        kpi_rate_band={"segment": "fast_competitive", "kj_per_kg_per_hour": {"min": 7.9, "max": 10.1}},
        season_plan_payload={
            "data": {
                "phases": [
                    {
                        "iso_week_range": "2026-21--2026-23",
                        "phase_intent": "shortened_re_entry",
                        "weekly_load_corridor": {"weekly_kj": {"min": 7329, "max": 11275}},
                        "allowed_forbidden_semantics": {
                            "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT"]
                        },
                    }
                ]
            }
        },
        baseline_load_kj=9302,
        week_role_by_week={
            "2026-21": "SHORTENED_RE_ENTRY",
            "2026-22": "SHORTENED_CONSOLIDATION",
            "2026-23": "SHORTENED_MINI_RESET",
        },
        phase_role_by_week={"2026-21": "Base", "2026-22": "Base", "2026-23": "Base"},
        scenario_cadence="2:1:1",
    )

    bands = {entry["week"]: entry["band"] for entry in context["s5_bands"]}
    traces = {entry["week"]: entry["trace"] for entry in context["s5_bands"]}

    assert bands["2026-22"]["max"] > bands["2026-21"]["max"]
    assert bands["2026-23"]["max"] < bands["2026-22"]["max"]
    assert traces["2026-23"]["s5_fallback_policy"]["kpi_lower_bound_mode"] == "upper_only"
    assert traces["2026-23"]["s5_fallback_policy"]["allow_progression_overlay_drop"] is False
    assert traces["2026-23"]["fallback_level"] == 0


def test_build_load_capacity_context_keeps_kpi_lower_bound_for_non_recovery_build_intent() -> None:
    context = build_load_capacity_context(
        target_week=IsoWeek(2026, 26),
        phase_range=IsoWeekRange(start=IsoWeek(2026, 26), end=IsoWeek(2026, 26)),
        athlete_profile_payload={"data": {"profile": {"endurance_anchor_w": 210, "body_mass_kg": 92}}},
        availability_payload={"data": {"weekly_hours": {"min": 10.5, "typical": 14.0, "max": 17.5}}},
        zone_model_payload=_rich_zone_model(300),
        kpi_rate_band={"segment": "fast_competitive", "kj_per_kg_per_hour": {"min": 7.9, "max": 10.1}},
        season_plan_payload={
            "data": {
                "phases": [
                    {
                        "iso_week_range": "2026-26--2026-26",
                        "phase_intent": "build_progression",
                        "weekly_load_corridor": {"weekly_kj": {"min": 7329, "max": 11275}},
                        "allowed_forbidden_semantics": {
                            "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT"]
                        },
                    }
                ]
            }
        },
        baseline_load_kj=9302,
        week_role_by_week={"2026-26": "LOAD_1"},
        phase_role_by_week={"2026-26": "Build"},
        scenario_cadence="2:1:1",
    )

    band = context["s5_bands"][0]["band"]
    trace = context["s5_bands"][0]["trace"]

    assert band == {"min": 10175, "max": 11275}
    assert trace["s5_fallback_policy"]["kpi_lower_bound_mode"] == "enforce"
    assert trace["fallback_reason"] == "dropped_progression_overlay"


def test_season_phase_load_context_caps_phase_corridors_by_availability_and_roles() -> None:
    context = build_season_phase_load_context(
        phase_slot_context={
            "selected_scenario_id": "B",
            "phase_slots": [
                {
                    "phase_id": "P01",
                    "iso_week_range": "2026-20--2026-21",
                    "is_shortened": True,
                    "scenario_cadence": "2:1",
                    "cadence_week_roles": ["SHORTENED_RE_ENTRY", "SHORTENED_CONSOLIDATION"],
                    "week_keys": ["2026-20", "2026-21"],
                },
                {
                    "phase_id": "P02",
                    "iso_week_range": "2026-22--2026-24",
                    "is_shortened": False,
                    "scenario_cadence": "2:1",
                    "cadence_week_roles": ["LOAD_1", "LOAD_2", "DELOAD"],
                    "week_keys": ["2026-22", "2026-23", "2026-24"],
                },
                {
                    "phase_id": "P03",
                    "iso_week_range": "2026-25--2026-27",
                    "is_shortened": False,
                    "scenario_cadence": "2:1",
                    "cadence_week_roles": ["LOAD_1", "LOAD_2", "DELOAD"],
                    "week_keys": ["2026-25", "2026-26", "2026-27"],
                },
            ],
        },
        target_week=IsoWeek(2026, 20),
        selected_structure_context={"allowed_intensity_domains": ["ENDURANCE", "TEMPO"]},
        athlete_profile_payload={"data": {"profile": {"endurance_anchor_w": 204, "body_mass_kg": 75}}},
        availability_payload={"data": {"weekly_hours": {"min": 6, "typical": 8, "max": 10}}},
        zone_model_payload=_zone_model(300, 0.66),
        previous_load_kj=3000,
    )

    p01, p02, p03 = context["phases"]

    assert p01["season_phase_role"] == "shortened_re_entry"
    assert p02["phase_cycle"] == "BUILD"
    assert p03["phase_cycle"] == "PEAK"
    assert context["season_allowed_intensity_domains"] == ["ENDURANCE", "TEMPO"]
    assert p02["recommended_phase_corridor"]["max"] > p01["recommended_phase_corridor"]["max"]
    assert p03["recommended_phase_corridor"]["max"] < p02["recommended_phase_corridor"]["max"]
    assert p02["recommended_phase_corridor"]["max"] <= p02["availability_cap_kj"]["typical"]


def test_season_phase_load_context_infers_baseline_from_representative_typical_capacity() -> None:
    context = build_season_phase_load_context(
        phase_slot_context={
            "selected_scenario_id": "B",
            "phase_slots": [
                {
                    "phase_id": "P01",
                    "iso_week_range": "2026-20--2026-21",
                    "is_shortened": True,
                    "scenario_cadence": "2:1:1",
                    "cadence_week_roles": ["SHORTENED_RE_ENTRY", "SHORTENED_CONSOLIDATION"],
                    "week_keys": ["2026-20", "2026-21"],
                }
            ],
        },
        target_week=IsoWeek(2026, 20),
        selected_structure_context={
            "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"]
        },
        athlete_profile_payload={"data": {"profile": {"endurance_anchor_w": 210, "body_mass_kg": 92}}},
        availability_payload={"data": {"weekly_hours": {"min": 10.5, "typical": 14.0, "max": 17.5}}},
        zone_model_payload=_rich_zone_model(300),
    )

    assert context["availability_load_capacity_kj"]["typical"] == 15660
    assert context["baseline_load_kj"] == 12528
    assert (
        "season_phase_load_context baseline_load_kj inferred from representative availability typical capacity."
        in context["warnings"]
    )


def test_selected_kpi_rate_band_from_selection_requires_kj_range() -> None:
    selected = selected_kpi_rate_band_from_selection(
        {
            "data": {
                "kpi_moving_time_rate_guidance_selection": {
                    "segment": "MID",
                    "kj_per_kg_per_hour": {"min": 16, "max": 20},
                }
            }
        }
    )
    missing = selected_kpi_rate_band_from_selection(
        {"data": {"kpi_moving_time_rate_guidance_selection": {"segment": "MID"}}}
    )

    assert selected is not None
    assert selected["segment"] == "MID"
    assert missing is None


def test_build_load_capacity_context_preserves_spec_stop_warnings() -> None:
    negative_availability = build_load_capacity_context(
        target_week=IsoWeek(2026, 20),
        athlete_profile_payload={"data": {"profile": {"endurance_anchor_w": 204}}},
        availability_payload={"data": {"weekly_hours": {"min": -1, "typical": -1, "max": -1}}},
        zone_model_payload=_zone_model(300, 0.66),
        season_plan_payload={
            "data": {
                "phases": [
                    {
                        "iso_week_range": "2026-20--2026-20",
                        "weekly_load_corridor": {"weekly_kj": {"min": 2000, "max": 6000}},
                        "allowed_forbidden_semantics": {"allowed_intensity_domains": ["ENDURANCE"]},
                    }
                ]
            }
        },
    )
    missing_domains = build_load_capacity_context(
        target_week=IsoWeek(2026, 20),
        athlete_profile_payload={"data": {"profile": {"endurance_anchor_w": 204}}},
        availability_payload={"data": {"weekly_hours": {"min": 6, "typical": 8, "max": 10}}},
        zone_model_payload=_zone_model(300, 0.66),
        season_plan_payload={
            "data": {
                "phases": [
                    {
                        "iso_week_range": "2026-20--2026-20",
                        "weekly_load_corridor": {"weekly_kj": {"min": 2000, "max": 6000}},
                    }
                ]
            }
        },
    )

    assert "negative_availability" in negative_availability["warnings"]
    assert negative_availability["s5_bands"][0]["error"] == "negative_availability"
    assert "missing_allowed_intensity_domains" in missing_domains["warnings"]
    assert missing_domains["s5_bands"][0]["error"] == "missing_allowed_intensity_domains"


def test_build_load_capacity_context_uses_complete_availability_table_for_s5() -> None:
    context = build_load_capacity_context(
        target_week=IsoWeek(2026, 20),
        athlete_profile_payload={"data": {"profile": {"endurance_anchor_w": 204}}},
        availability_payload={
            "data": {
                "weekly_hours": {"min": 20, "typical": 20, "max": 20},
                "fixed_rest_days": ["Mon"],
                "availability_table": [
                    {"weekday": "Mon", "hours_min": 9, "hours_typical": 9, "hours_max": 9},
                    {"weekday": "Tue", "hours_min": 1, "hours_typical": 1, "hours_max": 1},
                    {"weekday": "Wed", "hours_min": 1, "hours_typical": 1, "hours_max": 1},
                    {"weekday": "Thu", "hours_min": 1, "hours_typical": 1, "hours_max": 1},
                    {"weekday": "Fri", "hours_min": 1, "hours_typical": 1, "hours_max": 1},
                    {"weekday": "Sat", "hours_min": 1, "hours_typical": 1, "hours_max": 1},
                    {"weekday": "Sun", "hours_min": 1, "hours_typical": 1, "hours_max": 1},
                ],
            }
        },
        zone_model_payload=_zone_model(300, 0.66),
        season_plan_payload={
            "data": {
                "phases": [
                    {
                        "iso_week_range": "2026-20--2026-20",
                        "weekly_load_corridor": {"weekly_kj": {"min": 1000, "max": 9000}},
                        "allowed_forbidden_semantics": {"allowed_intensity_domains": ["ENDURANCE"]},
                    }
                ]
            }
        },
    )

    assert context["availability_hours_source"] == "AVAILABILITY.availability_table"
    assert context["availability_table_weekly_hours"]["hours"]["typical"] == pytest.approx(6.0)
    assert context["s5_bands"][0]["trace"]["feasible_band"]["max"] < 9000


def test_build_load_capacity_context_uses_kpi_profile_escalation_bands() -> None:
    context = build_load_capacity_context(
        target_week=IsoWeek(2026, 20),
        athlete_profile_payload={"data": {"profile": {"body_mass_kg": 75}}},
        availability_payload={"data": {"weekly_hours": {"min": 10, "typical": 10, "max": 10}}},
        zone_model_payload=_zone_model(300, 0.66),
        kpi_rate_band={"segment": "low", "kj_per_kg_per_hour": {"min": 1, "max": 2}},
        kpi_profile_payload={
            "data": {
                "durability": {
                    "moving_time_rate_guidance": {
                        "bands": [
                            {"segment": "low", "kj_per_kg_per_hour": {"min": 1, "max": 2}},
                            {"segment": "mid", "kj_per_kg_per_hour": {"min": 8, "max": 9}},
                        ]
                    }
                }
            }
        },
        season_plan_payload={
            "data": {
                "phases": [
                    {
                        "iso_week_range": "2026-20--2026-20",
                        "weekly_load_corridor": {"weekly_kj": {"min": 5000, "max": 7000}},
                        "allowed_forbidden_semantics": {"allowed_intensity_domains": ["ENDURANCE"]},
                    }
                ]
            }
        },
    )

    assert context["s5_bands"][0]["trace"]["fallback_level"] == 2
    assert context["s5_bands"][0]["trace"]["kpi_rate_band_selector_used"] == "mid"


def test_build_load_capacity_context_stops_when_kpi_active_without_body_mass() -> None:
    context = build_load_capacity_context(
        target_week=IsoWeek(2026, 20),
        athlete_profile_payload={"data": {"profile": {}}},
        availability_payload={"data": {"weekly_hours": {"min": 10, "typical": 10, "max": 10}}},
        zone_model_payload=_zone_model(300, 0.66),
        kpi_rate_band={"segment": "low", "kj_per_kg_per_hour": {"min": 1, "max": 2}},
        season_plan_payload={
            "data": {
                "phases": [
                    {
                        "iso_week_range": "2026-20--2026-20",
                        "weekly_load_corridor": {"weekly_kj": {"min": 1000, "max": 7000}},
                        "allowed_forbidden_semantics": {"allowed_intensity_domains": ["ENDURANCE"]},
                    }
                ]
            }
        },
    )

    assert "missing_body_mass_for_kpi_rate" in context["warnings"]
    assert context["s5_bands"][0]["error"] == "missing_body_mass_for_kpi_rate"
