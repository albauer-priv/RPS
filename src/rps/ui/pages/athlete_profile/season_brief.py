from __future__ import annotations

from pathlib import Path

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


def _latest_input(inputs_dir: Path, prefix: str) -> Path | None:
    if not inputs_dir.exists():
        return None
    matches = sorted(inputs_dir.glob(f"{prefix}_*.md"), key=lambda p: p.stat().st_mtime)
    return matches[-1] if matches else None


init_ui_state()
render_global_sidebar()
athlete_id = get_athlete_id()
announce_log_file(athlete_id)

st.title("Season Brief")
st.caption(f"Athlete: {athlete_id}")

inputs_dir = SETTINGS.workspace_root / athlete_id / "inputs"
season_brief_path = _latest_input(inputs_dir, "season_brief")

if season_brief_path and season_brief_path.exists():
    st.markdown(season_brief_path.read_text(encoding="utf-8"))
    set_status(status_state="done", title="Season Brief", message="Ready.")
else:
    st.error("No season_brief_*.md found for this athlete.")
    set_status(status_state="error", title="Season Brief", message="No season_brief_*.md found.")

render_status_panel()
