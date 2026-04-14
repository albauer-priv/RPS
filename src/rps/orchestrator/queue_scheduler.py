"""File-based queue + scheduler for planning runs."""

from __future__ import annotations

import json
import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from rps.agents.multi_output_runner import AgentRuntime
from rps.orchestrator.plan_hub_worker import PlanHubWorkerConfig, start_plan_hub_worker_with_stop
from rps.ui.run_store import load_runs

logger = logging.getLogger(__name__)

QueueItem = dict[str, object]


@dataclass(frozen=True)
class QueuePaths:
    """Queue directory layout."""

    root: Path

    @property
    def base(self) -> Path:
        return self.root / "runs" / "queue"

    @property
    def pending(self) -> Path:
        return self.base / "pending"

    @property
    def active(self) -> Path:
        return self.base / "active"

    @property
    def done(self) -> Path:
        return self.base / "done"

    @property
    def failed(self) -> Path:
        return self.base / "failed"


def ensure_queue_dirs(root: Path) -> QueuePaths:
    """Ensure queue directories exist."""
    paths = QueuePaths(root=root)
    paths.pending.mkdir(parents=True, exist_ok=True)
    paths.active.mkdir(parents=True, exist_ok=True)
    paths.done.mkdir(parents=True, exist_ok=True)
    paths.failed.mkdir(parents=True, exist_ok=True)
    return paths


def enqueue_run(
    root: Path,
    run_id: str,
    payload: QueueItem,
) -> Path:
    """Enqueue a run by writing a queue item into pending."""
    paths = ensure_queue_dirs(root)
    path = paths.pending / f"{run_id}.json"
    data = dict(payload)
    data.setdefault("run_id", run_id)
    data.setdefault("created_at", datetime.now(UTC).isoformat())
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _list_queue(paths: QueuePaths, folder: Path) -> list[Path]:
    return sorted(folder.glob("*.json"), key=lambda p: p.stat().st_mtime)


def _read_queue_item(path: Path) -> QueueItem:
    return json.loads(path.read_text(encoding="utf-8"))


def _item_str(item: QueueItem, key: str) -> str | None:
    """Return a required queue item string field when present and non-empty."""
    value = item.get(key)
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _eligible(root: Path, item: QueueItem) -> bool:
    """Return True if no other active run for the same athlete."""
    athlete_id = _item_str(item, "athlete_id")
    run_id = item.get("run_id")
    if not athlete_id:
        return False
    active_runs = load_runs(root, athlete_id, limit=20)
    for run in active_runs:
        if run.get("status") not in {"QUEUED", "RUNNING"}:
            continue
        # Ignore the queued run that matches this queue item.
        if run_id and run.get("run_id") == run_id:
            continue
        return False
    return True


def _move(path: Path, dest_dir: Path) -> Path:
    dest = dest_dir / path.name
    return path.replace(dest)


def start_queue_scheduler(
    *,
    root: Path,
    runtime_for_agent: Callable[[str], AgentRuntime],
    model_resolver: Callable[[str], str] | None,
    temperature_resolver: Callable[[str], float | None] | None,
    reasoning_effort_resolver: Callable[[str], str | None] | None,
    reasoning_summary_resolver: Callable[[str], str | None] | None,
    force_file_search: bool,
    max_num_results: int,
    poll_seconds: int = 2,
    stop_event: threading.Event | None = None,
) -> dict[str, object]:
    """Start a background scheduler that pulls from the queue and runs workers."""
    stop_event = stop_event or threading.Event()
    paths = ensure_queue_dirs(root)

    def _loop() -> None:
        logger.info("Queue scheduler started")
        while not stop_event.is_set():
            for item_path in _list_queue(paths, paths.pending):
                try:
                    item = _read_queue_item(item_path)
                except Exception as exc:
                    logger.warning("Queue item read failed %s: %s", item_path, exc)
                    _move(item_path, paths.failed)
                    continue
                if not _eligible(root, item):
                    continue
                # Claim
                active_path = _move(item_path, paths.active)
                athlete_id = _item_str(item, "athlete_id")
                run_id = _item_str(item, "run_id")
                if athlete_id is None or run_id is None:
                    logger.warning("Queue item missing athlete_id/run_id %s", active_path)
                    _move(active_path, paths.failed)
                    continue
                config = PlanHubWorkerConfig(
                    root=root,
                    athlete_id=athlete_id,
                    run_id=run_id,
                    runtime_for_agent=runtime_for_agent,
                    model_resolver=model_resolver,
                    temperature_resolver=temperature_resolver,
                    reasoning_effort_resolver=reasoning_effort_resolver,
                    reasoning_summary_resolver=reasoning_summary_resolver,
                    force_file_search=force_file_search,
                    max_num_results=max_num_results,
                    allow_delete_intervals=bool(item.get("allow_delete_intervals")),
                )
                worker = start_plan_hub_worker_with_stop(config, stop_event)
                # Wait for worker completion (poll run store status)
                while not stop_event.is_set():
                    runs = load_runs(root, config.athlete_id, limit=5)
                    active = next((r for r in runs if r.get("run_id") == config.run_id), None)
                    if not active:
                        break
                    if active.get("status") in {"DONE", "FAILED", "CANCELLED"}:
                        break
                    time.sleep(1)
                # Move queue item to done/failed
                runs = load_runs(root, config.athlete_id, limit=5)
                active = next((r for r in runs if r.get("run_id") == config.run_id), None)
                if active and active.get("status") == "DONE":
                    _move(active_path, paths.done)
                else:
                    _move(active_path, paths.failed)
                # Stop if a worker was cancelled
                if worker.get("stop"):
                    pass
            time.sleep(poll_seconds)
        logger.info("Queue scheduler stopped")

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
    return {"thread": thread, "stop": stop_event}
