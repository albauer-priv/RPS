from __future__ import annotations

from datetime import datetime

import streamlit as st

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
from rps.openai.vectorstores import VectorStoreResolver
from rps.prompts.loader import PromptLoader
from rps.ui.run_store import load_runs
from rps.orchestrator.plan_hub_worker import get_planning_run_status
from rps.orchestrator.queue_scheduler import ensure_queue_dirs, start_queue_scheduler
from rps.workspace.index_manager import WorkspaceIndexManager
from rps.workspace.types import ArtifactType


st.title("Status")

# CHECKLIST (System -> Status)
# - Show running processes with filters (status, athlete).
# - Provide a live list of latest artifacts (one per type).
# - Keep output compact and scannable.

init_ui_state()
render_global_sidebar()
athlete_id = get_athlete_id()
announce_log_file(athlete_id)

st.caption(f"Athlete: {athlete_id}")

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

if queue_counts["Pending"] and not queue_counts["Active"]:
    def _runtime_for_agent(agent_name: str) -> AgentRuntime:
        client = get_client()
        return AgentRuntime(
            client=client,
            model=SETTINGS.openai_model,
            temperature=SETTINGS.openai_temperature,
            reasoning_effort=SETTINGS.reasoning_effort_for_agent(agent_name),
            reasoning_summary=SETTINGS.reasoning_summary_for_agent(agent_name),
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

runs = load_runs(SETTINGS.workspace_root, athlete_id, limit=100)
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

set_status(
    status_state="done" if filtered_runs else "idle",
    title="System",
    message=f"{len(filtered_runs)} runs" if filtered_runs else "No runs found.",
    last_action="View Status",
)
render_status_panel()

if filtered_runs:
    st.subheader("Running Processes")
    rows = []
    for run in filtered_runs:
        rows.append(
            {
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
    st.dataframe(rows, width="stretch")
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
