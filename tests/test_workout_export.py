"""Tests for deterministic workout export generation."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rps.orchestrator.workout_export import create_intervals_workouts_export  # noqa: E402
from rps.workouts.exporter import build_intervals_workouts_export  # noqa: E402
from rps.workouts.validator import (  # noqa: E402
    WorkoutValidationError,
    validate_week_plan_exportability,
)
from rps.workspace.local_store import LocalArtifactStore  # noqa: E402
from rps.workspace.types import ArtifactType  # noqa: E402


def _sample_week_plan(workout_text: str) -> dict[str, object]:
    return {
        "meta": {
            "artifact_type": "WEEK_PLAN",
            "schema_id": "WeekPlanInterface",
            "schema_version": "1.2",
            "version": "1.0",
            "authority": "Binding",
            "owner_agent": "Week-Planner",
            "run_id": "week_plan_test",
            "created_at": "2026-04-21T14:53:19Z",
            "scope": "Week",
            "iso_week": "2026-17",
            "iso_week_range": "2026-17--2026-17",
            "temporal_scope": {"from": "2026-04-20", "to": "2026-04-26"},
            "trace_upstream": [],
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "HIGH",
            "notes": "",
        },
        "data": {
            "week_summary": {
                "week_objective": "Test objective",
                "weekly_load_corridor_kj": {"min": 1, "max": 2, "notes": ""},
                "planned_weekly_load_kj": 1,
                "notes": "",
            },
            "agenda": [
                {
                    "day": "Tue",
                    "date": "2026-04-21",
                    "day_role": "ENDURANCE",
                    "planned_duration": "01:45",
                    "planned_kj": 1260,
                    "workout_id": "W-2026-17-TUE",
                }
            ]
            + [
                {
                    "day": day,
                    "date": date_value,
                    "day_role": "REST",
                    "planned_duration": "00:00",
                    "planned_kj": 0,
                    "workout_id": None,
                }
                for day, date_value in [
                    ("Mon", "2026-04-20"),
                    ("Wed", "2026-04-22"),
                    ("Thu", "2026-04-23"),
                    ("Fri", "2026-04-24"),
                    ("Sat", "2026-04-25"),
                    ("Sun", "2026-04-26"),
                ]
            ],
            "workouts": [
                {
                    "workout_id": "W-2026-17-TUE",
                    "title": "Endurance Re-Entry",
                    "date": "2026-04-21",
                    "start": "07:00",
                    "duration": "01:45:00",
                    "workout_text": workout_text,
                    "notes": "",
                }
            ],
        },
    }


class WorkoutExportTests(unittest.TestCase):
    """Coverage for deterministic workout export behavior."""

    def test_validate_week_plan_accepts_valid_ramp_and_sections(self) -> None:
        week_plan = _sample_week_plan(
            "Warmup\n- 8m ramp 50%-70% 85-90rpm\n\nMain Set\n- 89m 68% 85-92rpm\n\nCooldown\n- 8m ramp 60%-45% 80-85rpm"
        )

        validate_week_plan_exportability(week_plan)

    def test_validate_week_plan_rejects_missing_cadence(self) -> None:
        week_plan = _sample_week_plan(
            "Warmup\n- 8m ramp 50%-70%\n\nMain Set\n- 89m 68% 85-92rpm\n\nCooldown\n- 8m ramp 60%-45% 80-85rpm"
        )

        with self.assertRaises(WorkoutValidationError):
            validate_week_plan_exportability(week_plan)

    def test_build_export_maps_week_plan_to_intervals_array(self) -> None:
        week_plan = _sample_week_plan(
            "Warmup\n- 8m ramp 50%-70% 85-90rpm\n\nMain Set\n2x\n- 20m 84% 88-92rpm\n- 5m 60% 85rpm\n\nCooldown\n- 8m ramp 60%-45% 80rpm"
        )

        payload = build_intervals_workouts_export(week_plan)

        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["start_date_local"], "2026-04-21T07:00:00")
        self.assertEqual(payload[0]["category"], "WORKOUT")
        self.assertEqual(payload[0]["type"], "Ride")
        self.assertEqual(payload[0]["name"], "Endurance Re-Entry")
        self.assertIn("2x", payload[0]["description"])

    def test_create_intervals_workouts_export_stores_week_scoped_payload(self) -> None:
        week_plan = _sample_week_plan(
            "Warmup\n- 8m ramp 50%-70% 85-90rpm\n\nMain Set\n- 89m 68% 85-92rpm\n\nCooldown\n- 8m ramp 60%-45% 80-85rpm"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            store = LocalArtifactStore(root=root)
            athlete_id = "ath_001"
            store.ensure_workspace(athlete_id)
            store.save_document(
                athlete_id,
                ArtifactType.PHASE_STRUCTURE,
                "2026-17--2026-18__20260421_143500",
                {"meta": {"artifact_type": "PHASE_STRUCTURE"}, "data": {}},
                producer_agent="phase_architect",
                run_id="phase_structure_test",
                update_latest=True,
            )
            store.save_document(
                athlete_id,
                ArtifactType.WEEK_PLAN,
                "2026-17__20260421_150000",
                week_plan,
                producer_agent="week_planner",
                run_id="week_plan_test",
                update_latest=True,
            )

            result = create_intervals_workouts_export(
                store=store,
                athlete_id=athlete_id,
                year=2026,
                week=17,
                run_id="plan_hub_week_plan_2026W17_test",
                plan_mtime=None,
                needs_week_plan=False,
            )

            self.assertTrue(result["ok"])
            stored = store.load_version(athlete_id, ArtifactType.INTERVALS_WORKOUTS, "2026-17")
            self.assertIsInstance(stored, list)
            self.assertEqual(stored[0]["name"], "Endurance Re-Entry")
            self.assertEqual(stored[0]["start_date_local"], "2026-04-21T07:00:00")
            versions = store.list_versions(athlete_id, ArtifactType.INTERVALS_WORKOUTS)
            self.assertEqual(len(versions), 1)
            self.assertTrue(versions[0].startswith("2026-17__"))

    def test_create_intervals_workouts_export_returns_error_for_invalid_text(self) -> None:
        week_plan = _sample_week_plan(
            "Warmup\n- 8m ramp 50%-70%\n\nMain Set\n- 89m 68% 85-92rpm\n\nCooldown\n- 8m ramp 60%-45% 80-85rpm"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            store = LocalArtifactStore(root=root)
            athlete_id = "ath_002"
            store.ensure_workspace(athlete_id)
            store.save_document(
                athlete_id,
                ArtifactType.PHASE_STRUCTURE,
                "2026-17--2026-18__20260421_143500",
                {"meta": {"artifact_type": "PHASE_STRUCTURE"}, "data": {}},
                producer_agent="phase_architect",
                run_id="phase_structure_test",
                update_latest=True,
            )
            store.save_document(
                athlete_id,
                ArtifactType.WEEK_PLAN,
                "2026-17__20260421_150000",
                week_plan,
                producer_agent="week_planner",
                run_id="week_plan_test",
                update_latest=True,
            )

            result = create_intervals_workouts_export(
                store=store,
                athlete_id=athlete_id,
                year=2026,
                week=17,
                run_id="plan_hub_week_plan_2026W17_test",
                plan_mtime=None,
                needs_week_plan=False,
            )

            self.assertFalse(result["ok"])
            self.assertIn("W-2026-17-TUE", result["result"]["error"])
            with self.assertRaises(FileNotFoundError):
                store.load_version(athlete_id, ArtifactType.INTERVALS_WORKOUTS, "2026-17")
