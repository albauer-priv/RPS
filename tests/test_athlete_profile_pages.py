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
        at.run()
        assert len(at.error) == 0
