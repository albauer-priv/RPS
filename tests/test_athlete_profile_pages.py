from streamlit.testing.v1 import AppTest


def test_athlete_profile_pages_render():
    pages = [
        "src/rps/ui/pages/athlete_profile/about_you.py",
        "src/rps/ui/pages/athlete_profile/availability.py",
        "src/rps/ui/pages/athlete_profile/events.py",
        "src/rps/ui/pages/athlete_profile/logistics.py",
        "src/rps/ui/pages/athlete_profile/historic_data.py",
    ]
    for page in pages:
        at = AppTest.from_file(page)
        at.run(timeout=10)
        assert len(at.error) == 0
        if page.endswith("about_you.py"):
            assert any(button.label == "Save Profile & Goals" for button in at.button)
        if page.endswith("events.py"):
            assert any(button.label == "Save Events" for button in at.button)
        if page.endswith("logistics.py"):
            assert any(button.label == "Save Logistics" for button in at.button)
        if page.endswith("historic_data.py"):
            assert any(button.label == "Refresh Historical Baseline" for button in at.button)
