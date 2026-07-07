from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from rps.crewai_runtime import load_crewai_config_bundle
from rps.crewai_runtime.guardrails_context import guardrail_runtime_context
from rps.crewai_runtime.guardrails_phase import phase_s5_band_match, phase_weeks_match_range
from rps.crewai_runtime.guardrails_week import (
    week_active_corridor_match,
    week_agenda_shape_and_calendar_check,
    week_bundle_domain_legality_check,
    week_corridor_and_capacity_check,
    week_daily_availability_check,
    week_phase_role_alignment_check,
    week_recovery_day_load_check,
    week_workout_structure_policy_check,
)
from rps.orchestrator.resolved_context import build_resolved_load_governance_context_block
from rps.planning.deterministic_context import (
    build_week_calendar_context,
    render_week_calendar_context_block,
)
from rps.workspace.iso_helpers import IsoWeek


def test_phase_s5_band_guardrail_rejects_explicit_s5_mismatch() -> None:
    failed, message = phase_s5_band_match(
        {
            "meta": {"artifact_type": "PHASE_GUARDRAILS", "schema_id": "PhaseGuardrailsInterface"},
            "data": {
                "load_guardrails": {
                    "weekly_kj_bands": [
                        {"week": "2026-20", "band": {"min": 1000, "max": 1500, "notes": "S5 band: 1100-1500"}}
                    ]
                }
            },
        }
    )

    assert failed is False
    assert "does not match deterministic S5 band" in message

def test_phase_weeks_match_range_rejects_missing_phase_week() -> None:
    failed, message = phase_weeks_match_range(
        {
            "meta": {
                "artifact_type": "PHASE_STRUCTURE",
                "schema_id": "PhaseStructureInterface",
                "iso_week_range": "2026-20--2026-22",
            },
            "data": {
                "load_ranges": {
                    "weekly_kj_bands": [
                        {"week": "2026-20", "band": {"min": 1000, "max": 1200}},
                        {"week": "2026-22", "band": {"min": 1000, "max": 1200}},
                    ]
                }
            },
        }
    )

    assert failed is False
    assert "missing=['2026-21']" in message

def test_week_corridor_guardrail_rejects_load_outside_band() -> None:
    failed, message = week_corridor_and_capacity_check(
        {
            "meta": {"artifact_type": "WEEK_PLAN", "schema_id": "WeekPlanInterface"},
            "data": {
                "week_summary": {
                    "planned_weekly_load_kj": 2500,
                    "weekly_load_corridor_kj": {"min": 1000, "max": 2000},
                }
            },
        }
    )

    assert failed is False
    assert "exceeds weekly load corridor" in message

def test_week_calendar_context_uses_phase_structure_week_role() -> None:
    phase_info = SimpleNamespace(phase_id="P01", phase_type="Build", raw={"cycle": "Build"})
    context = build_week_calendar_context(
        target_week=IsoWeek(2026, 21),
        phase_info=phase_info,
        phase_range=SimpleNamespace(
            range_key="2026-20--2026-22",
            start=IsoWeek(2026, 20),
            end=IsoWeek(2026, 22),
        ),
        phase_structure_payload={
            "data": {
                "execution_principles": {"phase_role": "Build"},
                "week_skeleton_logic": {
                    "week_roles": {
                        "week_roles": [
                            {"week": "2026-20", "role": "LOAD_1"},
                            {"week": "2026-21", "role": "LOAD_2"},
                            {"week": "2026-22", "role": "DELOAD"},
                        ],
                        "allowed_role_set": ["LOAD_1", "LOAD_2", "DELOAD"],
                    }
                },
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
            }
        },
    )

    assert context["phase_week_role"] == "LOAD_2"
    assert context["phase_week_role_source"] == "PHASE_STRUCTURE.week_skeleton_logic.week_roles"
    assert context["active_weekly_kj_band"] == {"min": 1000, "max": 2000}
    assert context["quality_day_cap"] == 1

def test_render_week_calendar_context_marks_active_weekly_band_as_binding() -> None:
    text = render_week_calendar_context_block(
        {
            "target_iso_week": "2026-21",
            "week_start_date": "2026-05-18",
            "week_end_date": "2026-05-24",
            "phase_id": "P01",
            "phase_iso_week_range": "2026-21--2026-23",
            "phase_cycle": "Base",
            "phase_role": "Base",
            "phase_intent": "shortened_re_entry",
            "phase_week_role": "SHORTENED_RE_ENTRY",
            "phase_week_role_source": "PHASE_STRUCTURE.week_skeleton_logic.week_roles",
            "phase_role_for_week": "SHORTENED_RE_ENTRY",
            "allowed_day_roles": ["REST", "ENDURANCE", "QUALITY"],
            "forbidden_day_roles": [],
            "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT"],
            "forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
            "allowed_load_modalities": ["NONE", "K3"],
            "quality_day_cap": 2,
            "active_weekly_kj_band": {"min": 7329, "max": 8372},
            "phase_weekly_kj_band": {"min": 7329, "max": 8372},
            "active_s5_band": {"min": 10175, "max": 11275},
            "week_skeleton_mandatory_elements": {"recovery_opportunities_min": 2, "endurance_anchor_required": True},
            "fixed_rest_days": ["Mon", "Fri"],
            "day_matrix": [],
            "event_proximity": {},
        }
    )

    assert "binding active weekly band" in text
    assert "active_weekly_kj_band: min 7329, max 8372 (binding target-week corridor)" in text
    assert "active_s5_band: min 10175, max 11275 (fallback/broader S5 context)" in text

