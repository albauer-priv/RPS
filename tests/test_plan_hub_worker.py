import threading
from pathlib import Path

from rps.orchestrator.plan_hub_worker import (
    PlanHubWorkerConfig,
    _bundled_phase_force_steps,
    run_plan_hub_worker,
)
from rps.ui.run_store import append_run


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
        force_file_search=True,
        max_num_results=20,
        allow_delete_intervals=False,
    )

    with caplog.at_level("INFO", logger="rps.orchestrator.plan_hub_worker"):
        run_plan_hub_worker(config, threading.Event())

    assert "Plan hub worker skipped terminal run_id=run_done" in caplog.text
