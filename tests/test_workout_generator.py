from __future__ import annotations

from rps.crewai_runtime.guardrails import guardrail_runtime_context, week_phase_role_alignment_check
from rps.workouts.generator import build_week_plan_document_from_bundle
from rps.workouts.structured import canonicalize_workout_text
from rps.workouts.validator import validate_week_plan_exportability


def test_canonicalize_workout_text_rewrites_inline_loop_and_headers() -> None:
    text = (
        "Warmup\n"
        "- 8m ramp 50%-70% 85-90rpm\n\n"
        "Activation\n"
        "- 3x 20s 120% 95rpm\n"
        "- 40s 60% 85rpm\n\n"
        "Main Set\n"
        "- 3x 12m 88%-90% 85-90rpm\n"
        "- 3m 60% 85rpm\n\n"
        "Cooldown\n"
        "- 8m ramp 60%-45% 80-85rpm"
    )

    canonical = canonicalize_workout_text(text, context_text="Sweet Spot")

    assert "#### Activation" in canonical
    assert "\n3x\n- 12m 88%-90% 85-90rpm" in canonical
    assert "- 3x 12m" not in canonical


def test_build_week_plan_document_from_bundle_is_exportable() -> None:
    planning_bundle = {
        "day_blueprints": [
            {"day": "Mon", "date": "2026-05-18", "day_role": "REST", "planned_duration_minutes": 0, "planned_kj": 0, "workout_id": None},
            {"day": "Tue", "date": "2026-05-19", "day_role": "QUALITY", "planned_duration_minutes": 75, "planned_kj": 900, "workout_id": "W-TUE"},
            {"day": "Wed", "date": "2026-05-20", "day_role": "ENDURANCE", "planned_duration_minutes": 60, "planned_kj": 700, "workout_id": "W-WED"},
            {"day": "Thu", "date": "2026-05-21", "day_role": "QUALITY", "planned_duration_minutes": 105, "planned_kj": 1300, "workout_id": "W-THU"},
            {"day": "Fri", "date": "2026-05-22", "day_role": "REST", "planned_duration_minutes": 0, "planned_kj": 0, "workout_id": None},
            {"day": "Sat", "date": "2026-05-23", "day_role": "ENDURANCE", "planned_duration_minutes": 210, "planned_kj": 2600, "workout_id": "W-SAT"},
            {"day": "Sun", "date": "2026-05-24", "day_role": "RECOVERY", "planned_duration_minutes": 60, "planned_kj": 600, "workout_id": "W-SUN"},
        ],
        "workout_blueprints": [
            {"workout_id": "W-TUE", "date": "2026-05-19", "day_role": "QUALITY", "intensity_domain": "TEMPO", "workout_family": "TEMPO", "protocol_type": "CLASSIC_INTERVALS", "protocol_variant": "TEMPO_CLASSIC", "planned_duration_minutes": 75, "planned_kj": 900, "primary_tiz_target_min": 48, "addon_policy": "Z2_FILL", "progression_parameters": {"warmup_minutes": 10, "cooldown_minutes": 8, "work_target": "82%-88%", "work_cadence": "90-95rpm", "recovery_target": "60%-65%", "recovery_cadence": "85-90rpm", "recovery_duration_minutes": 6, "tiz_min_minutes": 36, "tiz_max_minutes": 60, "set_count_min": 3, "set_count_max": 5, "work_duration_min_minutes": 10, "work_duration_max_minutes": 15, "addon_target": "68%-72%", "addon_cadence": "85-95rpm", "addon_min_block_minutes": 10, "addon_max_block_minutes": 45, "addon_step_minutes": 5, "addon_max_share_of_session": 0.45}, "progression_state": {"primary_axis": "work_duration", "secondary_axis": "set_redistribution"}},
            {"workout_id": "W-WED", "date": "2026-05-20", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "workout_family": "ENDURANCE", "protocol_type": "LONG_STEADY", "protocol_variant": "ENDURANCE_STEADY", "planned_duration_minutes": 60, "planned_kj": 700, "progression_parameters": {"warmup_minutes": 8, "cooldown_minutes": 8, "main_target": "68%-72%", "main_cadence": "85-90rpm"}},
            {"workout_id": "W-THU", "date": "2026-05-21", "day_role": "QUALITY", "intensity_domain": "SWEET_SPOT", "workout_family": "SWEET_SPOT", "protocol_type": "CLASSIC_INTERVALS", "protocol_variant": "SWEET_SPOT_CLASSIC", "planned_duration_minutes": 105, "planned_kj": 1300, "primary_tiz_target_min": 48, "addon_policy": "Z2_FILL", "activation_required": True, "progression_parameters": {"warmup_minutes": 10, "cooldown_minutes": 8, "activation_profile": "SWEET_SPOT_STANDARD", "work_target": "88%-92%", "work_cadence": "85-90rpm", "recovery_target": "60%-65%", "recovery_cadence": "85-90rpm", "recovery_duration_minutes": 3, "tiz_min_minutes": 40, "tiz_max_minutes": 60, "set_count_min": 2, "set_count_max": 5, "work_duration_min_minutes": 10, "work_duration_max_minutes": 20, "addon_target": "68%-72%", "addon_cadence": "85-95rpm", "addon_min_block_minutes": 10, "addon_max_block_minutes": 45, "addon_step_minutes": 5, "addon_max_share_of_session": 0.45}, "progression_state": {"primary_axis": "work_duration", "secondary_axis": "set_redistribution"}},
            {"workout_id": "W-SAT", "date": "2026-05-23", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "workout_family": "ENDURANCE", "protocol_type": "LONG_STEADY", "protocol_variant": "ENDURANCE_LONG_STEADY", "planned_duration_minutes": 210, "planned_kj": 2600, "progression_parameters": {"warmup_minutes": 10, "cooldown_minutes": 8, "main_target": "68%-72%", "main_cadence": "85-90rpm"}},
            {"workout_id": "W-SUN", "date": "2026-05-24", "day_role": "RECOVERY", "intensity_domain": "ENDURANCE", "workout_family": "ENDURANCE_LOW", "protocol_type": "LONG_STEADY", "protocol_variant": "ENDURANCE_LOW", "planned_duration_minutes": 60, "planned_kj": 600, "progression_parameters": {"warmup_minutes": 6, "cooldown_minutes": 6, "main_target": "60%-65%", "main_cadence": "85-90rpm"}},
        ],
        "load_target_summary": ["Shortened re-entry week with two quality sessions and a weekend endurance anchor."],
        "warnings": [],
    }
    week_calendar_context = {
        "target_iso_week": "2026-21",
        "week_start_date": "2026-05-18",
        "week_end_date": "2026-05-24",
        "phase_week_role": "SHORTENED_RE_ENTRY",
        "fixed_rest_days": ["Mon", "Fri"],
        "active_weekly_kj_band": {"min": 7329, "max": 8372, "notes": "Binding active weekly band."},
    }

    document = build_week_plan_document_from_bundle(
        planning_bundle=planning_bundle,
        week_calendar_context=week_calendar_context,
        review_decision={"warnings": []},
    )

    validate_week_plan_exportability(document)
    rendered = "\n".join(workout["workout_text"] for workout in document["data"]["workouts"])
    assert "- 3x " not in rendered
    assert "#### Z2 Add-On" in rendered


