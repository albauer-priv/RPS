"""Per-input-type JSON export and import for modular user inputs."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from rps.workspace.types import ArtifactType, Authority

if TYPE_CHECKING:
    from rps.workspace.local_store import LocalArtifactStore

logger = logging.getLogger(__name__)

INPUT_IO_TYPES: frozenset[ArtifactType] = frozenset(
    {
        ArtifactType.ATHLETE_PROFILE,
        ArtifactType.AVAILABILITY,
        ArtifactType.PLANNING_EVENTS,
        ArtifactType.LOGISTICS,
    }
)

_INPUT_META: dict[ArtifactType, dict[str, object]] = {
    ArtifactType.ATHLETE_PROFILE: {
        "schema_id": "AthleteProfileInterface",
        "schema_version": "1.0",
        "authority": Authority.BINDING.value,
    },
    ArtifactType.AVAILABILITY: {
        "schema_id": "AvailabilityInterface",
        "schema_version": "1.0",
        "authority": Authority.BINDING.value,
    },
    ArtifactType.PLANNING_EVENTS: {
        "schema_id": "PlanningEventsInterface",
        "schema_version": "1.0",
        "authority": Authority.BINDING.value,
    },
    ArtifactType.LOGISTICS: {
        "schema_id": "LogisticsInterface",
        "schema_version": "1.0",
        "authority": Authority.BINDING.value,
    },
}


def suggest_export_filename(athlete_id: str, artifact_type: ArtifactType) -> str:
    """Return a suggested filename for an exported input file."""
    today = datetime.now(UTC).strftime("%Y%m%d")
    return f"{athlete_id}_{artifact_type.value}_{today}.json"


def export_input(
    store: LocalArtifactStore,
    athlete_id: str,
    artifact_type: ArtifactType,
) -> bytes | None:
    """Return JSON bytes for the latest saved input, or None if none exists.

    The export envelope includes artifact_type, athlete_id, exported_at, and data.
    """
    if artifact_type not in INPUT_IO_TYPES:
        raise ValueError(f"export_input: unsupported artifact type {artifact_type.value!r}")
    path: Path = store.latest_path(athlete_id, artifact_type)
    if not path.exists():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("export_input: could not read %s: %s", path, exc)
        return None
    data = doc.get("data") if isinstance(doc, dict) else doc
    envelope = {
        "artifact_type": artifact_type.value,
        "athlete_id": athlete_id,
        "exported_at": datetime.now(UTC).isoformat(),
        "data": data,
    }
    return json.dumps(envelope, ensure_ascii=False, indent=2).encode("utf-8")


def import_input(
    store: LocalArtifactStore,
    athlete_id: str,
    artifact_type: ArtifactType,
    raw_bytes: bytes,
) -> str:
    """Parse, validate, and save an imported input JSON.

    Returns the version_key of the newly written artifact.
    Raises ValueError on type mismatch, parse error, or invalid data shape.
    """
    if artifact_type not in INPUT_IO_TYPES:
        raise ValueError(f"import_input: unsupported artifact type {artifact_type.value!r}")
    try:
        envelope = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc
    if not isinstance(envelope, dict):
        raise ValueError("Import file must be a JSON object.")
    imported_type = envelope.get("artifact_type")
    if imported_type != artifact_type.value:
        raise ValueError(
            f"Type mismatch: file contains {imported_type!r}, "
            f"expected {artifact_type.value!r}."
        )
    data = envelope.get("data")
    if not isinstance(data, (dict, list)):
        raise ValueError("Import file 'data' must be a JSON object or array.")
    run_ts = datetime.now(UTC)
    run_id = f"ui_import_{artifact_type.value.lower()}_{run_ts.strftime('%Y%m%dT%H%M%SZ')}"
    version_key = run_id
    meta = dict(_INPUT_META.get(artifact_type, {}))
    meta["version"] = "1.0"
    meta["owner_agent"] = "User"
    meta["notes"] = "Imported from file."
    store.save_version(
        athlete_id,
        artifact_type,
        version_key,
        data if isinstance(data, dict) else {"entries": data},
        payload_meta=meta,
        authority=Authority.BINDING,
        producer_agent="ui_import",
        run_id=run_id,
        update_latest=True,
    )
    logger.info("import_input: saved %s version_key=%s athlete=%s", artifact_type.value, version_key, athlete_id)
    return version_key
