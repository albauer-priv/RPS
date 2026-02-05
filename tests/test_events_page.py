from streamlit.testing.v1 import AppTest


def test_events_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/athlete_profile/events.py")
    at.run()
    assert len(at.error) == 0
    assert any(button.label == "Save Events" for button in at.button)
