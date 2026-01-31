from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import difflib
import json

import streamlit as st
import pandas as pd

from rps.ui.shared import (
    SETTINGS,
    announce_log_file,
    get_athlete_id,
    init_ui_state,
    render_global_sidebar,
    render_status_panel,
    set_status,
)
from rps.ui.run_store import load_runs
from rps.workspace.index_manager import WorkspaceIndexManager
from rps.workspace.types import ArtifactType


st.title("History")

# CHECKLIST (System -> History)
# - Show historical artefacts grouped by time (month -> week -> items).
# - Provide focus sections for Season/Phase/Week when available.
# - Keep newest months first.

init_ui_state()
render_global_sidebar()
athlete_id = get_athlete_id()
announce_log_file(athlete_id)

st.caption(f"Athlete: {athlete_id}")

index = WorkspaceIndexManager(root=SETTINGS.workspace_root, athlete_id=athlete_id).load()
artefacts = index.get("artefacts") or {}


def _latest_outputs(athlete_id: str) -> list[dict[str, str]]:
    targets = [
        (ArtifactType.SEASON_PLAN, "Season Plan"),
        (ArtifactType.PHASE_GUARDRAILS, "Phase Guardrails"),
        (ArtifactType.PHASE_STRUCTURE, "Phase Structure"),
        (ArtifactType.WEEK_PLAN, "Week Plan"),
        (ArtifactType.INTERVALS_WORKOUTS, "Export Workouts"),
        (ArtifactType.DES_ANALYSIS_REPORT, "Performance Report"),
    ]
    rows = []
    for artifact_type, label in targets:
        entry = (artefacts.get(artifact_type.value) or {}).get("latest") or {}
        rows.append(
            {
                "Type": artifact_type.value,
                "Title": label,
                "Version": str(entry.get("version_key") or "—"),
                "Run": str(entry.get("run_id") or "—"),
                "Updated": str(entry.get("created_at") or "—"),
            }
        )
    return rows


def _run_history(*, limit: int = 20, allowed: set[str] | None = None) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for artifact_type, entry in artefacts.items():
        if allowed is not None and artifact_type not in allowed:
            continue
        versions = (entry or {}).get("versions") or {}
        for version_key, record in versions.items():
            if not isinstance(record, dict):
                continue
            entries.append(
                {
                    "Artifact": artifact_type,
                    "Version": str(version_key),
                    "Run": str(record.get("run_id") or "—"),
                    "Producer": str(record.get("producer_agent") or "—"),
                    "Created": str(record.get("created_at") or "—"),
                }
            )
    entries.sort(key=lambda e: e.get("Created") or "", reverse=True)
    return entries[:limit]


def _run_store_history(*, limit: int = 20) -> list[dict[str, str]]:
    runs = load_runs(SETTINGS.workspace_root, athlete_id, limit=limit)
    rows: list[dict[str, str]] = []
    for run in runs:
        rows.append(
            {
                "Run ID": str(run.get("run_id") or "—"),
                "Status": str(run.get("status") or "—"),
                "Mode": str(run.get("mode") or "—"),
                "Scope": str(run.get("scope") or "—"),
                "Created": str(run.get("created_at") or "—"),
                "Superseded By": str(run.get("superseded_by") or "—"),
            }
        )
    return rows


