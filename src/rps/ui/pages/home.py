from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import streamlit as st

from rps.ui.shared import (
    SETTINGS,
    announce_log_file,
    athlete_phase_card,
    get_athlete_id,
    get_iso_year_week,
    init_ui_state,
    render_global_sidebar,
    render_status_panel,
    set_status,
    system_log_panel,
)
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType

ROOT = Path(__file__).resolve().parents[4]
MARKETING_PATH = ROOT / "static" / "marketing" / "home.md"


@st.cache_data(show_spinner=False)
def _load_marketing_text(path: Path) -> str:
    if not path.exists():
        return "Welcome to RPS."
    return path.read_text(encoding="utf-8")


def _latest_input(inputs_dir: Path, prefix: str) -> Path | None:
    if not inputs_dir.exists():
        return None
    matches = sorted(
        list(inputs_dir.glob(f"{prefix}*.json")) + list(inputs_dir.glob(f"{prefix}*.md")),
        key=lambda p: p.stat().st_mtime,
    )
    return matches[-1] if matches else None


def _artifact_status_rows(store: LocalArtifactStore, athlete_id: str) -> list[dict[str, str]]:
    inputs_dir = SETTINGS.workspace_root / athlete_id / "inputs"
    items = [
        ("About You & Goals", "User", "Profile, goals, constraints.", ArtifactType.ATHLETE_PROFILE),
        ("Availability", "User", "Weekly availability table.", ArtifactType.AVAILABILITY),
        ("Events", "User", "A/B/C planning events.", ArtifactType.PLANNING_EVENTS),
        ("Logistics", "User", "Context events (travel/work/weather).", ArtifactType.LOGISTICS),
        ("Historic Data", "System", "Intervals-aggregated baseline.", ArtifactType.HISTORICAL_BASELINE),
        ("KPI Profile", "User", "Performance KPIs and targets.", ArtifactType.KPI_PROFILE),
        ("Season Scenarios", "Agent", "Alternative season strategies.", ArtifactType.SEASON_SCENARIOS),
        ("Scenario Selection", "User", "Chosen scenario + rationale.", ArtifactType.SEASON_SCENARIO_SELECTION),
        ("Season Plan", "Agent", "Phase-level season plan.", ArtifactType.SEASON_PLAN),
        ("Phase Preview", "Agent", "Phase narrative + weekly previews.", ArtifactType.PHASE_PREVIEW),
        ("Week Plan", "Agent", "Structured weekly workouts.", ArtifactType.WEEK_PLAN),
        ("Zones", "Intervals", "Training zones model.", ArtifactType.ZONE_MODEL),
        ("Intervals Workouts", "Intervals", "Exported workouts for Intervals.", ArtifactType.INTERVALS_WORKOUTS),
        ("Activities Trend", "Intervals", "Weekly trend rollups.", ArtifactType.ACTIVITIES_TREND),
        ("Activities Actual", "Intervals", "Actual workouts and metrics.", ArtifactType.ACTIVITIES_ACTUAL),
        ("DES Report", "Agent", "Durability/efficiency analysis report.", ArtifactType.DES_ANALYSIS_REPORT),
    ]
    rows: list[dict[str, str]] = []
    for label, owner, description, source in items:
        if isinstance(source, ArtifactType):
            path = store.latest_path(athlete_id, source)
            validity = "—"
            if path.exists():
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    if isinstance(payload, dict):
                        meta = payload.get("meta") or {}
                        validity = meta.get("iso_week_range") or meta.get("iso_week") or "—"
                except json.JSONDecodeError:
                    validity = "—"
        else:
            key = str(source).split(":", maxsplit=1)[-1]
            path = _latest_input(inputs_dir, key) or Path()
            validity = "—"
        exists = path.exists()
        updated_at = "—"
        if exists:
            ts = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            updated_at = ts.strftime("%Y-%m-%d %H:%M UTC")
        rows.append(
            {
                "Artifact": label,
                "Owner": owner,
                "Description": description,
                "Validity (ISO)": validity,
                "Status": "OK" if exists else "X",
                "Last updated": updated_at,
            }
        )
    return rows

st.title("RPS - Randonneur Performance System")
st.caption("Chat-style control surface for preflight, season-plan, and plan-week flows.")

init_ui_state()
render_global_sidebar()
athlete_id = get_athlete_id()
year, week = get_iso_year_week()
announce_log_file(athlete_id)

set_status(status_state="done", title="Home", message="Ready.")
render_status_panel()

marketing_text = _load_marketing_text(MARKETING_PATH)
st.markdown(marketing_text)

store = LocalArtifactStore(root=SETTINGS.workspace_root)
status_rows = _artifact_status_rows(store, athlete_id)
st.table(status_rows)

athlete_phase_card(athlete_id, year, week)
