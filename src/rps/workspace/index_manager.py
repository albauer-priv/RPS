"""Index management for per-athlete artifact metadata."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
from datetime import datetime


def utc_iso_now() -> str:
    """Return current time as an ISO-8601 UTC string."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass
class WorkspaceIndexManager:
    """Read and update the per-athlete index.json file."""
    root: Path
    athlete_id: str

    def athlete_root(self) -> Path:
        """Return the athlete root path."""
        return (self.root / self.athlete_id).resolve()

    def index_path(self) -> Path:
        """Return the index.json path, creating the athlete directory if needed."""
        path = self.athlete_root()
        path.mkdir(parents=True, exist_ok=True)
        return path / "index.json"

    def load(self) -> dict[str, Any]:
        """Load the index file, returning a default structure if missing."""
        path = self.index_path()
        if not path.exists():
            return {
                "athlete_id": self.athlete_id,
                "updated_at": utc_iso_now(),
                "artefacts": {},
            }
        index = json.loads(path.read_text(encoding="utf-8"))
        return index

    def save(self, index: dict[str, Any]) -> None:
        """Persist the index to disk with an updated timestamp."""
        index["updated_at"] = utc_iso_now()
        path = self.index_path()
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

    def prune_missing(self) -> dict[str, int]:
        """Remove index entries whose files are missing on disk."""
        index = self.load()
        artefacts = index.get("artefacts", {})
        removed_versions = 0
        removed_types = 0
        changed = False

        def _parse_created(value: str | None) -> datetime | None:
            if not value:
                return None
            try:
                if value.endswith("Z"):
                    value = value.replace("Z", "+00:00")
                return datetime.fromisoformat(value)
            except ValueError:
                return None

        for artifact_type in list(artefacts.keys()):
            entry = artefacts.get(artifact_type)
            if not isinstance(entry, dict):
                continue
            versions = entry.get("versions", {})
            if not isinstance(versions, dict):
                continue
            for version_key in list(versions.keys()):
                record = versions.get(version_key)
                if not isinstance(record, dict):
                    continue
                rel_path = record.get("path") or record.get("relative_path")
                if not isinstance(rel_path, str):
                    continue
                full_path = self.athlete_root() / rel_path
                if not full_path.exists():
                    versions.pop(version_key, None)
                    removed_versions += 1
                    changed = True

            if not versions:
                artefacts.pop(artifact_type, None)
                removed_types += 1
                changed = True
                continue

            latest = entry.get("latest")
            latest_key = latest.get("version_key") if isinstance(latest, dict) else None
            if latest_key not in versions:
                sorted_versions = sorted(
                    versions.values(),
                    key=lambda rec: _parse_created(rec.get("created_at")) or datetime.min,
                )
                entry["latest"] = sorted_versions[-1] if sorted_versions else None
                changed = True

        if changed:
            index["artefacts"] = artefacts
            self.save(index)

        return {"removed_versions": removed_versions, "removed_types": removed_types}

    def record_write(
        self,
        *,
        artifact_type: str,
        version_key: str,
        relative_path: str,
        run_id: str,
        producer_agent: str,
        created_at: str | None = None,
        iso_week: Optional[dict[str, Any]] = None,
        iso_week_range: Optional[dict[str, Any]] = None,
    ) -> None:
        """Record a write event and mark it as latest for the artifact type."""
        index = self.load()
        artefacts = index.setdefault("artefacts", {})
        entry = artefacts.setdefault(artifact_type, {"latest": None, "versions": {}})

        record: dict[str, Any] = {
            "version_key": version_key,
            "path": relative_path,
            "run_id": run_id,
            "producer_agent": producer_agent,
            "created_at": created_at or utc_iso_now(),
        }
        if iso_week is not None:
            record["iso_week"] = iso_week
        if iso_week_range is not None:
            record["iso_week_range"] = iso_week_range

        entry["versions"][version_key] = record
        entry["latest"] = record

        self.save(index)
