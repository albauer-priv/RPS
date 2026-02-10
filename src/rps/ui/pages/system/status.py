from __future__ import annotations

from datetime import datetime
from pathlib import Path

import streamlit as st

from rps.core.config import load_env_file
from rps.ui.shared import (
    SETTINGS,
    announce_log_file,
    get_athlete_id,
    init_ui_state,
    render_global_sidebar,
    render_status_panel,
    set_status,
)
from rps.agents.multi_output_runner import AgentRuntime
from rps.openai.client import get_client
from rps.openai.vectorstore_state import VectorStoreResolver
from rps.prompts.loader import PromptLoader
import shutil

from rps.ui.run_store import load_runs, release_athlete_lock, update_run
from rps.orchestrator.plan_hub_worker import get_planning_run_status
from rps.orchestrator.queue_scheduler import ensure_queue_dirs, start_queue_scheduler
from rps.workspace.index_manager import WorkspaceIndexManager
from rps.workspace.types import ArtifactType


st.title("Status")

# Ensure .env values are loaded for worker threads started from this page.
ROOT = Path(__file__).resolve().parents[3]
load_env_file(ROOT / ".env")

# CHECKLIST (System -> Status)
# - Show running processes with filters (status, athlete).
# - Provide a live list of latest artifacts (one per type).
# - Keep output compact and scannable.

init_ui_state()
render_global_sidebar()
athlete_id = get_athlete_id()
announce_log_file(athlete_id)

st.caption(f"Athlete: {athlete_id}")
set_status(status_state="done", title="System", message="Status loaded.")
render_status_panel()

runs_status = get_planning_run_status(SETTINGS.workspace_root, athlete_id)
if runs_status:
    st.subheader("Planning Worker Status")
    st.table(
        [
            {
                "Run ID": runs_status.get("run_id"),
                "Status": runs_status.get("status"),
                "Current Step": runs_status.get("current_step") or "—",
                "Started": runs_status.get("started_at") or "—",
                "Finished": runs_status.get("finished_at") or "—",
            }
        ]
    )

queue_paths = ensure_queue_dirs(SETTINGS.workspace_root)
queue_counts = {
    "Pending": len(list(queue_paths.pending.glob("*.json"))),
    "Active": len(list(queue_paths.active.glob("*.json"))),
    "Done": len(list(queue_paths.done.glob("*.json"))),
    "Failed": len(list(queue_paths.failed.glob("*.json"))),
}
st.subheader("Queue Status")
st.table([queue_counts])

with st.expander("Reset run system", expanded=False):
    st.warning(
        "This clears all run queues and removes run state, locks, and logs for the current athlete.",
    )
    confirm_reset = st.text_input('Type "RESET RUNS" to confirm')
    if st.button("Reset run system", disabled=confirm_reset.strip() != "RESET RUNS"):
        release_athlete_lock(SETTINGS.workspace_root, athlete_id)
        lock_dir = SETTINGS.workspace_root / athlete_id / "locks"
        if lock_dir.exists():
            shutil.rmtree(lock_dir, ignore_errors=True)
        for folder in (queue_paths.pending, queue_paths.active, queue_paths.done, queue_paths.failed):
            for path in folder.glob("*.json"):
                path.unlink(missing_ok=True)
        run_root = SETTINGS.workspace_root / athlete_id / "runs"
        if run_root.exists():
            shutil.rmtree(run_root, ignore_errors=True)
        log_root = SETTINGS.workspace_root / athlete_id / "logs"
        if log_root.exists():
            shutil.rmtree(log_root, ignore_errors=True)
        st.success("Run system reset complete.")

runs = load_runs(SETTINGS.workspace_root, athlete_id, limit=100)
failed_run_ids = {path.stem for path in queue_paths.failed.glob("*.json")}
if failed_run_ids:
    for run in runs:
        run_id = run.get("run_id")
        if not run_id or run_id not in failed_run_ids:
            continue
        if run.get("status") not in {"QUEUED", "RUNNING"}:
            continue
        update_run(
            SETTINGS.workspace_root,
            athlete_id,
            run_id,
            {
                "status": "FAILED",
                "finished_at": datetime.now().isoformat(),
                "current_step": None,
            },
        )

