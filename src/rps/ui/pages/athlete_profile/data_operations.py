from __future__ import annotations

import streamlit as st

from rps.ui.shared import (
    announce_log_file,
    get_athlete_id,
    init_ui_state,
    render_global_sidebar,
    render_status_panel,
    set_status,
)
from rps.workspace.backup_restore import (
    PARTIAL_RESTORE_MODES,
    create_backup_bundle,
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
