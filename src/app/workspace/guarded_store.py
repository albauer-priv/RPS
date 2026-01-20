"""Guarded, validated writes to the local workspace."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.agents.tasks import OutputSpec
from app.workspace.schema_registry import SchemaRegistry, validate_or_raise
from app.workspace.schema_utils import is_envelope_schema
from app.workspace.types import ArtifactType
from app.workspace.versioning import derive_version_key_from_envelope
from app.workspace.local_store import LocalArtifactStore


class MissingDependenciesError(RuntimeError):
    """Raised when required upstream artifacts are missing."""
    pass


@dataclass(frozen=True)
class DependencyRule:
    """Defines required latest dependencies for a target artifact."""
    target: ArtifactType
    requires_latest: tuple[ArtifactType, ...]


DEFAULT_RULES = [
    DependencyRule(
        target=ArtifactType.WORKOUTS_PLAN,
        requires_latest=(ArtifactType.BLOCK_EXECUTION_ARCH,),
    ),
    DependencyRule(
        target=ArtifactType.INTERVALS_WORKOUTS,
        requires_latest=(ArtifactType.WORKOUTS_PLAN,),
    ),
    DependencyRule(
        target=ArtifactType.DES_ANALYSIS_REPORT,
        requires_latest=(ArtifactType.ACTIVITIES_TREND, ArtifactType.WORKOUTS_PLAN),
    ),
]


@dataclass
class GuardedValidatedStore:
    """Schema-validated store that enforces dependency rules."""
    athlete_id: str
    schema_dir: Path
    workspace_root: Path

    def __post_init__(self) -> None:
        """Initialize schema registry and local store."""
        self.schemas = SchemaRegistry(self.schema_dir)
        self.store = LocalArtifactStore(root=self.workspace_root)

    def _check_dependencies(self, target: ArtifactType) -> None:
        """Raise if required latest artifacts are missing."""
        for rule in DEFAULT_RULES:
            if rule.target == target:
                missing = [
                    item.value
                    for item in rule.requires_latest
                    if not self.store.latest_exists(self.athlete_id, item)
                ]
                if missing:
                    raise MissingDependenciesError(
                        f"Missing latest dependencies for {target.value}: {missing}"
                    )

    def guard_put_validated(
        self,
        *,
        output_spec: OutputSpec,
        document: Any,
        run_id: str,
        producer_agent: str,
        update_latest: bool = True,
    ) -> dict[str, Any]:
        """Validate, derive version key, and persist a document with guards."""
        target = output_spec.artifact_type
        self._check_dependencies(target)

        schema = self.schemas.get_schema(output_spec.schema_file)
        validator = self.schemas.validator_for(output_spec.schema_file)

        if is_envelope_schema(schema):
            if not isinstance(document, dict) or "meta" not in document or "data" not in document:
                raise ValueError("Envelope artefact must be an object with meta and data")
            validate_or_raise(validator, document)
            version_key = derive_version_key_from_envelope(document)
        else:
            validate_or_raise(validator, document)
            version_key = "raw"

        path = self.store.save_document(
            athlete_id=self.athlete_id,
            artifact_type=target,
            version_key=version_key,
            document=document,
            producer_agent=producer_agent,
            run_id=run_id,
            update_latest=update_latest,
        )

        return {
            "ok": True,
            "artifact_type": target.value,
            "version_key": version_key,
            "path": str(path),
            "run_id": run_id,
            "producer_agent": producer_agent,
        }
