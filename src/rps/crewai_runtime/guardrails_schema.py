"""Artifact-envelope and JSON-Schema guardrails for CrewAI persisted outputs."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from rps.crewai_runtime.guardrails_context import GuardrailResult
from rps.crewai_runtime.guardrails_utilities import _coerce_mapping
from rps.crewai_runtime.schema_backed_models import _normalize_schema_backed_metadata
from rps.workspace.schema_map import ARTIFACT_SCHEMA_FILE
from rps.workspace.schema_registry import SchemaRegistry, SchemaValidationError, validate_or_raise
from rps.workspace.types import ArtifactType

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_DIR = ROOT / "specs" / "schemas"

def artifact_envelope_basic(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Artifact output must decode to a JSON object.")
    meta = mapping.get("meta")
    data = mapping.get("data")
    if not isinstance(meta, dict) or not isinstance(data, dict):
        return (False, "Artifact output must include top-level 'meta' and 'data' objects.")
    return (True, mapping)


def artifact_meta_data_present(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Artifact output must decode to a JSON object.")
    meta = mapping.get("meta")
    if not isinstance(meta, dict):
        return (False, "Artifact output missing meta object.")
    required = ("artifact_type", "schema_id")
    missing = [field for field in required if not meta.get(field)]
    if missing:
        return (False, f"Artifact meta missing required fields: {', '.join(missing)}")
    if not isinstance(mapping.get("data"), dict):
        return (False, "Artifact output missing data object.")
    return (True, mapping)


@lru_cache(maxsize=1)
def _schema_registry() -> SchemaRegistry:
    return SchemaRegistry(SCHEMA_DIR)


def artifact_schema_valid(result: Any) -> GuardrailResult:
    """Validate a persisted artifact output against its canonical JSON Schema."""

    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Artifact output must decode to a JSON object.")
    meta = mapping.get("meta")
    if not isinstance(meta, dict):
        return (False, "Artifact output missing meta object.")
    artifact_type_raw = str(meta.get("artifact_type") or "").strip().upper()
    if not artifact_type_raw:
        return (False, "Artifact meta missing artifact_type.")
    try:
        artifact_type = ArtifactType(artifact_type_raw)
    except ValueError:
        return (False, f"Unknown artifact_type for schema validation: {artifact_type_raw}.")
    schema_file = ARTIFACT_SCHEMA_FILE.get(artifact_type)
    if not schema_file:
        return (False, f"No JSON schema mapping registered for artifact_type {artifact_type_raw}.")
    try:
        schema = _schema_registry().get_schema(schema_file)
        mapping = _normalize_schema_backed_metadata(mapping, schema)
        validator = _schema_registry().validator_for(schema_file)
        validate_or_raise(validator, mapping)
    except SchemaValidationError as exc:
        details = "; ".join(exc.errors[:8])
        if len(exc.errors) > 8:
            details += f"; ... and {len(exc.errors) - 8} more"
        return (False, f"Artifact schema validation failed for {schema_file}: {details}")
    except Exception as exc:
        return (False, f"Artifact schema validation failed for {schema_file}: {exc}")
    return (True, mapping)
