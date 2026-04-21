"""Background worker for Plan Hub run execution."""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from rps.agents.multi_output_runner import AgentRuntime
from rps.core.logging import DailySizeRotatingFileHandler
from rps.openai.client import get_client
from rps.orchestrator.plan_hub_actions import (
    execute_plan_week,
    execute_post_intervals,
    execute_scenario_selection,
    execute_season_plan,
    execute_season_scenarios,
)
from rps.ui.run_store import (
    RunRecord,
    acquire_athlete_lock,
    append_event,
    load_runs,
    release_athlete_lock,
    update_run,
)
from rps.workspace.index_manager import WorkspaceIndexManager
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType

logger = logging.getLogger(__name__)

StepRecord = dict[str, object]
IndexRecord = dict[str, object]
WorkerHandle = dict[str, object]


@dataclass(frozen=True)
class PlanHubWorkerConfig:
    """Configuration for a plan hub worker run."""

    root: Path
    athlete_id: str
    run_id: str
    runtime_for_agent: Callable[[str], AgentRuntime]
    model_resolver: Callable[[str], str] | None
    temperature_resolver: Callable[[str], float | None] | None
    reasoning_effort_resolver: Callable[[str], str | None] | None
    reasoning_summary_resolver: Callable[[str], str | None] | None
    force_file_search: bool
    max_num_results: int
    allow_delete_intervals: bool


def _step_str(step: StepRecord, key: str) -> str | None:
    """Return a string field from a step record when present."""
    value = step.get(key)
    return value if isinstance(value, str) else None


def _step_list(step: StepRecord, key: str) -> list[object]:
    """Return a list field from a step record when present."""
    value = step.get(key)
    return value if isinstance(value, list) else []


def _artefact_versions(index: IndexRecord, artifact_type: ArtifactType) -> dict[str, object]:
    """Return version records for one artefact type from the workspace index."""
    artefacts = index.get("artefacts")
    if not isinstance(artefacts, dict):
        return {}
    entry = artefacts.get(artifact_type.value)
    if not isinstance(entry, dict):
        return {}
    versions = entry.get("versions")
    return versions if isinstance(versions, dict) else {}


def _poll_response_status(response_id: str) -> str | None:
    """Poll OpenAI response status for a background response."""
    try:
        client = get_client()
        resp = client.responses.retrieve(response_id)
        status = getattr(resp, "status", None)
        if status is not None:
            return str(status)
        if isinstance(resp, dict):
            raw_status = resp.get("status")
            return str(raw_status) if raw_status is not None else None
        return None
    except Exception:
        return None


def _set_duration(step: StepRecord) -> None:
    """Set duration for a step if started/ended timestamps exist."""
    started = _step_str(step, "Started")
    ended = _step_str(step, "Ended")
    if not started or not ended:
        return
    try:
        start_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(ended.replace("Z", "+00:00"))
    except ValueError:
        return
    seconds = int((end_dt - start_dt).total_seconds())
    step["Duration"] = f"{max(seconds, 0)}s"


def _run_summary(steps: list[StepRecord]) -> dict[str, int]:
    done = sum(1 for step in steps if step.get("Status") == "DONE")
    failed = sum(1 for step in steps if step.get("Status") == "FAILED")
    outputs = sum(1 for step in steps if step.get("Outputs"))
    return {
        "steps_done": done,
        "steps_failed": failed,
        "artefacts_written": outputs,
    }


def _load_index(root: Path, athlete_id: str) -> IndexRecord:
    return WorkspaceIndexManager(root=root, athlete_id=athlete_id).load()


def _artifact_written_for_run(index: IndexRecord, artifact_type: ArtifactType, run_id: str) -> bool:
    versions = _artefact_versions(index, artifact_type)
    for record in versions.values():
        if isinstance(record, dict) and record.get("run_id") == run_id:
            return True
    return False


def _artifact_records_for_run(
    index: IndexRecord, artifact_type: ArtifactType, run_id: str
) -> list[StepRecord]:
    versions = _artefact_versions(index, artifact_type)
    outputs: list[StepRecord] = []
    for version_key, record in versions.items():
        if not isinstance(record, dict):
            continue
        if record.get("run_id") != run_id:
            continue
        outputs.append(
            {
                "version_key": version_key,
                "created_at": record.get("created_at"),
                "iso_week": record.get("iso_week"),
                "iso_week_range": record.get("iso_week_range"),
                "path": record.get("relative_path") or record.get("path"),
            }
        )
    return outputs


