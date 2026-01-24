"""Index management for per-athlete artifact metadata."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


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
        if self._normalize_paths(index):
            self.save(index)
        return index

    def _normalize_paths(self, index: dict[str, Any]) -> bool:
        """Normalize legacy paths in index records when newer paths exist."""
        artefacts = index.get("artefacts", {})
        if not isinstance(artefacts, dict):
            return False
        changed = False
        for entry in artefacts.values():
            versions = entry.get("versions", {})
            if not isinstance(versions, dict):
                continue
            for record in versions.values():
                if not isinstance(record, dict):
                    continue
                for key in ("path", "relative_path"):
                    value = record.get(key)
                    if not isinstance(value, str):
                        continue
                    if value.startswith("analysis/"):
                        candidate = f"data/{value}"
                        legacy_path = self.athlete_root() / value
                        new_path = self.athlete_root() / candidate
                        if new_path.exists() and not legacy_path.exists():
                            record[key] = candidate
                            changed = True
        return changed

    def save(self, index: dict[str, Any]) -> None:
        """Persist the index to disk with an updated timestamp."""
        index["updated_at"] = utc_iso_now()
        path = self.index_path()
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

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
