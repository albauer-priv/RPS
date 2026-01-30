from __future__ import annotations

import logging

import streamlit as st
from jinja2 import BaseLoader, Environment

from rps.ui.shared import (
    SETTINGS,
    announce_log_file,
    get_athlete_id,
    get_iso_year_week,
    init_ui_state,
    render_phase_markdown,
)
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType

logger = logging.getLogger(__name__)

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


def _load_season_plan(store: LocalArtifactStore, athlete_id: str) -> dict | None:
    """Load the latest season plan for an athlete."""
    if not store.latest_exists(athlete_id, ArtifactType.SEASON_PLAN):
        return None
    payload = store.load_latest(athlete_id, ArtifactType.SEASON_PLAN)
    if not isinstance(payload, dict):
        return None
    return payload


def _build_phase_options(phases: list[dict]) -> tuple[list[str], dict[str, dict]]:
    """Build selectbox options and a label→phase map."""
    options: list[str] = []
    phase_map: dict[str, dict] = {}
    for phase in phases:
        phase_id = phase.get("phase_id") or ""
        name = phase.get("name") or "Phase"
        iso_range = phase.get("iso_week_range") or ""
        label = f"{phase_id} · {name} · {iso_range}".strip(" ·")
        options.append(label)
        phase_map[label] = phase
    return options, phase_map


def _find_phase_preview(
    store: LocalArtifactStore, athlete_id: str, target_range: str
) -> dict | None:
    """Find the phase preview matching the ISO week range."""
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
    """Render a simple markdown table for a week preview."""
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


def _render_phase_preview(preview: dict) -> None:
    """Render phase preview details and weekly agenda."""
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


# --- UI ---

st.title("Phase")

init_ui_state()
athlete_id = get_athlete_id()
get_iso_year_week()
announce_log_file(athlete_id)

st.caption(f"Athlete: {athlete_id}")

store = LocalArtifactStore(root=SETTINGS.workspace_root)
season_plan = _load_season_plan(store, athlete_id)
if not season_plan:
    st.info("No Season Plan found for this athlete.")
    st.stop()

phases = season_plan.get("data", {}).get("phases", []) if isinstance(season_plan, dict) else []
if not phases:
    st.info("No phases found in Season Plan.")
    st.stop()

options, phase_map = _build_phase_options(phases)
selected_label = st.selectbox("Select phase", options=options)
selected_phase = phase_map[selected_label]

phase_name = selected_phase.get("name", "Phase")
iso_range = selected_phase.get("iso_week_range", "")
header = f"Phase: {phase_name} {iso_range}".strip()

with st.expander(header, expanded=True):
    st.markdown(render_phase_markdown(selected_phase), unsafe_allow_html=True)
    preview = _find_phase_preview(store, athlete_id, iso_range)
    if preview:
        _render_phase_preview(preview)
