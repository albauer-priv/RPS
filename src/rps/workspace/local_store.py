"""Local filesystem-backed artifact storage."""

from __future__ import annotations

import json
import logging
import os
import shutil
import time
from datetime import datetime
from pathlib import Path

from .index_manager import WorkspaceIndexManager
from .paths import ARTIFACT_PATHS, ensure_dir
from .types import ArtifactMeta, ArtifactType, Authority
from .versioning import (
    RANGE_SCOPED_ARTIFACTS,
    WEEK_SCOPED_ARTIFACTS,
    normalize_version_key,
    split_range_version_key,
    split_week_version_key,
)

logger = logging.getLogger(__name__)

JsonMap = dict[str, object]
JsonList = list[object]
JsonValue = JsonMap | JsonList


def _as_map(value: object) -> JsonMap:
    """Return a mapping when the value is dict-like."""
    return value if isinstance(value, dict) else {}


def _as_str(value: object) -> str | None:
    """Return a string when the value is a string."""
    return value if isinstance(value, str) else None

def utc_iso_now() -> str:
    """Return the current time in ISO-8601 UTC format."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _normalize_authority(authority: Authority | str | None) -> str | None:
    """Normalize authority labels to schema-compatible values."""
    if authority is None:
        return None
    value = authority.value if isinstance(authority, Authority) else str(authority)
    mapping = {
        "Structural": "Derived",
        "Advisory": "Informational",
    }
    return mapping.get(value, value)


class LocalArtifactStore:
    """Local dev storage for athlete-specific artifacts."""

    def __init__(self, root: Path | None = None):
        """Initialize the store rooted at ATHLETE_WORKSPACE_ROOT."""
        root_env = os.getenv("ATHLETE_WORKSPACE_ROOT", "runtime/athletes")
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
        ensure_dir(base / "data/plans/season")
        ensure_dir(base / "data/plans/phase")
        ensure_dir(base / "data/plans/week")
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
        meta: JsonMap | None = None,
    ) -> None:
        """Record a write in the per-athlete index.json."""
        rel_path = str(version_path.relative_to(self.athlete_root(athlete_id)))
        created_at = None
        iso_week = None
        iso_week_range = None
        if meta:
            created_at = _as_str(meta.get("created_at"))
            iso_week_raw = meta.get("iso_week")
            iso_week = iso_week_raw if isinstance(iso_week_raw, dict) else None
            iso_week_range_raw = meta.get("iso_week_range")
            iso_week_range = iso_week_range_raw if isinstance(iso_week_range_raw, dict) else None

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

    def load_latest(self, athlete_id: str, artifact_type: ArtifactType) -> object:
        """Load the latest artifact for the given type."""
        path = self.latest_path(athlete_id, artifact_type)
        if not path.exists():
            raise FileNotFoundError(f"No latest artifact found: {path}")
        return self._read_json(path)

    def load_version(self, athlete_id: str, artifact_type: ArtifactType, version_key: str) -> object:
        """Load a specific artifact version."""
        path = self._path_for_version(athlete_id, artifact_type, version_key)
        if not path.exists():
            raise FileNotFoundError(f"No artifact version found: {path}")
        return self._read_json(path)

    def exists(self, athlete_id: str, artifact_type: ArtifactType, version_key: str) -> bool:
        """Return True if the given version exists on disk."""
        if "--" in version_key:
            resolved = self._resolve_range_version_key(athlete_id, artifact_type, version_key)
        else:
            resolved = self._resolve_week_version_key(athlete_id, artifact_type, version_key)
        path = self.versioned_path(athlete_id, artifact_type, resolved)
        return path.exists()

    def latest_exists(self, athlete_id: str, artifact_type: ArtifactType) -> bool:
        """Return True if a latest artifact exists on disk."""
        path = self.latest_path(athlete_id, artifact_type)
        return path.exists()

    def resolve_week_version_key(
        self, athlete_id: str, artifact_type: ArtifactType, week_key: str
    ) -> str | None:
        """Return the newest week-scoped version key for a base week key, if it exists."""
        resolved = self._resolve_week_version_key(athlete_id, artifact_type, week_key)
        path = self.versioned_path(athlete_id, artifact_type, resolved)
        return resolved if path.exists() else None

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

    def _path_for_version(self, athlete_id: str, artifact_type: ArtifactType, version_key: str) -> Path:
        """Return the path for a recorded version, falling back to the canonical layout."""
        if "--" in version_key:
            version_key = self._resolve_range_version_key(athlete_id, artifact_type, version_key)
        else:
            version_key = self._resolve_week_version_key(athlete_id, artifact_type, version_key)
        root = self.athlete_root(athlete_id)
        index = self._index_manager(athlete_id).load()
        artefacts = _as_map(index.get("artefacts"))
        entry = _as_map(artefacts.get(artifact_type.value))
        versions = _as_map(entry.get("versions"))
        version = versions.get(version_key)
        if isinstance(version, dict):
            relative = _as_str(version.get("path"))
            if isinstance(relative, str):
                candidate = root / relative
                if candidate.exists():
                    return candidate
        return self.versioned_path(athlete_id, artifact_type, version_key)

    def _resolve_week_version_key(self, athlete_id: str, artifact_type: ArtifactType, version_key: str) -> str:
        """Return the newest week-scoped version key for a base week key."""
        if artifact_type not in WEEK_SCOPED_ARTIFACTS:
            return version_key
        base_week, suffix = split_week_version_key(version_key)
        if not base_week or suffix:
            return version_key
        index = self._index_manager(athlete_id).load()
        artefacts = _as_map(index.get("artefacts"))
        entry = _as_map(artefacts.get(artifact_type.value))
        versions = _as_map(entry.get("versions"))
        candidates: list[tuple[datetime, str, str]] = []
        for key, record in versions.items():
            cand_base, cand_suffix = split_week_version_key(key)
            if cand_base != base_week:
                continue
            created_raw = _as_str(record.get("created_at")) if isinstance(record, dict) else None
            created_dt = _parse_created_at(created_raw)
            candidates.append((created_dt, cand_suffix or "", key))
        if candidates:
            candidates.sort()
            return candidates[-1][2]
        return version_key

    def _resolve_range_version_key(self, athlete_id: str, artifact_type: ArtifactType, version_key: str) -> str:
        """Return the newest range-scoped version key for a base range key."""
        if artifact_type not in RANGE_SCOPED_ARTIFACTS:
            return version_key
        base_range, suffix = split_range_version_key(version_key)
        if not base_range or suffix:
            return version_key
        index = self._index_manager(athlete_id).load()
        artefacts = _as_map(index.get("artefacts"))
        entry = _as_map(artefacts.get(artifact_type.value))
        versions = _as_map(entry.get("versions"))
        candidates: list[tuple[datetime, str, str]] = []
        for key, record in versions.items():
            cand_base, cand_suffix = split_range_version_key(key)
            if cand_base != base_range:
                continue
            created_raw = _as_str(record.get("created_at")) if isinstance(record, dict) else None
            created_dt = _parse_created_at(created_raw)
            candidates.append((created_dt, cand_suffix or "", key))
        if candidates:
            candidates.sort()
            return candidates[-1][2]
        return version_key

    def save_version(
        self,
        athlete_id: str,
        artifact_type: ArtifactType,
        version_key: str,
        payload: JsonMap,
        *,
        payload_meta: JsonMap | None = None,
        authority: Authority = Authority.STRUCTURAL,
        producer_agent: str = "unknown_agent",
        run_id: str = "run_unknown",
        trace_upstream: list[str] | None = None,
        update_latest: bool = True,
    ) -> Path:
        """Write a schema-style {meta,data} envelope to disk."""
        self.ensure_workspace(athlete_id)

        normalized_key = normalize_version_key(version_key, artifact_type=artifact_type)
        meta = ArtifactMeta(
            artifact_type=artifact_type,
            athlete_id=athlete_id,
            version_key=normalized_key,
            authority=authority,
            producer_agent=producer_agent,
            run_id=run_id,
            created_at=utc_iso_now(),
            trace_upstream=trace_upstream or [],
        )

        payload_meta = payload_meta or {}
        authority_raw = payload_meta.get("authority", meta.authority)
        authority_value = (
            _normalize_authority(authority_raw)
            if authority_raw is None or isinstance(authority_raw, (Authority, str))
            else _normalize_authority(str(authority_raw))
        )
        version_meta = _as_str(payload_meta.get("version_key")) or meta.version_key
        meta_doc: JsonMap = {
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
            created_meta = _as_str(meta_doc.get("created_at"))
            meta_doc["version_key"] = normalize_version_key(
                version_meta,
                created_meta,
                artifact_type=artifact_type,
            )

        for key, value in payload_meta.items():
            if key in meta_doc or value is None:
                continue
            meta_doc[key] = value

        doc = {"meta": meta_doc, "data": payload}

        version_path = self.versioned_path(athlete_id, artifact_type, meta.version_key)
        ensure_dir(version_path.parent)

        self._atomic_write_json(version_path, doc)
        self._append_log(athlete_id, meta, version_path)
        logger.info(
            "Artifact write type=%s version_key=%s path=%s run_id=%s",
            meta.artifact_type.value,
            meta.version_key,
            version_path,
            meta.run_id,
        )

        if update_latest:
            latest_path = self.latest_path(athlete_id, artifact_type)
            ensure_dir(latest_path.parent)
            self._atomic_write_json(latest_path, doc)

        self._record_index_write(
            athlete_id=athlete_id,
            artifact_type=artifact_type,
            version_key=meta.version_key,
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

        normalized_key = normalize_version_key(version_key, artifact_type=artifact_type)
        meta_doc = None
        if isinstance(document, dict):
            candidate = document.get("meta")
            if isinstance(candidate, dict):
                meta_doc = candidate
                if "version_key" in meta_doc:
                    meta_doc["version_key"] = normalize_version_key(
                        str(meta_doc.get("version_key")),
                        meta_doc.get("created_at"),
                        artifact_type=artifact_type,
                    )
        version_path = self.versioned_path(athlete_id, artifact_type, normalized_key)
        ensure_dir(version_path.parent)
        self._atomic_write_json(version_path, document)

        if update_latest:
            latest_path = self.latest_path(athlete_id, artifact_type)
            ensure_dir(latest_path.parent)
            self._atomic_write_json(latest_path, document)

        self._append_log_simple(
            athlete_id=athlete_id,
            artifact_type=artifact_type.value,
            version_key=normalized_key,
            producer_agent=producer_agent,
            run_id=run_id,
            path=str(version_path),
        )
        logger.info(
            "Artifact write type=%s version_key=%s path=%s run_id=%s",
            artifact_type.value,
            normalized_key,
            version_path,
            run_id,
        )

        self._record_index_write(
            athlete_id=athlete_id,
            artifact_type=artifact_type,
            version_key=normalized_key,
            version_path=version_path,
            run_id=run_id,
            producer_agent=producer_agent,
            meta=meta_doc,
        )
        return version_path

    def _read_json(self, path: Path) -> object:
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


def _parse_created_at(value: str | None) -> datetime:
    """Parse an ISO-8601 timestamp, falling back to epoch."""
    if not value:
        return datetime.min
    try:
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.min


def _version_sort_key(version_key: str) -> tuple:
    """Sort version keys with week-like keys first."""
    try:
        if "--" in version_key:
            start = version_key.split("__", 1)[0].split("--", 1)[0]
            year, week = start.split("-")
            _, suffix = split_range_version_key(version_key)
            return (0, int(year), int(week), suffix or "", version_key)
        base_week, suffix = split_week_version_key(version_key)
        if base_week:
            year, week = base_week.split("-")
            return (0, int(year), int(week), suffix or "", version_key)
        year, week = version_key.split("-")
        return (0, int(year), int(week), version_key)
    except Exception:
        return (1, version_key)