def _attach_run_logger(log_ref: str | None) -> logging.Handler | None:
    """Attach a file handler for this run's log_ref if provided."""
    if not log_ref:
        return None
    try:
        path = Path(log_ref)
        path.parent.mkdir(parents=True, exist_ok=True)
        max_mb = os.getenv("RPS_LOG_ROTATE_MB")
        max_bytes = 50 * 1024 * 1024
        if max_mb is not None and max_mb != "":
            try:
                max_bytes = int(max_mb) * 1024 * 1024
            except ValueError:
                max_bytes = 50 * 1024 * 1024
        handler = DailySizeRotatingFileHandler(path, max_bytes)
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return handler
    except OSError:
        return None


def _is_blocked(step_id: str, failed_step_id: str, deps: dict[str, list[str]], visited: set[str]) -> bool:
    if step_id in visited:
        return False
    visited.add(step_id)
    parents = deps.get(step_id, [])
    if failed_step_id in parents:
        return True
    return any(_is_blocked(parent, failed_step_id, deps, visited) for parent in parents)


def _mark_blocked(steps: list[StepRecord], failed_step: StepRecord) -> None:
    """Mark queued steps as blocked when a failure prevents downstream steps."""
    failed_step_id = str(failed_step.get("step_id") or "")
    reason = f"Blocked by failed step: {failed_step.get('Step') or failed_step_id}"
    deps: dict[str, list[str]] = {}
    for step in steps:
        step_id = str(step.get("step_id") or "")
        raw_deps = _step_list(step, "Deps")
        deps[step_id] = [str(dep) for dep in raw_deps if dep is not None]
    for pending in steps:
        if pending.get("Status") != "QUEUED":
            continue
        step_id = str(pending.get("step_id") or "")
        if _is_blocked(step_id, failed_step_id, deps, set()):
            pending["Status"] = "BLOCKED"
            pending["Details"] = reason


def _active_int(run_record: RunRecord, key: str) -> int | None:
    """Return an integer run-field value when present and parseable."""
    value = run_record.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _active_str(run_record: RunRecord, key: str) -> str | None:
    """Return a string run-field value when present."""
    value = run_record.get(key)
    return value if isinstance(value, str) else None


def _active_steps(run_record: RunRecord | None) -> list[StepRecord]:
    """Return mutable step rows from a run record."""
    if not isinstance(run_record, dict):
        return []
    steps = run_record.get("steps")
    if not isinstance(steps, list):
        return []
    return [step for step in steps if isinstance(step, dict)]


_PHASE_STEP_IDS = ("PHASE_GUARDRAILS", "PHASE_STRUCTURE", "PHASE_PREVIEW")


def _bundled_phase_force_steps(steps: list[StepRecord], current_step_id: str | None) -> list[str]:
    """Return the phase step ids that should execute together for a phase-scoped run."""
    if current_step_id not in _PHASE_STEP_IDS:
        return []
    start_index = _PHASE_STEP_IDS.index(current_step_id)
    wanted = _PHASE_STEP_IDS[start_index:]
    queued = {
        str(step.get("step_id")): step
        for step in steps
        if isinstance(step.get("step_id"), str) and step.get("Status") in {"QUEUED", "RUNNING"}
    }
    return [step_id for step_id in wanted if step_id in queued]


def _mark_bundled_steps_done(
    *,
    bundled_step_ids: list[str],
    steps: list[StepRecord],
    index: IndexRecord,
    run_id: str,
) -> None:
    """Mark all bundled phase steps complete after a combined execution."""
    now = datetime.now(UTC).isoformat()
    for bundled_step_id in bundled_step_ids:
        step = next((item for item in steps if item.get("step_id") == bundled_step_id), None)
        if not isinstance(step, dict):
            continue
        step["Status"] = "DONE"
        step["Ended"] = now
        _set_duration(step)
        outputs: list[StepRecord] = []
        for artifact_type in _step_list(step, "write_types"):
            outputs.extend(_artifact_records_for_run(index, ArtifactType(artifact_type), run_id))
        if outputs:
            step["Outputs"] = outputs


