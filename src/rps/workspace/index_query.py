"""Index queries for range coverage lookups."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rps.workspace.index_manager import WorkspaceIndexManager
from rps.workspace.iso_helpers import IsoWeek, parse_iso_week_range
from rps.workspace.types import ArtifactType


def _as_map(value: object) -> dict[str, object]:
    """Return a mapping when the value is dict-like."""
    return value if isinstance(value, dict) else {}


def _week_index(week: IsoWeek) -> int:
    """Return a sortable index for ISO weeks."""
    return week.year * 60 + week.week


def _range_contains(range_meta: object, target: IsoWeek) -> bool:
    """Return True if range_meta covers the target week."""
    normalized = parse_iso_week_range(range_meta)
    if not normalized:
        return False
    return _week_index(normalized.start) <= _week_index(target) <= _week_index(normalized.end)


@dataclass
class IndexQuery:
    """Query helper for range coverage lookups in index.json."""
    root: Path
    athlete_id: str

    def __post_init__(self) -> None:
        """Initialize index manager after dataclass creation."""
        self._index_manager = WorkspaceIndexManager(root=self.root, athlete_id=self.athlete_id)

    def best_covering_range_version(
        self,
        artifact_type: ArtifactType | str,
        target: IsoWeek,
    ) -> str | None:
        """Return the newest version_key whose range covers the target week."""
        key = artifact_type.value if isinstance(artifact_type, ArtifactType) else str(artifact_type)
        index = self._index_manager.load()
        artefacts = _as_map(index.get("artefacts"))
        entry = artefacts.get(key)
        if not isinstance(entry, dict):
            return None

        versions = entry.get("versions", {})
        if not isinstance(versions, dict):
            versions = {}
        candidates: list[tuple[str, str]] = []

        for version_key, record in versions.items():
            range_meta = record.get("iso_week_range")
            if not range_meta:
                continue
            if _range_contains(range_meta, target):
                created_at = record.get("created_at", "")
                candidates.append((created_at, version_key))

        if not candidates:
            return None

        candidates.sort()
        return candidates[-1][1]
