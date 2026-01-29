from __future__ import annotations

import json

import streamlit as st
from jinja2 import BaseLoader, Environment

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

PHASE_PREVIEW_TEMPLATE = """
### What the next 4 weeks will feel like
| Topic | Details |
| --- | --- |
| Dominant theme | {{ feel.dominant_theme or 'N/A' }} |
| Intensity handling concept | {{ feel.intensity_handling_conceptual or 'N/A' }} |
| Recovery protection | {{ feel.recovery_protection_conceptual or 'N/A' }} |
| Week-to-week direction | {{ narrative.direction or 'N/A' }} |
| What will not change | {{ narrative.what_will_not_change or 'N/A' }} |
| What is flexible | {{ narrative.what_is_flexible or 'N/A' }} |
| Deviations | {% if deviations %}{% for d in deviations %}{{ d }}<br>{% endfor %}{% else %}N/A{% endif %} |
"""


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



def _find_phase_preview(store: LocalArtifactStore, target_range: str) -> dict | None:
    if not target_range:
        return None
    versions = store.list_versions(athlete_id, ArtifactType.PHASE_PREVIEW)
    for version_key in reversed(versions):
        payload = store.load_version(athlete_id, ArtifactType.PHASE_PREVIEW, version_key)
        if not isinstance(payload, dict):
            continue
        meta = payload.get("meta", {}) or {}
        if meta.get("iso_week_range") == target_range:
            return payload.get("data", {})
    return None


def _render_week_table(week: dict) -> str:
    header = "| Day | Role | Intensity | Modality | Notes |\n| --- | --- | --- | --- | --- |\n"
    rows = []
    for day in week.get("days", []):
        rows.append(
            "| {day} | {role} | {intensity} | {modality} | {notes} |".format(
                day=day.get("day_of_week", "N/A"),
                role=day.get("day_role", "N/A"),
                intensity=day.get("intensity_domain", "N/A"),
                modality=day.get("load_modality", "N/A"),
                notes=day.get("notes", "N/A"),
            )
        )
    return header + "\n".join(rows)



with st.expander(header, expanded=True):
    st.markdown(render_phase_markdown(selected_phase), unsafe_allow_html=True)
    # preview = _find_phase_preview(store, iso_range)
    if preview:
        env = Environment(loader=BaseLoader(), autoescape=False)
        template = env.from_string(PHASE_PREVIEW_TEMPLATE)
        st.markdown(
            template.render(
                feel=preview.get("feel_overview", {}),
                narrative=preview.get("week_to_week_narrative", {}),
                deviations=preview.get("deviation_rules", []),
            ),
            unsafe_allow_html=True,
        )
        for week in preview.get("weekly_agenda_preview", []):
            with st.expander(f"Week {week.get('week', 'N/A')} preview", expanded=False):
                st.markdown(_render_week_table(week), unsafe_allow_html=True)


