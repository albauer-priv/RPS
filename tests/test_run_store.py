import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from rps.orchestrator.queue_scheduler import ensure_queue_dirs
from rps.ui.run_store import clear_queue_folders, prune_run_history

EXPECTED_CLEARED_QUEUE_FILES = 2


def _write_run(root: Path, athlete_id: str, run_id: str, days_ago: int) -> None:
    run_dir = root / athlete_id / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    created_at = (datetime.now(UTC) - timedelta(days=days_ago)).isoformat()
    (run_dir / "run.json").write_text(json.dumps({"run_id": run_id, "created_at": created_at}), encoding="utf-8")


def test_prune_run_history(tmp_path: Path) -> None:
    root = tmp_path
    athlete_id = "athlete_1"
    _write_run(root, athlete_id, "old_run", days_ago=30)
    _write_run(root, athlete_id, "recent_run", days_ago=2)

    removed = prune_run_history(root, athlete_id, retention_days=7)
    assert removed == 1
    assert (root / athlete_id / "runs" / "old_run").exists() is False
    assert (root / athlete_id / "runs" / "recent_run").exists()


def test_clear_queue_folders(tmp_path: Path) -> None:
    root = tmp_path
    queues = ensure_queue_dirs(root)
    (queues.done / "one.json").write_text("{}", encoding="utf-8")
    (queues.failed / "two.json").write_text("{}", encoding="utf-8")

    removed = clear_queue_folders(root)
    assert removed == EXPECTED_CLEARED_QUEUE_FILES
    assert not any(queues.done.glob("*.json"))
    assert not any(queues.failed.glob("*.json"))
