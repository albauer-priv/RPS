"""Validated workspace writes with JSON schema enforcement."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .local_store import LocalArtifactStore, utc_iso_now
from .schema_map import ARTIFACT_SCHEMA_FILE
from .schema_registry import SchemaRegistry, validate_or_raise
from .schema_utils import is_envelope_schema
from .types import ArtifactType


@dataclass
class ValidatedWorkspace:
    """Workspace facade that validates payloads before writing to disk."""
    athlete_id: str
    store: LocalArtifactStore
    schemas: SchemaRegistry

    @classmethod
    def for_athlete(
        cls,
        athlete_id: str,
        *,
        schema_dir: Path,
        root: Optional[Path] = None,
    ) -> "ValidatedWorkspace":
        """Construct a validated workspace for an athlete."""
        return cls(
            athlete_id=athlete_id,
            store=LocalArtifactStore(root=root),
            schemas=SchemaRegistry(schema_dir=schema_dir),
        )

    def put_validated(
        self,
        artifact_type: ArtifactType,
        version_key: str,
        payload: Any,
        *,
        payload_meta: Optional[dict[str, Any]],
        producer_agent: str,
        run_id: str,
        update_latest: bool = True,
    ) -> str:
        """Validate payloads against schema and write to disk."""
        if artifact_type not in ARTIFACT_SCHEMA_FILE:
            raise ValueError(f"No schema mapping for artifact_type={artifact_type.value}")

        schema_file = ARTIFACT_SCHEMA_FILE[artifact_type]
        schema = self.schemas.get_schema(schema_file)
        validator = self.schemas.validator_for(schema_file)

        if is_envelope_schema(schema):
            meta = dict(payload_meta or {})
            meta.setdefault("created_at", utc_iso_now())
            meta.setdefault("run_id", run_id)
            meta.setdefault("artifact_type", artifact_type.value)
            meta.setdefault("trace_upstream", [])
            meta.setdefault("data_confidence", "unknown")

            instance = {"meta": meta, "data": payload}
            validate_or_raise(validator, instance)
            document = instance
        else:
            validate_or_raise(validator, payload)
            document = payload

        path = self.store.save_document(
            athlete_id=self.athlete_id,
            artifact_type=artifact_type,
            version_key=version_key,
            document=document,
            producer_agent=producer_agent,
            run_id=run_id,
            update_latest=update_latest,
        )
        return str(path)
