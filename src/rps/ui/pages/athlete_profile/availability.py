from __future__ import annotations

import json
from datetime import datetime, timezone

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


init_ui_state()
render_global_sidebar()
athlete_id = get_athlete_id()
announce_log_file(athlete_id)

st.title("Availability")
st.caption(f"Athlete: {athlete_id}")

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
TRAVEL_RISK_OPTIONS = ["LOW", "MED", "HIGH"]


def _snap_half(value: float) -> float:
    return round(round(float(value) * 2) / 2, 1)


def _normalize_weekday(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    for day in WEEKDAYS:
        if value.lower() == day.lower():
            return day
    return None


def _normalize_travel_risk(value: object) -> str:
    if value is None:
        return "LOW"
    text = str(value).strip().upper()
    if text in {"MEDIUM", "MID"}:
        return "MED"
    if text in TRAVEL_RISK_OPTIONS:
        return text
    return "LOW"


def _normalize_entry(row: dict[str, object] | None, weekday: str) -> dict[str, object]:
    row = row or {}
    def _coerce_hours(value: object, default: float) -> float:
        try:
            return float(str(value))
        except (TypeError, ValueError):
            return default

    hours = _coerce_hours(row.get("hours", 0.0), 0.0)
    hours_min = _coerce_hours(row.get("hours_min", hours), hours)
    hours_typical = _coerce_hours(row.get("hours_typical", hours), hours)
    hours_max = _coerce_hours(row.get("hours_max", hours), hours)
    return {
        "weekday": weekday,
        "hours_min": _snap_half(hours_min),
        "hours_typical": _snap_half(hours_typical),
        "hours_max": _snap_half(hours_max),
        "indoor_possible": bool(row.get("indoor_possible", row.get("indoor", False))),
        "travel_risk": _normalize_travel_risk(row.get("travel_risk")),
        "locked": bool(row.get("locked", False)),
    }


store = LocalArtifactStore(root=SETTINGS.workspace_root)
store.ensure_workspace(athlete_id)
availability_path = store.latest_path(athlete_id, ArtifactType.AVAILABILITY)

if not availability_path.exists():
    payload: dict[str, object] = {}
    set_status(status_state="running", title="Availability", message="Missing availability input.")
else:
    payload = json.loads(availability_path.read_text(encoding="utf-8"))
    set_status(status_state="done", title="Availability", message="Ready.")

render_status_panel()
st.info(
    "Describe typical weekly hours plus any fixed rest days. "
    "This is used to bound feasible weekly load corridors."
)
if not availability_path.exists():
    st.info("No availability input found yet. Add your weekly availability below.")

data = payload.get("data", {}) if isinstance(payload, dict) else {}
if not isinstance(data, dict):
    data = {}
availability_table = data.get("availability_table") or []
weekly_hours = data.get("weekly_hours") or {"min": 0.0, "typical": 0.0, "max": 0.0}
fixed_rest_days = data.get("fixed_rest_days") or []
notes = data.get("notes") or ""
if not isinstance(weekly_hours, dict):
    weekly_hours = {"min": 0.0, "typical": 0.0, "max": 0.0}

st.subheader("Weekly Hours")
col_min, col_typ, col_max = st.columns(3)
with col_min:
    weekly_min = st.number_input(
        "Min hours",
        min_value=0.0,
        step=0.5,
        format="%.1f",
        value=_snap_half(weekly_hours.get("min", 0.0)),
    )
with col_typ:
    weekly_typ = st.number_input(
        "Typical hours",
        min_value=0.0,
        step=0.5,
        format="%.1f",
        value=_snap_half(weekly_hours.get("typical", 0.0)),
    )
with col_max:
    weekly_max = st.number_input(
        "Max hours",
        min_value=0.0,
        step=0.5,
        format="%.1f",
        value=_snap_half(weekly_hours.get("max", 0.0)),
    )

st.subheader("Availability Table")
st.caption(
    "Hours must be in 0.5h increments. Travel risk uses uppercase enums (LOW/MED/HIGH)."
)
availability_by_day: dict[str, dict[str, object]] = {}
for row in availability_table:
    if not isinstance(row, dict):
        continue
    row = {key: value for key, value in row.items() if not key.startswith("source_")}
    day_key = _normalize_weekday(row.get("weekday")) or _normalize_weekday(row.get("day"))
    if not day_key:
        continue
    availability_by_day[day_key] = row

availability_table = [
    _normalize_entry(availability_by_day.get(day), day) for day in WEEKDAYS
]
availability_table = st.data_editor(
    availability_table,
    num_rows="fixed",
    column_order=[
        "weekday",
        "hours_min",
        "hours_typical",
        "hours_max",
        "indoor_possible",
        "travel_risk",
        "locked",
    ],
    column_config={
        "weekday": st.column_config.SelectboxColumn("weekday", options=WEEKDAYS, required=True),
        "hours_min": st.column_config.NumberColumn("hours_min", min_value=0.0, step=0.5, format="%.1f"),
        "hours_typical": st.column_config.NumberColumn("hours_typical", min_value=0.0, step=0.5, format="%.1f"),
        "hours_max": st.column_config.NumberColumn("hours_max", min_value=0.0, step=0.5, format="%.1f"),
        "indoor_possible": st.column_config.CheckboxColumn("indoor_possible"),
        "travel_risk": st.column_config.SelectboxColumn("travel_risk", options=TRAVEL_RISK_OPTIONS),
        "locked": st.column_config.CheckboxColumn("locked"),
    },
    width="stretch",
    key="availability_table_editor_v2",
)

table_hours_min = round(sum(row.get("hours_min", 0.0) for row in availability_table), 1)
table_hours_typ = round(sum(row.get("hours_typical", 0.0) for row in availability_table), 1)
table_hours_max = round(sum(row.get("hours_max", 0.0) for row in availability_table), 1)
if (
    abs(table_hours_min - weekly_min) > 0.1
    or abs(table_hours_typ - weekly_typ) > 0.1
    or abs(table_hours_max - weekly_max) > 0.1
):
    st.warning(
        "Weekly hours do not match table totals. "
        f"Table totals: min {table_hours_min:.1f}h, typical {table_hours_typ:.1f}h, max {table_hours_max:.1f}h."
    )

fixed_rest_days = st.multiselect(
    "Fixed rest days",
    ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    default=fixed_rest_days,
)

notes = st.text_area("Notes", value=notes, height=120)

if st.button("Save Availability", width="content"):
    run_ts = datetime.now(timezone.utc)
    version_key = run_ts.strftime("%Y%m%d_%H%M%S")
    normalized_table = [
        _normalize_entry(row if isinstance(row, dict) else None, day)
        for day, row in zip(WEEKDAYS, availability_table)
    ]
    fixed_rest_days_set = {day for day in fixed_rest_days}
    for row in normalized_table:
        if row["weekday"] in fixed_rest_days_set:
            row["locked"] = True
            row["hours_min"] = 0.0
            row["hours_typical"] = 0.0
            row["hours_max"] = 0.0
    payload = {
        "source_type": "manual",
        "source_ref": "ui_manual",
        "availability_table": normalized_table,
        "weekly_hours": {
            "min": _snap_half(weekly_min),
            "typical": _snap_half(weekly_typ),
            "max": _snap_half(weekly_max),
        },
        "fixed_rest_days": fixed_rest_days,
        "notes": notes,
    }
    store.save_version(
        athlete_id,
        ArtifactType.AVAILABILITY,
        version_key,
        payload,
        payload_meta={
            "schema_id": "AvailabilityInterface",
            "schema_version": "1.0",
            "version": "1.0",
            "authority": Authority.BINDING.value,
            "owner_agent": "User",
            "scope": "Shared",
            "data_confidence": "USER",
            "created_at": run_ts.isoformat(),
        },
        authority=Authority.BINDING,
        producer_agent="ui_availability",
        run_id=f"ui_availability_{run_ts.strftime('%Y%m%dT%H%M%SZ')}",
        update_latest=True,
    )
    st.success("Availability saved.")
    set_status(status_state="done", title="Availability", message="Saved availability input.")
