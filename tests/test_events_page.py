from streamlit.testing.v1 import AppTest


def test_events_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/athlete_profile/events.py")
    at.run(timeout=10)
    assert len(at.error) == 0
    labels = {button.label for button in at.button}
    assert "Save Events" in labels