def test_resolved_load_context_finds_mid_phase_season_band() -> None:
    block = build_resolved_load_governance_context_block(
        target_week=IsoWeek(2026, 21),
        season_plan_payload={
            "data": {
                "phases": [
                    {
                        "iso_week_range": "2026-20--2026-22",
                        "weekly_load_corridor": {"weekly_kj": {"min": 1000, "max": 2000, "notes": "build"}},
                    }
                ]
            }
        },
        phase_structure_payload={
            "data": {
                "week_skeleton_logic": {
                    "week_roles": {
                        "week_roles": [{"week": "2026-21", "role": "LOAD_2"}],
                        "allowed_role_set": ["LOAD_2"],
                    }
                }
            }
        },
    )

    assert "season_phase.weekly_load_corridor.weekly_kj: min 1000, max 2000" in block
    assert "phase_structure.active_week_role (2026-21): LOAD_2" in block

def test_week_active_corridor_guardrail_rejects_context_mismatch() -> None:
    week_plan = {
        "meta": {"artifact_type": "WEEK_PLAN", "schema_id": "WeekPlanInterface", "iso_week": "2026-20"},
        "data": {
            "week_summary": {
                "planned_weekly_load_kj": 1500,
                "weekly_load_corridor_kj": {"min": 1000, "max": 2000},
            }
        },
    }

    with guardrail_runtime_context(
        week_calendar_context={"active_weekly_kj_band": {"min": 1200, "max": 2200}},
        target_week=IsoWeek(2026, 20),
    ):
        failed, message = week_active_corridor_match(week_plan)

    assert failed is False
    assert "must exactly mirror active Phase/S5 band" in message

def test_week_recovery_day_guardrail_rejects_load_on_rest_day() -> None:
    failed, message = week_recovery_day_load_check(
        {
            "meta": {"artifact_type": "WEEK_PLAN", "schema_id": "WeekPlanInterface"},
            "data": {
                "agenda": [
                    {
                        "day": "Mon",
                        "date": "2026-05-11",
                        "day_role": "REST",
                        "planned_duration": "01:00",
                        "planned_kj": 400,
                        "workout_id": "W1",
                    }
                ]
            },
        }
    )

    assert failed is False
    assert "REST day Mon" in message

def test_week_daily_availability_guardrail_rejects_duration_above_day_max() -> None:
    week_plan = {
        "meta": {"artifact_type": "WEEK_PLAN", "schema_id": "WeekPlanInterface", "iso_week": "2026-20"},
        "data": {
            "week_summary": {"planned_weekly_load_kj": 1200},
            "agenda": [
                {
                    "day": "Mon",
                    "date": "2026-05-11",
                    "day_role": "REST",
                    "planned_duration": "00:00",
                    "planned_kj": 0,
                    "workout_id": None,
                },
                {
                    "day": "Tue",
                    "date": "2026-05-12",
                    "day_role": "ENDURANCE",
                    "planned_duration": "02:00",
                    "planned_kj": 600,
                    "workout_id": "W1",
                },
                {
                    "day": "Wed",
                    "date": "2026-05-13",
                    "day_role": "REST",
                    "planned_duration": "00:00",
                    "planned_kj": 0,
                    "workout_id": None,
                },
                {
                    "day": "Thu",
                    "date": "2026-05-14",
                    "day_role": "REST",
                    "planned_duration": "00:00",
                    "planned_kj": 0,
                    "workout_id": None,
                },
                {
                    "day": "Fri",
                    "date": "2026-05-15",
                    "day_role": "REST",
                    "planned_duration": "00:00",
                    "planned_kj": 0,
                    "workout_id": None,
                },
                {
                    "day": "Sat",
                    "date": "2026-05-16",
                    "day_role": "REST",
                    "planned_duration": "00:00",
                    "planned_kj": 0,
                    "workout_id": None,
                },
                {
                    "day": "Sun",
                    "date": "2026-05-17",
                    "day_role": "REST",
                    "planned_duration": "00:00",
                    "planned_kj": 0,
                    "workout_id": None,
                },
            ],
        },
    }
    availability = {
        "data": {
            "availability_table": [
                {
                    "weekday": "Tue",
                    "hours_min": 1.0,
                    "hours_typical": 1.0,
                    "hours_max": 1.5,
                }
            ]
        }
    }

    with guardrail_runtime_context(availability_payload=availability, target_week=IsoWeek(2026, 20)):
        failed, message = week_daily_availability_check(week_plan)

    assert failed is False
    assert "exceeds availability hours_max" in message

