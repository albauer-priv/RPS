from __future__ import annotations

import json

import streamlit as st

from rps.ui.shared import (
    SETTINGS,
    announce_log_file,
    get_athlete_id,
    get_iso_year_week,
    init_ui_state,
    load_rendered_markdown,
    render_phase_markdown,
)
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType


st.title("Phase")

init_ui_state()
athlete_id = get_athlete_id()
get_iso_year_week()
announce_log_file(athlete_id)

st.caption(f"Athlete: {athlete_id}")

store = LocalArtifactStore(root=SETTINGS.workspace_root)
if not store.latest_exists(athlete_id, ArtifactType.SEASON_PLAN):
    st.info("No Season Plan found for this athlete.")
    st.stop()

season_plan = store.load_latest(athlete_id, ArtifactType.SEASON_PLAN)
phases = season_plan.get("data", {}).get("phases", []) if isinstance(season_plan, dict) else []
if not phases:
    st.info("No phases found in Season Plan.")
    st.stop()

options = []
phase_map = {}
for phase in phases:
    phase_id = phase.get("phase_id") or ""
    name = phase.get("name") or "Phase"
    iso_range = phase.get("iso_week_range") or ""
    label = f"{phase_id} · {name} · {iso_range}".strip(" ·")
    options.append(label)
    phase_map[label] = phase

selected_label = st.selectbox("Select phase", options=options)
selected_phase = phase_map[selected_label]

phase_name = selected_phase.get("name", "Phase")
iso_range = selected_phase.get("iso_week_range", "")
header = f"Phase: {phase_name} {iso_range}".strip()

with st.expander(header, expanded=True):
    st.markdown(render_phase_markdown(selected_phase), unsafe_allow_html=True)


def _find_artifact_for_range(artifact_type: ArtifactType, target_range: str) -> str | None:
    versions = store.list_versions(athlete_id, artifact_type)
    for version_key in reversed(versions):
        payload = store.load_version(athlete_id, artifact_type, version_key)
        if not isinstance(payload, dict):
            continue
        meta = payload.get("meta", {}) or {}
        if meta.get("iso_week_range") == target_range:
            return version_key
    return None


for label, artifact_type in (
    ("Phase Guardrails", ArtifactType.PHASE_GUARDRAILS),
    ("Phase Structure", ArtifactType.PHASE_STRUCTURE),
    ("Phase Preview", ArtifactType.PHASE_PREVIEW),
):
    st.subheader(label)
    version_key = _find_artifact_for_range(artifact_type, iso_range)
    if not version_key:
        st.info(f"No {label.lower()} found for this phase.")
        continue
    rendered = load_rendered_markdown(athlete_id, artifact_type, version_key=version_key)
    if rendered:
        st.markdown(rendered)
    else:
        payload = store.load_version(athlete_id, artifact_type, version_key)
        st.json(payload)
