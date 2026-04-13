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

st.title("About You & Goals")
st.caption(f"Athlete: {athlete_id}")

store = LocalArtifactStore(root=SETTINGS.workspace_root)
store.ensure_workspace(athlete_id)
profile_path = store.latest_path(athlete_id, ArtifactType.ATHLETE_PROFILE)

payload: dict[str, object] = {}
if profile_path.exists():
    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    set_status(status_state="done", title="About You & Goals", message="Ready.")
else:
    set_status(status_state="running", title="About You & Goals", message="Missing profile input.")
render_status_panel()
st.info(
    "Capture your core profile, goals, and constraints here. "
    "These values inform season planning and load estimation."
)

data = payload.get("data", {}) if isinstance(payload, dict) else {}
if not isinstance(data, dict):
    data = {}
profile = data.get("profile") or {}
objectives = data.get("objectives") or {}
constraints = data.get("constraints") or {}
if not isinstance(profile, dict):
    profile = {}
if not isinstance(objectives, dict):
    objectives = {}
if not isinstance(constraints, dict):
    constraints = {}

st.subheader("Athlete Profile")
col_left, col_right = st.columns(2)
with col_left:
    athlete_name = st.text_input("Athlete name", value=profile.get("athlete_name", ""))
    athlete_story = st.text_area("Athlete story", value=profile.get("athlete_story", ""), height=100)
    location_tz = st.text_input("Location time zone", value=profile.get("location_time_zone", ""))
    primary_disciplines = st.text_input(
        "Primary disciplines (comma-separated)",
        value=", ".join(profile.get("primary_disciplines") or []),
    )
    training_age_years = st.number_input(
        "Training age (years)",
        min_value=0,
        step=1,
        value=int(profile.get("training_age_years") or 0),
        format="%d",
    )
with col_right:
    year = st.number_input("Season year", min_value=1900, value=int(profile.get("year") or datetime.now().year))
    age = st.number_input("Age", min_value=0, value=int(profile.get("age") or 0))
    body_mass_kg = st.number_input(
        "Body mass (kg)",
        min_value=0.0,
        step=0.1,
        value=round(float(profile.get("body_mass_kg") or 0.0), 1),
        format="%.1f",
    )
    sex = st.text_input("Sex (optional)", value=profile.get("sex", ""))
    age_group = st.text_input("Age group", value=profile.get("age_group", ""))
    endurance_anchor_w = st.number_input(
        "Endurance anchor (W)",
        min_value=0,
        step=1,
        value=int(profile.get("endurance_anchor_w") or 0),
        format="%d",
    )
    ambition_low = st.number_input(
        "Ambition IF (low)",
        min_value=0.0,
        max_value=2.0,
        value=float((profile.get("ambition_if_range") or [0.0, 0.0])[0]),
    )
    ambition_high = st.number_input(
        "Ambition IF (high)",
        min_value=0.0,
        max_value=2.0,
        value=float((profile.get("ambition_if_range") or [0.0, 0.0])[1]),
    )

st.subheader("Goals")
st.markdown("**Primary objective**")
st.caption("Describe the single most important outcome for the season. Example: Finish 400 km brevet, top 20% age group, steady pacing.")
primary_objective = st.text_area(
    "Primary objective",
    value=objectives.get("primary", ""),
    height=80,
)
st.markdown("**Secondary objectives**")
st.caption("List supporting goals, one per line. Example: Complete two 300 km events; Improve endurance anchor to 240 W.")
secondary_objectives = st.text_area(
    "Secondary objectives (one per line)",
    value="\n".join(objectives.get("secondary") or []),
    height=120,
)
st.markdown("**Goal priority order**")
st.caption("Rank goals from most to least important, one per line. Example: Finish 400 km; Complete 300 km; Maintain 70 kg.")
priority_order = st.text_area(
    "Goal priority order (one per line)",
    value="\n".join(objectives.get("priority_order") or []),
    height=120,
)