def run_plan_hub_worker(config: PlanHubWorkerConfig, stop_event: threading.Event) -> None:
    """Background worker to update run steps based on artifacts or response status."""
    store = LocalArtifactStore(root=config.root)
    handler: logging.Handler | None = None
    run_log_ref = None
    try:
        active = next(
            (r for r in load_runs(config.root, config.athlete_id, limit=50) if r.get("run_id") == config.run_id),
            None,
        )
        if isinstance(active, dict) and active.get("status") in {"DONE", "FAILED", "CANCELLED"}:
            logger.info(
                "Plan hub worker skipped terminal run_id=%s athlete=%s status=%s",
                config.run_id,
                config.athlete_id,
                active.get("status"),
            )
            return
        logger.info("Plan hub worker started run_id=%s athlete=%s", config.run_id, config.athlete_id)
        run_log_ref = _active_str(active or {}, "log_ref")
    except Exception:
        run_log_ref = None
    handler = _attach_run_logger(run_log_ref)
    acquired_lock = acquire_athlete_lock(config.root, config.athlete_id, config.run_id)
    if not acquired_lock:
        records = load_runs(config.root, config.athlete_id, limit=50)
        active = next((r for r in records if r.get("run_id") == config.run_id), None)
        steps = _active_steps(active)
        for step in steps:
            if step.get("Status") == "QUEUED":
                step["Status"] = "BLOCKED"
                step["Details"] = "Athlete lock busy."
        update_run(
            config.root,
            config.athlete_id,
            config.run_id,
            {
                "status": "FAILED",
                "finished_at": datetime.now(UTC).isoformat(),
                "summary": _run_summary(steps),
                "steps": steps,
            },
        )
        append_event(config.root, config.athlete_id, config.run_id, {"type": "RUN_FAILED", "reason": "Athlete lock busy."})
        return

    try:
        while not stop_event.is_set():
            records = load_runs(config.root, config.athlete_id, limit=50)
            active = next((r for r in records if r.get("run_id") == config.run_id), None)
            if not active:
                break
            status = active.get("status")
            if status in {"DONE", "FAILED", "CANCELLED"}:
                break
            if active.get("cancel_requested"):
                update_run(
                    config.root,
                    config.athlete_id,
                    config.run_id,
                    {
                        "status": "CANCELLED",
                        "finished_at": datetime.now(UTC).isoformat(),
                        "summary": _run_summary(_active_steps(active)),
                        "current_step": None,
                    },
                )
                append_event(
                    config.root,
                    config.athlete_id,
                    config.run_id,
                    {"type": "RUN_CANCELLED", "reason": "cancel_requested"},
                )
                break
            steps = _active_steps(active)
            index = _load_index(config.root, config.athlete_id)
            running_found = any(step.get("Status") == "RUNNING" for step in steps)

            for step in steps:
                step_status = step.get("Status")
                if step_status in {"DONE", "FAILED", "SKIPPED", "BLOCKED"}:
                    continue
                if step_status == "QUEUED" and not running_found:
                    step["Status"] = "RUNNING"
                    step["Started"] = datetime.now(UTC).isoformat()
                    if not active.get("started_at"):
                        append_event(config.root, config.athlete_id, config.run_id, {"type": "RUN_STARTED"})
                        update_run(
                            config.root,
                            config.athlete_id,
                            config.run_id,
                            {
                                "status": "RUNNING",
                                "started_at": datetime.now(UTC).isoformat(),
                                "current_step": step.get("step_id"),
                                "steps": steps,
                            },
                        )
                    else:
                        update_run(
                            config.root,
                            config.athlete_id,
                            config.run_id,
                            {"status": "RUNNING", "current_step": step.get("step_id"), "steps": steps},
                        )
                    append_event(
                        config.root,
                        config.athlete_id,
                        config.run_id,
                        {"type": "STEP_STARTED", "step_id": step.get("step_id")},
                    )
                    running_found = True
                    break
                if step_status == "RUNNING":
                    response_id = _step_str(step, "response_id")
                    response_status = _poll_response_status(response_id) if response_id else None
                    if response_status == "completed":
                        step["Status"] = "DONE"
                        step["Ended"] = datetime.now(UTC).isoformat()
                        _set_duration(step)
                        index = _load_index(config.root, config.athlete_id)
                        outputs: list[StepRecord] = []
                        for artifact_type in _step_list(step, "write_types"):
                            outputs.extend(_artifact_records_for_run(index, ArtifactType(artifact_type), config.run_id))
                        if outputs:
                            step["Outputs"] = outputs
                            append_event(config.root, config.athlete_id, config.run_id, {"type": "ARTEFACT_WRITTEN", "step_id": step.get("step_id"), "outputs": outputs})
                        append_event(config.root, config.athlete_id, config.run_id, {"type": "STEP_FINISHED", "step_id": step.get("step_id")})
                    elif response_status in {"failed", "cancelled"}:
                        step["Status"] = "FAILED"
                        step["Details"] = f"Response {response_status}"
                        step["Ended"] = datetime.now(UTC).isoformat()
                        _set_duration(step)
                        _mark_blocked(steps, step)
                        append_event(config.root, config.athlete_id, config.run_id, {"type": "STEP_FAILED", "step_id": step.get("step_id"), "reason": step.get("Details")})
                        update_run(
                            config.root,
                            config.athlete_id,
                            config.run_id,
                            {
                                "status": "FAILED",
                                "finished_at": datetime.now(UTC).isoformat(),
                                "summary": _run_summary(steps),
                                "steps": steps,
                            },
                        )
                        return
                    else:
                        exec_result = None
                        step_id = step.get("step_id")
                        active_year = _active_int(active, "iso_year")
                        active_week = _active_int(active, "iso_week")
                        if step_id == "SEASON_SCENARIOS":
                            if active_year is None or active_week is None:
                                exec_result = {"ok": False, "error": "Missing ISO year/week on queued run."}
                            else:
                                exec_result = execute_season_scenarios(
                                    config.runtime_for_agent,
                                    athlete_id=config.athlete_id,
                                    year=active_year,
                                    week=active_week,
                                    run_id=config.run_id,
                                    override_text=_active_str(active, "override_text"),
                                    model_resolver=config.model_resolver,
                                    temperature_resolver=config.temperature_resolver,
                                    force_file_search=config.force_file_search,
                                    max_num_results=config.max_num_results,
                                )
                        elif step_id == "SCENARIO_SELECTION":
                            if store.latest_exists(config.athlete_id, ArtifactType.SEASON_SCENARIO_SELECTION):
                                exec_result = {"ok": True}
                            else:
                                exec_result = execute_scenario_selection()
                        elif step_id == "SEASON_PLAN":
                            if active_year is None or active_week is None:
                                exec_result = {"ok": False, "error": "Missing ISO year/week on queued run."}
                            else:
                                exec_result = execute_season_plan(
                                    config.runtime_for_agent,
                                    athlete_id=config.athlete_id,
                                    year=active_year,
                                    week=active_week,
                                    run_id=config.run_id,
                                    override_text=_active_str(active, "override_text"),
                                    model_resolver=config.model_resolver,
                                    temperature_resolver=config.temperature_resolver,
                                    force_file_search=config.force_file_search,
                                    max_num_results=config.max_num_results,
                                )
                        elif step_id in {"PHASE_GUARDRAILS", "PHASE_STRUCTURE", "PHASE_PREVIEW", "WEEK_PLAN", "WORKOUT_EXPORT"}:
                            if active_year is None or active_week is None:
                                exec_result = {"ok": False, "error": "Missing ISO year/week on queued run."}
                            else:
                                force_steps = [step_id] if step_id else None
                                if step_id in _PHASE_STEP_IDS:
                                    bundled_phase_steps = _bundled_phase_force_steps(steps, step_id)
                                    if bundled_phase_steps:
                                        force_steps = bundled_phase_steps
                                exec_result = execute_plan_week(
                                    config.runtime_for_agent,
                                    athlete_id=config.athlete_id,
                                    year=active_year,
                                    week=active_week,
                                    run_id=config.run_id,
                                    force_steps=force_steps,
                                    override_text=_active_str(active, "override_text"),
                                    model_resolver=config.model_resolver,
                                    temperature_resolver=config.temperature_resolver,
                                    reasoning_effort_resolver=config.reasoning_effort_resolver,
                                    reasoning_summary_resolver=config.reasoning_summary_resolver,
                                    force_file_search=config.force_file_search,
                                    max_num_results=config.max_num_results,
                                )
                        elif step_id == "POST_INTERVALS":
                            if active_year is None or active_week is None:
                                exec_result = {"ok": False, "error": "Missing ISO year/week on queued run."}
                            else:
                                exec_result = execute_post_intervals(
                                    store=store,
                                    athlete_id=config.athlete_id,
                                    year=active_year,
                                    week=active_week,
                                    run_id=config.run_id,
                                    allow_delete=config.allow_delete_intervals,
                                )

                        if exec_result and exec_result.get("ok"):
                            index = _load_index(config.root, config.athlete_id)
                            if step_id in _PHASE_STEP_IDS:
                                bundled_phase_steps = _bundled_phase_force_steps(steps, step_id)
                                if bundled_phase_steps:
                                    _mark_bundled_steps_done(
                                        bundled_step_ids=bundled_phase_steps,
                                        steps=steps,
                                        index=index,
                                        run_id=config.run_id,
                                    )
                                    for bundled_step_id in bundled_phase_steps:
                                        bundled_step = next(
                                            (item for item in steps if item.get("step_id") == bundled_step_id),
                                            None,
                                        )
                                        if not isinstance(bundled_step, dict):
                                            continue
                                        bundled_outputs = bundled_step.get("Outputs")
                                        if isinstance(bundled_outputs, list) and bundled_outputs:
                                            append_event(
                                                config.root,
                                                config.athlete_id,
                                                config.run_id,
                                                {
                                                    "type": "ARTEFACT_WRITTEN",
                                                    "step_id": bundled_step_id,
                                                    "outputs": bundled_outputs,
                                                },
                                            )
                                        append_event(
                                            config.root,
                                            config.athlete_id,
                                            config.run_id,
                                            {"type": "STEP_FINISHED", "step_id": bundled_step_id},
                                        )
                                else:
                                    step["Status"] = "DONE"
                                    step["Ended"] = datetime.now(UTC).isoformat()
                                    _set_duration(step)
                            else:
                                step["Status"] = "DONE"
                                step["Ended"] = datetime.now(UTC).isoformat()
                                _set_duration(step)
                                step_outputs: list[StepRecord] = []
                                raw_outputs = exec_result.get("outputs")
                                if isinstance(raw_outputs, list):
                                    step_outputs.extend(output for output in raw_outputs if isinstance(output, dict))
                                for artifact_type in _step_list(step, "write_types"):
                                    step_outputs.extend(_artifact_records_for_run(index, ArtifactType(artifact_type), config.run_id))
                                if step_outputs:
                                    step["Outputs"] = step_outputs
                                    append_event(config.root, config.athlete_id, config.run_id, {"type": "ARTEFACT_WRITTEN", "step_id": step.get("step_id"), "outputs": step_outputs})
                                append_event(config.root, config.athlete_id, config.run_id, {"type": "STEP_FINISHED", "step_id": step.get("step_id")})
                        else:
                            index = _load_index(config.root, config.athlete_id)
                            for artifact_type in _step_list(step, "write_types"):
                                if _artifact_written_for_run(index, ArtifactType(artifact_type), config.run_id):
                                    step["Status"] = "DONE"
                                    step["Ended"] = datetime.now(UTC).isoformat()
                                    _set_duration(step)
                                    written_outputs: list[StepRecord] = []
                                    for artifact_type in _step_list(step, "write_types"):
                                        written_outputs.extend(_artifact_records_for_run(index, ArtifactType(artifact_type), config.run_id))
                                    if written_outputs:
                                        step["Outputs"] = written_outputs
                                        append_event(config.root, config.athlete_id, config.run_id, {"type": "ARTEFACT_WRITTEN", "step_id": step.get("step_id"), "outputs": written_outputs})
                                    append_event(config.root, config.athlete_id, config.run_id, {"type": "STEP_FINISHED", "step_id": step.get("step_id")})
                                    break
                            if step.get("Status") != "DONE":
                                step["Status"] = "FAILED"
                                step["Details"] = (exec_result or {}).get("error") or "Execution failed."
                                step["Ended"] = datetime.now(UTC).isoformat()
                                _set_duration(step)
                                _mark_blocked(steps, step)
                                append_event(config.root, config.athlete_id, config.run_id, {"type": "STEP_FAILED", "step_id": step.get("step_id"), "reason": step.get("Details")})
                                update_run(
                                    config.root,
                                    config.athlete_id,
                                    config.run_id,
                                    {
                                        "status": "FAILED",
                                        "finished_at": datetime.now(UTC).isoformat(),
                                        "summary": _run_summary(steps),
                                        "steps": steps,
                                    },
                                )
                                return
                    update_run(config.root, config.athlete_id, config.run_id, {"summary": _run_summary(steps), "steps": steps})
                    break

            if all(step.get("Status") in {"DONE", "SKIPPED", "BLOCKED"} for step in steps):
                update_run(
                    config.root,
                    config.athlete_id,
                    config.run_id,
                    {
                        "status": "DONE",
                        "finished_at": datetime.now(UTC).isoformat(),
                        "summary": _run_summary(steps),
                        "current_step": None,
                        "steps": steps,
                    },
                )
                append_event(config.root, config.athlete_id, config.run_id, {"type": "RUN_FINISHED"})
                break

            time.sleep(2)
    except Exception as exc:
        logger.exception("Plan hub worker failed run_id=%s athlete=%s: %s", config.run_id, config.athlete_id, exc)
        records = load_runs(config.root, config.athlete_id, limit=50)
        active = next((r for r in records if r.get("run_id") == config.run_id), None)
        steps = _active_steps(active)
        for step in steps:
            if step.get("Status") == "RUNNING":
                step["Status"] = "FAILED"
                step["Details"] = str(exc)
                step["Ended"] = datetime.now(UTC).isoformat()
                _set_duration(step)
                _mark_blocked(steps, step)
                append_event(
                    config.root,
                    config.athlete_id,
                    config.run_id,
                    {"type": "STEP_FAILED", "step_id": step.get("step_id"), "reason": step.get("Details")},
                )
                break
        update_run(
            config.root,
            config.athlete_id,
            config.run_id,
            {
                "status": "FAILED",
                "finished_at": datetime.now(UTC).isoformat(),
                "summary": _run_summary(steps),
                "steps": steps,
            },
        )
        append_event(config.root, config.athlete_id, config.run_id, {"type": "RUN_FAILED", "reason": str(exc)})
    finally:
        release_athlete_lock(config.root, config.athlete_id)
        if handler:
            logger.removeHandler(handler)
            handler.close()

    logger.info("Plan hub worker stopped run_id=%s athlete=%s", config.run_id, config.athlete_id)


