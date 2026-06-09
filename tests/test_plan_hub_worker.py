import logging
import threading
from pathlib import Path

from rps.orchestrator.plan_hub_worker import (
    PlanHubWorkerConfig,
    _attach_run_logger,
    _bundled_phase_force_steps,
    _latest_failure_reason,
    run_plan_hub_worker,
)
from rps.ui.run_store import append_event, append_run, load_events


def test_bundled_phase_force_steps_groups_remaining_phase_outputs() -> None:
    steps = [
        {"step_id": "PHASE_GUARDRAILS", "Status": "RUNNING"},
        {"step_id": "PHASE_STRUCTURE", "Status": "QUEUED"},
        {"step_id": "PHASE_PREVIEW", "Status": "QUEUED"},
        {"step_id": "WEEK_PLAN", "Status": "QUEUED"},
    ]

    assert _bundled_phase_force_steps(steps, "PHASE_GUARDRAILS") == [
        "PHASE_GUARDRAILS",
        "PHASE_STRUCTURE",
        "PHASE_PREVIEW",
    ]
    assert _bundled_phase_force_steps(steps, "PHASE_STRUCTURE") == [
        "PHASE_STRUCTURE",
        "PHASE_PREVIEW",
    ]
    assert _bundled_phase_force_steps(steps, "PHASE_PREVIEW") == ["PHASE_PREVIEW"]


def test_plan_hub_worker_skips_terminal_run(tmp_path: Path, caplog) -> None:
    athlete_id = "test_athlete"
    run_id = "run_done"
    append_run(
        tmp_path,
        athlete_id,
        {
            "run_id": run_id,
            "athlete_id": athlete_id,
            "status": "DONE",
            "steps": [],
        },
    )

    config = PlanHubWorkerConfig(
        root=tmp_path,
        athlete_id=athlete_id,
        run_id=run_id,
        runtime_for_agent=lambda _name: None,  # type: ignore[arg-type]
        model_resolver=None,
        temperature_resolver=None,
        reasoning_effort_resolver=None,
        reasoning_summary_resolver=None,
        allow_delete_intervals=False,
    )

    with caplog.at_level("INFO", logger="rps.orchestrator.plan_hub_worker"):
        run_plan_hub_worker(config, threading.Event())

    assert "Plan hub worker skipped terminal run_id=run_done" in caplog.text


def test_latest_failure_reason_prefers_llm_failure_event(tmp_path: Path) -> None:
    append_event(
        tmp_path,
        "athlete",
        "run-1",
        {
            "type": "TOOL_FAILED",
            "reason": "fallback tool failure",
        },
    )
    append_event(
        tmp_path,
        "athlete",
        "run-1",
        {
            "type": "LLM_REQUEST_FAILED",
            "reason": "You exceeded your current quota.",
            "error_code": "insufficient_quota",
            "error_type": "insufficient_quota",
            "status_code": "429",
        },
    )

    reason = _latest_failure_reason(tmp_path, "athlete", "run-1")

    assert reason == "You exceeded your current quota. | code=insufficient_quota | status=429"


def test_attach_run_logger_filters_debug_noise(tmp_path: Path) -> None:
    log_path = tmp_path / "plan_run.log"
    root = logging.getLogger()
    previous_level = root.level
    root.setLevel(logging.DEBUG)

    handler = _attach_run_logger(str(log_path))
    assert handler is not None

    try:
        logger = logging.getLogger("rps.tests.plan_hub_worker")
        logger.debug("debug line should stay out of run log")
        logger.info("info line should be visible in run log")
        handler.flush()
    finally:
        root.removeHandler(handler)
        handler.close()
        root.setLevel(previous_level)

    content = log_path.read_text(encoding="utf-8")
    assert "info line should be visible in run log" in content
    assert "debug line should stay out of run log" not in content


def test_plan_hub_worker_emits_enriched_parent_step_events(tmp_path: Path, monkeypatch) -> None:
    athlete_id = "athlete"
    run_id = "plan_run"
    append_run(
        tmp_path,
        athlete_id,
        {
            "run_id": run_id,
            "athlete_id": athlete_id,
            "status": "QUEUED",
            "iso_year": 2026,
            "iso_week": 24,
            "message": "Scoped planning run.",
            "steps": [
                {
                    "step_id": "WEEK_PLAN",
                    "Step": "Week Plan",
                    "Agent": "Week Planner",
                    "Writes": "WEEK_PLAN",
                    "Authority": "Binding",
                    "Details": "Explicit scoped rerun requested.",
                    "Status": "QUEUED",
                    "write_types": [],
                }
            ],
        },
    )

    monkeypatch.setattr(
        "rps.orchestrator.plan_hub_worker.execute_plan_week",
        lambda *args, **kwargs: {"ok": True},
    )

    config = PlanHubWorkerConfig(
        root=tmp_path,
        athlete_id=athlete_id,
        run_id=run_id,
        runtime_for_agent=lambda _name: None,  # type: ignore[arg-type]
        model_resolver=None,
        temperature_resolver=None,
        reasoning_effort_resolver=None,
        reasoning_summary_resolver=None,
        allow_delete_intervals=False,
    )

    run_plan_hub_worker(config, threading.Event())

    events = load_events(tmp_path, athlete_id, run_id, limit=20)
    step_started = next(event for event in events if event["type"] == "STEP_STARTED")
    step_finished = next(event for event in events if event["type"] == "STEP_FINISHED")
    run_started = next(event for event in events if event["type"] == "RUN_STARTED")

    assert step_started["step"] == "Week Plan"
    assert step_started["details"] == "Explicit scoped rerun requested."
    assert step_started["agent"] == "Week Planner"
    assert step_started["writes"] == "WEEK_PLAN"
    assert step_started["authority"] == "Binding"
    assert step_finished["step"] == "Week Plan"
    assert run_started["details"] == "Scoped planning run."
