from rps.orchestrator.context_snapshots import (
    build_advisory_memory_document,
    build_advisory_memory_prompt_block,
    build_athlete_state_snapshot_document,
    build_current_week_status_snapshot_document,
    build_planning_context_snapshot_document,
    ensure_current_week_status_snapshot,
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
                "selected_scenario_contract": {
                    "load_posture": "balanced_progressive",
                    "recovery_margin": "medium",
                    "specificity_density": "controlled",
                },
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
            "data": {
                "reason_context": {"intent_of_adjustment": "Protect recovery early week."},
                "inherited_scenario_contract": {
                    "specificity_density": "controlled",
                    "recovery_margin": "medium",
                },
            },
        },
    )
    prompt_blocks = snapshot["data"]["prompt_blocks"]
    assert "season" in prompt_blocks
    assert "week" in prompt_blocks
    assert "current_week_plan" in prompt_blocks
    assert "des_report" in prompt_blocks
    assert "season_phase_feed_forward" in prompt_blocks
    assert "phase_feed_forward" in prompt_blocks
    assert "selected_scenario_posture" in prompt_blocks
    assert "inherited_posture" in prompt_blocks
    assert "Tempo Session" in prompt_blocks["current_week_plan"]


def test_athlete_snapshot_includes_selected_scenario_contract(tmp_path):
    store = LocalArtifactStore(root=tmp_path)
    athlete_id = "i150546"
    store.save_document(
        athlete_id=athlete_id,
        artifact_type=ArtifactType.SEASON_SCENARIOS,
        version_key="2026-22__20260528_064757",
        document={
            "meta": {"artifact_type": "SEASON_SCENARIOS"},
            "data": {
                "planning_horizon_weeks": 16,
                "scenarios": [
                    {
                        "scenario_id": "B",
                        "name": "Balanced build",
                        "load_philosophy": "balanced_progressive",
                        "best_suited_if": ["stable recovery"],
                        "key_differences": ["balanced pressure"],
                        "main_payoff": "repeatable progression",
                        "main_cost": "less conservative than A",
                        "risk_profile": "medium",
                        "scenario_guidance": {
                            "recovery_margin": "medium",
                            "fatigue_exposure": "moderate",
                            "specificity_density": "controlled",
                            "constraint_summary": ["preserve continuity"],
                            "event_alignment_notes": ["B event rehearsal"],
                            "risk_flags": ["needs stable recovery"],
                            "kpi_guardrail_notes": ["stay repeatable"],
                            "decision_notes": ["athlete selected B"],
                            "season_archetype": "none",
                            "intensity_guidance": {"allowed_domains": ["ENDURANCE", "TEMPO"], "avoid_domains": ["VO2MAX"]},
                            "deload_cadence": "2:1:1",
                            "phase_length_weeks": 4,
                            "phase_count_expected": 4,
                            "phase_plan_summary": {"full_phases": 4, "shortened_phases": []},
                            "max_shortened_phases": 0,
                            "shortening_budget_weeks": 0,
                        },
                    }
                ]
            },
        },
        producer_agent="test",
        run_id="test",
    )
    snapshot = build_athlete_state_snapshot_document(
        store,
        athlete_id,
        target_week=IsoWeek(year=2026, week=22),
        selection_payload={
            "meta": {"artifact_type": "SEASON_SCENARIO_SELECTION", "version_key": "2026-22__sel", "run_id": "sel"},
            "data": {"selected_scenario_id": "B", "selection_source": "athlete", "selection_rationale": "Controlled progression"},
        },
    )
    assert "selected_scenario_contract" in snapshot["data"]["prompt_blocks"]
    assert "load_posture: balanced_progressive" in snapshot["data"]["prompt_blocks"]["selected_scenario_contract"]


