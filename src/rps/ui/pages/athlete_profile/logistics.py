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


def _next_event_id(existing_ids: set[str]) -> str:
    numbers = []
    for event_id in existing_ids:
        if event_id.startswith("EVT-"):
            suffix = event_id.split("-", 1)[-1]
            if suffix.isdigit():
                numbers.append(int(suffix))
    next_num = max(numbers, default=0) + 1
    return f"EVT-{next_num:03d}"


def _normalize_events(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    existing_ids = set()
    for row in rows:
        event_id = str(row.get("event_id") or "").strip()
        if event_id:
            existing_ids.add(event_id)
    next_id = _next_event_id(existing_ids)
    normalized: list[dict[str, object]] = []
    for row in rows:
        event_id = str(row.get("event_id") or "").strip()
        if not event_id:
            event_id = next_id
            existing_ids.add(event_id)
            next_id = _next_event_id(existing_ids)
        normalized.append(
            {
                "date": str(row.get("date") or "").strip(),
                "event_id": event_id,
                "event_type": str(row.get("event_type") or "").strip().upper(),
                "status": str(row.get("status") or "").strip().upper(),
                "impact": str(row.get("impact") or "").strip().upper(),
                "description": str(row.get("description") or "").strip(),
            }
        )
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


def _sort_events(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    def _sort_key(row: dict[str, object]) -> tuple[int, str]:
        parsed = _parse_event_date(row.get("date"))
        return (0, parsed.isoformat()) if parsed else (1, "")

    return sorted(rows, key=_sort_key, reverse=True)


def _validate_events(rows: list[dict[str, object]]) -> list[str]:
    errors: list[str] = []
    seen_dates: set[str] = set()
    for idx, row in enumerate(rows, start=1):
        raw_date = row.get("date")
        parsed = _parse_event_date(raw_date)
        if not raw_date:
            errors.append(f"Row {idx}: missing date.")
        elif parsed is None:
            errors.append(f"Row {idx}: date must be YYYY-MM-DD.")
        else:
            date_key = parsed.isoformat()
            if date_key in seen_dates:
                errors.append(f"Row {idx}: duplicate date {date_key}.")
            else:
                seen_dates.add(date_key)
        description = str(row.get("description") or "").strip()
        if not description:
            errors.append(f"Row {idx}: description is required.")
    return errors


init_ui_state()
render_global_sidebar()
athlete_id = get_athlete_id()
announce_log_file(athlete_id)

st.title("Logistics")
st.caption(f"Athlete: {athlete_id}")

store = LocalArtifactStore(root=SETTINGS.workspace_root)
store.ensure_workspace(athlete_id)
logistics_path = store.latest_path(athlete_id, ArtifactType.LOGISTICS)

payload: dict[str, object] = {}
if logistics_path.exists():
    payload = json.loads(logistics_path.read_text(encoding="utf-8"))
    set_status(status_state="done", title="Logistics", message="Ready.")
else:
    set_status(status_state="running", title="Logistics", message="Missing logistics input.")

render_status_panel()
st.info(
    "Capture context events (travel, work, life constraints) that affect training availability "
    "but are not A/B/C planning events."
)
if not logistics_path.exists():
    st.info("No logistics input found yet. Add context events below.")

data = payload.get("data", {}) if isinstance(payload, dict) else {}
if not isinstance(data, dict):
    data = {}
events = data.get("events") or []

EVENT_TYPE_OPTIONS = [
    "TRAVEL",
    "WORK",
    "WEATHER",
    "HEALTH",
    "FAMILY",
    "EQUIPMENT",
    "OTHER",
]
STATUS_OPTIONS = ["PLANNED", "OCCURRED", "CANCELLED"]
IMPACT_OPTIONS = [
    "AVAILABILITY",
    "MISSED_SESSION",
    "MODALITY",
    "RECOVERY",
    "DATA_QUALITY",
    "NONE",
    "OTHER",
]

st.subheader("Context Events")
st.caption(
    "Event IDs are generated automatically on save. "
    "Status and impact use uppercase enum values."
)
if not events:
    events = [
        {
            "date": "",
            "event_id": "",
            "event_type": EVENT_TYPE_OPTIONS[0],
            "status": STATUS_OPTIONS[0],
            "impact": IMPACT_OPTIONS[0],
            "description": "",
        }
    ]
events = _sort_events(events)

status_counts = {"PLANNED": 0, "OCCURRED": 0}
for row in events:
    status = str(row.get("status") or "").strip().upper()
    if status in status_counts:
        status_counts[status] += 1
st.caption(
    f"Planned: {status_counts['PLANNED']} · Occurred: {status_counts['OCCURRED']}"
)
events = st.data_editor(
    events,
    num_rows="dynamic",
    width="stretch",
    key="logistics_events_editor",
    column_config={
        "date": st.column_config.TextColumn("Date (YYYY-MM-DD)"),
        "event_id": st.column_config.TextColumn("Event ID (auto)", disabled=True),
        "event_type": st.column_config.SelectboxColumn("Event Type", options=EVENT_TYPE_OPTIONS),
        "status": st.column_config.SelectboxColumn("Status", options=STATUS_OPTIONS),
        "impact": st.column_config.SelectboxColumn("Impact", options=IMPACT_OPTIONS),
        "description": st.column_config.TextColumn("Description"),
    },
    column_order=["date", "event_id", "event_type", "status", "impact", "description"],
)

if st.button("Save Logistics", width="content"):
    run_ts = datetime.now(timezone.utc)
    version_key = run_ts.strftime("%Y%m%d_%H%M%S")
    validation_errors = _validate_events(events)
    if validation_errors:
        st.error("\n".join(validation_errors))
        st.stop()
    events = _sort_events(_normalize_events(events))
    payload = {"events": events}
    store.save_version(
        athlete_id,
        ArtifactType.LOGISTICS,
        version_key,
        payload,
        payload_meta={
            "schema_id": "LogisticsInterface",
            "schema_version": "1.0",
            "version": "1.0",
            "authority": Authority.INFORMATIONAL.value,
            "owner_agent": "User",
            "scope": "Context",
            "data_confidence": "USER",
            "created_at": run_ts.isoformat(),
            "notes": "",
        },
        authority=Authority.INFORMATIONAL,
        producer_agent="ui_logistics",
        run_id=f"ui_logistics_{run_ts.strftime('%Y%m%dT%H%M%SZ')}",
        update_latest=True,
    )
    st.success("Logistics saved.")
    set_status(status_state="done", title="Logistics", message="Saved logistics input.")