def test_week_agenda_shape_guardrail_rejects_non_monday_start() -> None:
    week_plan = {
        "meta": {"artifact_type": "WEEK_PLAN", "schema_id": "WeekPlanInterface", "iso_week": "2026-20"},
        "data": {
            "agenda": [
                {"day": "Tue", "date": "2026-05-12", "day_role": "REST", "planned_duration": "00:00", "planned_kj": 0, "workout_id": None}
            ]
        },
    }

    failed, message = week_agenda_shape_and_calendar_check(week_plan)

    assert failed is False
    assert "agenda must contain exactly seven Mon-Sun entries" in message

def test_week_phase_role_alignment_blocks_quality_in_mini_reset() -> None:
    week_plan = {
        "meta": {"artifact_type": "WEEK_PLAN", "schema_id": "WeekPlanInterface", "iso_week": "2026-20"},
        "data": {
            "agenda": [
                {"day": "Mon", "date": "2026-05-11", "day_role": "QUALITY", "planned_duration": "01:00", "planned_kj": 500, "workout_id": "W1"}
            ],
            "workouts": [{"workout_id": "W1", "title": "Endurance", "notes": "", "workout_text": ""}],
        },
    }

    with guardrail_runtime_context(
        week_calendar_context={
            "phase_week_role": "MINI_RESET",
            "allowed_day_roles": ["REST", "RECOVERY", "ENDURANCE", "QUALITY"],
            "quality_day_cap": 1,
            "allowed_intensity_domains": ["RECOVERY", "ENDURANCE"],
            "forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
        }
    ):
        failed, message = week_phase_role_alignment_check(week_plan)

    assert failed is False
    assert "MINI_RESET week must not schedule QUALITY days" in message

def test_week_workout_structure_guardrail_rejects_missing_cooldown() -> None:
    week_plan = {
        "meta": {"artifact_type": "WEEK_PLAN", "schema_id": "WeekPlanInterface", "iso_week": "2026-20"},
        "data": {
            "week_summary": {"planned_weekly_load_kj": 500, "weekly_load_corridor_kj": {"min": 1, "max": 1000}},
            "agenda": [
                {"day": "Mon", "date": "2026-05-11", "day_role": "ENDURANCE", "planned_duration": "00:20", "planned_kj": 100, "workout_id": "W1"},
                {"day": "Tue", "date": "2026-05-12", "day_role": "REST", "planned_duration": "00:00", "planned_kj": 0, "workout_id": None},
                {"day": "Wed", "date": "2026-05-13", "day_role": "REST", "planned_duration": "00:00", "planned_kj": 0, "workout_id": None},
                {"day": "Thu", "date": "2026-05-14", "day_role": "REST", "planned_duration": "00:00", "planned_kj": 0, "workout_id": None},
                {"day": "Fri", "date": "2026-05-15", "day_role": "REST", "planned_duration": "00:00", "planned_kj": 0, "workout_id": None},
                {"day": "Sat", "date": "2026-05-16", "day_role": "REST", "planned_duration": "00:00", "planned_kj": 0, "workout_id": None},
                {"day": "Sun", "date": "2026-05-17", "day_role": "REST", "planned_duration": "00:00", "planned_kj": 0, "workout_id": None},
            ],
            "workouts": [
                {
                    "workout_id": "W1",
                    "title": "Endurance",
                    "date": "2026-05-11",
                    "start": "07:00",
                    "duration": "00:20:00",
                    "workout_text": "Warmup\n- 5m ramp 50%-60% 85rpm\n\nMain Set\n- 15m 65% 85rpm",
                    "notes": "planned_kJ 100",
                }
            ],
        },
    }

    failed, message = week_workout_structure_policy_check(week_plan)

    assert failed is False
    assert "missing required section: Cooldown" in message