if queue_counts["Pending"] and not queue_counts["Active"]:
    def _runtime_for_agent(agent_name: str) -> AgentRuntime:
        client = get_client()
        return AgentRuntime(
            client=client,
            model=SETTINGS.openai_model,
            temperature=SETTINGS.openai_temperature,
            reasoning_effort=SETTINGS.reasoning_effort_for_agent(agent_name),
            reasoning_summary=SETTINGS.reasoning_summary_for_agent(agent_name),
            max_completion_tokens=SETTINGS.max_completion_tokens_for_agent(agent_name),
            prompt_loader=PromptLoader(SETTINGS.prompts_dir),
            vs_resolver=VectorStoreResolver(SETTINGS.vs_state_path),
            schema_dir=SETTINGS.schema_dir,
            workspace_root=SETTINGS.workspace_root,
        )

    @st.cache_resource
    def _get_scheduler() -> dict:
        return start_queue_scheduler(
            root=SETTINGS.workspace_root,
            runtime_for_agent=_runtime_for_agent,
            model_resolver=SETTINGS.model_for_agent,
            temperature_resolver=SETTINGS.temperature_for_agent,
            reasoning_effort_resolver=SETTINGS.reasoning_effort_for_agent,
            reasoning_summary_resolver=SETTINGS.reasoning_summary_for_agent,
            force_file_search=True,
            max_num_results=SETTINGS.file_search_max_results,
        )

    scheduler = _get_scheduler()
    if not scheduler.get("thread") or not scheduler["thread"].is_alive():
        _get_scheduler.clear()
        _get_scheduler()
    st.caption("Queue worker started to drain pending runs.")
status_filter = st.selectbox(
    "Process status",
    options=["All", "QUEUED", "RUNNING", "DONE", "FAILED", "CANCELLED", "SUPERSEDED"],
    index=1,
)
type_values = sorted({run.get("process_type") or "Unspecified" for run in runs})
type_filter = st.selectbox(
    "Process type",
    options=["All", *type_values],
    index=0,
)
subtype_values = sorted({run.get("process_subtype") or "Unspecified" for run in runs})
subtype_filter = st.selectbox(
    "Process subtype",
    options=["All", *subtype_values],
    index=0,
)

def _matches_filter(run: dict) -> bool:
    if status_filter != "All" and run.get("status") != status_filter:
        return False
    process_type = run.get("process_type") or "Unspecified"
    if type_filter != "All" and process_type != type_filter:
        return False
    process_subtype = run.get("process_subtype") or "Unspecified"
    if subtype_filter != "All" and process_subtype != subtype_filter:
        return False
    return True


filtered_runs = [run for run in runs if _matches_filter(run)]

if filtered_runs:
    st.subheader("Running Processes")
    rows = []
    for run in filtered_runs:
        rows.append(
            {
                "Select": False,
                "Run ID": run.get("run_id"),
                "Status": run.get("status"),
                "Type": run.get("process_type") or "Unspecified",
                "Subtype": run.get("process_subtype") or "Unspecified",
                "Mode": run.get("mode"),
                "Scope": run.get("scope") or "—",
                "Created": run.get("created_at") or "—",
                "Current Step": run.get("current_step") or "—",
            }
        )
    edited = st.data_editor(
        rows,
        width="stretch",
        hide_index=True,
        column_config={"Select": st.column_config.CheckboxColumn("Select")},
        key="status_runs_editor",
    )
    selected_run_ids = [
        row.get("Run ID")
        for row in edited
        if row.get("Select") and row.get("Status") in {"QUEUED", "RUNNING"}
    ]
    if selected_run_ids:
        st.caption(f"Selected runs: {', '.join(selected_run_ids)}")
    cancel_disabled = not selected_run_ids
    if st.button("Cancel selected runs", disabled=cancel_disabled):
        queue_paths = ensure_queue_dirs(SETTINGS.workspace_root)
        for run_id in selected_run_ids:
            update_run(
                SETTINGS.workspace_root,
                athlete_id,
                run_id,
                {
                    "cancel_requested": True,
                    "status": "CANCELLED",
                    "finished_at": datetime.now().isoformat(),
                },
            )
            for folder in (queue_paths.pending, queue_paths.active, queue_paths.failed):
                path = folder / f"{run_id}.json"
                if path.exists():
                    path.unlink()
        st.info("Cancel requested. Active workers will stop after the current step.")
        st.rerun()
else:
    st.info("No matching runs.")

st.subheader("Latest Artefacts")
index = WorkspaceIndexManager(root=SETTINGS.workspace_root, athlete_id=athlete_id).load()
latest_rows = []
for artifact_type in ArtifactType:
    entry = (index.get("artefacts") or {}).get(artifact_type.value)
    if not entry or not isinstance(entry, dict):
        continue
    latest = entry.get("latest")
    if not isinstance(latest, dict):
        continue
    created_at = latest.get("created_at")
    latest_rows.append(
        {
            "Artefact": artifact_type.value,
            "Version": latest.get("version_key") or "—",
            "Run": latest.get("run_id") or "—",
            "Updated": created_at or "—",
        }
    )

latest_rows.sort(key=lambda row: row.get("Updated") or "", reverse=True)
if latest_rows:
    st.dataframe(latest_rows, width="stretch")
else:
    st.info("No artefacts found.")
