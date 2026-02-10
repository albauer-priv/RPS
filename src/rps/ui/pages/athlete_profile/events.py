from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone

import streamlit as st
import pandas as pd

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

logger = logging.getLogger(__name__)
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

store = LocalArtifactStore(root=SETTINGS.workspace_root)
store.ensure_workspace(athlete_id)
events_path = store.latest_path(athlete_id, ArtifactType.PLANNING_EVENTS)
profile_path = store.latest_path(athlete_id, ArtifactType.KPI_PROFILE)

payload: dict[str, object] = {}
if events_path.exists():
    payload = json.loads(events_path.read_text(encoding="utf-8"))
    set_status(status_state="done", title="Events", message="Ready.")
else:
    set_status(status_state="running", title="Events", message="Missing planning events input.")

render_status_panel()
st.info(
    "Add your A/B/C planning events. Type is A/B/C; Priority ranks events within the type "
    "(e.g. B1/B2/B3). A-events must be spaced at least 12 weeks apart."
)
if not events_path.exists():
    st.info("No planning events found yet. Add A/B/C events below.")

data = payload.get("data", {}) if isinstance(payload, dict) else {}
events = data.get("events") or []
if "events_auto_upgrade_done" not in st.session_state:
    st.session_state["events_auto_upgrade_done"] = False

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


EVENT_COLUMNS = [
    "priority",
    "rank",
    "event_name",
    "date",
    "event_type",
    "goal",
    "distance_km",
    "elevation_m",
    "expected_duration",
    "time_limit",
]


def _normalize_event(entry: dict[str, object]) -> dict[str, object]:
    normalized = dict(entry)
    if "priority" not in normalized:
        normalized["priority"] = normalized.get("type") or normalized.get("priority")
    if "rank" not in normalized:
        normalized["rank"] = normalized.get("priority_rank", 1)
    if not normalized.get("priority"):
        normalized["priority"] = "A"
    if not normalized.get("goal") and normalized.get("objective"):
        normalized["goal"] = normalized.get("objective")
    normalized.setdefault("event_name", "")
    normalized.setdefault("date", "")
    normalized.setdefault("event_type", event_type_options[0] if event_type_options else "")
    normalized.setdefault("goal", "")
    normalized.setdefault("distance_km", 0)
    normalized.setdefault("elevation_m", 0)
    normalized.setdefault("expected_duration", "TBD")
    normalized.setdefault("time_limit", "TBD")
    normalized.pop("objective", None)
    return normalized


def _needs_upgrade(rows: list[dict[str, object]]) -> bool:
    if not rows:
        return False
    for row in rows:
        if not isinstance(row, dict):
            return True
        has_priority_rank = "priority" in row and "rank" in row
        has_type_rank = "type" in row and "priority_rank" in row
        if not (has_priority_rank or has_type_rank):
            return True
        if "objective" in row:
            return True
    return False


def _to_storage_event(entry: dict[str, object]) -> dict[str, object]:
    return {
        "type": str(entry.get("priority") or "A").upper(),
        "priority_rank": int(entry.get("rank") or 1),
        "event_name": str(entry.get("event_name") or "").strip(),
        "date": str(entry.get("date") or "").strip(),
        "event_type": str(entry.get("event_type") or "").strip(),
        "goal": str(entry.get("goal") or "").strip(),
        "distance_km": entry.get("distance_km") or 0,
        "elevation_m": entry.get("elevation_m") or 0,
        "expected_duration": str(entry.get("expected_duration") or "").strip(),
        "time_limit": str(entry.get("time_limit") or "").strip(),
    }


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
        "priority",
        "rank",
        "event_name",
        "date",
        "event_type",
        "goal",
        "distance_km",
        "elevation_m",
        "expected_duration",
        "time_limit",
    ]
    for idx, row in enumerate(rows, start=1):
        for field in required_fields:
            value = row.get(field)
            if value is None or value == "":
                missing_errors.append(f"Row {idx}: missing {field}.")
    priority_rank_map: dict[str, set[int]] = {}
    a_dates: list[date] = []
    for idx, row in enumerate(rows, start=1):
        priority = str(row.get("priority") or "").upper()
        if priority not in {"A", "B", "C"}:
            missing_errors.append(f"Row {idx}: priority must be A, B, or C.")
        rank_val = row.get("rank")
        try:
            rank = int(rank_val)
        except (TypeError, ValueError):
            missing_errors.append(f"Row {idx}: rank must be an integer 1-3.")
            continue
        if rank < 1 or rank > 3:
            missing_errors.append(f"Row {idx}: rank must be between 1 and 3.")
        rank_set = priority_rank_map.setdefault(priority, set())
        if rank in rank_set:
            missing_errors.append(
                f"Row {idx}: duplicate rank {rank} within priority {priority}."
            )
        else:
            rank_set.add(rank)
        parsed_date = _parse_event_date(row.get("date"))
        if row.get("date") and parsed_date is None:
            missing_errors.append(f"Row {idx}: date must be YYYY-MM-DD.")
        if priority == "A" and parsed_date:
            a_dates.append(parsed_date)
    a_dates = sorted(a_dates)
    for prev, current in zip(a_dates, a_dates[1:]):
        if (current - prev).days < 84:
            missing_errors.append(
                "A events must be spaced at least 12 weeks apart."
            )
            break
    return missing_errors


