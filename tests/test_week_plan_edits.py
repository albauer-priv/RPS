from __future__ import annotations

from pathlib import Path

from rps.orchestrator.week_plan_edits import (
    apply_week_plan_edit,
    load_week_plan_for_edit,
    preview_change_start_time,
    preview_move_workout,
    preview_update_workout_text,
)
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType


def _sample_week_plan() -> dict[str, object]:
    return {
        "meta": {
            "artifact_type": "WEEK_PLAN",
            "schema_id": "WeekPlanInterface",
            "schema_version": "1.2",
            "version": "1.0",
            "authority": "Binding",
            "owner_agent": "Week-Planner",
            "run_id": "seed_week_plan",
            "created_at": "2026-04-27T10:00:00Z",
            "scope": "Week",
            "iso_week": "2026-18",
            "iso_week_range": "2026-18--2026-18",
            "temporal_scope": {"from": "2026-04-27", "to": "2026-05-03"},
            "trace_upstream": [],
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "HIGH",
            "notes": "Seed week plan.",
        },
        "data": {
            "inherited_planning_posture": {
                "selected_scenario_id": "B",
                "load_posture": "balanced_progressive",
                "recovery_margin": "medium",
                "fatigue_exposure": "moderate",
                "specificity_density": "moderate",
                "season_archetype": "endurance_build",
                "allowed_intensity_domains": ["ENDURANCE", "TEMPO"],
                "forbidden_intensity_domains": ["VO2MAX"],
                "risk_flags": [],
                "phase_intent": "durability_build",
                "phase_week_role": "LOAD_1",
            },
            "effective_week_constraints": {
                "phase_intent": "durability_build",
                "phase_week_role": "LOAD_1",
                "allowed_intensity_domains": ["ENDURANCE", "TEMPO"],
                "forbidden_intensity_domains": ["VO2MAX"],
                "allowed_load_modalities": ["NONE"],
                "weekly_kj_band": {"min": 1, "max": 2000, "notes": "test band"},
            },
            "week_summary": {
                "week_objective": "Test objective.",
                "weekly_load_corridor_kj": {"min": 1000, "max": 2000, "notes": "Test band."},
                "planned_weekly_load_kj": 1500,
                "notes": "Test notes.",
            },
            "agenda": [
                {"day": "Mon", "date": "2026-04-27", "day_role": "REST", "planned_duration": "00:00", "planned_kj": 0, "workout_id": None},
                {"day": "Tue", "date": "2026-04-28", "day_role": "QUALITY", "planned_duration": "01:30", "planned_kj": 700, "workout_id": "W-2026-18-TUE"},
                {"day": "Wed", "date": "2026-04-29", "day_role": "REST", "planned_duration": "00:00", "planned_kj": 0, "workout_id": None},
                {"day": "Thu", "date": "2026-04-30", "day_role": "ENDURANCE", "planned_duration": "01:00", "planned_kj": 400, "workout_id": "W-2026-18-THU"},
                {"day": "Fri", "date": "2026-05-01", "day_role": "REST", "planned_duration": "00:00", "planned_kj": 0, "workout_id": None},
                {"day": "Sat", "date": "2026-05-02", "day_role": "ENDURANCE", "planned_duration": "03:00", "planned_kj": 400, "workout_id": "W-2026-18-SAT"},
                {"day": "Sun", "date": "2026-05-03", "day_role": "REST", "planned_duration": "00:00", "planned_kj": 0, "workout_id": None},
            ],
            "workouts": [
                {
                    "workout_id": "W-2026-18-TUE",
                    "title": "Tempo Stabilization",
                    "date": "2026-04-28",
                    "start": "18:00",
                    "duration": "01:30:00",
                    "workout_text": "Warmup\n- 10m 55% 85rpm\n\nMain Set\n- 1h 80%-82% 88-92rpm\n\nCooldown\n- 20m 55% 80rpm",
                    "notes": "Seed Tuesday workout.",
                },
                {
                    "workout_id": "W-2026-18-THU",
                    "title": "Endurance Support",
                    "date": "2026-04-30",
                    "start": "18:00",
                    "duration": "01:00:00",
                    "workout_text": "Warmup\n- 10m 55% 85rpm\n\nMain Set\n- 40m 68%-72% 85-90rpm\n\nCooldown\n- 10m 55% 80rpm",
                    "notes": "Seed Thursday workout.",
                },
                {
                    "workout_id": "W-2026-18-SAT",
                    "title": "Long Endurance Anchor",
                    "date": "2026-05-02",
                    "start": "08:00",
                    "duration": "03:00:00",
                    "workout_text": "Warmup\n- 10m 55% 85rpm\n\nMain Set\n- 2h40m 68%-72% 85-90rpm\n\nCooldown\n- 10m 55% 80rpm",
                    "notes": "Seed Saturday workout.",
                },
            ],
        },
    }


