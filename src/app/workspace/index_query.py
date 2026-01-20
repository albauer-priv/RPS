"""Index queries for range coverage lookups."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from app.workspace.index_manager import WorkspaceIndexManager
from app.workspace.iso_helpers import IsoWeek
from app.workspace.types import ArtifactType


def _week_index(week: IsoWeek) -> int:
    """Return a sortable index for ISO weeks."""
    return week.year * 60 + week.week


def _range_contains(range_meta: dict[str, Any], target: IsoWeek) -> bool:
    """Return True if range_meta covers the target week."""
    start = range_meta.get("start")
    end = range_meta.get("end")
    if not start or not end:
        return False
    start_week = IsoWeek(int(start["year"]), int(start["week"]))
    end_week = IsoWeek(int(end["year"]), int(end["week"]))
    return _week_index(start_week) <= _week_index(target) <= _week_index(end_week)


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
    ) -> Optional[str]:
        """Return the newest version_key whose range covers the target week."""
        key = artifact_type.value if isinstance(artifact_type, ArtifactType) else str(artifact_type)
        index = self._index_manager.load()
        artefacts = index.get("artefacts", {})
        entry = artefacts.get(key)
        if not entry:
            return None

        versions: dict[str, Any] = entry.get("versions", {})
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