def _style_superseded(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    def _row_style(row: pd.Series) -> list[str]:
        if row.get("Status") == "SUPERSEDED":
            return ["color: #8c8c8c; background-color: #f5f5f5;"] * len(row)
        return ["" for _ in row]

    return df.style.apply(_row_style, axis=1)


def _version_records(artifact_type: ArtifactType) -> list[dict]:
    entry = (artefacts.get(artifact_type.value) or {}).get("versions") or {}
    records = []
    for version_key, record in entry.items():
        if isinstance(record, dict):
            record = dict(record)
            record["version_key"] = version_key
            records.append(record)
    records.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return records


def _load_artifact_json(record: dict) -> dict | list | None:
    path = record.get("path") or record.get("relative_path")
    if not isinstance(path, str):
        return None
    full_path = SETTINGS.workspace_root / athlete_id / path
    if not full_path.exists():
        return None
    try:
        return json.loads(full_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _diff_json(a: dict | list | None, b: dict | list | None) -> str:
    left = json.dumps(a or {}, ensure_ascii=False, indent=2, sort_keys=True).splitlines(keepends=True)
    right = json.dumps(b or {}, ensure_ascii=False, indent=2, sort_keys=True).splitlines(keepends=True)
    return "".join(difflib.unified_diff(left, right, fromfile="older", tofile="latest"))

rows = []
for artifact_type, entry in artefacts.items():
    if not isinstance(entry, dict):
        continue
    versions = entry.get("versions") or {}
    for version_key, record in versions.items():
        if not isinstance(record, dict):
            continue
        created_at = record.get("created_at") or ""
        rows.append(
            {
                "Artefact": artifact_type,
                "Version": str(version_key),
                "Run": record.get("run_id") or "—",
                "Created": created_at or "—",
                "Validity": record.get("iso_week_range") or record.get("iso_week") or "—",
            }
        )

if not rows:
    set_status(status_state="idle", title="System", message="No artefacts found.")
    render_status_panel()
    st.stop()

set_status(status_state="done", title="System", message="History loaded.")
render_status_panel()

st.subheader("Overview")
st.caption("Latest outputs and run history (planning + data).")

st.subheader("Latest Outputs")
latest_rows = _latest_outputs(athlete_id)
table_header = st.columns([2, 1, 1, 1, 1, 1.5])
table_header[0].markdown("**Artefact**")
table_header[1].markdown("**Authority**")
table_header[2].markdown("**Version**")
table_header[3].markdown("**Run**")
table_header[4].markdown("**Updated**")
table_header[5].markdown("**Actions**")

authority_map = {
    ArtifactType.SEASON_PLAN.value: "Binding",
    ArtifactType.PHASE_GUARDRAILS.value: "Binding",
    ArtifactType.PHASE_STRUCTURE.value: "Binding",
    ArtifactType.WEEK_PLAN.value: "Binding",
    ArtifactType.INTERVALS_WORKOUTS.value: "Raw",
    ArtifactType.DES_ANALYSIS_REPORT.value: "Advisory",
}
open_pages = {
    ArtifactType.SEASON_PLAN.value: "pages/plan/season.py",
    ArtifactType.PHASE_GUARDRAILS.value: "pages/plan/phase.py",
    ArtifactType.PHASE_STRUCTURE.value: "pages/plan/phase.py",
    ArtifactType.WEEK_PLAN.value: "pages/plan/week.py",
    ArtifactType.INTERVALS_WORKOUTS.value: "pages/plan/workouts.py",
    ArtifactType.DES_ANALYSIS_REPORT.value: "pages/performance/report.py",
}

for row in latest_rows:
    cols = st.columns([2, 1, 1, 1, 1, 1.5])
    cols[0].write(row["Title"])
    cols[1].write(authority_map.get(row["Type"], "—"))
    cols[2].write(row["Version"])
    cols[3].write(row["Run"])
    cols[4].write(row["Updated"])
    with cols[5]:
        action_cols = st.columns(3)
        page_path = open_pages.get(row["Type"])
        if page_path:
            action_cols[0].page_link(page_path, label="Open")
        else:
            action_cols[0].button("Open", key=f"open_{row['Type']}", disabled=True)
        if action_cols[1].button("Diff", key=f"diff_{row['Type']}"):
            st.session_state["system_history_diff_type"] = row["Type"]
        if action_cols[2].button("Versions", key=f"versions_{row['Type']}"):
            st.session_state["system_history_versions_type"] = row["Type"]

versions_type = st.session_state.get("system_history_versions_type")
diff_type = st.session_state.get("system_history_diff_type")

if versions_type:
    try:
        artifact_type = ArtifactType(versions_type)
    except ValueError:
        artifact_type = None
    if artifact_type:
        st.subheader(f"Versions · {artifact_type.value}")
        records = _version_records(artifact_type)
        if not records:
            st.info("No versions found.")
        else:
            for record in records[:10]:
                label = f"{record.get('version_key')} · {record.get('created_at') or '—'}"
                with st.expander(label, expanded=False):
                    st.caption(f"Run: {record.get('run_id') or '—'}")
                    st.caption(f"Producer: {record.get('producer_agent') or '—'}")
                    payload = _load_artifact_json(record)
                    if payload is None:
                        st.info("No payload found.")
                    else:
                        st.json(payload)
        if st.button("Close Versions"):
            st.session_state["system_history_versions_type"] = None

if diff_type:
    try:
        artifact_type = ArtifactType(diff_type)
    except ValueError:
        artifact_type = None
    if artifact_type:
        st.subheader(f"Diff · {artifact_type.value}")
        records = _version_records(artifact_type)
        if len(records) < 2:
            st.info("Need at least two versions to diff.")
        else:
            a = _load_artifact_json(records[1])
            b = _load_artifact_json(records[0])
            st.code(_diff_json(a, b))
        if st.button("Close Diff"):
            st.session_state["system_history_diff_type"] = None

st.subheader("Run History")
planning_types = {
    ArtifactType.SEASON_SCENARIOS.value,
    ArtifactType.SEASON_SCENARIO_SELECTION.value,
    ArtifactType.SEASON_PLAN.value,
    ArtifactType.PHASE_GUARDRAILS.value,
    ArtifactType.PHASE_STRUCTURE.value,
    ArtifactType.PHASE_PREVIEW.value,
    ArtifactType.PHASE_FEED_FORWARD.value,
    ArtifactType.SEASON_PHASE_FEED_FORWARD.value,
    ArtifactType.WEEK_PLAN.value,
    ArtifactType.INTERVALS_WORKOUTS.value,
    ArtifactType.DES_ANALYSIS_REPORT.value,
}
data_types = {
    ArtifactType.ACTIVITIES_ACTUAL.value,
    ArtifactType.ACTIVITIES_TREND.value,
    ArtifactType.ZONE_MODEL.value,
    ArtifactType.WELLNESS.value,
    ArtifactType.AVAILABILITY.value,
    ArtifactType.KPI_PROFILE.value,
}

tab_planning, tab_data = st.tabs(["Planning", "Data"])
with tab_planning:
    st.caption("Plan Hub runs")
    plan_runs = _run_store_history(limit=20)
    if plan_runs:
        df_runs = pd.DataFrame(plan_runs)
        st.dataframe(_style_superseded(df_runs), use_container_width=True)
    else:
        st.info("No Plan Hub runs yet.")
    st.caption("Artefact history")
    st.dataframe(_run_history(limit=50, allowed=planning_types), use_container_width=True)
with tab_data:
    st.dataframe(_run_history(limit=50, allowed=data_types), use_container_width=True)

st.subheader("Artifact History")
st.caption("Historical artefacts grouped by month (newest first).")

month_map: dict[str, list[dict[str, str]]] = defaultdict(list)
for row in rows:
    created = row.get("Created") or ""
    month_key = "unknown"
    if created:
        try:
            month_key = datetime.fromisoformat(created.replace("Z", "+00:00")).strftime("%Y-%m")
        except ValueError:
            month_key = created[:7] if len(created) >= 7 else "unknown"
    month_map[month_key].append(row)

for month_key in sorted(month_map.keys(), reverse=True):
    with st.expander(month_key, expanded=False):
        month_rows = month_map[month_key]
        season_rows = [row for row in month_rows if row["Artefact"] == ArtifactType.SEASON_PLAN.value]
        phase_rows = [
            row
            for row in month_rows
            if row["Artefact"] in {ArtifactType.PHASE_GUARDRAILS.value, ArtifactType.PHASE_STRUCTURE.value}
        ]
        week_rows = [row for row in month_rows if row["Artefact"] == ArtifactType.WEEK_PLAN.value]
        other_rows = [
            row
            for row in month_rows
            if row not in season_rows + phase_rows + week_rows
        ]
        if season_rows:
            st.subheader("Season Plan")
            st.dataframe(season_rows, use_container_width=True)
        if phase_rows:
            st.subheader("Phase")
            st.dataframe(phase_rows, use_container_width=True)
        if week_rows:
            st.subheader("Week")
            st.dataframe(week_rows, use_container_width=True)
        if other_rows:
            st.subheader("Other")
            st.dataframe(other_rows, use_container_width=True)
