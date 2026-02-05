from __future__ import annotations

import logging
import streamlit as st

from rps.data_pipeline.season_brief_availability import parse_and_store_availability
from rps.ui.shared import (
    SETTINGS,
    announce_log_file,
    get_athlete_id,
    get_iso_year_week,
    init_ui_state,
    render_global_sidebar,
    render_status_panel,
    set_status,
)
from rps.workspace.backup_restore import (
    PARTIAL_RESTORE_MODES,
    create_backup_bundle,
    list_backup_files,
    restore_backup_bundle,
    validate_backup_bundle,
)


init_ui_state()
render_global_sidebar()
athlete_id = get_athlete_id()
announce_log_file(athlete_id)

st.title("Data Operations")
st.caption(f"Athlete: {athlete_id}")
st.write("Backup and restore athlete data for portability and recovery.")

set_status(status_state="ready", title="Data Operations", message="Backup/restore tools are available.")
render_status_panel()

mode_labels = {
    "full": "Full backup",
    "inputs": "Inputs only",
    "plans": "Plans only",
    "metrics": "Metrics only",
    "receipts": "Receipts only",
    "rendered": "Rendered only",
}
mode_options = list(PARTIAL_RESTORE_MODES.keys())

with st.expander("Backup (Export)", expanded=False):
    st.write("Create a portable archive of this athlete’s data.")
    backup_mode = st.selectbox(
        "Backup scope",
        options=mode_options,
        format_func=lambda key: mode_labels.get(key, key),
    )
    if st.button("Create Backup", width="content"):
        with st.spinner("Building backup archive..."):
            try:
                bundle = create_backup_bundle(
                    athlete_id=athlete_id,
                    workspace_root=SETTINGS.workspace_root,
                    mode=backup_mode,
                )
            except Exception as exc:  # pragma: no cover - UI error path
                st.error(f"Backup failed: {exc}")
                set_status(status_state="error", title="Data Operations", message="Backup failed.")
            else:
                st.success(f"Backup ready: {bundle.filename}")
                st.download_button(
                    "Download Backup",
                    data=bundle.data,
                    file_name=bundle.filename,
                    mime="application/zip",
                )
                st.session_state["last_backup_bundle"] = bundle
                set_status(status_state="done", title="Data Operations", message="Backup created.")

    last_bundle = st.session_state.get("last_backup_bundle")
    if last_bundle:
        st.download_button(
            "Download Last Backup",
            data=last_bundle.data,
            file_name=last_bundle.filename,
            mime="application/zip",
        )
    st.info("Backups exclude logs and run history; see the backup/restore doc for scope.")

with st.expander("Restore (Import)", expanded=False):
    st.write("Restore an archive into this athlete’s workspace.")
    restore_mode = st.selectbox(
        "Restore scope",
        options=mode_options,
        format_func=lambda key: mode_labels.get(key, key),
        key="restore_mode",
    )
    archive = st.file_uploader("Backup archive (.zip or .tar.gz)", type=["zip", "tar", "gz"])
    confirm = st.text_input('Type "RESTORE" to confirm', value="")
    force = st.checkbox("Force restore into non-empty workspace", value=False)
    show_files = st.checkbox("Show files to restore", value=False)
    if archive is not None and show_files:
        with st.spinner("Listing files..."):
            try:
                files = list_backup_files(
                    athlete_id=athlete_id,
                    workspace_root=SETTINGS.workspace_root,
                    archive_bytes=archive.getvalue(),
                    mode=restore_mode,
                )
            except Exception as exc:  # pragma: no cover - UI error path
                st.error(f"Could not list files: {exc}")
            else:
                st.caption(f"{len(files)} files in restore scope.")
                summary = {
                    "inputs/": 0,
                    "latest/": 0,
                    "data/": 0,
                    "receipts/": 0,
                    "rendered/": 0,
                    "other": 0,
                }
                for path in files:
                    if path.startswith("inputs/"):
                        summary["inputs/"] += 1
                    elif path.startswith("latest/"):
                        summary["latest/"] += 1
                    elif path.startswith("data/"):
                        summary["data/"] += 1
                    elif path.startswith("receipts/"):
                        summary["receipts/"] += 1
                    elif path.startswith("rendered/"):
                        summary["rendered/"] += 1
                    else:
                        summary["other"] += 1
                st.write(
                    "Summary: "
                    + ", ".join(f"{key}{value}" for key, value in summary.items() if value > 0)
                )
                st.dataframe(files, width="stretch", hide_index=True)
    if st.button("Validate Backup", width="content", disabled=archive is None):
        with st.spinner("Validating backup..."):
            try:
                count = validate_backup_bundle(
                    athlete_id=athlete_id,
                    workspace_root=SETTINGS.workspace_root,
                    archive_bytes=archive.getvalue() if archive else b"",
                    mode=restore_mode,
                )
            except Exception as exc:  # pragma: no cover - UI error path
                st.error(f"Validation failed: {exc}")
                set_status(status_state="error", title="Data Operations", message="Backup validation failed.")
            else:
                st.success(f"Validation OK ({count} files in scope).")
                set_status(status_state="done", title="Data Operations", message="Backup validated.")

    if st.button("Restore Backup", width="content", disabled=archive is None):
        if confirm.strip() != "RESTORE":
            st.error("Confirmation missing. Type RESTORE to proceed.")
        else:
            with st.spinner("Restoring backup..."):
                try:
                    restored = restore_backup_bundle(
                        athlete_id=athlete_id,
                        workspace_root=SETTINGS.workspace_root,
                        archive_bytes=archive.getvalue() if archive else b"",
                        mode=restore_mode,
                        force=force,
                    )
                except Exception as exc:  # pragma: no cover - UI error path
                    st.error(f"Restore failed: {exc}")
                    set_status(status_state="error", title="Data Operations", message="Restore failed.")
                else:
                    st.success(f"Restore complete ({len(restored)} files).")
                    set_status(status_state="done", title="Data Operations", message="Restore completed.")
    st.warning("Restores are destructive; target workspace should be empty unless using a partial restore.")

with st.expander("Availability Import (Deprecated)", expanded=False):
    st.write("Legacy Season Brief parsing is deprecated after the modular input cut-over.")
    iso_year, _iso_week = get_iso_year_week()
    season_year = st.number_input(
        "Season year (optional)",
        min_value=2000,
        max_value=2100,
        value=int(iso_year),
        step=1,
        help="Used only for parsing legacy Season Brief availability tables.",
    )
    if st.button("Parse Availability from Season Brief", width="content"):
        with st.spinner("Parsing Season Brief availability..."):
            try:
                result = parse_and_store_availability(
                    athlete_id=athlete_id,
                    workspace_root=SETTINGS.workspace_root,
                    schema_dir=SETTINGS.schema_dir,
                    year=int(season_year),
                )
            except Exception as exc:  # pragma: no cover - UI error path
                st.error(f"Parse failed: {exc}")
                set_status(status_state="error", title="Data Operations", message="Availability parse failed.")
            else:
                st.success(f"Availability updated: {result.output_path.name}")
                set_status(status_state="done", title="Data Operations", message="Availability parsed.")
