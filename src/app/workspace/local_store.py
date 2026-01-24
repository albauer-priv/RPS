"""Local filesystem-backed artifact storage."""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Optional

from .index_manager import WorkspaceIndexManager
from .paths import ARTIFACT_PATHS, ensure_dir
from .types import ArtifactMeta, ArtifactType, Authority


def utc_iso_now() -> str:
    """Return the current time in ISO-8601 UTC format."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _normalize_authority(authority: Authority | str | None) -> str | None:
    """Normalize authority labels to schema-compatible values."""
    if authority is None:
        return None
    if isinstance(authority, Authority):
        value = authority.value
    else:
        value = str(authority)
    mapping = {
        "Structural": "Derived",
        "Advisory": "Informational",
    }
    return mapping.get(value, value)


class LocalArtifactStore:
    """Local dev storage for athlete-specific artifacts."""

    def __init__(self, root: Optional[Path] = None):
        """Initialize the store rooted at ATHLETE_WORKSPACE_ROOT."""
        root_env = os.getenv("ATHLETE_WORKSPACE_ROOT", "var/athletes")
        self.root = (root or Path(root_env)).resolve()

    def athlete_root(self, athlete_id: str) -> Path:
        """Return the root directory for an athlete."""
        return self.root / athlete_id

    def latest_dir(self, athlete_id: str) -> Path:
        """Return the latest/ directory path for an athlete."""
        return self.athlete_root(athlete_id) / "latest"

    def logs_dir(self, athlete_id: str) -> Path:
        """Return the logs/ directory path for an athlete."""
        return self.athlete_root(athlete_id) / "logs"

    def type_dir(self, athlete_id: str, artifact_type: ArtifactType) -> Path:
        """Return the directory for the given artifact type."""
        cfg = ARTIFACT_PATHS[artifact_type]
        return self.athlete_root(athlete_id) / cfg.folder

    def versioned_path(self, athlete_id: str, artifact_type: ArtifactType, version_key: str) -> Path:
        """Return the path for a versioned artifact file."""
        cfg = ARTIFACT_PATHS[artifact_type]
        filename = f"{cfg.filename_prefix}_{version_key}.json"
        return self.type_dir(athlete_id, artifact_type) / filename

    def latest_path(self, athlete_id: str, artifact_type: ArtifactType) -> Path:
        """Return the path for the latest artifact file."""
        cfg = ARTIFACT_PATHS[artifact_type]
        return self.latest_dir(athlete_id) / f"{cfg.filename_prefix}.json"

    def ensure_workspace(self, athlete_id: str) -> None:
        """Ensure the athlete workspace directories exist."""
        base = self.athlete_root(athlete_id)
        ensure_dir(base)

        ensure_dir(base / "inputs")
        ensure_dir(base / "data/plans/macro")
        ensure_dir(base / "data/plans/meso")
        ensure_dir(base / "data/plans/micro")
        ensure_dir(base / "data/exports")
        ensure_dir(base / "data/analysis")
        ensure_dir(base / "logs")
        ensure_dir(base / "latest")

    def _index_manager(self, athlete_id: str) -> WorkspaceIndexManager:
        """Return an index manager for the athlete."""
        return WorkspaceIndexManager(root=self.root, athlete_id=athlete_id)

    def _record_index_write(
        self,
        *,
        athlete_id: str,
        artifact_type: ArtifactType,
        version_key: str,
        version_path: Path,
        run_id: str,
        producer_agent: str,
        meta: Optional[dict[str, Any]] = None,
    ) -> None:
        """Record a write in the per-athlete index.json."""
        rel_path = str(version_path.relative_to(self.athlete_root(athlete_id)))
        created_at = None
        iso_week = None
        iso_week_range = None
        if meta:
            created_at = meta.get("created_at")
            iso_week = meta.get("iso_week")
            iso_week_range = meta.get("iso_week_range")

        self._index_manager(athlete_id).record_write(
            artifact_type=artifact_type.value,
            version_key=version_key,
            relative_path=rel_path,
            run_id=run_id,
            producer_agent=producer_agent,
            created_at=created_at,
            iso_week=iso_week,
            iso_week_range=iso_week_range,
        )

    def load_latest(self, athlete_id: str, artifact_type: ArtifactType) -> Any:
        """Load the latest artifact for the given type."""
        path = self.latest_path(athlete_id, artifact_type)
        if not path.exists():
            raise FileNotFoundError(f"No latest artifact found: {path}")
        return self._read_json(path)

    def load_version(self, athlete_id: str, artifact_type: ArtifactType, version_key: str) -> Any:
        """Load a specific artifact version."""
        path = self.versioned_path(athlete_id, artifact_type, version_key)
        if not path.exists():
            raise FileNotFoundError(f"No artifact version found: {path}")
        return self._read_json(path)

    def exists(self, athlete_id: str, artifact_type: ArtifactType, version_key: str) -> bool:
        """Return True if the given version exists on disk."""
        path = self.versioned_path(athlete_id, artifact_type, version_key)
        return path.exists()

    def latest_exists(self, athlete_id: str, artifact_type: ArtifactType) -> bool:
        """Return True if a latest artifact exists on disk."""
        path = self.latest_path(athlete_id, artifact_type)
        return path.exists()

    def get_latest_version_key(self, athlete_id: str, artifact_type: ArtifactType) -> str:
        """Return the version_key for the latest artifact, if available."""
        doc = self.load_latest(athlete_id, artifact_type)
        if isinstance(doc, dict):
            meta = doc.get("meta") or doc.get("_meta", {})
            version_key = meta.get("version_key")
            if version_key:
                return str(version_key)

        log_path = self.logs_dir(athlete_id) / "artifact_writes.jsonl"
        if not log_path.exists():
            raise ValueError(f"Latest artifact for {artifact_type.value} has no meta.version_key")

        with log_path.open("r", encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        for raw_line in reversed(lines):
            try:
                entry = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            if entry.get("artifact_type") == artifact_type.value:
                version_key = entry.get("version_key")
                if version_key:
                    return str(version_key)

        raise ValueError(f"Latest artifact for {artifact_type.value} has no meta.version_key")

    def list_versions(self, athlete_id: str, artifact_type: ArtifactType) -> list[str]:
        """List version keys stored for an artifact type."""
        self.ensure_workspace(athlete_id)

        cfg = ARTIFACT_PATHS[artifact_type]
        folder = self.type_dir(athlete_id, artifact_type)
        if not folder.exists():
            return []

        prefix = cfg.filename_prefix + "_"
        versions: list[str] = []

        for path in folder.glob(f"{cfg.filename_prefix}_*.json"):
            name = path.name
            if not name.startswith(prefix):
                continue
            version_key = name[len(prefix):-5]
            versions.append(version_key)

        return sorted(versions, key=_version_sort_key)

    def save_version(
        self,
        athlete_id: str,
        artifact_type: ArtifactType,
        version_key: str,
        payload: dict[str, Any],
        *,
        payload_meta: Optional[dict[str, Any]] = None,
        authority: Authority = Authority.STRUCTURAL,
        producer_agent: str = "unknown_agent",
        run_id: str = "run_unknown",
        trace_upstream: Optional[list[str]] = None,
        update_latest: bool = True,
    ) -> Path:
        """Write a schema-style {meta,data} envelope to disk."""
        self.ensure_workspace(athlete_id)

        meta = ArtifactMeta(
            artifact_type=artifact_type,
            athlete_id=athlete_id,
            version_key=version_key,
            authority=authority,
            producer_agent=producer_agent,
            run_id=run_id,
            created_at=utc_iso_now(),
            trace_upstream=trace_upstream or [],
        )

        payload_meta = payload_meta or {}
        authority_value = _normalize_authority(payload_meta.get("authority", meta.authority))
        meta_doc: dict[str, Any] = {
            "artifact_type": meta.artifact_type.value,
            "schema_id": payload_meta.get("schema_id", f"{meta.artifact_type.value}Interface"),
            "schema_version": payload_meta.get("schema_version", "1.0"),
            "version": payload_meta.get("version", "1.0"),
            "authority": authority_value,
            "owner_agent": payload_meta.get("owner_agent", meta.producer_agent),
            "run_id": meta.run_id,
            "created_at": payload_meta.get("created_at", meta.created_at),
            "trace_upstream": payload_meta.get("trace_upstream", meta.trace_upstream),
        }

        if "version_key" in payload_meta or not payload_meta:
            meta_doc["version_key"] = payload_meta.get("version_key", meta.version_key)

        for key, value in payload_meta.items():
            if key in meta_doc or value is None:
                continue
            meta_doc[key] = value

        doc = {"meta": meta_doc, "data": payload}

        version_path = self.versioned_path(athlete_id, artifact_type, version_key)
        ensure_dir(version_path.parent)

        self._atomic_write_json(version_path, doc)
        self._append_log(athlete_id, meta, version_path)

        if update_latest:
            latest_path = self.latest_path(athlete_id, artifact_type)
            ensure_dir(latest_path.parent)
            self._atomic_write_json(latest_path, doc)

        self._record_index_write(
            athlete_id=athlete_id,
            artifact_type=artifact_type,
            version_key=version_key,
            version_path=version_path,
            run_id=meta.run_id,
            producer_agent=meta.producer_agent,
            meta=meta_doc,
        )

        return version_path

    def save_document(
        self,
        athlete_id: str,
        artifact_type: ArtifactType,
        version_key: str,
        document: object,
        *,
        producer_agent: str,
        run_id: str,
        update_latest: bool = True,
    ) -> Path:
        """Write a validated document (envelope or raw) to disk."""
        self.ensure_workspace(athlete_id)

        version_path = self.versioned_path(athlete_id, artifact_type, version_key)
        ensure_dir(version_path.parent)
        self._atomic_write_json(version_path, document)

        if update_latest:
            latest_path = self.latest_path(athlete_id, artifact_type)
            ensure_dir(latest_path.parent)
            self._atomic_write_json(latest_path, document)

        meta_doc = None
        if isinstance(document, dict):
            candidate = document.get("meta")
            if isinstance(candidate, dict):
                meta_doc = candidate

        self._append_log_simple(
            athlete_id=athlete_id,
            artifact_type=artifact_type.value,
            version_key=version_key,
            producer_agent=producer_agent,
            run_id=run_id,
            path=str(version_path),
        )

        self._record_index_write(
            athlete_id=athlete_id,
            artifact_type=artifact_type,
            version_key=version_key,
            version_path=version_path,
            run_id=run_id,
            producer_agent=producer_agent,
            meta=meta_doc,
        )
        return version_path

    def _read_json(self, path: Path) -> Any:
        """Read JSON from a file."""
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _atomic_write_json(self, target: Path, data: object) -> None:
        """Write JSON atomically by using a temporary file."""
        tmp = target.with_suffix(target.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        shutil.move(str(tmp), str(target))

    def _append_log(self, athlete_id: str, meta: ArtifactMeta, path: Path) -> None:
        """Append a JSONL entry for an artifact write."""
        ensure_dir(self.logs_dir(athlete_id))
        log_path = self.logs_dir(athlete_id) / "artifact_writes.jsonl"
        entry = {
            "ts": utc_iso_now(),
            "artifact_type": meta.artifact_type.value,
            "version_key": meta.version_key,
            "authority": meta.authority.value,
            "producer_agent": meta.producer_agent,
            "run_id": meta.run_id,
            "path": str(path),
            "trace_upstream": meta.trace_upstream,
        }
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _append_log_simple(
        self,
        athlete_id: str,
        artifact_type: str,
        version_key: str,
        producer_agent: str,
        run_id: str,
        path: str,
    ) -> None:
        """Append a minimal JSONL log entry for a write."""
        ensure_dir(self.logs_dir(athlete_id))
        log_path = self.logs_dir(athlete_id) / "artifact_writes.jsonl"
        entry = {
            "artifact_type": artifact_type,
            "version_key": version_key,
            "producer_agent": producer_agent,
            "run_id": run_id,
            "path": path,
        }
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _version_sort_key(version_key: str) -> tuple:
    """Sort version keys with week-like keys first."""
    try:
        if "--" in version_key:
            start = version_key.split("--", 1)[0]
            year, week = start.split("-")
            return (0, int(year), int(week), version_key)
        year, week = version_key.split("-")
        return (0, int(year), int(week), version_key)
    except Exception:
        return (1, version_key)
