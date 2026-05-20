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
            {"day": "Thu", "date": "2026-05-21", "day_role": "QUALITY", "planned_duration_minutes": 90, "planned_kj": 1100, "workout_id": "W-THU"},
            {"day": "Fri", "date": "2026-05-22", "day_role": "REST", "planned_duration_minutes": 0, "planned_kj": 0, "workout_id": None},
            {"day": "Sat", "date": "2026-05-23", "day_role": "ENDURANCE", "planned_duration_minutes": 210, "planned_kj": 2600, "workout_id": "W-SAT"},
            {"day": "Sun", "date": "2026-05-24", "day_role": "RECOVERY", "planned_duration_minutes": 60, "planned_kj": 600, "workout_id": "W-SUN"},
        ],
        "workout_blueprints": [
            {"workout_id": "W-TUE", "date": "2026-05-19", "day_role": "QUALITY", "intensity_domain": "TEMPO", "workout_family": "TEMPO", "planned_duration_minutes": 75, "planned_kj": 900},
            {"workout_id": "W-WED", "date": "2026-05-20", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "workout_family": "ENDURANCE", "planned_duration_minutes": 60, "planned_kj": 700},
            {"workout_id": "W-THU", "date": "2026-05-21", "day_role": "QUALITY", "intensity_domain": "SWEET_SPOT", "workout_family": "SWEET_SPOT", "planned_duration_minutes": 90, "planned_kj": 1100},
            {"workout_id": "W-SAT", "date": "2026-05-23", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "workout_family": "ENDURANCE", "planned_duration_minutes": 210, "planned_kj": 2600},
            {"workout_id": "W-SUN", "date": "2026-05-24", "day_role": "RECOVERY", "intensity_domain": "ENDURANCE", "workout_family": "ENDURANCE_LOW", "planned_duration_minutes": 60, "planned_kj": 600},
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
