from __future__ import annotations

import streamlit as st

from rps.ui.shared import (
    SETTINGS,
    announce_log_file,
    get_athlete_id,
    get_iso_year_week,
    init_ui_state,
    load_rendered_markdown,
)
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType


st.title("WoW")

init_ui_state()
athlete_id = get_athlete_id()
year, week = get_iso_year_week()
announce_log_file(athlete_id)

st.caption(f"Athlete: {athlete_id}")

col_year, col_week = st.columns(2)
year = int(
    col_year.number_input(
        "ISO Year",
        min_value=2000,
        max_value=2100,
        value=year,
        step=1,
    )
)
week = int(
    col_week.number_input(
        "ISO Week",
        min_value=1,
        max_value=53,
        value=week,
        step=1,
    )
)

store = LocalArtifactStore(root=SETTINGS.workspace_root)
version_key = f"{year}-{week:02d}"

st.subheader(f"Workouts of the Week · {version_key}")

if not store.latest_exists(athlete_id, ArtifactType.WEEK_PLAN):
    st.info("No Week Plan found yet.")
    st.stop()

if store.latest_exists(athlete_id, ArtifactType.WEEK_PLAN):
    try:
        payload = store.load_version(athlete_id, ArtifactType.WEEK_PLAN, version_key)
    except FileNotFoundError:
        payload = None

    if payload is None:
        st.info(f"No Week Plan found for {version_key}.")
        st.stop()

    rendered = load_rendered_markdown(athlete_id, ArtifactType.WEEK_PLAN, version_key=version_key)
    if rendered:
        st.markdown(rendered)
    else:
        st.json(payload)
