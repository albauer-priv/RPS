from __future__ import annotations

from pathlib import Path

import streamlit as st

from rps.ui.shared import SETTINGS, announce_log_file, get_athlete_id, init_ui_state


init_ui_state()
athlete_id = get_athlete_id()
announce_log_file(athlete_id)

def _latest_input(inputs_dir: Path, prefix: str) -> Path | None:
    if not inputs_dir.exists():
        return None
    matches = sorted(inputs_dir.glob(f"{prefix}*.md"), key=lambda p: p.stat().st_mtime)
    return matches[-1] if matches else None


st.title("Logistics")
st.caption(f"Athlete: {athlete_id}")

inputs_dir = SETTINGS.workspace_root / athlete_id / "inputs"
events_path = _latest_input(inputs_dir, "events")
if events_path and events_path.exists():
    st.markdown(events_path.read_text(encoding="utf-8"))
else:
    st.error("No events*.md found for this athlete.")
