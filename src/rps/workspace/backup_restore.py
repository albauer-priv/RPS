from __future__ import annotations

import hashlib
import io
import json
import logging
import tarfile
import tempfile
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC
from pathlib import Path

LOGGER = logging.getLogger("rps.workspace.backup_restore")


@dataclass(frozen=True)
class BackupBundle:
    """Container for a backup archive payload.

    Attributes:
        filename: Suggested filename for download.
        data: Raw archive bytes.
    """

    filename: str
    data: bytes


BACKUP_ROOT = "athlete"

PARTIAL_RESTORE_MODES: dict[str, list[str]] = {
    "full": ["inputs", "latest", "data", "receipts", "rendered"],
    "inputs": ["inputs"],
    "plans": ["data/plans", "latest"],
    "metrics": ["data", "latest"],
    "receipts": ["receipts"],
    "rendered": ["rendered"],
}


def _hash_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iter_files(root: Path, include_paths: Iterable[str]) -> list[Path]:
    paths: list[Path] = []
    for rel in include_paths:
        resolved = (root / rel).resolve()
        if not resolved.exists():
            continue
        if resolved.is_file():
            paths.append(resolved)
        else:
            paths.extend(item for item in resolved.rglob("*") if item.is_file())
    return sorted(set(paths))


def _build_manifest(athlete_id: str, included_paths: list[str], file_paths: list[Path], athlete_root: Path) -> dict:
    return {
        "athlete_id": athlete_id,
        "created_at": _utc_now(),
        "included_paths": included_paths,
        "files": [str(path.relative_to(athlete_root).as_posix()) for path in file_paths],
    }


def _utc_now() -> str:
    from datetime import datetime

    return datetime.now(UTC).replace(microsecond=0).isoformat()


def create_backup_bundle(
    athlete_id: str,
    workspace_root: Path,
    mode: str = "full",
) -> BackupBundle:
    """Create a backup archive for an athlete.

    Inputs:
        athlete_id: Athlete identifier.
        workspace_root: Root path for athlete workspaces.
        mode: Partial restore mode (see PARTIAL_RESTORE_MODES).

    Returns:
        BackupBundle with filename + bytes.
    """

    if mode not in PARTIAL_RESTORE_MODES:
        raise ValueError(f"Unsupported backup mode: {mode}")

    athlete_root = (workspace_root / athlete_id).resolve()
    if not athlete_root.exists():
        raise FileNotFoundError(f"Athlete workspace not found: {athlete_root}")

    included_paths = PARTIAL_RESTORE_MODES[mode]
    file_paths = _iter_files(athlete_root, included_paths)

    manifest = _build_manifest(athlete_id, included_paths, file_paths, athlete_root)
    checksums = {}
    for path in file_paths:
        rel = path.relative_to(athlete_root)
        checksums[str(rel.as_posix())] = _hash_file(path)

    payload = io.BytesIO()
    filename = f"athlete_backup_{athlete_id}_{_utc_now().replace(':', '').replace('-', '')}.zip"

    with zipfile.ZipFile(payload, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        manifest_path = f"{BACKUP_ROOT}/{athlete_id}/manifest.json"
        checksums_path = f"{BACKUP_ROOT}/{athlete_id}/checksums.sha256"
        archive.writestr(manifest_path, json.dumps(manifest, indent=2))
        archive.writestr(checksums_path, json.dumps(checksums, indent=2))

        for path in file_paths:
            rel = path.relative_to(athlete_root)
            arcname = f"{BACKUP_ROOT}/{athlete_id}/{rel.as_posix()}"
            archive.write(path, arcname=arcname)

    LOGGER.info("Created backup bundle for athlete=%s mode=%s files=%d", athlete_id, mode, len(file_paths))
    return BackupBundle(filename=filename, data=payload.getvalue())


def restore_backup_bundle(
    athlete_id: str,
    workspace_root: Path,
    archive_bytes: bytes,
    mode: str = "full",
    force: bool = False,
) -> list[Path]:
    """Restore a backup archive into the athlete workspace.

    Inputs:
        athlete_id: Athlete identifier to restore into.
        workspace_root: Root path for athlete workspaces.
        archive_bytes: Raw archive bytes.
        mode: Partial restore mode (see PARTIAL_RESTORE_MODES).
        force: Allow restore into non-empty workspace.

    Returns:
        List of restored file paths.
    """

    if mode not in PARTIAL_RESTORE_MODES:
        raise ValueError(f"Unsupported restore mode: {mode}")

    athlete_root = (workspace_root / athlete_id).resolve()
    if athlete_root.exists() and any(athlete_root.iterdir()) and not force:
        raise RuntimeError("Target workspace is not empty. Use force to override.")
    athlete_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="rps_restore_", dir=str(workspace_root)) as temp_dir:
        temp_path = Path(temp_dir)
        archive_path = temp_path / "bundle"
        archive_path.write_bytes(archive_bytes)
        extract_root = temp_path / "extracted"
        extract_root.mkdir(parents=True, exist_ok=True)

        if zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(extract_root)
        elif tarfile.is_tarfile(archive_path):
            with tarfile.open(archive_path) as archive:
                archive.extractall(extract_root)
        else:
            raise ValueError("Unsupported archive format")

        bundle_root = extract_root / BACKUP_ROOT / athlete_id
        manifest_path = bundle_root / "manifest.json"
        checksums_path = bundle_root / "checksums.sha256"
        if not manifest_path.exists() or not checksums_path.exists():
            raise ValueError("Missing manifest or checksums in backup bundle")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("athlete_id") != athlete_id:
            raise ValueError("Backup athlete_id does not match restore target")

        checksums = json.loads(checksums_path.read_text(encoding="utf-8"))

        restored_paths: list[Path] = []
        allowed_prefixes = PARTIAL_RESTORE_MODES[mode]

        for rel_str, digest in checksums.items():
            rel_path = Path(rel_str)
            if not any(rel_path.as_posix().startswith(prefix) for prefix in allowed_prefixes):
                continue
            source_path = bundle_root / rel_path
            if not source_path.exists():
                raise ValueError(f"Missing file in bundle: {rel_str}")
            if _hash_file(source_path) != digest:
                raise ValueError(f"Checksum mismatch for {rel_str}")
            dest_path = athlete_root / rel_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(source_path.read_bytes())
            restored_paths.append(dest_path)

    LOGGER.info("Restored backup for athlete=%s mode=%s files=%d", athlete_id, mode, len(restored_paths))
    return restored_paths