def start_plan_hub_worker(config: PlanHubWorkerConfig) -> WorkerHandle:
    """Start a background worker thread."""
    stop_event = threading.Event()
    thread = threading.Thread(
        target=run_plan_hub_worker,
        args=(config, stop_event),
        daemon=True,
    )
    thread.start()
    return {"run_id": config.run_id, "stop": stop_event, "thread": thread}


def start_plan_hub_worker_with_stop(
    config: PlanHubWorkerConfig, stop_event: threading.Event
) -> WorkerHandle:
    """Start a background worker thread with a provided stop event."""
    thread = threading.Thread(
        target=run_plan_hub_worker,
        args=(config, stop_event),
        daemon=True,
    )
    thread.start()
    return {"run_id": config.run_id, "stop": stop_event, "thread": thread}


def get_planning_run_status(root: Path, athlete_id: str) -> RunRecord | None:
    """Return the most recent planning run status for an athlete."""
    runs = load_runs(root, athlete_id, limit=10)
    planning = [run for run in runs if run.get("process_type") == "planning"]
    if not planning:
        return None
    run = planning[0]
    return {
        "run_id": run.get("run_id"),
        "status": run.get("status"),
        "current_step": run.get("current_step"),
        "started_at": run.get("started_at"),
        "finished_at": run.get("finished_at"),
    }
