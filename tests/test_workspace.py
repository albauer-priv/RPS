"""Unit tests for workspace helpers and storage."""

import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    # Allow running tests without installing the package.
    sys.path.insert(0, str(SRC))

from rps.tools.workspace_read_tools import ReadToolContext, read_tool_handlers  # noqa: E402
from rps.workspace.api import Workspace  # noqa: E402
from rps.workspace.guards import MissingDependenciesError  # noqa: E402
from rps.workspace.helpers import (  # noqa: E402
    resolve_current_phase,
    resolve_current_week,
    upstream_ref,
)
from rps.workspace.local_store import LocalArtifactStore  # noqa: E402
from rps.workspace.types import ArtifactType  # noqa: E402


class WorkspaceHelperTests(unittest.TestCase):
    """Coverage for helper utilities."""
    def test_resolve_current_week(self) -> None:
        """Verify ISO week key formatting."""
        self.assertEqual(resolve_current_week(date(2026, 2, 3)), "2026-06")

    def test_resolve_current_phase(self) -> None:
        """Verify phase range calculation."""
        phase = resolve_current_phase("2026-06", phase_length_weeks=4)
        self.assertEqual(phase.start_week, "2026-06")
        self.assertEqual(phase.end_week, "2026-09")
        self.assertEqual(phase.range_key, "2026-06--2026-09")

    def test_upstream_ref(self) -> None:
        """Verify upstream reference formatting."""
        self.assertEqual(upstream_ref("PHASE_STRUCTURE", "2026-06--2026-09"), "PHASE_STRUCTURE:2026-06--2026-09")