def validate_backup_bundle(
    athlete_id: str,
    workspace_root: Path,
    archive_bytes: bytes,
    mode: str = "full",
) -> int:
    """Validate a backup archive without writing to disk.

    Inputs:
        athlete_id: Athlete identifier to validate against.
        workspace_root: Root path for athlete workspaces (used for temp extraction).
        archive_bytes: Raw archive bytes.
        mode: Partial restore mode (see PARTIAL_RESTORE_MODES).

    Returns:
        Count of files that would be restored.
    """

    if mode not in PARTIAL_RESTORE_MODES:
        raise ValueError(f"Unsupported restore mode: {mode}")

    with tempfile.TemporaryDirectory(prefix="rps_restore_", dir=str(workspace_root)) as temp_dir:
        temp_path = Path(temp_dir)
        archive_path = temp_path / "bundle"
        archive_path.write_bytes(archive_bytes)
        extract_root = temp_path / "extracted"
        extract_root.mkdir(parents=True, exist_ok=True)

        if zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(extract_root)
        elif tarfile.is_tarfile(archive_path):
            with tarfile.open(archive_path) as archive:
                archive.extractall(extract_root)
        else:
            raise ValueError("Unsupported archive format")

        bundle_root = extract_root / BACKUP_ROOT / athlete_id
        manifest_path = bundle_root / "manifest.json"
        checksums_path = bundle_root / "checksums.sha256"
        if not manifest_path.exists() or not checksums_path.exists():
            raise ValueError("Missing manifest or checksums in backup bundle")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("athlete_id") != athlete_id:
            raise ValueError("Backup athlete_id does not match restore target")

        checksums = json.loads(checksums_path.read_text(encoding="utf-8"))
        allowed_prefixes = PARTIAL_RESTORE_MODES[mode]
        matched = 0
        for rel_str, digest in checksums.items():
            rel_path = Path(rel_str)
            if not any(rel_path.as_posix().startswith(prefix) for prefix in allowed_prefixes):
                continue
            source_path = bundle_root / rel_path
            if not source_path.exists():
                raise ValueError(f"Missing file in bundle: {rel_str}")
            if _hash_file(source_path) != digest:
                raise ValueError(f"Checksum mismatch for {rel_str}")
            matched += 1

    return matched


def list_backup_files(
    athlete_id: str,
    workspace_root: Path,
    archive_bytes: bytes,
    mode: str = "full",
) -> list[str]:
    """Return the relative file paths that would be restored.

    Inputs:
        athlete_id: Athlete identifier to validate against.
        workspace_root: Root path for athlete workspaces (used for temp extraction).
        archive_bytes: Raw archive bytes.
        mode: Partial restore mode (see PARTIAL_RESTORE_MODES).

    Returns:
        Sorted list of relative file paths included in the restore scope.
    """

    if mode not in PARTIAL_RESTORE_MODES:
        raise ValueError(f"Unsupported restore mode: {mode}")

    with tempfile.TemporaryDirectory(prefix="rps_restore_", dir=str(workspace_root)) as temp_dir:
        temp_path = Path(temp_dir)
        archive_path = temp_path / "bundle"
        archive_path.write_bytes(archive_bytes)
        extract_root = temp_path / "extracted"
        extract_root.mkdir(parents=True, exist_ok=True)

        if zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(extract_root)
        elif tarfile.is_tarfile(archive_path):
            with tarfile.open(archive_path) as archive:
                archive.extractall(extract_root)
        else:
            raise ValueError("Unsupported archive format")

        bundle_root = extract_root / BACKUP_ROOT / athlete_id
        manifest_path = bundle_root / "manifest.json"
        checksums_path = bundle_root / "checksums.sha256"
        if not manifest_path.exists() or not checksums_path.exists():
            raise ValueError("Missing manifest or checksums in backup bundle")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("athlete_id") != athlete_id:
            raise ValueError("Backup athlete_id does not match restore target")

        checksums = json.loads(checksums_path.read_text(encoding="utf-8"))
        allowed_prefixes = PARTIAL_RESTORE_MODES[mode]
        included: list[str] = []

        for rel_str, digest in checksums.items():
            rel_path = Path(rel_str)
            if not any(rel_path.as_posix().startswith(prefix) for prefix in allowed_prefixes):
                continue
            source_path = bundle_root / rel_path
            if not source_path.exists():
                raise ValueError(f"Missing file in bundle: {rel_str}")
            if _hash_file(source_path) != digest:
                raise ValueError(f"Checksum mismatch for {rel_str}")
            included.append(rel_path.as_posix())

    return sorted(included)
