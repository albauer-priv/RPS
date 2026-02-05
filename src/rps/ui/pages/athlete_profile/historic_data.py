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


def _parse_duration_to_hours(value: str | None) -> float:
    if not value:
        return 0.0
    parts = value.split(":")
    try:
        if len(parts) == 2:
            hours, minutes = parts
            return float(hours) + float(minutes) / 60.0
        if len(parts) == 3:
            hours, minutes, seconds = parts
            return float(hours) + float(minutes) / 60.0 + float(seconds) / 3600.0
    except ValueError:
        return 0.0
    return 0.0


def _compute_baseline(trend_doc: dict[str, object]) -> dict[str, object]:
    data = trend_doc.get("data", {}) if isinstance(trend_doc, dict) else {}
    weekly = data.get("weekly_trends") or []
    total_kj = 0.0
    total_hours = 0.0
    for item in weekly:
        if not isinstance(item, dict):
            continue
        aggregates = item.get("weekly_aggregates") or {}
        work_kj = aggregates.get("work_kj") or 0.0
        total_kj += float(work_kj or 0.0)
        total_hours += _parse_duration_to_hours(aggregates.get("moving_time"))
    weeks = max(len(weekly), 1)
    avg_weekly_kj = total_kj / weeks
    kj_per_year = avg_weekly_kj * 52.0
    kj_per_day = total_kj / (weeks * 7.0)
    kj_per_hour = total_kj / total_hours if total_hours > 0 else 0.0
    return {
        "metrics": {
            "kj_per_year": round(kj_per_year, 2),
            "kj_per_day": round(kj_per_day, 2),
            "kj_per_hour": round(kj_per_hour, 2),
        },
        "source": {
            "source_type": "intervals",
            "range": f"{weeks} weeks",
        },
    }


init_ui_state()
render_global_sidebar()
athlete_id = get_athlete_id()
announce_log_file(athlete_id)

st.title("Historic Data")
st.caption(f"Athlete: {athlete_id}")

store = LocalArtifactStore(root=SETTINGS.workspace_root)
store.ensure_workspace(athlete_id)
baseline_path = store.latest_path(athlete_id, ArtifactType.HISTORICAL_BASELINE)

payload: dict[str, object] = {}
if baseline_path.exists():
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    set_status(status_state="done", title="Historic Data", message="Ready.")
else:
    set_status(status_state="running", title="Historic Data", message="Missing baseline.")

render_status_panel()

data = payload.get("data", {}) if isinstance(payload, dict) else {}
metrics = data.get("metrics") or {}

st.subheader("Baseline Metrics")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("kJ / year", metrics.get("kj_per_year", "—"))
with col2:
    st.metric("kJ / day", metrics.get("kj_per_day", "—"))
with col3:
    st.metric("kJ / hour", metrics.get("kj_per_hour", "—"))

st.info("Baseline is aggregated from Intervals data. Use Refresh to recompute.")

if st.button("Refresh Historical Baseline", width="content"):
    trend_path = store.latest_path(athlete_id, ArtifactType.ACTIVITIES_TREND)
    if not trend_path.exists():
        st.error("activities_trend.json not found. Run the Intervals data pipeline first.")
    else:
        trend_doc = json.loads(trend_path.read_text(encoding="utf-8"))
        baseline_data = _compute_baseline(trend_doc)
        run_ts = datetime.now(timezone.utc)
        version_key = run_ts.strftime("%Y%m%d_%H%M%S")
        store.save_version(
            athlete_id,
            ArtifactType.HISTORICAL_BASELINE,
            version_key,
            baseline_data,
            payload_meta={
                "schema_id": "HistoricalBaselineInterface",
                "schema_version": "1.0",
                "version": "1.0",
                "authority": Authority.DERIVED.value,
                "owner_agent": "Data-Pipeline",
                "scope": "Shared",
                "data_confidence": "MEDIUM",
                "created_at": run_ts.isoformat(),
                "notes": "",
                "trace_upstream": [
                    {
                        "artifact": "ACTIVITIES_TREND",
                        "version": "1.0",
                    }
                ],
            },
            authority=Authority.DERIVED,
            producer_agent="ui_historical_baseline",
            run_id=f"ui_historical_baseline_{run_ts.strftime('%Y%m%dT%H%M%SZ')}",
            update_latest=True,
        )
        st.success("Historical baseline refreshed.")
        set_status(status_state="done", title="Historic Data", message="Baseline refreshed.")
