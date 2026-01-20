"""Index queries for exact iso_week_range matches."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from app.workspace.index_manager import WorkspaceIndexManager
from app.workspace.iso_helpers import IsoWeek, IsoWeekRange


def _normalize_range_dict(range_obj: dict[str, Any]) -> IsoWeekRange:
    """Normalize a range dict into an IsoWeekRange."""
    start = range_obj["start"]
    end = range_obj["end"]
    return IsoWeekRange(
        start=IsoWeek(int(start["year"]), int(start["week"])),
        end=IsoWeek(int(end["year"]), int(end["week"])),
    )


@dataclass
class IndexExactQuery:
    """Query helper for exact iso_week_range lookups in index.json."""
    root: Path
    athlete_id: str

    def __post_init__(self) -> None:
        """Initialize index manager after dataclass creation."""
        self._index_manager = WorkspaceIndexManager(root=self.root, athlete_id=self.athlete_id)

    def has_exact_range(self, artifact_type: str, expected_range: IsoWeekRange) -> bool:
        """Return True if any version has exactly the expected range."""
        index = self._index_manager.load()
        entry = index.get("artefacts", {}).get(artifact_type)
        if not entry:
            return False

        versions: dict[str, Any] = entry.get("versions", {})
        for record in versions.values():
            range_obj = record.get("iso_week_range")
            if not range_obj:
                continue
            if _normalize_range_dict(range_obj).key == expected_range.key:
                return True
        return False

    def best_exact_range_version(
        self,
        artifact_type: str,
        expected_range: IsoWeekRange,
    ) -> Optional[str]:
        """Return the newest version_key matching the exact range."""
        index = self._index_manager.load()
        entry = index.get("artefacts", {}).get(artifact_type)
        if not entry:
            return None

        versions: dict[str, Any] = entry.get("versions", {})
        candidates: list[tuple[str, str]] = []

        for version_key, record in versions.items():
            range_obj = record.get("iso_week_range")
            if not range_obj:
                continue
            if _normalize_range_dict(range_obj).key == expected_range.key:
                candidates.append((record.get("created_at", ""), version_key))

        if not candidates:
            return None

        candidates.sort()
        return candidates[-1][1]
