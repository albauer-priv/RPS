from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="RPS - Randonneur Performance System",
    layout="wide",
)

home = st.Page("pages/home.py", title="Home", icon=":material/home:", default=True)
coach = st.Page("pages/coach.py", title="Coach", icon=":material/support_agent:")
analyse = st.Page("pages/analysis.py", title="Analyse", icon=":material/insights:")
plan = st.Page("pages/plan.py", title="Plan", icon=":material/calendar_month:")

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
    {
        "Main": [home, coach, analyse, plan],
        "Athlete Profile": [about_you, season_brief, availability, logistics],
    }
)
pg.run()