class LocalStoreTests(unittest.TestCase):
    """Coverage for local store behaviors."""
    def test_list_versions_sorted(self) -> None:
        """Verify version listing is sorted in week order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalArtifactStore(root=Path(tmpdir))
            athlete_id = "ath_001"
            store.save_version(
                athlete_id=athlete_id,
                artifact_type=ArtifactType.WEEK_PLAN,
                version_key="2026-06__20260201_120000",
                payload={"foo": "bar"},
            )
            store.save_version(
                athlete_id=athlete_id,
                artifact_type=ArtifactType.WEEK_PLAN,
                version_key="2026-04__20260201_090000",
                payload={"foo": "baz"},
            )

            versions = store.list_versions(athlete_id, ArtifactType.WEEK_PLAN)
            self.assertEqual(versions, ["2026-04__20260201_090000", "2026-06__20260201_120000"])

    def test_exists_and_latest_version_key(self) -> None:
        """Verify existence checks and latest version key lookup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalArtifactStore(root=Path(tmpdir))
            athlete_id = "ath_002"
            self.assertFalse(store.latest_exists(athlete_id, ArtifactType.WEEK_PLAN))
            self.assertFalse(store.exists(athlete_id, ArtifactType.WEEK_PLAN, "2026-06"))

            store.save_version(
                athlete_id=athlete_id,
                artifact_type=ArtifactType.WEEK_PLAN,
                version_key="2026-06__20260201_120000",
                payload={"foo": "bar"},
            )
            self.assertTrue(store.latest_exists(athlete_id, ArtifactType.WEEK_PLAN))
            self.assertTrue(store.exists(athlete_id, ArtifactType.WEEK_PLAN, "2026-06"))
            self.assertEqual(
                store.get_latest_version_key(athlete_id, ArtifactType.WEEK_PLAN),
                "2026-06__20260201_120000",
            )

    def test_range_version_resolution(self) -> None:
        """Verify range-scoped versions resolve to newest timestamped version."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalArtifactStore(root=Path(tmpdir))
            athlete_id = "ath_003"
            store.save_version(
                athlete_id=athlete_id,
                artifact_type=ArtifactType.PHASE_GUARDRAILS,
                version_key="2026-05--2026-08__20260201_090000",
                payload={"foo": "bar"},
            )
            store.save_version(
                athlete_id=athlete_id,
                artifact_type=ArtifactType.PHASE_GUARDRAILS,
                version_key="2026-05--2026-08__20260201_120000",
                payload={"foo": "baz"},
            )
            self.assertTrue(store.exists(athlete_id, ArtifactType.PHASE_GUARDRAILS, "2026-05--2026-08"))

    def test_load_latest_normalizes_legacy_user_data_confidence(self) -> None:
        """Verify legacy USER data_confidence is normalized on read."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalArtifactStore(root=Path(tmpdir))
            athlete_id = "ath_004"
            store.ensure_workspace(athlete_id)
            latest_path = store.latest_path(athlete_id, ArtifactType.LOGISTICS)
            latest_path.write_text(
                json.dumps(
                    {
                        "meta": {
                            "artifact_type": "LOGISTICS",
                            "schema_id": "LogisticsInterface",
                            "schema_version": "1.0",
                            "version": "1.0",
                            "authority": "Informational",
                            "owner_agent": "User",
                            "run_id": "legacy_logistics",
                            "created_at": "2026-04-13T21:41:00Z",
                            "scope": "Context",
                            "data_confidence": "USER",
                            "trace_upstream": [],
                            "notes": "",
                        },
                        "data": {"events": []},
                    }
                ),
                encoding="utf-8",
            )

            loaded = store.load_latest(athlete_id, ArtifactType.LOGISTICS)

            self.assertIsInstance(loaded, dict)
            meta = loaded["meta"]
            self.assertEqual(meta["data_confidence"], "UNKNOWN")
            self.assertEqual(meta["iso_week"], "2026-16")
            self.assertEqual(meta["iso_week_range"], "2026-16--2026-16")
            self.assertEqual(meta["temporal_scope"], {"from": "2026-04-13", "to": "2026-04-19"})
            self.assertEqual(meta["trace_data"], [])
            self.assertEqual(meta["trace_events"], [])

    def test_load_latest_backfills_legacy_kpi_profile_meta(self) -> None:
        """Verify shared KPI profiles get canonical traceability fields on read."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalArtifactStore(root=Path(tmpdir))
            athlete_id = "ath_005"
            store.ensure_workspace(athlete_id)
            latest_path = store.latest_path(athlete_id, ArtifactType.KPI_PROFILE)
            latest_path.write_text(
                json.dumps(
                    {
                        "meta": {
                            "artifact_type": "KPI_PROFILE",
                            "schema_id": "KPIProfileInterface",
                            "schema_version": "1.0",
                            "version": "1.0",
                            "authority": "Binding",
                            "owner_agent": "Policy-Owner",
                            "run_id": "legacy_kpi_profile",
                            "created_at": "2026-01-17T06:21:32.377139+00:00",
                            "scope": "Shared",
                            "data_confidence": "UNKNOWN",
                            "trace_upstream": [
                                {"artifact": "kpi_profile_des_brevet_600_km_masters.md", "version": "1.0"}
                            ],
                            "notes": "Converted from v1 markdown spec.",
                        },
                        "data": {"profile_metadata": {"profile_id": "sample"}},
                    }
                ),
                encoding="utf-8",
            )

            loaded = store.load_latest(athlete_id, ArtifactType.KPI_PROFILE)

            self.assertIsInstance(loaded, dict)
            meta = loaded["meta"]
            self.assertEqual(meta["iso_week"], "2026-03")
            self.assertEqual(meta["iso_week_range"], "2026-03--2026-03")
            self.assertEqual(meta["temporal_scope"], {"from": "2026-01-12", "to": "2026-01-18"})
            self.assertEqual(
                meta["trace_upstream"],
                [
                    {
                        "artifact": "kpi_profile_des_brevet_600_km_masters.md",
                        "version": "1.0",
                        "run_id": "legacy_trace_1",
                    }
                ],
            )
            self.assertEqual(meta["trace_data"], [])
            self.assertEqual(meta["trace_events"], [])


class GuardTests(unittest.TestCase):
    """Coverage for dependency guard behavior."""
    def test_guard_put_requires_latest(self) -> None:
        """Verify guard_put enforces required latest dependencies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Workspace.for_athlete("ath_003", root=Path(tmpdir))
            with self.assertRaises(MissingDependenciesError):
                ws.guard_put(
                    ArtifactType.WEEK_PLAN,
                    version_key="2026-06__20260201_120000",
                    payload={"week": "2026-06"},
                    producer_agent="week_planner",
                    run_id="run_2026-06_week_001",
                )


