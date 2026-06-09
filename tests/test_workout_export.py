"""Tests for deterministic workout export generation."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rps.agents.tasks import AgentTask, OutputSpec  # noqa: E402
from rps.orchestrator.workout_export import run_workout_export  # noqa: E402
from rps.workouts.exporter import build_workout_export_payload  # noqa: E402
from rps.workouts.validator import (  # noqa: E402
    WorkoutValidationError,
    collect_week_plan_export_issues,
    validate_week_plan_exportability,
)
from rps.workouts.week_plan_consistency import (  # noqa: E402
    derive_workout_duration_hhmmss,
    normalize_week_plan_consistency,
)
from rps.workspace.guarded_store import GuardedValidatedStore  # noqa: E402
from rps.workspace.local_store import LocalArtifactStore  # noqa: E402
from rps.workspace.schema_registry import SchemaValidationError  # noqa: E402
from rps.workspace.types import ArtifactType  # noqa: E402


def _sample_week_plan(workout_text: str) -> dict[str, object]:
    return {
        "meta": {
            "artifact_type": "WEEK_PLAN",
            "schema_id": "WeekPlanInterface",
            "schema_version": "1.2",
            "version": "1.0",
            "version_key": "2026-17__20260421_150000",
            "authority": "Binding",
            "owner_agent": "Week-Artifact-Writer",
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
                "week_objective": "Test objective",
                "weekly_load_corridor_kj": {"min": 1, "max": 2000, "notes": "test band"},
                "planned_weekly_load_kj": 1260,
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

    def test_validate_week_plan_rejects_missing_step_duration(self) -> None:
        week_plan = _sample_week_plan(
            "Warmup\n- 8m ramp 50%-70% 85-90rpm\n\nMain Set\n- 68% 85-92rpm\n\nCooldown\n- 8m ramp 60%-45% 80-85rpm"
        )

        with self.assertRaises(WorkoutValidationError):
            validate_week_plan_exportability(week_plan)

    def test_validate_week_plan_rejects_missing_required_activation(self) -> None:
        week_plan = _sample_week_plan(
            "Warmup\n- 8m ramp 50%-70% 85-90rpm\n\nMain Set\n- 20m 90% 88-92rpm\n\nCooldown\n- 8m ramp 60%-45% 80-85rpm"
        )
        week_plan["data"]["workouts"][0]["title"] = "Sweet Spot Development"

        issues = [issue.format() for issue in collect_week_plan_export_issues(week_plan)]

        self.assertTrue(any("Activation section is required" in issue for issue in issues))

    def test_validate_week_plan_rejects_section_order_violation(self) -> None:
        week_plan = _sample_week_plan(
            "Main Set\n- 20m 70% 85rpm\n\nWarmup\n- 8m ramp 50%-70% 85-90rpm\n\nCooldown\n- 8m ramp 60%-45% 80-85rpm"
        )

        issues = [issue.format() for issue in collect_week_plan_export_issues(week_plan)]

        self.assertTrue(any("workout sections are out of policy order" in issue for issue in issues))

    def test_validate_week_plan_rejects_prose_workout_text(self) -> None:
        week_plan = _sample_week_plan(
            "Warmup: 20 min progressive spin, power 160-190 W, cadence 90-95 rpm.\n"
            "Main Set: 3 x 25 min steady Z2 endurance, power 185-205 W.\n"
            "Cooldown: 15 min easy spin, power 120-150 W."
        )

        issues = [issue.format() for issue in collect_week_plan_export_issues(week_plan)]

        self.assertTrue(any("step line" in issue or "no sections" in issue or "forbidden" in issue.lower() for issue in issues))

    def test_build_export_maps_week_plan_to_intervals_array(self) -> None:
        week_plan = _sample_week_plan(
            "Warmup\n- 8m ramp 50%-70% 85-90rpm\n\nMain Set\n2x\n- 20m 84% 88-92rpm\n- 5m 60% 85rpm\n\nCooldown\n- 8m ramp 60%-45% 80rpm"
        )

        payload = build_workout_export_payload(week_plan)

        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["start_date_local"], "2026-04-21T07:00:00")
        self.assertEqual(payload[0]["category"], "WORKOUT")
        self.assertEqual(payload[0]["type"], "Ride")
        self.assertEqual(payload[0]["name"], "Endurance Re-Entry")
        self.assertIn("2x", payload[0]["description"])

    def test_derive_workout_duration_honors_simple_loop_blocks(self) -> None:
        text = (
            "Warmup\n- 10m ramp 50%-70% 85-90rpm\n\n"
            "Main Set\n2x\n- 20m 80% 88-92rpm\n- 5m 60% 85rpm\n\n"
            "Cooldown\n- 8m ramp 60%-45% 80-85rpm"
        )
        self.assertEqual(derive_workout_duration_hhmmss(text), "01:08:00")

    def test_normalize_week_plan_repairs_sentinel_duration_and_agenda_kj(self) -> None:
        week_plan = _sample_week_plan(
            "Warmup\n- 10m ramp 50%-68% 85-90rpm\n\nMain Set\n- 1h27m 70% 85-92rpm\n\nCooldown\n- 8m ramp 60%-45% 80-85rpm"
        )
        week_plan["data"]["week_summary"]["notes"] = "Weekly planned_kJ mechanical total across agenda = 0."
        week_plan["data"]["agenda"][0]["planned_duration"] = "00:00"
        week_plan["data"]["agenda"][0]["planned_kj"] = 0
        week_plan["data"]["workouts"][0]["duration"] = "00:00:01"
        week_plan["data"]["workouts"][0]["notes"] = "ENDURANCE. planned_kJ 1260; planned_Load_kJ 1280."

        normalized = normalize_week_plan_consistency(week_plan)

        agenda_row = normalized["data"]["agenda"][0]
        workout = normalized["data"]["workouts"][0]
        self.assertEqual(agenda_row["planned_duration"], "01:45")
        self.assertEqual(agenda_row["planned_kj"], 1260)
        self.assertEqual(workout["duration"], "01:45:00")
        self.assertIn("= 1260.", normalized["data"]["week_summary"]["notes"])

    def test_normalize_week_plan_overrides_duration_drift_from_workout_text(self) -> None:
        week_plan = _sample_week_plan(
            "Warmup\n- 10m ramp 50%-75% 85-90rpm\n\nMain Set\n- 90m 80%-82% 88-92rpm\n\nCooldown\n- 8m ramp 60%-45% 80-85rpm"
        )
        week_plan["data"]["agenda"][0]["planned_duration"] = "01:50"
        week_plan["data"]["workouts"][0]["duration"] = "01:50:00"

        normalized = normalize_week_plan_consistency(week_plan)

        agenda_row = normalized["data"]["agenda"][0]
        workout = normalized["data"]["workouts"][0]
        self.assertEqual(agenda_row["planned_duration"], "01:48")
        self.assertEqual(workout["duration"], "01:48:00")

    def test_validate_week_plan_rejects_linked_zero_duration_and_zero_kj(self) -> None:
        week_plan = _sample_week_plan(
            "Warmup\n- 8m ramp 50%-70% 85-90rpm\n\nMain Set\n- 89m 68% 85-92rpm\n\nCooldown\n- 8m ramp 60%-45% 80-85rpm"
        )
        week_plan["data"]["agenda"][0]["planned_duration"] = "00:00"
        week_plan["data"]["agenda"][0]["planned_kj"] = 0
        week_plan["data"]["workouts"][0]["duration"] = "00:00:01"
        week_plan["data"]["workouts"][0]["notes"] = ""

        issues = [issue.format() for issue in collect_week_plan_export_issues(week_plan)]

        self.assertTrue(any("invalid duration metadata" in issue for issue in issues))
        self.assertTrue(any("non-zero planned_duration" in issue for issue in issues))
        self.assertTrue(any("positive planned_kj" in issue for issue in issues))

    def test_run_workout_export_stores_week_scoped_payload(self) -> None:
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

            result = run_workout_export(
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

    def test_run_workout_export_returns_error_for_invalid_text(self) -> None:
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

            result = run_workout_export(
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

    def test_guarded_store_rejects_non_exportable_week_plan(self) -> None:
        week_plan = _sample_week_plan(
            "Warmup\n- 8m ramp 50%-70% 85-90rpm\n\nMain Set\n- 3x\n- 10m 84% 88-92rpm\n\nCooldown\n- 8m ramp 60%-45% 80-85rpm"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            guarded = GuardedValidatedStore(
                athlete_id="ath_003",
                schema_dir=Path("specs/schemas"),
                workspace_root=root,
            )
            guarded.store.ensure_workspace("ath_003")
            guarded.store.save_document(
                "ath_003",
                ArtifactType.PHASE_STRUCTURE,
                "2026-17--2026-19__20260424_094939",
                {"meta": {"artifact_type": "PHASE_STRUCTURE"}, "data": {}},
                producer_agent="phase_architect",
                run_id="phase_structure_test",
                update_latest=True,
            )

            with self.assertRaises(SchemaValidationError) as exc:
                guarded.guard_put_validated(
                    output_spec=OutputSpec(
                        task=AgentTask.CREATE_WEEK_PLAN,
                        artifact_type=ArtifactType.WEEK_PLAN,
                        schema_file="week_plan.schema.json",
                        tool_name="store_week_plan",
                        envelope=True,
                    ),
                    document=week_plan,
                    run_id="week_plan_test",
                    producer_agent="week_planner",
                    update_latest=True,
                )

            self.assertTrue(
                any(
                    "step line does not match the cycling workout subset" in error
                    for error in exc.exception.errors
                )
            )

    def test_guarded_store_normalizes_repairable_week_plan_consistency(self) -> None:
        week_plan = _sample_week_plan(
            "Warmup\n- 10m ramp 50%-68% 85-90rpm\n\nMain Set\n- 1h27m 70% 85-92rpm\n\nCooldown\n- 8m ramp 60%-45% 80-85rpm"
        )
        week_plan["data"]["week_summary"]["notes"] = "Weekly planned_kJ mechanical total across agenda = 0."
        week_plan["data"]["agenda"][0]["planned_duration"] = "00:00"
        week_plan["data"]["agenda"][0]["planned_kj"] = 0
        week_plan["data"]["workouts"][0]["duration"] = "00:00:01"
        week_plan["data"]["workouts"][0]["notes"] = "ENDURANCE. planned_kJ 1260; planned_Load_kJ 1280."
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            guarded = GuardedValidatedStore(
                athlete_id="ath_004",
                schema_dir=Path("specs/schemas"),
                workspace_root=root,
            )
            guarded.store.ensure_workspace("ath_004")
            guarded.store.save_document(
                "ath_004",
                ArtifactType.PHASE_STRUCTURE,
                "2026-17--2026-19__20260424_094939",
                {"meta": {"artifact_type": "PHASE_STRUCTURE"}, "data": {}},
                producer_agent="phase_architect",
                run_id="phase_structure_test",
                update_latest=True,
            )

            guarded.guard_put_validated(
                output_spec=OutputSpec(
                    task=AgentTask.CREATE_WEEK_PLAN,
                    artifact_type=ArtifactType.WEEK_PLAN,
                    schema_file="week_plan.schema.json",
                    tool_name="store_week_plan",
                    envelope=True,
                ),
                document=week_plan,
                run_id="week_plan_test",
                producer_agent="week_planner",
                update_latest=True,
            )

            saved = guarded.store.load_version("ath_004", ArtifactType.WEEK_PLAN, "2026-17")
            agenda_row = saved["data"]["agenda"][0]
            workout = saved["data"]["workouts"][0]
            self.assertEqual(agenda_row["planned_duration"], "01:45")
            self.assertEqual(agenda_row["planned_kj"], 1260)
            self.assertEqual(workout["duration"], "01:45:00")

    def test_guarded_store_rejects_unrepairable_week_plan_consistency(self) -> None:
        week_plan = _sample_week_plan(
            "Warmup\n- 8m ramp 50%-70% 85-90rpm\n\nMain Set\n- 89m 68% 85-92rpm\n\nCooldown\n- 8m ramp 60%-45% 80-85rpm"
        )
        week_plan["data"]["agenda"][0]["planned_duration"] = "00:00"
        week_plan["data"]["agenda"][0]["planned_kj"] = 0
        week_plan["data"]["workouts"][0]["duration"] = "00:00:01"
        week_plan["data"]["workouts"][0]["notes"] = ""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            guarded = GuardedValidatedStore(
                athlete_id="ath_005",
                schema_dir=Path("specs/schemas"),
                workspace_root=root,
            )
            guarded.store.ensure_workspace("ath_005")
            guarded.store.save_document(
                "ath_005",
                ArtifactType.PHASE_STRUCTURE,
                "2026-17--2026-19__20260424_094939",
                {"meta": {"artifact_type": "PHASE_STRUCTURE"}, "data": {}},
                producer_agent="phase_architect",
                run_id="phase_structure_test",
                update_latest=True,
            )

            with self.assertRaises(SchemaValidationError) as exc:
                guarded.guard_put_validated(
                    output_spec=OutputSpec(
                        task=AgentTask.CREATE_WEEK_PLAN,
                        artifact_type=ArtifactType.WEEK_PLAN,
                        schema_file="week_plan.schema.json",
                        tool_name="store_week_plan",
                        envelope=True,
                    ),
                    document=week_plan,
                    run_id="week_plan_test",
                    producer_agent="week_planner",
                    update_latest=True,
                )

            self.assertTrue(any("positive planned_kj" in error for error in exc.exception.errors))
