"""Schema validation and confidence-scoring utilities shared by the Intervals.icu pipeline stages."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

import pandas as pd

from rps.workspace.artifact_metadata import canonicalize_artifact_envelope_meta
from rps.workspace.schema_registry import SchemaRegistry
from rps.workspace.types import ArtifactType


def _canonicalize_pipeline_payload(
    *,
    schema_dir: Path,
    schema_file: str,
    artifact_type: ArtifactType,
    payload: dict[str, Any],
) -> tuple[object, dict[str, Any]]:
    """Return a validator and runtime-canonical envelope for data-pipeline outputs."""

    registry = SchemaRegistry(schema_dir)
    schema = registry.get_schema(schema_file)
    validator = registry.validator_for(schema_file)
    normalized = canonicalize_artifact_envelope_meta(
        payload,
        artifact_type=artifact_type,
        schema=schema,
    )
    return validator, cast(dict[str, Any], normalized)


def _value_present(val) -> bool:
    if val is None or pd.isna(val):
        return False
    if isinstance(val, str):
        return val.strip() != ""
    return True


def _confidence_from_columns(df: pd.DataFrame, columns: Sequence[str]) -> str:
    """Return HIGH if all core columns are present for all rows, else MEDIUM."""
    for col in columns:
        if col not in df.columns:
            return "MEDIUM"
        if not df[col].apply(_value_present).all():
            return "MEDIUM"
    return "HIGH"
