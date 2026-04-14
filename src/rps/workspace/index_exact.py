"""Index queries for exact iso_week_range matches."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rps.workspace.index_manager import WorkspaceIndexManager
from rps.workspace.iso_helpers import IsoWeekRange, parse_iso_week_range

JsonMap = dict[str, object]


def _as_map(value: object) -> JsonMap:
    """Return a mapping when the value is dict-like."""
    return value if isinstance(value, dict) else {}


def _normalize_range(range_obj: object) -> IsoWeekRange | None:
    """Normalize a range into an IsoWeekRange."""
    return parse_iso_week_range(range_obj)


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
        artefacts = _as_map(index.get("artefacts"))
        entry = artefacts.get(artifact_type)
        if not isinstance(entry, dict):
            return False

        versions = entry.get("versions", {})
        if not isinstance(versions, dict):
            versions = {}
        for record in versions.values():
            path = record.get("path") or record.get("relative_path")
            if not path:
                continue
            full_path = (self.root / self.athlete_id / path).resolve()
            if not full_path.exists():
                continue
            range_obj = record.get("iso_week_range")
            if not range_obj:
                continue
            normalized = _normalize_range(range_obj)
            if normalized and normalized.key == expected_range.key:
                return True
        return False

    def best_exact_range_version(
        self,
        artifact_type: str,
        expected_range: IsoWeekRange,
    ) -> str | None:
        """Return the newest version_key matching the exact range."""
        index = self._index_manager.load()
        artefacts = _as_map(index.get("artefacts"))
        entry = artefacts.get(artifact_type)
        if not isinstance(entry, dict):
            return None

        versions = entry.get("versions", {})
        if not isinstance(versions, dict):
            versions = {}
        candidates: list[tuple[str, str]] = []

        for version_key, record in versions.items():
            path = record.get("path") or record.get("relative_path")
            if not path:
                continue
            full_path = (self.root / self.athlete_id / path).resolve()
            if not full_path.exists():
                continue
            range_obj = record.get("iso_week_range")
            if not range_obj:
                continue
            normalized = _normalize_range(range_obj)
            if normalized and normalized.key == expected_range.key:
                candidates.append((record.get("created_at", ""), version_key))

        if not candidates:
            return None

        candidates.sort()
        return candidates[-1][1]
