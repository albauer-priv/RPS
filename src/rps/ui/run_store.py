"""Run store for Plan Hub execution tracking."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunStoreConfig:
    """Configuration for the run store."""

    root: Path


def _run_store_dir(root: Path, athlete_id: str) -> Path:
    """Return the run store directory for an athlete."""
    return (root / athlete_id / "runs").resolve()


def run_store_path(root: Path, athlete_id: str) -> Path:
    """Return the JSONL path for legacy plan hub runs."""
    return _run_store_dir(root, athlete_id) / "plan_hub_runs.jsonl"


def run_dir(root: Path, athlete_id: str, run_id: str) -> Path:
    """Return the directory for a specific run."""
    return _run_store_dir(root, athlete_id) / run_id


def run_json_path(root: Path, athlete_id: str, run_id: str) -> Path:
    """Return the path for the run.json."""
    return run_dir(root, athlete_id, run_id) / "run.json"


def steps_json_path(root: Path, athlete_id: str, run_id: str) -> Path:
    """Return the path for the steps.json."""
    return run_dir(root, athlete_id, run_id) / "steps.json"


def events_jsonl_path(root: Path, athlete_id: str, run_id: str) -> Path:
    """Return the path for the events JSONL."""
    return run_dir(root, athlete_id, run_id) / "events.jsonl"


def _utc_iso_now() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _utc_run_id_suffix() -> str:
    """Return a filesystem-safe UTC suffix for run ids."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utc_timestamp() -> str:
    """Return current UTC time as ISO-8601 string."""
    return _utc_iso_now()


def _atomic_write_json(path: Path, payload: dict | list) -> None:
    """Write JSON atomically to avoid partial reads."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp_path, path)


def _load_run_dir(root: Path, athlete_id: str, run_id: str) -> dict[str, Any] | None:
    """Load a run.json + steps.json for a run."""
    run_path = run_json_path(root, athlete_id, run_id)
    if not run_path.exists():
        return None
    try:
        run_record = json.loads(run_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("Skipping invalid run.json for run_id=%s", run_id)
        return None
    steps_path = steps_json_path(root, athlete_id, run_id)
    if steps_path.exists():
        try:
            run_record["steps"] = json.loads(steps_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("Skipping invalid steps.json for run_id=%s", run_id)
    return run_record


def load_runs(root: Path, athlete_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
    """Load run records from per-run directories (fallback to legacy JSONL)."""
    records: list[dict[str, Any]] = []
    run_root = _run_store_dir(root, athlete_id)
    if run_root.exists():
        for run_path in run_root.iterdir():
            if not run_path.is_dir():
                continue
            record = _load_run_dir(root, athlete_id, run_path.name)
            if record:
                records.append(record)
    # Legacy fallback for older runs
    path = run_store_path(root, athlete_id)
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                # skip if run already loaded from per-run dir
                if any(r.get("run_id") == record.get("run_id") for r in records):
                    continue
                records.append(record)
            except json.JSONDecodeError:
                logger.warning("Skipping invalid run_store line in %s", path)
    records.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return records[:limit]


def append_run(root: Path, athlete_id: str, record: dict[str, Any]) -> None:
    """Write a run.json + steps.json for the run (append-only)."""
    record = dict(record)
    run_id = record.get("run_id")
    if not run_id:
        raise ValueError("run_id is required")
    record.setdefault("created_at", _utc_iso_now())
    steps = record.pop("steps", None)
    run_path = run_json_path(root, athlete_id, run_id)
    run_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Appending run record run_id=%s athlete=%s", run_id, athlete_id)
    _atomic_write_json(run_path, record)
    if steps is not None:
        steps_path = steps_json_path(root, athlete_id, run_id)
        _atomic_write_json(steps_path, steps)


def update_run(root: Path, athlete_id: str, run_id: str, updates: dict[str, Any]) -> bool:
    """Update a run record in-place; returns True if updated."""
    run_path = run_json_path(root, athlete_id, run_id)
    if not run_path.exists():
        return False
    try:
        record = json.loads(run_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    steps = updates.pop("steps", None)
    record.update(updates)
    logger.info("Updating run record run_id=%s athlete=%s", run_id, athlete_id)
    _atomic_write_json(run_path, record)
    if steps is not None:
        steps_path = steps_json_path(root, athlete_id, run_id)
        _atomic_write_json(steps_path, steps)
    return True


def append_event(root: Path, athlete_id: str, run_id: str, event: dict[str, Any]) -> None:
    """Append an event to the run events.jsonl."""
    path = events_jsonl_path(root, athlete_id, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(event)
    payload.setdefault("ts", _utc_iso_now())
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def start_background_run(
    root: Path,
    athlete_id: str,
    *,
    process_type: str,
    process_subtype: str,
    message: str,
    status: str = "QUEUED",
) -> str:
    """Create a run store record for a background process."""
    run_id = f"bg_{process_type}_{process_subtype}_{_utc_run_id_suffix()}"
    record = {
        "run_id": run_id,
        "status": status,
        "mode": "BACKGROUND",
        "process_type": process_type,
        "process_subtype": process_subtype,
        "message": message,
        "created_at": _utc_iso_now(),
    }
    if status == "RUNNING":
        record["started_at"] = _utc_iso_now()
    append_run(root, athlete_id, record)
    return run_id


@dataclass(frozen=True)
class BackgroundRunTracker:
    """Helper for updating background run status."""

    root: Path
    athlete_id: str
    run_id: str

    def mark_running(self, message: str) -> None:
        update_run(
            self.root,
            self.athlete_id,
            self.run_id,
            {"status": "RUNNING", "message": message, "started_at": _utc_timestamp()},
        )

    def mark_done(self, message: str) -> None:
        update_run(
            self.root,
            self.athlete_id,
            self.run_id,
            {"status": "DONE", "message": message, "finished_at": _utc_timestamp()},
        )

    def mark_failed(self, message: str) -> None:
        update_run(
            self.root,
            self.athlete_id,
            self.run_id,
            {"status": "FAILED", "message": message, "finished_at": _utc_timestamp()},
        )


def start_background_tracker(
    root: Path,
    athlete_id: str,
    *,
    process_type: str,
    process_subtype: str,
    message: str,
    status: str = "QUEUED",
) -> BackgroundRunTracker:
    """Start a background run and return a tracker for updates."""
    run_id = start_background_run(
        root,
        athlete_id,
        process_type=process_type,
        process_subtype=process_subtype,
        message=message,
        status=status,
    )
    return BackgroundRunTracker(root=root, athlete_id=athlete_id, run_id=run_id)


def acquire_athlete_lock(root: Path, athlete_id: str, run_id: str) -> bool:
    """Acquire a per-athlete lock; returns True on success."""
    lock_dir = (root / athlete_id / "locks").resolve()
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / f"athlete_{athlete_id}.lock"
    try:
        with lock_path.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps({"run_id": run_id, "ts": _utc_iso_now()}, ensure_ascii=False) + "\n")
        return True
    except FileExistsError:
        return False


def release_athlete_lock(root: Path, athlete_id: str) -> None:
    """Release the per-athlete lock if present."""
    lock_path = (root / athlete_id / "locks" / f"athlete_{athlete_id}.lock").resolve()
    if lock_path.exists():
        lock_path.unlink()


def load_events(root: Path, athlete_id: str, run_id: str, *, limit: int = 200) -> list[dict[str, Any]]:
    """Load run events from events.jsonl."""
    path = events_jsonl_path(root, athlete_id, run_id)
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            logger.warning("Skipping invalid event line in %s", path)
    return events[-limit:]
