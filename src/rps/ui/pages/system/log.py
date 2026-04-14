from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from rps.core.config import load_env_file
from rps.ui.shared import (
    ROOT,
    announce_log_file,
    ensure_logging,
    init_ui_state,
    render_global_sidebar,
    render_status_panel,
    set_status,
    system_log_panel,
)

st.title("Log")

# CHECKLIST (System -> Log)
# - Show system log output.
# - Allow changing UI log level and persist it.
# - Make debugging easy without leaving the UI.

init_ui_state()
render_global_sidebar()
athlete_id = st.session_state.get("rps_state", {}).get("athlete_id")
if athlete_id:
    announce_log_file(athlete_id)
    st.caption(f"Athlete: {athlete_id}")

set_status(status_state="done", title="System", message="System logs.")
render_status_panel()

st.subheader("UI Log Level")
levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
current_level = os.getenv("RPS_LOG_UI", "INFO")
selected = st.selectbox("Log level", options=levels, index=levels.index(current_level) if current_level in levels else 1)

if st.button("Save log level"):
    env_path = Path(ROOT / ".env")
    lines = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    updated = False
    for idx, line in enumerate(lines):
        if line.strip().startswith("RPS_LOG_UI="):
            lines[idx] = f"RPS_LOG_UI={selected}"
            updated = True
            break
    if not updated:
        lines.append(f"RPS_LOG_UI={selected}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.environ["RPS_LOG_UI"] = selected
    load_env_file(env_path)
    st.success("Log level saved. Reload the page to apply to new logs.")

if athlete_id:
    log_file = ensure_logging(athlete_id)
    st.caption(f"Log file: {log_file}")

system_log_panel(expanded=True)