def test_week_phase_role_alignment_reports_forbidden_domain_workout_ids() -> None:
    week_plan = {
        "meta": {"artifact_type": "WEEK_PLAN", "schema_id": "WeekPlanInterface", "iso_week": "2026-20"},
        "data": {
            "agenda": [
                {"day": "Thu", "date": "2026-05-14", "day_role": "RECOVERY", "planned_duration": "00:45", "planned_kj": 250, "workout_id": "REC-1"}
            ],
            "workouts": [
                {
                    "workout_id": "REC-1",
                    "title": "Recovery Spin",
                    "notes": "RECOVERY",
                    "workout_text": "Warmup\n- 5m 55% 85rpm\n\nMain Set\n- 30m 60% 85rpm\n\nCooldown\n- 5m 55% 80rpm",
                }
            ],
        },
    }

    with guardrail_runtime_context(
        week_calendar_context={
            "phase_week_role": "LOAD",
            "allowed_day_roles": ["REST", "RECOVERY", "ENDURANCE", "QUALITY"],
            "quality_day_cap": 2,
            "allowed_intensity_domains": ["ENDURANCE", "TEMPO"],
            "forbidden_intensity_domains": ["RECOVERY", "THRESHOLD", "VO2MAX"],
        }
    ):
        failed, message = week_phase_role_alignment_check(week_plan)

        assert failed is True
        assert message == week_plan

def test_week_bundle_domain_legality_check_rejects_forbidden_workout_domains() -> None:
    bundle = {
        "context_summary": {},
        "constraint_summary": [],
        "load_target_summary": [],
        "revision_summary": [],
        "day_blueprints": [
            {"day": day, "date": date_value, "day_role": "REST" if day in {"Mon", "Fri"} else "ENDURANCE"}
            for day, date_value in [
                ("Mon", "2026-05-18"),
                ("Tue", "2026-05-19"),
                ("Wed", "2026-05-20"),
                ("Thu", "2026-05-21"),
                ("Fri", "2026-05-22"),
                ("Sat", "2026-05-23"),
                ("Sun", "2026-05-24"),
            ]
        ],
        "workout_blueprints": [
            {
                "workout_id": "REC-1",
                "date": "2026-05-19",
                "day_role": "ENDURANCE",
                "intensity_domain": "RECOVERY",
                "workout_family": "RECOVERY",
                "phase_legality_status": "illegal",
                "planned_duration_minutes": 60,
                "planned_kj": 500,
            },
            {
                "workout_id": "THR-1",
                "date": "2026-05-23",
                "day_role": "QUALITY",
                "intensity_domain": "THRESHOLD",
                "workout_family": "THRESHOLD",
                "phase_legality_status": "illegal",
                "planned_duration_minutes": 90,
                "planned_kj": 900,
            },
        ],
    }

    with guardrail_runtime_context(
        week_calendar_context={
            "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT"],
            "forbidden_intensity_domains": ["RECOVERY", "THRESHOLD", "VO2MAX"],
        }
    ):
        failed, message = week_bundle_domain_legality_check(bundle)

    assert failed is False
    assert "forbidden intensity domains: RECOVERY (REC-1), THRESHOLD (THR-1)" in message

def test_week_phase_role_alignment_uses_approved_bundle_before_text_only_inference() -> None:
    week_plan = {
        "meta": {"artifact_type": "WEEK_PLAN", "schema_id": "WeekPlanInterface", "iso_week": "2026-20"},
        "data": {
            "agenda": [
                {"day": "Tue", "date": "2026-05-19", "day_role": "ENDURANCE", "planned_duration": "01:00", "planned_kj": 500, "workout_id": "W1"}
            ],
            "workouts": [
                {
                    "workout_id": "W1",
                    "title": "Endurance Ride",
                    "notes": "Threshold-like feel",
                    "workout_text": "Warmup\n- 5m 55% 85rpm\n\nMain Set\n- 30m 90% 85rpm\n\nCooldown\n- 5m 55% 80rpm",
                }
            ],
        },
    }

    with guardrail_runtime_context(
        week_calendar_context={
            "phase_week_role": "LOAD",
            "allowed_day_roles": ["REST", "ENDURANCE", "QUALITY"],
            "quality_day_cap": 2,
            "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT"],
            "forbidden_intensity_domains": ["RECOVERY", "THRESHOLD", "VO2MAX"],
        },
        approved_planning_bundle={
            "workout_blueprints": [
                {
                    "workout_id": "W1",
                    "intensity_domain": "ENDURANCE",
                    "workout_family": "ENDURANCE",
                    "phase_legality_status": "legal",
                }
            ]
        },
    ):
        failed, message = week_phase_role_alignment_check(week_plan)

    assert failed is True
    assert message == week_plan

def test_runtime_profiles_keep_week_crews_planning_disabled_but_manager_reasoning_enabled() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])

    assert bundle.runtime_profiles["crews"]["week_planning"]["planning"]["enabled"] is False
    assert bundle.runtime_profiles["crews"]["week_review"]["planning"]["enabled"] is False
    assert bundle.runtime_profiles["crews"]["week_writer"]["planning"]["enabled"] is False
    assert bundle.runtime_profiles["agents"]["week_plan_manager"]["reasoning"]["enabled"] is True
