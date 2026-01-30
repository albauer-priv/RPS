import pytest
from streamlit.testing.v1 import AppTest


@pytest.fixture(autouse=True)
def _env_setup(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")


def test_coach_summary_above_input(monkeypatch):
    import rps.ui.rps_chatbot as rps_chatbot

    def _noop_summarize(self) -> None:
        self.summary = self.summary or "New Chat"

    monkeypatch.setattr(rps_chatbot.Chat, "summarize", _noop_summarize)

    at = AppTest.from_file("src/rps/ui/pages/coach.py")
    at.run()

    assert len(at.error) == 0
    assert len(at.chat_input) == 1
    assert len(at.info) >= 1

    summary_info = None
    for info in at.info:
        if info.value.startswith("Summary:"):
            summary_info = info
            break
    assert summary_info is not None

    info_index = next(idx for idx, node in enumerate(list(at)) if node is summary_info)
    chat_index = next(idx for idx, node in enumerate(list(at)) if node.type == "chat_input")
    assert info_index < chat_index
