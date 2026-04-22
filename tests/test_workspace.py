"""Unit tests for workspace helpers and storage."""

import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    # Allow running tests without installing the package.
    sys.path.insert(0, str(SRC))

from rps.agents.task_router import AgentTaskRouter, RouterContext  # noqa: E402
from rps.agents.tasks import AgentTask  # noqa: E402
from rps.tools.workspace_read_tools import ReadToolContext, read_tool_handlers  # noqa: E402
from rps.tools.workspace_tools import ToolContext, get_tool_handlers  # noqa: E402
from rps.workspace.api import Workspace  # noqa: E402
from rps.workspace.guards import MissingDependenciesError  # noqa: E402
from rps.workspace.helpers import (  # noqa: E402
    resolve_current_phase,
    resolve_current_week,
    upstream_ref,
)
from rps.workspace.index_manager import WorkspaceIndexManager  # noqa: E402
from rps.workspace.iso_helpers import IsoWeek  # noqa: E402
from rps.workspace.local_store import LocalArtifactStore  # noqa: E402
from rps.workspace.types import ArtifactType  # noqa: E402
from rps.workspace.versioning import derive_version_key_from_envelope  # noqa: E402


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

    def test_week_plan_version_key_prefers_iso_week_over_iso_week_range(self) -> None:
        """Verify non-range artefacts do not derive their version key from iso_week_range."""
        envelope = {
            "meta": {
                "artifact_type": "WEEK_PLAN",
                "iso_week": "2026-17",
                "iso_week_range": "2026-17--2026-17",
                "created_at": "2026-04-21T14:39:45Z",
            },
            "data": {},
        }

        version_key = derive_version_key_from_envelope(envelope, ArtifactType.WEEK_PLAN)

        self.assertTrue(version_key.startswith("2026-17__"))
        self.assertNotIn("--", version_key)

    def test_week_plan_version_key_ignores_range_shaped_meta_version_key(self) -> None:
        """Verify week-scoped artefacts ignore stale range-shaped meta.version_key values."""
        envelope = {
            "meta": {
                "artifact_type": "WEEK_PLAN",
                "iso_week": "2026-17",
                "iso_week_range": "2026-17--2026-17",
                "version_key": "2026-17--2026-17",
                "created_at": "2026-04-21T14:48:13Z",
            },
            "data": {},
        }

        version_key = derive_version_key_from_envelope(envelope, ArtifactType.WEEK_PLAN)

        self.assertTrue(version_key.startswith("2026-17__"))
        self.assertNotIn("--", version_key)

    def test_season_scenarios_version_key_uses_created_at_not_stale_meta_suffix(self) -> None:
        """Verify season-scenarios ignore stale timestamp suffixes in meta.version_key."""
        envelope = {
            "meta": {
                "artifact_type": "SEASON_SCENARIOS",
                "iso_week": "2026-17",
                "version_key": "2026-17__20260422_100346",
                "created_at": "2026-04-22T10:59:35Z",
            },
            "data": {},
        }

        version_key = derive_version_key_from_envelope(envelope, ArtifactType.SEASON_SCENARIOS)

        self.assertEqual(version_key, "2026-17__20260422_105935")


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

    def test_range_version_index_records_string_iso_week_range(self) -> None:
        """Verify index writes preserve string iso_week_range metadata for exact-range lookups."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            store = LocalArtifactStore(root=root)
            athlete_id = "ath_003b"
            payload = {
                "meta": {
                    "artifact_type": "PHASE_GUARDRAILS",
                    "version_key": "2026-05--2026-08",
                    "iso_week_range": "2026-05--2026-08",
                    "created_at": "2026-02-01T12:00:00Z",
                },
                "data": {},
            }
            store.save_document(
                athlete_id,
                ArtifactType.PHASE_GUARDRAILS,
                "2026-05--2026-08",
                payload,
                producer_agent="phase_architect",
                run_id="test_run",
                update_latest=True,
            )

            index = WorkspaceIndexManager(root=root, athlete_id=athlete_id).load()
            versions = index["artefacts"][ArtifactType.PHASE_GUARDRAILS.value]["versions"]
            record = next(iter(versions.values()))
            self.assertEqual(record["iso_week_range"], "2026-05--2026-08")

    def test_save_document_canonicalizes_envelope_meta_to_store_write(self) -> None:
        """Verify envelope writes replace stale model timestamps with the actual store write metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalArtifactStore(root=Path(tmpdir))
            athlete_id = "ath_003c"
            payload = {
                "meta": {
                    "artifact_type": "PHASE_STRUCTURE",
                    "version_key": "2026-17--2026-18__20260421_143228",
                    "iso_week_range": "2026-17--2026-18",
                    "created_at": "2026-04-21T14:32:28Z",
                    "run_id": "stale_model_run",
                },
                "data": {},
            }

            path = store.save_document(
                athlete_id,
                ArtifactType.PHASE_STRUCTURE,
                "2026-17--2026-18__20260421_143500",
                payload,
                producer_agent="phase_architect",
                run_id="actual_store_run",
                update_latest=True,
            )

            written = json.loads(Path(path).read_text(encoding="utf-8"))
            meta = written["meta"]
            self.assertEqual(meta["version_key"], "2026-17--2026-18__20260421_143500")
            self.assertEqual(meta["run_id"], "actual_store_run")
            self.assertNotEqual(meta["created_at"], "2026-04-21T14:32:28Z")

    def test_save_document_week_scoped_envelope_uses_store_write_time_for_version_key(self) -> None:
        """Verify week-scoped envelope writes ignore stale payload timestamps for the stored key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalArtifactStore(root=Path(tmpdir))
            athlete_id = "ath_003d"
            payload = {
                "meta": {
                    "artifact_type": "SEASON_SCENARIOS",
                    "iso_week": "2026-17",
                    "version_key": "2026-17__20260422_100346",
                    "created_at": "2026-04-22",
                    "run_id": "stale_model_run",
                },
                "data": {},
            }

            with patch(
                "rps.workspace.local_store.utc_iso_now",
                return_value="2026-04-22T11:08:52Z",
            ):
                path = store.save_document(
                    athlete_id,
                    ArtifactType.SEASON_SCENARIOS,
                    "2026-17",
                    payload,
                    producer_agent="season_scenario",
                    run_id="actual_store_run",
                    update_latest=True,
                )

            written = json.loads(Path(path).read_text(encoding="utf-8"))
            meta = written["meta"]
            self.assertEqual(path.name, "season_scenarios_2026-17__20260422_110852.json")
            self.assertEqual(meta["version_key"], "2026-17__20260422_110852")
            self.assertEqual(meta["created_at"], "2026-04-22T11:08:52Z")
            self.assertEqual(meta["run_id"], "actual_store_run")

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

    def test_workspace_get_latest_warns_for_week_sensitive_artifact(self) -> None:
        """Verify latest reads expose a warning for week-sensitive artefacts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            store = LocalArtifactStore(root=root)
            athlete_id = "ath_007"
            store.ensure_workspace(athlete_id)
            store.save_document(
                athlete_id,
                ArtifactType.ACTIVITIES_TREND,
                "2026-15",
                {"meta": {"artifact_type": "ACTIVITIES_TREND"}, "data": {}},
                producer_agent="test",
                run_id="activities_trend_test",
                update_latest=True,
            )
            handlers = read_tool_handlers(
                ReadToolContext(
                    athlete_id=athlete_id,
                    workspace_root=root,
                    agent_name="coach",
                )
            )

            result = handlers["workspace_get_latest"]({"artifact_type": "ACTIVITIES_TREND"})

            self.assertIsInstance(result, dict)
            self.assertIn("_tool_warning", result)
            self.assertIn("week-sensitive", result["_tool_warning"])

    def test_workspace_tools_get_latest_warns_for_week_sensitive_artifact(self) -> None:
        """Verify validated workspace tools expose the same latest-warning guidance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            store = LocalArtifactStore(root=root)
            athlete_id = "ath_010"
            store.ensure_workspace(athlete_id)
            store.save_document(
                athlete_id,
                ArtifactType.DES_ANALYSIS_REPORT,
                "2026-15",
                {"meta": {"artifact_type": "DES_ANALYSIS_REPORT"}, "data": {}},
                producer_agent="test",
                run_id="des_analysis_report_test",
                update_latest=True,
            )
            handlers = get_tool_handlers(
                ToolContext(
                    athlete_id=athlete_id,
                    agent_name="performance_analysis",
                    workspace_root=root,
                    schema_dir=ROOT / "specs" / "schemas",
                )
            )

            result = handlers["workspace_get_latest"]({"artifact_type": "DES_ANALYSIS_REPORT"})

            self.assertIsInstance(result, dict)
            self.assertIn("_tool_warning", result)
            self.assertIn("week-sensitive", result["_tool_warning"])


class TaskRouterTests(unittest.TestCase):
    """Coverage for task router week-scoped decisions."""

    def test_route_analysis_requires_target_week_activity_versions(self) -> None:
        """Verify analysis routing does not rely on unrelated latest week artefacts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            store = LocalArtifactStore(root=root)
            athlete_id = "ath_008"
            store.ensure_workspace(athlete_id)
            season_plan = {
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
                "data": {"phases": []},
            }
            generic = {"meta": {"artifact_type": "TEST"}, "data": {}}
            for artifact_type, version_key, payload in (
                (ArtifactType.SEASON_PLAN, "2026-14--2026-20", season_plan),
                (ArtifactType.KPI_PROFILE, "sample_profile", generic),
                (ArtifactType.ACTIVITIES_ACTUAL, "2026-15", generic),
                (ArtifactType.ACTIVITIES_TREND, "2026-15", generic),
            ):
                store.save_document(
                    athlete_id,
                    artifact_type,
                    version_key,
                    payload,
                    producer_agent="test",
                    run_id=f"store_{artifact_type.value.lower()}",
                    update_latest=True,
                )

            router = AgentTaskRouter(RouterContext(Workspace.for_athlete(athlete_id, root=root)))
            tasks = router.route_analysis(IsoWeek(2026, 14))

            self.assertEqual(tasks, [])

    def test_route_analysis_creates_report_for_target_week_when_inputs_exist(self) -> None:
        """Verify analysis routing schedules DES report when target-week inputs are available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            store = LocalArtifactStore(root=root)
            athlete_id = "ath_009"
            store.ensure_workspace(athlete_id)
            season_plan = {
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
                "data": {"phases": []},
            }
            generic = {"meta": {"artifact_type": "TEST"}, "data": {}}
            for artifact_type, version_key, payload, update_latest in (
                (ArtifactType.SEASON_PLAN, "2026-14--2026-20", season_plan, True),
                (ArtifactType.KPI_PROFILE, "sample_profile", generic, True),
                (ArtifactType.ACTIVITIES_ACTUAL, "2026-15", generic, True),
                (ArtifactType.ACTIVITIES_TREND, "2026-15", generic, True),
                (ArtifactType.ACTIVITIES_ACTUAL, "2026-14", generic, False),
                (ArtifactType.ACTIVITIES_TREND, "2026-14", generic, False),
            ):
                store.save_document(
                    athlete_id,
                    artifact_type,
                    version_key,
                    payload,
                    producer_agent="test",
                    run_id=f"store_{artifact_type.value.lower()}_{version_key}",
                    update_latest=update_latest,
                )

            router = AgentTaskRouter(RouterContext(Workspace.for_athlete(athlete_id, root=root)))
            tasks = router.route_analysis(IsoWeek(2026, 14))

            self.assertEqual(tasks, [AgentTask.CREATE_DES_ANALYSIS_REPORT])


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
