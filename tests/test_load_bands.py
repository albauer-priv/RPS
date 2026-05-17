from __future__ import annotations

import pytest

from rps.planning.load_bands import (
    DEFAULT_IF_REF_LOAD,
    LoadBandError,
    NumberBand,
    build_load_capacity_context,
    calculate_availability_feasible_band,
    calculate_kpi_capacity_band,
    calculate_progression_band,
    derive_phase_s5_band,
    resolve_if_ref_load,
    selected_kpi_rate_band_from_selection,
)
from rps.workspace.iso_helpers import IsoWeek, IsoWeekRange


def _zone_model(ftp: float | None = 300.0, typical_if: float | None = 0.66) -> dict:
    metadata = {} if ftp is None else {"ftp_watts": ftp}
    zones = [] if typical_if is None else [{"zone_id": "Z2", "typical_if": typical_if}]
    return {"data": {"model_metadata": metadata, "zones": zones}}


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
        allowed_intensity_domains=["ENDURANCE_LOW", "TEMPO"],
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
            allowed_intensity_domains=["ENDURANCE_LOW"],
            if_ref_load=0.68,
        )
    with pytest.raises(LoadBandError, match="negative_availability"):
        calculate_availability_feasible_band(
            availability_hours=-1,
            ftp_watts=300,
            allowed_intensity_domains=["ENDURANCE_LOW"],
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
                        "allowed_forbidden_semantics": {"allowed_intensity_domains": ["ENDURANCE_LOW"]},
                    }
                ]
            }
        },
    )

    assert context["availability_load_capacity_kj"]["max"] > context["availability_load_capacity_kj"]["min"]
    assert len(context["s5_bands"]) == 2
    assert context["s5_bands"][0]["band"]["min"] >= 0
    assert context["logistics_constraints"]


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
                        "allowed_forbidden_semantics": {"allowed_intensity_domains": ["ENDURANCE_LOW"]},
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
                        "allowed_forbidden_semantics": {"allowed_intensity_domains": ["ENDURANCE_LOW"]},
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
                        "allowed_forbidden_semantics": {"allowed_intensity_domains": ["ENDURANCE_LOW"]},
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
                        "allowed_forbidden_semantics": {"allowed_intensity_domains": ["ENDURANCE_LOW"]},
                    }
                ]
            }
        },
    )

    assert "missing_body_mass_for_kpi_rate" in context["warnings"]
    assert context["s5_bands"][0]["error"] == "missing_body_mass_for_kpi_rate"
