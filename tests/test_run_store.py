import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from rps.orchestrator.queue_scheduler import ensure_queue_dirs
from rps.ui.run_store import (
    append_event,
    append_run,
    clear_queue_folders,
    find_active_runs,
    load_enriched_run_events,
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


def test_load_enriched_run_events_backfills_parent_step_metadata(tmp_path: Path) -> None:
    athlete_id = "athlete"
    run_id = "plan_run"
    append_run(
        tmp_path,
        athlete_id,
        {
            "run_id": run_id,
            "status": "RUNNING",
            "message": "Scoped planning run.",
            "steps": [
                {
                    "step_id": "WEEK_PLAN",
                    "Step": "Week Plan",
                    "Details": "Explicit scoped rerun requested.",
                    "Agent": "Week Planner",
                    "Writes": "WEEK_PLAN",
                    "Authority": "Binding",
                }
            ],
        },
    )
    append_event(
        tmp_path,
        athlete_id,
        run_id,
        {"type": "STEP_STARTED", "step_id": "WEEK_PLAN"},
    )

    events = load_enriched_run_events(tmp_path, athlete_id, run_id)

    assert len(events) == 1
    event = events[0]
    assert event["step"] == "Week Plan"
    assert event["agent"] == "Week Planner"
    assert event["writes"] == "WEEK_PLAN"
    assert event["authority"] == "Binding"
    assert event["details"] == "Explicit scoped rerun requested."


def test_load_enriched_run_events_merges_direct_child_telemetry(tmp_path: Path) -> None:
    athlete_id = "athlete"
    parent_run_id = "plan_run"
    append_run(tmp_path, athlete_id, {"run_id": parent_run_id, "status": "RUNNING", "steps": []})
    append_event(
        tmp_path,
        athlete_id,
        parent_run_id,
        {"type": "RUN_STARTED", "ts": "2026-06-09T07:25:46+00:00", "details": "Parent"},
    )

    child_run_id = f"{parent_run_id}_week"
    append_run(tmp_path, athlete_id, {"run_id": child_run_id, "status": "RUNNING", "steps": []})
    append_event(
        tmp_path,
        athlete_id,
        child_run_id,
        {
            "type": "FLOW_STEP_STARTED",
            "ts": "2026-06-09T07:25:47+00:00",
            "flow": "WeekOuterFlow",
            "step": "run_planning_cycle",
        },
    )

    events = load_enriched_run_events(tmp_path, athlete_id, parent_run_id)

    assert [event["source_run_id"] for event in events] == [parent_run_id, child_run_id]
    assert events[0]["details"] == "Parent"
    assert events[1]["timestamp"] == "2026-06-09T07:25:47+00:00"
    assert events[1]["flow"] == "WeekOuterFlow"
    assert events[1]["step"] == "run_planning_cycle"


def test_load_enriched_run_events_prefers_explicit_detail_fields(tmp_path: Path) -> None:
    athlete_id = "athlete"
    run_id = "plan_run"
    append_run(
        tmp_path,
        athlete_id,
        {
            "run_id": run_id,
            "status": "RUNNING",
            "steps": [{"step_id": "WEEK_PLAN", "Step": "Week Plan", "Details": "Fallback details"}],
        },
    )
    append_event(
        tmp_path,
        athlete_id,
        run_id,
        {
            "type": "STEP_FAILED",
            "step_id": "WEEK_PLAN",
            "details": "Explicit details",
            "reason": "Lower priority reason",
        },
    )

    events = load_enriched_run_events(tmp_path, athlete_id, run_id)

    assert len(events) == 1
    assert events[0]["details"] == "Explicit details"


def test_load_enriched_run_events_ignores_unknown_prefixed_child_runs(tmp_path: Path) -> None:
    athlete_id = "athlete"
    parent_run_id = "plan_run"
    append_run(tmp_path, athlete_id, {"run_id": parent_run_id, "status": "RUNNING", "steps": []})
    append_event(tmp_path, athlete_id, parent_run_id, {"type": "RUN_STARTED", "details": "Parent"})

    unknown_child = f"{parent_run_id}_adhoc_debug"
    append_run(tmp_path, athlete_id, {"run_id": unknown_child, "status": "RUNNING", "steps": []})
    append_event(
        tmp_path,
        athlete_id,
        unknown_child,
        {"type": "FLOW_STARTED", "flow": "UnexpectedFlow"},
    )

    events = load_enriched_run_events(tmp_path, athlete_id, parent_run_id)

    assert [event["source_run_id"] for event in events] == [parent_run_id]


def test_load_enriched_run_events_stringifies_list_details(tmp_path: Path) -> None:
    athlete_id = "athlete"
    run_id = "plan_run"
    append_run(tmp_path, athlete_id, {"run_id": run_id, "status": "RUNNING", "steps": []})
    append_event(
        tmp_path,
        athlete_id,
        run_id,
        {"type": "CREW_FAILED", "tasks": ["phase_guardrails", {"retry": 2}, "done"]},
    )

    events = load_enriched_run_events(tmp_path, athlete_id, run_id)

    assert events[0]["details"] == 'phase_guardrails, {"retry":2}, done'


def test_load_enriched_run_events_stringifies_dict_details(tmp_path: Path) -> None:
    athlete_id = "athlete"
    run_id = "plan_run"
    append_run(tmp_path, athlete_id, {"run_id": run_id, "status": "RUNNING", "steps": []})
    append_event(
        tmp_path,
        athlete_id,
        run_id,
        {"type": "STEP_FAILED", "outputs": {"b": 2, "a": 1}},
    )

    events = load_enriched_run_events(tmp_path, athlete_id, run_id)

    assert events[0]["details"] == '{"a":1,"b":2}'


def test_load_enriched_run_events_truncates_oversized_details(tmp_path: Path) -> None:
    athlete_id = "athlete"
    run_id = "plan_run"
    append_run(tmp_path, athlete_id, {"run_id": run_id, "status": "RUNNING", "steps": []})
    append_event(
        tmp_path,
        athlete_id,
        run_id,
        {"type": "STEP_FAILED", "details": "x" * 400},
    )

    events = load_enriched_run_events(tmp_path, athlete_id, run_id)

    assert str(events[0]["details"]).endswith("…")
    assert len(str(events[0]["details"])) == 240


def test_load_enriched_run_events_orders_by_normalized_timestamp(tmp_path: Path) -> None:
    athlete_id = "athlete"
    run_id = "plan_run"
    append_run(tmp_path, athlete_id, {"run_id": run_id, "status": "RUNNING", "steps": []})
    append_event(
        tmp_path,
        athlete_id,
        run_id,
        {"type": "STEP_FINISHED", "ts": "2026-06-09T07:25:49+00:00"},
    )
    append_event(
        tmp_path,
        athlete_id,
        run_id,
        {"type": "STEP_STARTED", "timestamp": "2026-06-09T07:25:46+00:00"},
    )

    events = load_enriched_run_events(tmp_path, athlete_id, run_id)

    assert [event["type"] for event in events] == ["STEP_STARTED", "STEP_FINISHED"]


def test_load_enriched_run_events_without_run_metadata_degrades_cleanly(tmp_path: Path) -> None:
    athlete_id = "athlete"
    run_id = "plan_run"
    append_event(
        tmp_path,
        athlete_id,
        run_id,
        {"type": "STEP_STARTED", "step_id": "WEEK_PLAN"},
    )

    events = load_enriched_run_events(tmp_path, athlete_id, run_id)

    assert len(events) == 1
    assert events[0]["step"] == "Week Plan"
    assert events[0]["details"] == "—"