def _sort_events(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    def _sort_key(row: dict[str, object]) -> tuple[int, str]:
        parsed = _parse_event_date(row.get("date"))
        return (0, parsed.isoformat()) if parsed else (1, "")

    return sorted(rows, key=_sort_key, reverse=True)


def _save_events_payload(
    store: LocalArtifactStore,
    athlete_id: str,
    ui_events: list[dict[str, object]],
) -> None:
    run_ts = datetime.now(timezone.utc)
    version_key = run_ts.strftime("%Y%m%d_%H%M%S")
    storage_events = [_to_storage_event(event) for event in _sort_events(ui_events)]
    replaced = sum(
        1
        for event in ui_events
        if not event.get("goal") and event.get("objective")
    )
    if replaced:
        logger.info("Events upgrade mapped objective->goal rows=%d", replaced)
    payload = {"events": storage_events}
    store.save_version(
        athlete_id,
        ArtifactType.PLANNING_EVENTS,
        version_key,
        payload,
        payload_meta={
            "schema_id": "PlanningEventsInterface",
            "schema_version": "1.2",
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


st.subheader("Planning Events (A/B/C)")
legacy_upgrade_needed = _needs_upgrade([row for row in events if isinstance(row, dict)])
if legacy_upgrade_needed and not st.session_state["events_auto_upgrade_done"]:
    normalized_events = [_normalize_event(row) for row in events if isinstance(row, dict)]
    if not normalized_events:
        normalized_events = [_normalize_event({})]
    logger.info("Events auto-upgrade triggered")
    _save_events_payload(store, athlete_id, normalized_events)
    set_status(status_state="done", title="Events", message="Events upgraded.")
    st.session_state["events_auto_upgrade_done"] = True
    st.rerun()
events = [_normalize_event(row) for row in events if isinstance(row, dict)]
if not events:
    events = [_normalize_event({})]
events = _sort_events(events)
st.caption(
    "Add A/B/C events with a priority rank (1-3). Event Type defaults to the KPI profile when available."
)
events_df = pd.DataFrame(events, columns=EVENT_COLUMNS)
events_df = st.data_editor(
    events_df,
    num_rows="dynamic",
    width="stretch",
    key="planning_events_editor",
    column_config={
        "priority": st.column_config.SelectboxColumn(
            "Priority",
            options=["A", "B", "C"],
            help="Event tier used in planning (A/B/C).",
        ),
        "rank": st.column_config.NumberColumn(
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
        "time_limit": st.column_config.TextColumn(
            "Time Limit",
            help="Use HH:MM or a clear text limit (e.g. 24:00, TBD).",
        ),
    },
    column_order=EVENT_COLUMNS,
)

if st.button("Save Events", width="content"):
    ui_events = events_df.to_dict(orient="records")
    validation_errors = _validate_events(ui_events)
    if validation_errors:
        st.error("\n".join(validation_errors))
        st.stop()
    _save_events_payload(store, athlete_id, ui_events)
    st.success("Planning events saved.")
    set_status(status_state="done", title="Events", message="Saved planning events input.")
