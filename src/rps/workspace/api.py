"""Workspace facade for reading and writing artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from .guards import DEFAULT_RULES, MissingDependenciesError
from .helpers import PhaseRange, resolve_current_phase, resolve_current_week
from .local_store import LocalArtifactStore
from .types import ArtifactType, Authority


@dataclass
class Workspace:
    """Facade used by agents to access the athlete workspace."""

    athlete_id: str
    store: LocalArtifactStore

    @classmethod
    def for_athlete(cls, athlete_id: str, root: Optional[Path] = None) -> "Workspace":
        """Create a workspace instance for an athlete."""
        return cls(athlete_id=athlete_id, store=LocalArtifactStore(root=root))

    def ensure(self) -> None:
        """Create the workspace directory structure if needed."""
        self.store.ensure_workspace(self.athlete_id)

    def get_latest(self, artifact_type: ArtifactType) -> Any:
        """Return the latest artifact for a type."""
        return self.store.load_latest(self.athlete_id, artifact_type)

    def get(self, artifact_type: ArtifactType, version_key: str) -> Any:
        """Return a specific artifact version."""
        return self.store.load_version(self.athlete_id, artifact_type, version_key)

    def list_versions(self, artifact_type: ArtifactType) -> list[str]:
        """List version keys for a given artifact type."""
        return self.store.list_versions(self.athlete_id, artifact_type)

    def current_week_key(self, d: date | datetime) -> str:
        """Return the ISO week key for a date."""
        return resolve_current_week(d)

    def current_phase(self, week_key: str, phase_length_weeks: int = 4) -> PhaseRange:
        """Return a phase range anchored at week_key."""
        return resolve_current_phase(week_key, phase_length_weeks=phase_length_weeks)

    def exists(self, artifact_type: ArtifactType, version_key: str) -> bool:
        """Return True if a specific version exists."""
        return self.store.exists(self.athlete_id, artifact_type, version_key)

    def latest_exists(self, artifact_type: ArtifactType) -> bool:
        """Return True if a latest artifact exists."""
        return self.store.latest_exists(self.athlete_id, artifact_type)

    def latest_version_key(self, artifact_type: ArtifactType) -> str:
        """Return the latest version key for an artifact type."""
        return self.store.get_latest_version_key(self.athlete_id, artifact_type)

    def require_latest(self, *artifact_types: ArtifactType) -> None:
        """Ensure latest artifacts exist for all provided types."""
        missing = [item.value for item in artifact_types if not self.latest_exists(item)]
        if missing:
            raise MissingDependenciesError(
                message=f"Missing latest dependencies for athlete={self.athlete_id}: {missing}",
                missing=missing,
            )

    def guard_put(
        self,
        artifact_type: ArtifactType,
        version_key: str,
        payload: dict[str, Any],
        *,
        producer_agent: str,
        run_id: str,
        authority: Authority = Authority.STRUCTURAL,
        trace_upstream: Optional[list[str]] = None,
        update_latest: bool = True,
    ) -> str:
        """Write an artifact after enforcing dependency rules."""
        for rule in DEFAULT_RULES:
            if rule.target == artifact_type:
                self.require_latest(*rule.requires_latest)
                break

        return self.put(
            artifact_type=artifact_type,
            version_key=version_key,
            payload=payload,
            authority=authority,
            producer_agent=producer_agent,
            run_id=run_id,
            trace_upstream=trace_upstream,
            update_latest=update_latest,
        )

    def put_validated(
        self,
        artifact_type: ArtifactType,
        version_key: str,
        payload: Any,
        *,
        payload_meta: Optional[dict[str, Any]] = None,
        producer_agent: str,
        run_id: str,
        update_latest: bool = True,
        schema_dir: Optional[Path] = None,
    ) -> str:
        """Validate against schemas and write a document."""
        if schema_dir is None:
            schema_dir = Path("specs/schemas")

        from .validated_api import ValidatedWorkspace

        workspace = ValidatedWorkspace.for_athlete(
            self.athlete_id,
            schema_dir=schema_dir,
            root=self.store.root,
        )
        return workspace.put_validated(
            artifact_type=artifact_type,
            version_key=version_key,
            payload=payload,
            payload_meta=payload_meta,
            producer_agent=producer_agent,
            run_id=run_id,
            update_latest=update_latest,
        )

    def put(
        self,
        artifact_type: ArtifactType,
        version_key: str,
        payload: dict[str, Any],
        *,
        authority: Authority = Authority.STRUCTURAL,
        producer_agent: str = "unknown_agent",
        run_id: str = "run_unknown",
        trace_upstream: Optional[list[str]] = None,
        update_latest: bool = True,
    ) -> str:
        """Write a schema-style {meta,data} envelope without validation."""
        path = self.store.save_version(
            athlete_id=self.athlete_id,
            artifact_type=artifact_type,
            version_key=version_key,
            payload=payload,
            authority=authority,
            producer_agent=producer_agent,
            run_id=run_id,
            trace_upstream=trace_upstream,
            update_latest=update_latest,
        )
        return str(path)