def test_week_phase_role_alignment_ignores_recovery_wording_in_title_and_notes() -> None:
    week_plan = {
        "meta": {"artifact_type": "WEEK_PLAN", "schema_id": "WeekPlanInterface", "iso_week": "2026-20"},
        "data": {
            "agenda": [
                {"day": "Tue", "date": "2026-05-19", "day_role": "ENDURANCE", "planned_duration": "01:00", "planned_kj": 500, "workout_id": "W1"}
            ],
            "workouts": [
                {
                    "workout_id": "W1",
                    "title": "Recovery Endurance Spin",
                    "notes": "Recovery-like feel while staying aerobic.",
                    "workout_text": "Warmup\n- 6m ramp 50%-60% 85-90rpm\n\nMain Set\n- 48m 60%-65% 85-90rpm\n\nCooldown\n- 6m ramp 55%-45% 80-85rpm",
                }
            ],
        },
    }

    with guardrail_runtime_context(
        week_calendar_context={
            "phase_week_role": "SHORTENED_RE_ENTRY",
            "allowed_day_roles": ["REST", "RECOVERY", "ENDURANCE", "QUALITY"],
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
        failed, payload = week_phase_role_alignment_check(week_plan)

    assert failed is True
    assert payload == week_plan


def test_protocol_solver_renders_vo2_microburst_sets_without_nested_loops() -> None:
    planning_bundle = {
        "day_blueprints": [
            {"day": "Mon", "date": "2026-05-18", "day_role": "REST", "planned_duration_minutes": 0, "planned_kj": 0, "workout_id": None},
                {"day": "Tue", "date": "2026-05-19", "day_role": "QUALITY", "planned_duration_minutes": 120, "planned_kj": 1500, "workout_id": "VO2-TUE"},
            {"day": "Wed", "date": "2026-05-20", "day_role": "REST", "planned_duration_minutes": 0, "planned_kj": 0, "workout_id": None},
            {"day": "Thu", "date": "2026-05-21", "day_role": "REST", "planned_duration_minutes": 0, "planned_kj": 0, "workout_id": None},
            {"day": "Fri", "date": "2026-05-22", "day_role": "REST", "planned_duration_minutes": 0, "planned_kj": 0, "workout_id": None},
            {"day": "Sat", "date": "2026-05-23", "day_role": "REST", "planned_duration_minutes": 0, "planned_kj": 0, "workout_id": None},
            {"day": "Sun", "date": "2026-05-24", "day_role": "REST", "planned_duration_minutes": 0, "planned_kj": 0, "workout_id": None},
        ],
        "workout_blueprints": [
            {
                "workout_id": "VO2-TUE",
                "date": "2026-05-19",
                "day_role": "QUALITY",
                "intensity_domain": "VO2MAX",
                "workout_family": "VO2MAX",
                "protocol_type": "MICROBURST_SETS",
                "protocol_variant": "VO2_40_20",
                    "planned_duration_minutes": 120,
                    "planned_kj": 1500,
                "primary_tiz_target_min": 20,
                "addon_policy": "Z2_FILL",
                "activation_required": True,
                "progression_parameters": {
                    "warmup_minutes": 10,
                    "cooldown_minutes": 8,
                    "activation_profile": "VO2_STANDARD",
                    "work_duration_seconds": 40,
                    "recovery_duration_seconds": 20,
                    "work_target_by_set": ["110%-112%", "112%-115%", "115%-118%"],
                    "work_cadence": "92-95rpm",
                    "recovery_target": "50%",
                    "recovery_cadence": "85rpm",
                    "between_set_recovery_minutes": 4,
                    "between_set_recovery_target": "55%",
                    "between_set_recovery_cadence": "85rpm",
                    "set_count_min": 2,
                    "set_count_max": 4,
                    "reps_per_set_min": 8,
                    "reps_per_set_max": 15,
                    "addon_target": "68%-72%",
                    "addon_cadence": "85-95rpm",
                    "addon_min_block_minutes": 10,
                    "addon_max_block_minutes": 30,
                    "addon_step_minutes": 5,
                    "addon_max_share_of_session": 0.35,
                },
                "progression_state": {"primary_axis": "reps", "secondary_axis": "sets"},
            }
        ],
    }

    document = build_week_plan_document_from_bundle(planning_bundle=planning_bundle, week_calendar_context={"target_iso_week": "2026-21"})
    validate_week_plan_exportability(document)
    text = document["data"]["workouts"][0]["workout_text"]
    assert "10x" in text or "9x" in text or "13x" in text
    assert "- 10x " not in text
    assert "#### Z2 Add-On" in text


def test_protocol_solver_renders_threshold_classic_with_activation() -> None:
    planning_bundle = {
        "day_blueprints": [
            {"day": "Mon", "date": "2026-05-18", "day_role": "REST", "planned_duration_minutes": 0, "planned_kj": 0, "workout_id": None},
            {"day": "Tue", "date": "2026-05-19", "day_role": "QUALITY", "planned_duration_minutes": 90, "planned_kj": 1200, "workout_id": "THR-TUE"},
            {"day": "Wed", "date": "2026-05-20", "day_role": "REST", "planned_duration_minutes": 0, "planned_kj": 0, "workout_id": None},
            {"day": "Thu", "date": "2026-05-21", "day_role": "REST", "planned_duration_minutes": 0, "planned_kj": 0, "workout_id": None},
            {"day": "Fri", "date": "2026-05-22", "day_role": "REST", "planned_duration_minutes": 0, "planned_kj": 0, "workout_id": None},
            {"day": "Sat", "date": "2026-05-23", "day_role": "REST", "planned_duration_minutes": 0, "planned_kj": 0, "workout_id": None},
            {"day": "Sun", "date": "2026-05-24", "day_role": "REST", "planned_duration_minutes": 0, "planned_kj": 0, "workout_id": None},
        ],
        "workout_blueprints": [
            {
                "workout_id": "THR-TUE",
                "date": "2026-05-19",
                "day_role": "QUALITY",
                "intensity_domain": "THRESHOLD",
                "workout_family": "THRESHOLD",
                "protocol_type": "CLASSIC_INTERVALS",
                "protocol_variant": "THRESHOLD_CLASSIC",
                "planned_duration_minutes": 90,
                "planned_kj": 1200,
                "primary_tiz_target_min": 30,
                "addon_policy": "Z2_FILL",
                "activation_required": True,
                "progression_parameters": {
                    "warmup_minutes": 8,
                    "cooldown_minutes": 10,
                    "activation_profile": "THRESHOLD_STANDARD",
                    "work_target": "95%-100%",
                    "work_cadence": "85-90rpm",
                    "recovery_target": "60%",
                    "recovery_cadence": "85rpm",
                    "recovery_duration_minutes": 3,
                    "tiz_min_minutes": 24,
                    "tiz_max_minutes": 45,
                    "set_count_min": 3,
                    "set_count_max": 5,
                    "work_duration_min_minutes": 6,
                    "work_duration_max_minutes": 15,
                    "addon_target": "68%-72%",
                    "addon_cadence": "85-95rpm",
                    "addon_min_block_minutes": 10,
                    "addon_max_block_minutes": 30,
                    "addon_step_minutes": 5,
                    "addon_max_share_of_session": 0.35,
                },
                "progression_state": {"primary_axis": "tiz", "secondary_axis": "set_count"},
            }
        ],
    }

    document = build_week_plan_document_from_bundle(planning_bundle=planning_bundle, week_calendar_context={"target_iso_week": "2026-21"})
    validate_week_plan_exportability(document)
    text = document["data"]["workouts"][0]["workout_text"]
    assert "#### Activation" in text
    assert "95%-100%" in text


def test_protocol_solver_renders_tempo_over_under_intervals() -> None:
    planning_bundle = {
        "day_blueprints": [
            {"day": "Mon", "date": "2026-05-18", "day_role": "REST", "planned_duration_minutes": 0, "planned_kj": 0, "workout_id": None},
            {"day": "Tue", "date": "2026-05-19", "day_role": "REST", "planned_duration_minutes": 0, "planned_kj": 0, "workout_id": None},
            {"day": "Wed", "date": "2026-05-20", "day_role": "REST", "planned_duration_minutes": 0, "planned_kj": 0, "workout_id": None},
            {"day": "Thu", "date": "2026-05-21", "day_role": "QUALITY", "planned_duration_minutes": 85, "planned_kj": 1100, "workout_id": "OU-THU"},
            {"day": "Fri", "date": "2026-05-22", "day_role": "REST", "planned_duration_minutes": 0, "planned_kj": 0, "workout_id": None},
            {"day": "Sat", "date": "2026-05-23", "day_role": "REST", "planned_duration_minutes": 0, "planned_kj": 0, "workout_id": None},
            {"day": "Sun", "date": "2026-05-24", "day_role": "REST", "planned_duration_minutes": 0, "planned_kj": 0, "workout_id": None},
        ],
        "workout_blueprints": [
            {
                "workout_id": "OU-THU",
                "date": "2026-05-21",
                "day_role": "QUALITY",
                "intensity_domain": "TEMPO",
                "workout_family": "TEMPO",
                "protocol_type": "OVER_UNDER_INTERVALS",
                "protocol_variant": "TEMPO_OVER_UNDER",
                "planned_duration_minutes": 85,
                "planned_kj": 1100,
                "primary_tiz_target_min": 24,
                "addon_policy": "Z2_FILL",
                "progression_parameters": {
                    "warmup_minutes": 8,
                    "cooldown_minutes": 10,
                    "under_target": "95%",
                    "under_cadence": "85-90rpm",
                    "over_target": "105%",
                    "over_cadence": "90rpm",
                    "under_duration_minutes": 3,
                    "over_duration_minutes": 1,
                    "oscillation_count_min": 4,
                    "oscillation_count_max": 8,
                    "addon_target": "68%-72%",
                    "addon_cadence": "85-95rpm",
                    "addon_min_block_minutes": 10,
                    "addon_max_block_minutes": 30,
                    "addon_step_minutes": 5,
                    "addon_max_share_of_session": 0.35,
                },
                "progression_state": {"primary_axis": "oscillation_count", "secondary_axis": "tiz"},
            }
        ],
    }

    document = build_week_plan_document_from_bundle(planning_bundle=planning_bundle, week_calendar_context={"target_iso_week": "2026-21"})
    validate_week_plan_exportability(document)
    text = document["data"]["workouts"][0]["workout_text"]
    assert "4x" in text or "5x" in text or "6x" in text
    assert "95% 85-90rpm" in text
    assert "105% 90rpm" in text
