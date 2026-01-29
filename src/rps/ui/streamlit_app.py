from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="RPS - Randonneur Performance System", layout="wide")

home = st.Page("pages/home.py", title="Home", icon=":material/home:", default=True)
coach = st.Page("pages/coach.py", title="Coach", icon=":material/support_agent:")

performance_data = st.Page(
    "pages/performance/data_metrics.py",
    title="Data & Metrics",
    icon=":material/insights:",
)
performance_report = st.Page(
    "pages/performance/report.py",
    title="Report",
    icon=":material/assignment:",
)

plan_season = st.Page(
    "pages/plan/season.py",
    title="Season",
    icon=":material/emoji_events:",
)
plan_phase = st.Page(
    "pages/plan/phase.py",
    title="Phase",
    icon=":material/timeline:",
)
plan_week = st.Page(
    "pages/plan/week.py",
    title="Week",
    icon=":material/calendar_month:",
)
plan_wow = st.Page(
    "pages/plan/wow.py",
    title="WoW",
    icon=":material/fitness_center:",
)

about_you = st.Page(
    "pages/athlete_profile/about_you.py",
    title="About You",
    icon=":material/person:",
)
season_brief = st.Page(
    "pages/athlete_profile/season_brief.py",
    title="Season Brief",
    icon=":material/article:",
)
availability = st.Page(
    "pages/athlete_profile/availability.py",
    title="Availability",
    icon=":material/event_available:",
)
logistics = st.Page(
    "pages/athlete_profile/logistics.py",
    title="Logistics",
    icon=":material/local_shipping:",
)

pg = st.navigation(
    [
        home,
        coach,
        {"Performance": [performance_data, performance_report]},
        {"Plan": [plan_season, plan_phase, plan_week, plan_wow]},
        {"Athlete Profile": [about_you, season_brief, availability, logistics]},
    ]
)
pg.run()