st.subheader("Constraints")
st.markdown("**Time constraints**")
st.caption("Training availability and limits. Example: Max 8h/week; no training Tue/Thu evenings.")
time_constraints = st.text_area(
    "Time constraints",
    value=constraints.get("time_constraints", ""),
    height=80,
)
st.markdown("**Environmental constraints**")
st.caption("Weather, terrain, travel, or facility limits. Example: Winter indoor only; no MTB trails.")
environmental_constraints = st.text_area(
    "Environmental constraints",
    value=constraints.get("environmental_constraints", ""),
    height=80,
)
st.markdown("**Injury history**")
st.caption("Relevant injuries and current limitations. Example: Left knee pain in 2024, avoid high-impact running.")
injury_history = st.text_area(
    "Injury history",
    value=constraints.get("injury_history", ""),
    height=80,
)

def _lines_to_list(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]

strengths = st.text_area(
    "Strengths (one per line)",
    value="\n".join(data.get("strengths") or []),
    height=120,
)
st.caption("List performance strengths. Example: High durability base; Strong long-distance pacing.")
limitations = st.text_area(
    "Limitations (one per line)",
    value="\n".join(data.get("limitations") or []),
    height=120,
)
st.caption("List limiting factors to address. Example: Weak climbing; low cadence efficiency.")
risk_flags = st.text_area(
    "Risk flags (one per line)",
    value="\n".join(data.get("risk_flags") or []),
    height=120,
)
st.caption("List risk factors that need monitoring. Example: Masters athlete (50+); history of knee pain.")
success_criteria = st.text_area(
    "Success criteria (one per line)",
    value="\n".join(data.get("success_criteria") or []),
    height=120,
)
st.caption("Define how success is measured. Example: Finish 400 km within time limit; steady power without bonk.")

if st.button("Save Profile & Goals", width="content"):
    run_ts = datetime.now(timezone.utc)
    version_key = run_ts.strftime("%Y%m%d_%H%M%S")
    payload = {
        "profile": {
            "athlete_id": athlete_id,
            "year": int(year),
            "athlete_name": athlete_name,
            "athlete_story": athlete_story,
            "location_time_zone": location_tz,
            "primary_disciplines": _lines_to_list(primary_disciplines.replace(",", "\n")),
            "training_age_years": int(training_age_years),
            "age": int(age),
            "body_mass_kg": round(float(body_mass_kg), 1),
            "sex": sex,
            "age_group": age_group,
            "endurance_anchor_w": int(endurance_anchor_w),
            "ambition_if_range": [ambition_low, ambition_high],
        },
        "objectives": {
            "primary": primary_objective,
            "secondary": _lines_to_list(secondary_objectives),
            "priority_order": _lines_to_list(priority_order),
        },
        "constraints": {
            "time_constraints": time_constraints,
            "environmental_constraints": environmental_constraints,
            "injury_history": injury_history,
        },
        "strengths": _lines_to_list(strengths),
        "limitations": _lines_to_list(limitations),
        "risk_flags": _lines_to_list(risk_flags),
        "success_criteria": _lines_to_list(success_criteria),
        "measurement_assumptions": data.get("measurement_assumptions") or {},
    }
    store.save_version(
        athlete_id,
        ArtifactType.ATHLETE_PROFILE,
        version_key,
        payload,
        payload_meta={
            "schema_id": "AthleteProfileInterface",
            "schema_version": "1.0",
            "version": "1.0",
            "authority": Authority.BINDING.value,
            "owner_agent": "User",
            "scope": "Shared",
            "data_confidence": "USER",
            "created_at": run_ts.isoformat(),
            "notes": "",
        },
        authority=Authority.BINDING,
        producer_agent="ui_athlete_profile",
        run_id=f"ui_athlete_profile_{run_ts.strftime('%Y%m%dT%H%M%SZ')}",
        update_latest=True,
    )
    st.success("Profile & goals saved.")
    set_status(status_state="done", title="About You & Goals", message="Saved profile input.")
