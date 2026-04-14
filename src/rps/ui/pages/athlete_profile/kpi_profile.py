from __future__ import annotations

import json
from datetime import UTC, date, datetime

import streamlit as st

from rps.ui.shared import (
    ROOT,
    SETTINGS,
    announce_log_file,
    get_athlete_id,
    init_ui_state,
    iso_week_date_range,
    render_global_sidebar,
    render_status_panel,
    set_status,
)
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType


def _iso_week_key(value: date) -> str:
    """Return the canonical ISO week key for a date."""
    iso_year, iso_week, _ = value.isocalendar()
    return f"{iso_year:04d}-{iso_week:02d}"


def _canonical_trace_upstream(meta: dict[str, object], *, version_key: str) -> list[dict[str, str]]:
    """Return canonical trace_upstream entries for a selected KPI profile."""
    trace_upstream = meta.get("trace_upstream")
    if not isinstance(trace_upstream, list):
        trace_upstream = []
    normalized: list[dict[str, str]] = []
    for index, entry in enumerate(trace_upstream, start=1):
        if not isinstance(entry, dict):
            continue
        artifact = str(entry.get("artifact") or f"kpi_profile_{version_key}.json")
        version = str(entry.get("version") or "1.0")
        run_id = str(entry.get("run_id") or meta.get("run_id") or f"spec_kpi_profile_{index}")
        normalized.append(
            {
                "artifact": artifact,
                "version": version,
                "run_id": run_id,
            }
        )
    if normalized:
        return normalized
    return [
        {
            "artifact": f"kpi_profile_{version_key}.json",
            "version": "1.0",
            "run_id": f"spec_kpi_profile_{version_key}",
        }
    ]


def _build_selected_kpi_profile_document(
    selected_payload: dict[str, object],
    *,
    version_key: str,
    run_id: str,
) -> dict[str, object]:
    """Build a canonical KPI_PROFILE envelope for workspace storage."""
    selected_meta = selected_payload.get("meta")
    source_meta = selected_meta if isinstance(selected_meta, dict) else {}
    selected_data = selected_payload.get("data")
    data = dict(selected_data) if isinstance(selected_data, dict) else {}

    created_at = datetime.now(UTC)
    created_at_iso = created_at.isoformat()
    iso = created_at.date().isocalendar()
    iso_week = _iso_week_key(created_at.date())
    week_start, week_end = iso_week_date_range(iso.year, iso.week)
    notes = str(source_meta.get("notes") or "").strip()

    return {
        "meta": {
            "artifact_type": "KPI_PROFILE",
            "schema_id": "KPIProfileInterface",
            "schema_version": "1.0",
            "version": str(source_meta.get("version") or "1.0"),
            "authority": "Binding",
            "owner_agent": "Policy-Owner",
            "run_id": run_id,
            "created_at": created_at_iso,
            "scope": "Shared",
            "iso_week": iso_week,
            "iso_week_range": f"{iso_week}--{iso_week}",
            "temporal_scope": {"from": week_start.isoformat(), "to": week_end.isoformat()},
            "trace_upstream": _canonical_trace_upstream(source_meta, version_key=version_key),
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "UNKNOWN",
            "notes": notes,
        },
        "data": data,
    }


st.title("KPI Profile")

# CHECKLIST (Athlete Profile -> KPI Profile)
# - Show all available KPI profiles (expandable list).
# - Provide dropdown selection and core profile metadata summary.
# - Apply selection to workspace (inputs + latest) on confirm.

init_ui_state()
render_global_sidebar()
athlete_id = get_athlete_id()
announce_log_file(athlete_id)

st.caption(f"Athlete: {athlete_id}")

profiles_dir = ROOT / "specs" / "kpi_profiles"
profile_paths = sorted(profiles_dir.glob("kpi_profile_*.json"))

if not profile_paths:
    set_status(status_state="idle", title="KPI Profile", message="No KPI profiles found.")
    render_status_panel()
    st.stop()

set_status(status_state="done", title="KPI Profile", message="Ready.")
render_status_panel()

profile_map = {path.stem: path for path in profile_paths}
profile_keys = list(profile_map.keys())
store = LocalArtifactStore(root=SETTINGS.workspace_root)
current_profile_key = None
try:
    current_version_key = store.get_latest_version_key(athlete_id, ArtifactType.KPI_PROFILE)
    candidate_key = f"kpi_profile_{current_version_key}"
    if candidate_key in profile_map:
        current_profile_key = candidate_key
except (FileNotFoundError, ValueError):
    current_profile_key = None

selectbox_key = "kpi_profile_selected_key"
if current_profile_key and st.session_state.get(selectbox_key) not in profile_keys:
    st.session_state[selectbox_key] = current_profile_key
elif selectbox_key not in st.session_state or st.session_state.get(selectbox_key) not in profile_keys:
    st.session_state[selectbox_key] = profile_keys[0]

selected_key = st.selectbox("Select KPI Profile", options=profile_keys, key=selectbox_key)

selected_payload = json.loads(profile_map[selected_key].read_text(encoding="utf-8"))
meta = selected_payload.get("meta", {}) if isinstance(selected_payload, dict) else {}
data = selected_payload.get("data", {}) if isinstance(selected_payload, dict) else {}
profile_meta = data.get("profile_metadata", {}) if isinstance(data, dict) else {}

active_profile_label = current_profile_key or "No KPI profile selected yet."
st.info(f"Active KPI Profile: {active_profile_label}")

with st.expander("Available KPI Profiles", expanded=False):
    for key, path in profile_map.items():
        payload = json.loads(path.read_text(encoding="utf-8"))
        data_block = payload.get("data", {}) if isinstance(payload, dict) else {}
        meta_block = data_block.get("profile_metadata", {}) if isinstance(data_block, dict) else {}
        summary = " · ".join(
            str(meta_block.get(field) or "").strip()
            for field in ("profile_id", "event_type", "distance_range", "athlete_class")
            if meta_block.get(field)
        )
        st.markdown(f"**{key}**\n\n{summary or 'No metadata available.'}")

st.subheader("Profile Summary")
if profile_meta:
    st.table(
        {
            "Profile ID": [profile_meta.get("profile_id", "—")],
            "Event Type": [profile_meta.get("event_type", "—")],
            "Distance Range": [profile_meta.get("distance_range", "—")],
            "Athlete Class": [profile_meta.get("athlete_class", "—")],
            "Primary Objective": [profile_meta.get("primary_objective", "—")],
        }
    )
else:
    st.info("No profile metadata found.")

with st.expander("Profile Details", expanded=False):
    st.json(data)

if st.button("Use this KPI Profile"):
    version_key = selected_key.replace("kpi_profile_", "")
    run_id = f"ui_kpi_profile_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    document = _build_selected_kpi_profile_document(
        selected_payload,
        version_key=version_key,
        run_id=run_id,
    )
    store.save_document(
        athlete_id,
        ArtifactType.KPI_PROFILE,
        version_key,
        document,
        producer_agent="ui_kpi_profile",
        run_id=run_id,
        update_latest=True,
    )
    # Ensure a canonical inputs copy exists (kpi_profile.json) alongside versioned input.
    inputs_path = store.type_dir(athlete_id, ArtifactType.KPI_PROFILE) / "kpi_profile.json"
    inputs_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    st.session_state[selectbox_key] = selected_key
    set_status(
        status_state="done",
        title="KPI Profile",
        message=f"Selected {selected_key}.",
        last_action="Select KPI Profile",
    )
    st.success("KPI Profile updated.")