class WorkspaceReadToolTests(unittest.TestCase):
    """Coverage for workspace read tool helpers."""

    def test_workspace_get_phase_context_includes_phase_info(self) -> None:
        """Verify phase context includes derived phase week and focus."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            store = LocalArtifactStore(root=root)
            athlete_id = "ath_006"
            store.ensure_workspace(athlete_id)
            store.save_document(
                athlete_id,
                ArtifactType.SEASON_PLAN,
                "2026-14--2026-20",
                {
                    "meta": {
                        "artifact_type": "SEASON_PLAN",
                        "schema_id": "SeasonPlanInterface",
                        "schema_version": "1.0",
                        "version": "1.0",
                        "authority": "Binding",
                        "owner_agent": "Season-Planner",
                        "run_id": "season_plan_test",
                        "created_at": "2026-04-01T00:00:00Z",
                        "scope": "Season",
                        "iso_week": "2026-14",
                        "iso_week_range": "2026-14--2026-20",
                        "temporal_scope": {"from": "2026-03-30", "to": "2026-05-17"},
                        "trace_upstream": [],
                        "trace_data": [],
                        "trace_events": [],
                        "data_confidence": "UNKNOWN",
                        "notes": "",
                    },
                    "data": {
                        "phases": [
                            {
                                "phase_id": "P02",
                                "phase_name": "Build 1",
                                "phase_type": "Build",
                                "iso_week_range": "2026-14--2026-16",
                            }
                        ]
                    },
                },
                producer_agent="test",
                run_id="season_plan_test",
                update_latest=True,
            )

            handlers = read_tool_handlers(
                ReadToolContext(
                    athlete_id=athlete_id,
                    workspace_root=root,
                    agent_name="performance_analysis",
                )
            )
            result = handlers["workspace_get_phase_context"]({"year": 2026, "week": 15})

            self.assertIsInstance(result, dict)
            self.assertTrue(result["ok"])
            self.assertEqual(result["phase_info"]["phase_id"], "P02")
            self.assertEqual(result["phase_info"]["phase_focus"], "Build 1")
            self.assertEqual(result["phase_info"]["phase_week"], 2)
            self.assertEqual(result["phase_info"]["range_key"], "2026-14--2026-16")


class SchemaRegistryTests(unittest.TestCase):
    """Coverage for schema registry validation."""
    def test_registry_validation(self) -> None:
        """Verify schema registry validation catches valid documents."""
        try:
            import jsonschema  # noqa: F401
            import referencing  # noqa: F401
        except ImportError:
            self.skipTest("jsonschema or referencing not available")

        with tempfile.TemporaryDirectory() as tmpdir:
            from rps.workspace.schema_registry import SchemaRegistry, validate_or_raise

            schema_dir = Path(tmpdir)
            meta_schema = {
                "$id": "meta.schema.json",
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                    "artifact_type": {"type": "string"},
                },
                "required": ["artifact_type"],
            }
            envelope_schema = {
                "$id": "envelope.schema.json",
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                    "meta": {"$ref": "meta.schema.json"},
                    "data": {"type": "object"},
                },
                "required": ["meta", "data"],
            }
            (schema_dir / "meta.schema.json").write_text(json.dumps(meta_schema))
            (schema_dir / "envelope.schema.json").write_text(json.dumps(envelope_schema))

            registry = SchemaRegistry(schema_dir)
            validator = registry.validator_for("envelope.schema.json")
            validate_or_raise(validator, {"meta": {"artifact_type": "TEST"}, "data": {}})


if __name__ == "__main__":
    unittest.main()
