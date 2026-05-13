from rps.orchestrator.context_snapshots import (
    build_advisory_memory_document,
    build_advisory_memory_prompt_block,
    build_current_week_actuals_prompt_block,
)
from rps.workspace.iso_helpers import IsoWeek
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType


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


def test_build_current_week_actuals_prompt_block_summarizes_completed_target_week_sessions(tmp_path):
    store = LocalArtifactStore(root=tmp_path)
    athlete_id = "i150546"
    store.save_document(
        athlete_id,
        ArtifactType.ACTIVITIES_ACTUAL,
        "2026-20",
        {
            "data": {
                "activities": [
                    {
                        "iso_year": 2026,
                        "iso_week": 20,
                        "day": "2026-05-12",
                        "start_time_local": "2026-05-12T18:00:00",
                        "type": "Ride",
                        "moving_time": "01:33:00",
                        "work_kj": 1017.0,
                        "load_tss": 96.0,
                        "intensity_factor": 0.78,
                    },
                    {
                        "iso_year": 2026,
                        "iso_week": 20,
                        "day": "2026-05-14",
                        "start_time_local": "2026-05-14T06:30:00",
                        "type": "Ride",
                        "moving_time": "01:10:00",
                        "work_kj": 680.0,
                        "load_tss": 58.0,
                        "intensity_factor": 0.71,
                    },
                ]
            }
        },
        producer_agent="test",
        run_id="activities_actual",
        update_latest=True,
    )

    block = build_current_week_actuals_prompt_block(
        store,
        athlete_id,
        target_week=IsoWeek(year=2026, week=20),
    )

    assert "**Current Week Actuals Snapshot**" in block
    assert "completed sessions in the current target week up to now" in block
    assert "completed_sessions_count: 2" in block
    assert "completed_moving_time: 02:43:00" in block
    assert "completed_work_kj: 1697" in block
    assert "- 2026-05-12 Ride, moving_time 01:33:00, work_kj 1017.0, load_tss 96.0, if 0.78" in block
