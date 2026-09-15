"""Tests for per-input-type JSON export/import (FEAT_user_inputs_io)."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from rps.workspace.input_io import (
    INPUT_IO_TYPES,
    export_input,
    import_input,
    suggest_export_filename,
)
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType, Authority


def _make_store(root: Path) -> LocalArtifactStore:
    return LocalArtifactStore(root=root)


def _save_input(store: LocalArtifactStore, athlete_id: str, artifact_type: ArtifactType, data: dict) -> None:
    run_ts = datetime.now(UTC)
    store.save_version(
        athlete_id,
        artifact_type,
        f"ui_test_{run_ts.strftime('%Y%m%dT%H%M%SZ')}",
        data,
        authority=Authority.BINDING,
        producer_agent="test",
        run_id="run_test",
        update_latest=True,
    )


# ---------------------------------------------------------------------------
# suggest_export_filename
# ---------------------------------------------------------------------------

def test_suggest_export_filename_includes_athlete_and_type(tmp_path: Path) -> None:
    name = suggest_export_filename("ath1", ArtifactType.ATHLETE_PROFILE)
    assert "ath1" in name
    assert "ATHLETE_PROFILE" in name
    assert name.endswith(".json")


def test_suggest_export_filename_all_input_types(tmp_path: Path) -> None:
    for artifact_type in INPUT_IO_TYPES:
        name = suggest_export_filename("ath", artifact_type)
        assert artifact_type.value in name


# ---------------------------------------------------------------------------
# export_input
# ---------------------------------------------------------------------------

def test_export_input_no_artifact_returns_none(tmp_path: Path) -> None:
    store = _make_store(tmp_path)
    store.ensure_workspace("ath1")
    result = export_input(store, "ath1", ArtifactType.ATHLETE_PROFILE)
    assert result is None


def test_export_input_returns_bytes_with_data(tmp_path: Path) -> None:
    store = _make_store(tmp_path)
    _save_input(store, "ath1", ArtifactType.ATHLETE_PROFILE, {"profile": {"athlete_name": "Alice"}})
    result = export_input(store, "ath1", ArtifactType.ATHLETE_PROFILE)
    assert result is not None
    envelope = json.loads(result)
    assert envelope["artifact_type"] == "ATHLETE_PROFILE"
    assert envelope["athlete_id"] == "ath1"
    assert "exported_at" in envelope
    assert envelope["data"] == {"profile": {"athlete_name": "Alice"}}


def test_export_input_all_supported_types(tmp_path: Path) -> None:
    store = _make_store(tmp_path)
    for artifact_type in INPUT_IO_TYPES:
        _save_input(store, "ath1", artifact_type, {"type_test": artifact_type.value})
        result = export_input(store, "ath1", artifact_type)
        assert result is not None
        envelope = json.loads(result)
        assert envelope["artifact_type"] == artifact_type.value


def test_export_input_unsupported_type_raises(tmp_path: Path) -> None:
    store = _make_store(tmp_path)
    with pytest.raises(ValueError, match="unsupported"):
        export_input(store, "ath1", ArtifactType.SEASON_PLAN)


# ---------------------------------------------------------------------------
# import_input
# ---------------------------------------------------------------------------

def _make_envelope(artifact_type: ArtifactType, data: dict, *, bad_type: str | None = None) -> bytes:
    envelope = {
        "artifact_type": bad_type if bad_type is not None else artifact_type.value,
        "athlete_id": "ath1",
        "exported_at": datetime.now(UTC).isoformat(),
        "data": data,
    }
    return json.dumps(envelope).encode("utf-8")


def test_import_input_round_trip(tmp_path: Path) -> None:
    store = _make_store(tmp_path)
    data = {"profile": {"athlete_name": "Bob"}, "objectives": {}}
    raw = _make_envelope(ArtifactType.ATHLETE_PROFILE, data)
    version_key = import_input(store, "ath1", ArtifactType.ATHLETE_PROFILE, raw)
    assert version_key

    path = store.latest_path("ath1", ArtifactType.ATHLETE_PROFILE)
    assert path.exists()
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["data"] == data


def test_import_input_type_mismatch_raises(tmp_path: Path) -> None:
    store = _make_store(tmp_path)
    raw = _make_envelope(ArtifactType.ATHLETE_PROFILE, {}, bad_type="LOGISTICS")
    with pytest.raises(ValueError, match="Type mismatch"):
        import_input(store, "ath1", ArtifactType.ATHLETE_PROFILE, raw)


def test_import_input_invalid_json_raises(tmp_path: Path) -> None:
    store = _make_store(tmp_path)
    with pytest.raises(ValueError, match="Invalid JSON"):
        import_input(store, "ath1", ArtifactType.ATHLETE_PROFILE, b"not json")


def test_import_input_non_object_raises(tmp_path: Path) -> None:
    store = _make_store(tmp_path)
    with pytest.raises(ValueError, match="JSON object"):
        import_input(store, "ath1", ArtifactType.ATHLETE_PROFILE, b'"a string"')


def test_import_input_null_data_raises(tmp_path: Path) -> None:
    store = _make_store(tmp_path)
    envelope = {"artifact_type": "ATHLETE_PROFILE", "data": None}
    with pytest.raises(ValueError, match="data.*object or array"):
        import_input(store, "ath1", ArtifactType.ATHLETE_PROFILE, json.dumps(envelope).encode())


def test_import_input_all_supported_types(tmp_path: Path) -> None:
    store = _make_store(tmp_path)
    for artifact_type in INPUT_IO_TYPES:
        raw = _make_envelope(artifact_type, {"test_key": artifact_type.value})
        version_key = import_input(store, "ath1", artifact_type, raw)
        assert version_key
        path = store.latest_path("ath1", artifact_type)
        assert path.exists()


def test_import_input_unsupported_type_raises(tmp_path: Path) -> None:
    store = _make_store(tmp_path)
    with pytest.raises(ValueError, match="unsupported"):
        import_input(store, "ath1", ArtifactType.SEASON_PLAN, b"{}")


def test_export_then_import_round_trip(tmp_path: Path) -> None:
    store = _make_store(tmp_path)
    original_data = {
        "profile": {"athlete_name": "Carol", "age": 35},
        "objectives": {"primary": "Complete brevet"},
    }
    _save_input(store, "ath1", ArtifactType.ATHLETE_PROFILE, original_data)
    exported = export_input(store, "ath1", ArtifactType.ATHLETE_PROFILE)
    assert exported is not None

    store2 = _make_store(tmp_path)
    store2.ensure_workspace("ath2")
    import_input(store2, "ath2", ArtifactType.ATHLETE_PROFILE, exported)
    path = store2.latest_path("ath2", ArtifactType.ATHLETE_PROFILE)
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["data"] == original_data
