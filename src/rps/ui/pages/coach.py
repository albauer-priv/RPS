from __future__ import annotations

import os

import streamlit as st

try:
    from rps.ui.rps_chatbot import CustomFunction
except Exception as exc:  # pragma: no cover - UI fallback
    st.error(f"Coach toolkit not available: {exc}")
    st.stop()

from rps.agents.registry import AGENTS
from rps.orchestrator.plan_week import _build_injection_block
from rps.prompts.loader import PromptLoader
from rps.tools.workspace_read_tools import ReadToolContext, read_tool_defs, read_tool_handlers
from rps.ui.rps_chatbot import Chat
from rps.ui.shared import (
    SETTINGS,
    base_runtime,
    get_athlete_id,
    get_iso_year_week,
    init_ui_state,
    ui_log,
)


init_ui_state()
athlete_id = get_athlete_id()
year, _ = get_iso_year_week()

st.title("Coach")
st.caption(f"Athlete: {athlete_id}")

try:
    base = base_runtime()
except RuntimeError as exc:
    st.error(str(exc))
    st.info("Set OPENAI_API_KEY in your environment or .env, then restart the app.")
    st.stop()
vs_id = None
try:
    vs_id = base["vs_resolver"].id_for_store_name(AGENTS["coach"].vector_store_name)
except Exception:
    vs_id = None

ctx = ReadToolContext(
    athlete_id=athlete_id,
    workspace_root=SETTINGS.workspace_root,
)
handlers = read_tool_handlers(ctx)
functions: list[CustomFunction] = []
for spec in read_tool_defs():
    name = spec["name"]
    handler = handlers.get(name)
    if handler is None:
        continue

    def _wrap(h=handler):
        return lambda **kwargs: h(kwargs)

    functions.append(
        CustomFunction(
            name=name,
            description=spec.get("description", ""),
            parameters=spec.get("parameters", {}),
            handler=_wrap(),
        )
    )

prompt_loader = PromptLoader(SETTINGS.prompts_dir)
base_prompt = prompt_loader.combined_system_prompt("coach")
base_prompt = base_prompt.replace("SEASON_BRIEF_YEAR", str(year))
injected = _build_injection_block("coach", mode="coach")

instructions = base_prompt
if injected:
    instructions = f"{base_prompt}\n\n{injected}"

allow_web_search = False
if os.getenv("OPENAI_ENABLE_WEB_SEARCH", "").lower() in {"1", "true", "yes"}:
    agents = {
        a.strip().lower()
        for a in os.getenv("OPENAI_WEB_SEARCH_AGENTS", "").split(",")
        if a.strip()
    }
    allow_web_search = "coach" in agents

model = os.getenv("OPENAI_MODEL_COACH", "gpt-5-mini")
use_background = os.getenv("OPENAI_COACH_BACKGROUND", "").lower() in {"1", "true", "yes"}
poll_interval = os.getenv("OPENAI_COACH_POLL_INTERVAL_SEC")
chat = st.session_state.get("coach_chat")
if chat and not isinstance(chat, Chat):
    st.session_state.pop("coach_chat", None)
    chat = None
if chat and getattr(chat, "model", None) != model:
    st.session_state.pop("coach_chat", None)
if "coach_chat" not in st.session_state:
    chat_kwargs = {
        "model": model,
        "instructions": instructions,
        "functions": functions,
        "vector_store_ids": [vs_id] if vs_id else None,
        "allow_code_interpreter": False,
        "allow_file_search": True,
        "allow_web_search": allow_web_search,
        "allow_image_generation": False,
        "placeholder": "Ask the coach…",
        "auto_compact_turns": 3,
    }
    compact_turns = os.getenv("OPENAI_COACH_COMPACT_TURNS")
    if compact_turns:
        try:
            chat_kwargs["auto_compact_turns"] = int(compact_turns)
        except ValueError:
            pass
    compact_model = os.getenv("OPENAI_COACH_COMPACT_MODEL")
    if compact_model:
        chat_kwargs["compact_model"] = compact_model
    temperature = os.getenv("OPENAI_TEMPERATURE_COACH")
    if temperature and not model.startswith("gpt-5"):
        chat_kwargs["temperature"] = float(temperature)
    st.session_state.coach_chat = Chat(**chat_kwargs)

ui_log(f"Coach initialized with model={model}")

st.session_state.coach_chat.use_background = use_background
if poll_interval:
    try:
        st.session_state.coach_chat.poll_interval_sec = float(poll_interval)
    except ValueError:
        pass

st.session_state.coach_chat.run()
