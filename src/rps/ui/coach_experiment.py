"""Deprecated: replaced by pages/coach.py (multipage UI)."""
import os
from pathlib import Path

import streamlit as st

try:
    from rps.ui.rps_chatbot import Chat
except Exception as exc:  # pragma: no cover - UI fallback
    st.error(f"Coach toolkit not available: {exc}")
    st.stop()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_coach_prompt() -> str:
    prompt_path = _repo_root() / "prompts" / "agents" / "coach.md"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return "You are the RPS Coach. Be evidence-based and concise."


def _load_env_if_needed() -> None:
    """Load .env into process env if RPS_LLM_API_KEY is missing."""
    if os.getenv("RPS_LLM_API_KEY"):
        return
    try:
        from rps.core.config import load_env_file

        load_env_file(_repo_root() / ".env")
    except Exception:
        return


def render_coach_experiment() -> None:
    """Render the coach experiment chat using the in-repo Chat."""
    _load_env_if_needed()

    model = os.getenv("RPS_LLM_MODEL_COACH", "gpt-5-mini")
    temperature = os.getenv("RPS_LLM_TEMPERATURE_COACH")
    api_key = os.getenv("RPS_LLM_API_KEY")
    if api_key:
        os.environ["RPS_LLM_API_KEY"] = api_key

    instructions = _load_coach_prompt()
    if "coach_chat" not in st.session_state:
        chat_kwargs = {
            "model": model,
            "instructions": instructions,
            "api_key": api_key,
            "agent_name": "coach",
        }
        if temperature and not model.startswith("gpt-5"):
            chat_kwargs["temperature"] = float(temperature)
        st.session_state.coach_chat = Chat(**chat_kwargs)

    st.session_state.coach_chat.run()
