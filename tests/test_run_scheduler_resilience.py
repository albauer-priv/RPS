"""Tests for stuck-run detection and recovery (FEAT_run_scheduler_resilience)."""

import json
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from rps.orchestrator.queue_scheduler import (
    _recover_orphaned_active_items,
    _recover_orphaned_queued_runs,
    _recover_stuck_runs,
    ensure_queue_dirs,
)
from rps.ui.run_store import (
    STALE_LOCK_AGE_SECONDS,
    _lock_is_stale,
    _lock_path,
    _read_lock_run_id,
    _recover_stale_lock,
    acquire_athlete_lock,
    load_events,
    load_runs,
    release_athlete_lock,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_run(root: Path, athlete_id: str, run_id: str, status: str) -> None:
    run_dir = root / athlete_id / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "athlete_id": athlete_id,
                "status": status,
                "created_at": datetime.now(UTC).isoformat(),
            }
        ),
        encoding="utf-8",
    )


def _write_lock(root: Path, athlete_id: str, run_id: str) -> Path:
    lock = _lock_path(root, athlete_id)
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(
        json.dumps({"run_id": run_id, "ts": datetime.now(UTC).isoformat()}) + "\n",
        encoding="utf-8",
    )
    return lock


def _write_queue_item(folder: Path, run_id: str, athlete_id: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{run_id}.json"
    path.write_text(
        json.dumps({"run_id": run_id, "athlete_id": athlete_id}),
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# _read_lock_run_id
# ---------------------------------------------------------------------------

def test_read_lock_run_id_returns_run_id(tmp_path: Path) -> None:
    _write_lock(tmp_path, "ath1", "run_abc")
    assert _read_lock_run_id(tmp_path, "ath1") == "run_abc"


def test_read_lock_run_id_missing_returns_none(tmp_path: Path) -> None:
    assert _read_lock_run_id(tmp_path, "ath1") is None


def test_read_lock_run_id_corrupt_returns_none(tmp_path: Path) -> None:
    lock = _lock_path(tmp_path, "ath1")
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text("not json", encoding="utf-8")
    assert _read_lock_run_id(tmp_path, "ath1") is None


# ---------------------------------------------------------------------------
# _lock_is_stale
# ---------------------------------------------------------------------------

def test_lock_is_stale_no_lock(tmp_path: Path) -> None:
    assert _lock_is_stale(tmp_path, "ath1") is False


def test_lock_is_stale_run_missing(tmp_path: Path) -> None:
    _write_lock(tmp_path, "ath1", "run_gone")
    # No run record written → stale
    assert _lock_is_stale(tmp_path, "ath1") is True


def test_lock_is_stale_run_done(tmp_path: Path) -> None:
    _write_run(tmp_path, "ath1", "run_done", "DONE")
    _write_lock(tmp_path, "ath1", "run_done")
    assert _lock_is_stale(tmp_path, "ath1") is True


def test_lock_is_stale_run_failed(tmp_path: Path) -> None:
    _write_run(tmp_path, "ath1", "run_fail", "FAILED")
    _write_lock(tmp_path, "ath1", "run_fail")
    assert _lock_is_stale(tmp_path, "ath1") is True


def test_lock_is_stale_run_running_fresh(tmp_path: Path) -> None:
    _write_run(tmp_path, "ath1", "run_live", "RUNNING")
    _write_lock(tmp_path, "ath1", "run_live")
    # Lock is recent, run is active → not stale
    assert _lock_is_stale(tmp_path, "ath1") is False


def test_lock_is_stale_old_mtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_run(tmp_path, "ath1", "run_live", "RUNNING")
    lock = _write_lock(tmp_path, "ath1", "run_live")
    # Backdate mtime beyond threshold
    old_ts = time.time() - STALE_LOCK_AGE_SECONDS - 60
    import os
    os.utime(lock, (old_ts, old_ts))
    assert _lock_is_stale(tmp_path, "ath1") is True


# ---------------------------------------------------------------------------
# _recover_stale_lock
# ---------------------------------------------------------------------------

def test_recover_stale_lock_no_lock(tmp_path: Path) -> None:
    assert _recover_stale_lock(tmp_path, "ath1") is False


def test_recover_stale_lock_live_run_not_recovered(tmp_path: Path) -> None:
    _write_run(tmp_path, "ath1", "run_live", "RUNNING")
    _write_lock(tmp_path, "ath1", "run_live")
    assert _recover_stale_lock(tmp_path, "ath1") is False
    assert _lock_path(tmp_path, "ath1").exists()


def test_recover_stale_lock_terminal_run(tmp_path: Path) -> None:
    _write_run(tmp_path, "ath1", "run_done", "DONE")
    _write_lock(tmp_path, "ath1", "run_done")
    result = _recover_stale_lock(tmp_path, "ath1")
    assert result is True
    assert not _lock_path(tmp_path, "ath1").exists()


def test_recover_stale_lock_fails_stuck_running_run(tmp_path: Path) -> None:
    _write_run(tmp_path, "ath1", "run_stuck", "RUNNING")
    _write_lock(tmp_path, "ath1", "run_stuck")
    # Make lock stale by setting mtime in the past
    lock = _lock_path(tmp_path, "ath1")
    import os
    old_ts = time.time() - STALE_LOCK_AGE_SECONDS - 60
    os.utime(lock, (old_ts, old_ts))

    result = _recover_stale_lock(tmp_path, "ath1")
    assert result is True
    assert not lock.exists()

    runs = load_runs(tmp_path, "ath1", limit=10)
    run = next(r for r in runs if r["run_id"] == "run_stuck")
    assert run["status"] == "FAILED"

    events = load_events(tmp_path, "ath1", "run_stuck")
    assert any(e.get("type") == "RUN_FAILED" for e in events)
    assert any("stale lock" in str(e.get("reason", "")) for e in events)


def test_recover_stale_lock_missing_run_id_in_lock(tmp_path: Path) -> None:
    lock = _lock_path(tmp_path, "ath1")
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(json.dumps({"ts": datetime.now(UTC).isoformat()}) + "\n", encoding="utf-8")
    # Lock has no run_id → stale
    result = _recover_stale_lock(tmp_path, "ath1")
    assert result is True
    assert not lock.exists()


# ---------------------------------------------------------------------------
# acquire_athlete_lock with stale lock recovery
# ---------------------------------------------------------------------------

def test_acquire_lock_succeeds_after_stale_recovery(tmp_path: Path) -> None:
    _write_run(tmp_path, "ath1", "old_run", "DONE")
    _write_lock(tmp_path, "ath1", "old_run")

    acquired = acquire_athlete_lock(tmp_path, "ath1", "new_run")
    assert acquired is True
    assert _read_lock_run_id(tmp_path, "ath1") == "new_run"


def test_acquire_lock_fails_with_live_run(tmp_path: Path) -> None:
    _write_run(tmp_path, "ath1", "live_run", "RUNNING")
    _write_lock(tmp_path, "ath1", "live_run")

    acquired = acquire_athlete_lock(tmp_path, "ath1", "new_run")
    assert acquired is False
    # Original lock untouched
    assert _read_lock_run_id(tmp_path, "ath1") == "live_run"


def test_acquire_lock_idempotent_stale_recovery(tmp_path: Path) -> None:
    _write_run(tmp_path, "ath1", "old_run", "FAILED")
    _write_lock(tmp_path, "ath1", "old_run")

    # First call acquires after recovery
    assert acquire_athlete_lock(tmp_path, "ath1", "run_a") is True
    release_athlete_lock(tmp_path, "ath1")

    # Second call — no stale lock, fresh acquire
    assert acquire_athlete_lock(tmp_path, "ath1", "run_b") is True


# ---------------------------------------------------------------------------
# _recover_orphaned_active_items
# ---------------------------------------------------------------------------

def test_recover_orphaned_moves_done_run_to_done(tmp_path: Path) -> None:
    paths = ensure_queue_dirs(tmp_path)
    _write_run(tmp_path, "ath2", "run_done", "DONE")
    _write_queue_item(paths.active, "run_done", "ath2")

    _recover_orphaned_active_items(paths, tmp_path)

    assert not (paths.active / "run_done.json").exists()
    assert (paths.done / "run_done.json").exists()


def test_recover_orphaned_moves_failed_run_to_failed(tmp_path: Path) -> None:
    paths = ensure_queue_dirs(tmp_path)
    _write_run(tmp_path, "ath2", "run_fail", "FAILED")
    _write_queue_item(paths.active, "run_fail", "ath2")

    _recover_orphaned_active_items(paths, tmp_path)

    assert not (paths.active / "run_fail.json").exists()
    assert (paths.failed / "run_fail.json").exists()


def test_recover_orphaned_fails_stuck_running_run(tmp_path: Path) -> None:
    paths = ensure_queue_dirs(tmp_path)
    _write_run(tmp_path, "ath2", "run_stuck", "RUNNING")
    _write_lock(tmp_path, "ath2", "run_stuck")
    _write_queue_item(paths.active, "run_stuck", "ath2")

    _recover_orphaned_active_items(paths, tmp_path)

    assert not (paths.active / "run_stuck.json").exists()
    assert (paths.failed / "run_stuck.json").exists()

    runs = load_runs(tmp_path, "ath2", limit=10)
    run = next(r for r in runs if r["run_id"] == "run_stuck")
    assert run["status"] == "FAILED"

    events = load_events(tmp_path, "ath2", "run_stuck")
    assert any("orphaned" in str(e.get("reason", "")) for e in events)


def test_recover_orphaned_fails_missing_run(tmp_path: Path) -> None:
    paths = ensure_queue_dirs(tmp_path)
    # No run record written, just the queue item
    _write_queue_item(paths.active, "run_ghost", "ath2")

    _recover_orphaned_active_items(paths, tmp_path)

    assert not (paths.active / "run_ghost.json").exists()
    assert (paths.failed / "run_ghost.json").exists()


def test_recover_orphaned_skips_corrupt_item(tmp_path: Path) -> None:
    paths = ensure_queue_dirs(tmp_path)
    (paths.active / "bad.json").write_text("not json", encoding="utf-8")

    # Must not raise
    _recover_orphaned_active_items(paths, tmp_path)
    assert (paths.failed / "bad.json").exists()


def test_recover_orphaned_idempotent(tmp_path: Path) -> None:
    paths = ensure_queue_dirs(tmp_path)
    _write_run(tmp_path, "ath2", "run_done", "DONE")
    _write_queue_item(paths.active, "run_done", "ath2")

    _recover_orphaned_active_items(paths, tmp_path)
    # Second call: nothing in active/ → no-op, no error
    _recover_orphaned_active_items(paths, tmp_path)
    assert (paths.done / "run_done.json").exists()


# ---------------------------------------------------------------------------
# _recover_stuck_runs
# ---------------------------------------------------------------------------

def test_recover_stuck_runs_no_locks(tmp_path: Path) -> None:
    # Should not raise when no lock files exist
    _recover_stuck_runs(tmp_path)


def test_recover_stuck_runs_clears_stale_lock(tmp_path: Path) -> None:
    _write_run(tmp_path, "ath3", "old_run", "DONE")
    _write_lock(tmp_path, "ath3", "old_run")

    _recover_stuck_runs(tmp_path)

    assert not _lock_path(tmp_path, "ath3").exists()


def test_recover_stuck_runs_leaves_live_lock(tmp_path: Path) -> None:
    _write_run(tmp_path, "ath3", "live_run", "RUNNING")
    _write_lock(tmp_path, "ath3", "live_run")

    _recover_stuck_runs(tmp_path)

    # Lock is fresh + run is active → untouched
    assert _lock_path(tmp_path, "ath3").exists()


def test_recover_stuck_runs_fails_run_with_failed_queue_item(tmp_path: Path) -> None:
    """RUNNING run whose queue item landed in failed/ (no active/ item) is recovered."""
    paths = ensure_queue_dirs(tmp_path)
    _write_run(tmp_path, "ath4", "stuck_run", "RUNNING")
    _write_lock(tmp_path, "ath4", "stuck_run")
    # Simulate: queue item already moved to failed/, nothing in active/
    _write_queue_item(paths.failed, "stuck_run", "ath4")

    _recover_stuck_runs(tmp_path)

    assert not _lock_path(tmp_path, "ath4").exists()
    runs = load_runs(tmp_path, "ath4", limit=10)
    run = next(r for r in runs if r["run_id"] == "stuck_run")
    assert run["status"] == "FAILED"
    events = load_events(tmp_path, "ath4", "stuck_run")
    assert any("queue item in failed" in str(e.get("reason", "")) for e in events)


def test_recover_stuck_runs_ignores_run_with_active_queue_item(tmp_path: Path) -> None:
    """RUNNING run with a healthy active/ item is left alone."""
    paths = ensure_queue_dirs(tmp_path)
    _write_run(tmp_path, "ath4", "live_run", "RUNNING")
    _write_lock(tmp_path, "ath4", "live_run")
    _write_queue_item(paths.active, "live_run", "ath4")
    # Also put a stale copy in failed/ — active/ presence should suppress recovery
    _write_queue_item(paths.failed, "live_run", "ath4")

    _recover_stuck_runs(tmp_path)

    assert _lock_path(tmp_path, "ath4").exists()
    runs = load_runs(tmp_path, "ath4", limit=10)
    run = next(r for r in runs if r["run_id"] == "live_run")
    assert run["status"] == "RUNNING"


# ---------------------------------------------------------------------------
# _recover_orphaned_queued_runs
# ---------------------------------------------------------------------------

def test_recover_orphaned_queued_runs_fails_queued_run_with_no_queue_item(tmp_path: Path) -> None:
    """QUEUED run with no pending/ or active/ item is failed so new runs can start."""
    paths = ensure_queue_dirs(tmp_path)
    _write_run(tmp_path, "ath5", "orphan_run", "QUEUED")
    # Queue item only in failed/ — simulates read-error-then-move scenario
    _write_queue_item(paths.failed, "orphan_run", "ath5")

    _recover_orphaned_queued_runs(paths, tmp_path)

    runs = load_runs(tmp_path, "ath5", limit=10)
    run = next(r for r in runs if r["run_id"] == "orphan_run")
    assert run["status"] == "FAILED"
    events = load_events(tmp_path, "ath5", "orphan_run")
    assert any("no pending or active queue item" in str(e.get("reason", "")) for e in events)


def test_recover_orphaned_queued_runs_leaves_pending_run_alone(tmp_path: Path) -> None:
    """QUEUED run with a valid pending/ item must not be failed."""
    paths = ensure_queue_dirs(tmp_path)
    _write_run(tmp_path, "ath5", "waiting_run", "QUEUED")
    _write_queue_item(paths.pending, "waiting_run", "ath5")

    _recover_orphaned_queued_runs(paths, tmp_path)

    runs = load_runs(tmp_path, "ath5", limit=10)
    run = next(r for r in runs if r["run_id"] == "waiting_run")
    assert run["status"] == "QUEUED"


def test_recover_orphaned_queued_runs_leaves_active_run_alone(tmp_path: Path) -> None:
    """RUNNING run with an item in active/ must not be touched."""
    paths = ensure_queue_dirs(tmp_path)
    _write_run(tmp_path, "ath5", "active_run", "RUNNING")
    _write_queue_item(paths.active, "active_run", "ath5")

    _recover_orphaned_queued_runs(paths, tmp_path)

    runs = load_runs(tmp_path, "ath5", limit=10)
    run = next(r for r in runs if r["run_id"] == "active_run")
    assert run["status"] == "RUNNING"
