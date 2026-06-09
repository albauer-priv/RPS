import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from rps.orchestrator.queue_scheduler import ensure_queue_dirs
from rps.ui.run_store import (
    clear_queue_folders,
    find_active_runs,
    load_runs,
    prune_run_history,
    summarize_runtime_events,
)

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


def test_load_runs_and_find_active_runs_sort_by_record_created_at(tmp_path: Path) -> None:
    root = tmp_path
    athlete_id = "athlete_2"
    run_root = root / athlete_id / "runs"
    newer = run_root / "newer_run"
    older = run_root / "older_run"
    newer.mkdir(parents=True, exist_ok=True)
    older.mkdir(parents=True, exist_ok=True)

    (older / "run.json").write_text(
        json.dumps(
            {
                "run_id": "older_run",
                "status": "QUEUED",
                "process_type": "data_pipeline",
                "process_subtype": "intervals_fetch",
                "created_at": "2026-04-15T10:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    (newer / "run.json").write_text(
        json.dumps(
            {
                "run_id": "newer_run",
                "status": "RUNNING",
                "process_type": "data_pipeline",
                "process_subtype": "intervals_fetch",
                "created_at": "2026-04-15T11:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    runs = load_runs(root, athlete_id, limit=10)
    assert [run["run_id"] for run in runs] == ["newer_run", "older_run"]

    active = find_active_runs(
        root,
        athlete_id,
        process_type="data_pipeline",
        process_subtype="intervals_fetch",
    )
    assert [run["run_id"] for run in active] == ["newer_run", "older_run"]


def test_summarize_runtime_events_reports_active_crew_task_and_progress() -> None:
    events = [
        {"type": "FLOW_STARTED", "flow": "PhaseOuterFlow"},
        {"type": "FLOW_STEP_STARTED", "flow": "PhaseOuterFlow", "step": "run_planning_cycle"},
        {"type": "CREW_STARTED", "crew": "phase_planning"},
        {
            "type": "CREW_TASK_PREPARED",
            "crew": "phase_planning",
            "task": "phase_context_read",
            "agent": "phase_context_specialist",
            "status": "1/9",
        },
        {
            "type": "CREW_TASK_PREPARED",
            "crew": "phase_planning",
            "task": "phase_guardrail_band_draft",
            "agent": "phase_guardrail_band_specialist",
            "status": "2/9",
        },
        {
            "type": "CREW_TASK_STARTED",
            "crew": "phase_planning",
            "task": "phase_guardrail_band_draft",
            "agent": "phase_guardrail_band_specialist",
            "model": "gpt-5.4-mini",
            "component": "crew:phase_bundle_finalize",
        },
    ]

    summary = summarize_runtime_events(events)

    assert summary["flow"] == "PhaseOuterFlow"
    assert summary["flow_step"] == "run_planning_cycle"
    assert summary["crew"] == "phase_planning"
    assert summary["task"] == "phase_guardrail_band_draft"
    assert summary["agent"] == "phase_guardrail_band_specialist"
    assert summary["model"] == "gpt-5.4-mini"
    assert summary["task_progress"] == "2/9"
    assert summary["task_index"] == 2
    assert summary["task_total"] == 9