def test_preview_move_workout_transfers_agenda_and_workout_date():
    preview = preview_move_workout(
        _sample_week_plan(),
        year=2026,
        week=18,
        workout_id="W-2026-18-SAT",
        target_day="Sun",
        target_start="09:15",
    )

    assert preview.ok
    assert not preview.issues
    agenda = preview.document["data"]["agenda"]
    sat = next(row for row in agenda if row["day"] == "Sat")
    sun = next(row for row in agenda if row["day"] == "Sun")
    assert sat["workout_id"] is None
    assert sat["day_role"] == "REST"
    assert sat["planned_duration"] == "00:00"
    assert sat["planned_kj"] == 0
    assert sun["workout_id"] == "W-2026-18-SAT"
    assert sun["day_role"] == "ENDURANCE"
    workouts = preview.document["data"]["workouts"]
    moved = next(item for item in workouts if item["workout_id"] == "W-2026-18-SAT")
    assert moved["date"] == "2026-05-03"
    assert moved["start"] == "09:15"


def test_preview_change_start_time_updates_only_workout_start():
    preview = preview_change_start_time(
        _sample_week_plan(),
        workout_id="W-2026-18-TUE",
        start="19:00",
    )

    assert preview.ok
    workout = next(item for item in preview.document["data"]["workouts"] if item["workout_id"] == "W-2026-18-TUE")
    assert workout["start"] == "19:00"


def test_preview_update_workout_text_recalculates_duration_fields():
    workout_text = "Warmup\n- 10m 55% 85rpm\n\nMain Set\n- 1h 68%-72% 85-90rpm\n\nCooldown\n- 5m 55% 80rpm"
    preview = preview_update_workout_text(
        _sample_week_plan(),
        workout_id="W-2026-18-THU",
        workout_text=workout_text,
        title="Easy Endurance",
        notes="Reduced complexity.",
    )

    assert preview.ok
    workout = next(item for item in preview.document["data"]["workouts"] if item["workout_id"] == "W-2026-18-THU")
    agenda_row = next(row for row in preview.document["data"]["agenda"] if row["workout_id"] == "W-2026-18-THU")
    assert workout["title"] == "Easy Endurance"
    assert workout["notes"] == "Reduced complexity."
    assert workout["duration"] == "01:15:00"
    assert agenda_row["planned_duration"] == "01:15"


def test_preview_update_workout_text_honors_loop_duration_derivation():
    workout_text = (
        "Warmup\n- 10m 55% 85rpm\n\n"
        "Main Set\n2x\n- 20m 80% 88-92rpm\n- 5m 60% 85rpm\n\n"
        "Cooldown\n- 8m 55% 80rpm"
    )
    preview = preview_update_workout_text(
        _sample_week_plan(),
        workout_id="W-2026-18-THU",
        workout_text=workout_text,
    )

    assert preview.ok
    workout = next(item for item in preview.document["data"]["workouts"] if item["workout_id"] == "W-2026-18-THU")
    agenda_row = next(row for row in preview.document["data"]["agenda"] if row["workout_id"] == "W-2026-18-THU")
    assert workout["duration"] == "01:08:00"
    assert agenda_row["planned_duration"] == "01:08"


def test_preview_update_workout_text_canonicalizes_inline_loop_headers():
    workout_text = (
        "Warmup\n- 8m ramp 50%-70% 85-90rpm\n\n"
        "Main Set\n- 2x 20m 80% 88-92rpm\n- 5m 60% 85rpm\n\n"
        "Cooldown\n- 8m ramp 60%-45% 80-85rpm"
    )

    preview = preview_update_workout_text(
        _sample_week_plan(),
        workout_id="W-2026-18-THU",
        workout_text=workout_text,
    )

    workout = next(item for item in preview.document["data"]["workouts"] if item["workout_id"] == "W-2026-18-THU")
    assert "\n2x\n- 20m 80% 88-92rpm" in workout["workout_text"]
    assert "- 2x 20m 80% 88-92rpm" not in workout["workout_text"]


def test_apply_week_plan_edit_stores_new_week_plan_and_export(tmp_path):
    store = LocalArtifactStore(root=tmp_path)
    athlete_id = "test_athlete"
    store.ensure_workspace(athlete_id)
    week_plan = _sample_week_plan()
    store.save_document(
        athlete_id,
        ArtifactType.WEEK_PLAN,
        "2026-18",
        week_plan,
        producer_agent="week_planner",
        run_id="seed_week_plan",
        update_latest=True,
    )
    latest_phase_structure = store.latest_path(athlete_id, ArtifactType.PHASE_STRUCTURE)
    latest_phase_structure.parent.mkdir(parents=True, exist_ok=True)
    latest_phase_structure.write_text("{}", encoding="utf-8")

    document = load_week_plan_for_edit(store, athlete_id, 2026, 18)
    preview = preview_change_start_time(document, workout_id="W-2026-18-TUE", start="19:30")
    result = apply_week_plan_edit(
        workspace_root=tmp_path,
        schema_dir=Path("specs/schemas"),
        athlete_id=athlete_id,
        document=preview.document,
        run_id="test_apply_week_plan_edit",
    )

    assert result.ok
    assert result.week_plan_path
    assert result.export_path
    saved = store.load_version(athlete_id, ArtifactType.WEEK_PLAN, "2026-18")
    workouts = saved["data"]["workouts"]
    updated = next(item for item in workouts if item["workout_id"] == "W-2026-18-TUE")
    assert updated["start"] == "19:30"
    export_payload = store.load_version(athlete_id, ArtifactType.INTERVALS_WORKOUTS, "2026-18")
    assert isinstance(export_payload, list)
    assert export_payload
