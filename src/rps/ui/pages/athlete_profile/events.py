from __future__ import annotations

import json
from datetime import date, datetime, timezone

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
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType, Authority

DEFAULT_EVENT_TYPES = [
    "BREVET",
    "GRAVEL",
    "BIKEPACKING",
    "ROAD",
    "MTB",
    "TRAIL",
    "OTHER",
]


init_ui_state()
render_global_sidebar()
athlete_id = get_athlete_id()
announce_log_file(athlete_id)

st.title("Events")
st.caption(f"Athlete: {athlete_id}")
st.info(
    "Add your A/B/C planning events. Type is A/B/C; Priority ranks events within the type "
    "(e.g. B1/B2/B3). A-events must be spaced at least 12 weeks apart."
)

store = LocalArtifactStore(root=SETTINGS.workspace_root)
store.ensure_workspace(athlete_id)
events_path = store.latest_path(athlete_id, ArtifactType.PLANNING_EVENTS)
profile_path = store.latest_path(athlete_id, ArtifactType.KPI_PROFILE)

payload: dict[str, object] = {}
if events_path.exists():
    payload = json.loads(events_path.read_text(encoding="utf-8"))
    set_status(status_state="done", title="Events", message="Ready.")
else:
    st.info("No planning events found yet. Add A/B/C events below.")
    set_status(status_state="running", title="Events", message="Missing planning events input.")

render_status_panel()

data = payload.get("data", {}) if isinstance(payload, dict) else {}
events = data.get("events") or []

event_type_options = list(DEFAULT_EVENT_TYPES)
if profile_path.exists():
    try:
        profile_payload = json.loads(profile_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        profile_payload = {}
    profile_data = profile_payload.get("data") if isinstance(profile_payload, dict) else {}
    profile_meta = profile_data.get("profile_metadata") if isinstance(profile_data, dict) else {}
    profile_event_type = profile_meta.get("event_type") if isinstance(profile_meta, dict) else None
    if profile_event_type:
        event_type_options.insert(0, str(profile_event_type).upper())
    event_type_options = sorted(set(event_type_options))


def _normalize_event(entry: dict[str, object]) -> dict[str, object]:
    normalized = dict(entry)
    if "type" not in normalized and "priority" in normalized:
        normalized["type"] = normalized.get("priority")
    if "priority_rank" not in normalized:
        normalized["priority_rank"] = 1
    normalized.setdefault("event_name", "")
    normalized.setdefault("date", "")
    normalized.setdefault("event_type", event_type_options[0] if event_type_options else "")
    normalized.setdefault("goal", "")
    normalized.setdefault("distance_km", 0)
    normalized.setdefault("elevation_m", 0)
    normalized.setdefault("expected_duration", "TBD")
    normalized.setdefault("time_limit", "TBD")
    normalized.setdefault("objective", "")
    return normalized


def _parse_event_date(raw: object) -> date | None:
    if isinstance(raw, date):
        return raw
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw))
    except ValueError:
        return None


def _validate_events(rows: list[dict[str, object]]) -> list[str]:
    missing_errors: list[str] = []
    required_fields = [
        "type",
        "priority_rank",
        "event_name",
        "date",
        "event_type",
        "goal",
        "distance_km",
        "elevation_m",
        "expected_duration",
        "time_limit",
        "objective",
    ]
    for idx, row in enumerate(rows, start=1):
        for field in required_fields:
            value = row.get(field)
            if value is None or value == "":
                missing_errors.append(f"Row {idx}: missing {field}.")
    a_dates = [
        _parse_event_date(row.get("date"))
        for row in rows
        if str(row.get("type", "")).upper() == "A"
    ]
    a_dates = sorted([d for d in a_dates if d is not None])
    for prev, current in zip(a_dates, a_dates[1:]):
        if (current - prev).days < 84:
            missing_errors.append(
                "A events must be spaced at least 12 weeks apart."
            )
            break
    return missing_errors

st.subheader("Planning Events (A/B/C)")
events = [_normalize_event(row) for row in events if isinstance(row, dict)]
if not events:
    events = [_normalize_event({})]
st.caption(
    "Add A/B/C events with a priority rank (1-3). Event Type defaults to the KPI profile when available."
)
events = st.data_editor(
    events,
    num_rows="dynamic",
    width="stretch",
    key="planning_events_editor",
    column_config={
        "type": st.column_config.SelectboxColumn(
            "Priority",
            options=["A", "B", "C"],
            help="Event tier used in planning (A/B/C).",
        ),
        "priority_rank": st.column_config.NumberColumn(
            "Rank",
            min_value=1,
            max_value=3,
            step=1,
            format="%d",
            help="Priority within the same type (e.g. B1/B2/B3).",
        ),
        "event_name": st.column_config.TextColumn("Event Name"),
        "date": st.column_config.TextColumn("Date (YYYY-MM-DD)"),
        "event_type": st.column_config.SelectboxColumn(
            "Event Type",
            options=event_type_options,
            help="Select from KPI profile event types when available.",
        ),
        "goal": st.column_config.TextColumn("Goal"),
        "distance_km": st.column_config.NumberColumn("Distance (km)", min_value=0, step=1),
        "elevation_m": st.column_config.NumberColumn("Elevation (m)", min_value=0, step=50),
        "expected_duration": st.column_config.TextColumn("Expected Duration"),
        "time_limit": st.column_config.TextColumn("Time Limit"),
        "objective": st.column_config.TextColumn("Objective"),
    },
    column_order=[
        "type",
        "priority_rank",
        "event_name",
        "date",
        "event_type",
        "goal",
        "distance_km",
        "elevation_m",
        "expected_duration",
        "time_limit",
        "objective",
    ],
)

if st.button("Save Events", width="content"):
    run_ts = datetime.now(timezone.utc)
    version_key = run_ts.strftime("%Y%m%d_%H%M%S")
    validation_errors = _validate_events(events)
    if validation_errors:
        st.error(" ".join(validation_errors))
        st.stop()
    payload = {"events": events}
    store.save_version(
        athlete_id,
        ArtifactType.PLANNING_EVENTS,
        version_key,
        payload,
        payload_meta={
            "schema_id": "PlanningEventsInterface",
            "schema_version": "1.1",
            "version": "1.0",
            "authority": Authority.BINDING.value,
            "owner_agent": "User",
            "scope": "Shared",
            "data_confidence": "USER",
            "created_at": run_ts.isoformat(),
            "notes": "",
        },
        authority=Authority.BINDING,
        producer_agent="ui_planning_events",
        run_id=f"ui_planning_events_{run_ts.strftime('%Y%m%dT%H%M%SZ')}",
        update_latest=True,
    )
    st.success("Planning events saved.")
    set_status(status_state="done", title="Events", message="Saved planning events input.")
