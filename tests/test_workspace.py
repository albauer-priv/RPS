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