def test_planning_snapshot_includes_inherited_posture_blocks(tmp_path):
    store = LocalArtifactStore(root=tmp_path)
    snapshot = build_planning_context_snapshot_document(
        store,
        "i150546",
        target_week=IsoWeek(year=2026, week=22),
        phase_info=type(
            "PhaseInfo",
            (),
                {
                    "phase_id": "P01",
                    "phase_name": "Base",
                    "phase_type": "BASE",
                    "phase_intent": "general_base",
                    "phase_range": type(
                        "InnerPhaseRange",
                        (),
                        {"start": IsoWeek(2026, 21), "end": IsoWeek(2026, 24), "key": "2026-21--2026-24"},
                    )(),
                    "raw": {},
                },
        )(),
        season_plan_payload={
            "meta": {"artifact_type": "SEASON_PLAN", "version_key": "sp", "run_id": "sp"},
            "data": {
                "selected_scenario_contract": {
                    "selected_scenario_id": "B",
                    "load_posture": "balanced_progressive",
                    "recovery_margin": "medium",
                    "fatigue_exposure": "moderate",
                    "specificity_density": "controlled",
                }
            },
        },
        phase_range=type(
            "PhaseRange",
            (),
            {"start": IsoWeek(2026, 21), "end": IsoWeek(2026, 24), "key": "2026-21--2026-24"},
        )(),
        phase_guardrails_payload={
            "meta": {"artifact_type": "PHASE_GUARDRAILS", "version_key": "pg", "run_id": "pg"},
            "data": {
                "inherited_scenario_contract": {
                    "selected_scenario_id": "B",
                    "load_posture": "balanced_progressive",
                    "recovery_margin": "medium",
                    "fatigue_exposure": "moderate",
                    "specificity_density": "controlled",
                }
            },
        },
    )
    blocks = snapshot["data"]["prompt_blocks"]
    assert "selected_scenario_contract" in blocks
    assert "inherited_scenario_contract" in blocks
    assert "inherited_planning_posture" in blocks


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


def test_build_current_week_status_snapshot_document_summarizes_actuals_and_plan_gap():
    snapshot = build_current_week_status_snapshot_document(
        target_week=IsoWeek(year=2026, week=20),
        week_plan_payload={
            "meta": {"artifact_type": "WEEK_PLAN", "version_key": "2026-20__20260511_080000", "run_id": "week"},
            "data": {
                "week_summary": {"planned_weekly_load_kj": 6700},
                "agenda": [
                    {
                        "day": "Tue",
                        "date": "2026-05-12",
                        "day_role": "QUALITY",
                        "planned_duration": "01:33",
                        "planned_kj": 1017,
                        "workout_id": "w1",
                    },
                    {
                        "day": "Thu",
                        "date": "2026-05-14",
                        "day_role": "ENDURANCE",
                        "planned_duration": "01:10",
                        "planned_kj": 680,
                        "workout_id": "w2",
                    },
                ],
                "workouts": [
                    {"workout_id": "w1", "title": "Tempo Stabilization", "start": "18:00", "duration": "01:33"},
                    {"workout_id": "w2", "title": "Endurance Ride", "start": "06:30", "duration": "01:10"},
                ],
            },
        },
        current_week_actual_payload={
            "meta": {"iso_week": "2026-20", "version_key": "2026-20"},
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
                    }
                ]
            },
        },
    )
    prompt_blocks = snapshot["data"]["prompt_blocks"]
    assert "current_week_actuals" in prompt_blocks
    assert "plan_vs_actual" in prompt_blocks
    assert "completed_sessions_count: 1" in prompt_blocks["current_week_actuals"]
    assert "open_planned_days_count: 1" in prompt_blocks["plan_vs_actual"]
    assert "- 2026-05-14 | Endurance Ride" in prompt_blocks["plan_vs_actual"]


def test_ensure_current_week_status_snapshot_fetches_live_current_week(monkeypatch, tmp_path):
    store = LocalArtifactStore(root=tmp_path)
    athlete_id = "i150546"
    monkeypatch.setattr(
        "rps.orchestrator.context_snapshots.date",
        type(
            "FakeDate",
            (),
            {
                "today": staticmethod(lambda: __import__("datetime").date(2026, 5, 13)),
                "fromisocalendar": __import__("datetime").date.fromisocalendar,
            },
        ),
    )
    monkeypatch.setattr(
        "rps.orchestrator.context_snapshots.fetch_current_week_activities_actual_payload",
        lambda **_: {
            "meta": {"iso_week": "2026-20", "version_key": "2026-20"},
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
                    }
                ]
            },
        },
    )

    snapshot = ensure_current_week_status_snapshot(
        store,
        athlete_id,
        target_week=IsoWeek(year=2026, week=20),
        run_id="test_run",
        week_plan_payload={},
    )

    assert snapshot["meta"]["artifact_type"] == "CURRENT_WEEK_STATUS_SNAPSHOT"
    prompt_blocks = snapshot["data"]["prompt_blocks"]
    assert "current_week_actuals" in prompt_blocks
    assert "completed_sessions_count: 1" in prompt_blocks["current_week_actuals"]
    assert store.latest_exists(athlete_id, ArtifactType.CURRENT_WEEK_STATUS_SNAPSHOT)
