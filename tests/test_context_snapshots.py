from rps.orchestrator.context_snapshots import (
    build_advisory_memory_document,
    build_advisory_memory_prompt_block,
)
from rps.workspace.iso_helpers import IsoWeek


def test_build_advisory_memory_document_collects_recent_output_summaries():
    snapshot = build_advisory_memory_document(
        target_week=IsoWeek(year=2026, week=18),
        season_plan_payload={
            "meta": {"artifact_type": "SEASON_PLAN", "version_key": "2026-17__20260424_123613", "run_id": "season"},
            "data": {
                "season_objective": "Peak for the A-event.",
                "phases": [{"phase_type": "peak_bridge", "label": "P01"}],
            },
        },
        week_plan_payload={
            "meta": {"artifact_type": "WEEK_PLAN", "version_key": "2026-18__20260427_102637", "run_id": "week"},
            "data": {
                "week_summary": {"week_objective": "Absorb and rebuild.", "planned_weekly_load_kj": 8028},
                "agenda": [
                    {
                        "day": "Tue",
                        "date": "2026-04-28",
                        "day_role": "QUALITY",
                        "planned_duration": "01:30",
                        "planned_kj": 980,
                        "workout_id": "w1",
                    }
                ],
                "workouts": [{"workout_id": "w1", "title": "Tempo Session", "start": "18:00", "duration": "01:30"}],
            },
        },
        des_analysis_payload={
            "meta": {"artifact_type": "DES_ANALYSIS_REPORT", "version_key": "2026-18__20260427_090000", "run_id": "des"},
            "data": {"recommendation": {"suggested_considerations": ["Protect freshness"], "rationale": ["High fatigue"]}},
        },
        season_phase_feed_forward_payload={
            "meta": {"artifact_type": "SEASON_PHASE_FEED_FORWARD", "version_key": "2026-18__20260427_091000", "run_id": "sff"},
            "data": {
                "decision_summary": {"conclusion": "Reduce corridor slightly."},
                "phase_adjustment": {
                    "adjustments": {
                        "kj_corridor": {"direction": "down", "percent": 5},
                        "quality_density": {"action": "hold", "details": "Keep one quality day."},
                    }
                },
            },
        },
        phase_feed_forward_payload={
            "meta": {"artifact_type": "PHASE_FEED_FORWARD", "version_key": "2026-18__20260427_092000", "run_id": "pff"},
            "data": {"reason_context": {"intent_of_adjustment": "Protect recovery early week."}},
        },
    )
    prompt_blocks = snapshot["data"]["prompt_blocks"]
    assert "season" in prompt_blocks
    assert "week" in prompt_blocks
    assert "current_week_plan" in prompt_blocks
    assert "des_report" in prompt_blocks
    assert "season_phase_feed_forward" in prompt_blocks
    assert "phase_feed_forward" in prompt_blocks
    assert "Tempo Session" in prompt_blocks["current_week_plan"]


def test_build_advisory_memory_prompt_block_marks_memory_as_non_binding():
    snapshot = build_advisory_memory_document(
        target_week=IsoWeek(year=2026, week=18),
        week_plan_payload={
            "meta": {"artifact_type": "WEEK_PLAN", "version_key": "2026-18__20260427_102637", "run_id": "week"},
            "data": {"week_summary": {"week_objective": "Absorb and rebuild."}},
        },
    )
    block = build_advisory_memory_prompt_block(snapshot)
    assert "**Advisory Memory**" in block
    assert "non-binding narrative context" in block
    assert "week_objective: Absorb and rebuild." in block
