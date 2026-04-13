from __future__ import annotations

import json
import os

import streamlit as st

try:
    from rps.ui.rps_chatbot import CustomFunction
except Exception as exc:  # pragma: no cover - UI fallback
    st.error(f"Coach toolkit not available: {exc}")
    st.stop()

from rps.agents.registry import AGENTS
from rps.agents.knowledge_injection import build_injection_block
from rps.prompts.loader import PromptLoader
from rps.tools.workspace_read_tools import ReadToolContext, read_tool_defs, read_tool_handlers
from rps.ui.rps_chatbot import Chat
from rps.ui.shared import (
    SETTINGS,
    base_runtime,
    get_athlete_id,
    get_iso_year_week,
    init_ui_state,
    render_status_panel,
    set_status,
    ui_log,
)


init_ui_state()
athlete_id = get_athlete_id()
year, _ = get_iso_year_week()

st.title("Coach")
st.caption(f"Athlete: {athlete_id}")
set_status(status_state="done", title="Coach", message="Ready.")
render_status_panel()

try:
    base = base_runtime()
except RuntimeError as exc:
    st.error(str(exc))
    st.info("Set RPS_LLM_API_KEY in your environment or .env, then restart the app.")
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
injected = build_injection_block("coach", mode="coach")

instructions = base_prompt
if injected:
    instructions = f"{base_prompt}\n\n{injected}"

preload_enabled = os.getenv("RPS_COACH_PRELOAD_ARTIFACTS", "1").lower() in {"1", "true", "yes"}
if preload_enabled:
    per_artifact_max = int(os.getenv("RPS_COACH_PRELOAD_MAX_CHARS", "12000"))
    context_chunks: list[str] = []

    def _stringify(value: object) -> str:
        text = json.dumps(value, ensure_ascii=False)
        if len(text) > per_artifact_max:
            return text[:per_artifact_max] + "...(truncated)"
        return text

    def _append_context(label: str, fn, args: dict[str, object]) -> None:
        try:
            result = fn(args)
        except Exception as exc:
            result = {"ok": False, "error": str(exc)}
        context_chunks.append(f"{label}:\n{_stringify(result)}")

    _append_context("athlete_profile", handlers["workspace_get_input"], {"input_type": "athlete_profile"})
    _append_context("planning_events", handlers["workspace_get_input"], {"input_type": "planning_events"})
    _append_context("logistics", handlers["workspace_get_input"], {"input_type": "logistics"})
    _append_context("availability", handlers["workspace_get_input"], {"input_type": "availability"})
    _append_context("activities_trend", handlers["workspace_get_latest"], {"artifact_type": "ACTIVITIES_TREND"})
    _append_context("activities_actual", handlers["workspace_get_latest"], {"artifact_type": "ACTIVITIES_ACTUAL"})
    _append_context("season_plan", handlers["workspace_get_latest"], {"artifact_type": "SEASON_PLAN"})
    _append_context("phase_preview", handlers["workspace_get_latest"], {"artifact_type": "PHASE_PREVIEW"})
    _append_context("phase_guardrails", handlers["workspace_get_latest"], {"artifact_type": "PHASE_GUARDRAILS"})
    _append_context("kpi_profile", handlers["workspace_get_latest"], {"artifact_type": "KPI_PROFILE"})
    _append_context("zone_model", handlers["workspace_get_latest"], {"artifact_type": "ZONE_MODEL"})
    _append_context("wellness", handlers["workspace_get_latest"], {"artifact_type": "WELLNESS"})

    if context_chunks:
        instructions = (
            f"{instructions}\n\n"
            "Workspace artifacts (auto-loaded). Use these instead of asking for missing artifacts:\n"
            + "\n\n".join(context_chunks)
        )

allow_web_search = False
if os.getenv("RPS_LLM_ENABLE_WEB_SEARCH", "").lower() in {"1", "true", "yes"}:
    agents = {
        a.strip().lower()
        for a in os.getenv("RPS_LLM_WEB_SEARCH_AGENTS", "").split(",")
        if a.strip()
    }
    allow_web_search = "coach" in agents

model = os.getenv("RPS_LLM_MODEL_COACH", "gpt-5-mini")
use_background = os.getenv("RPS_LLM_COACH_BACKGROUND", "").lower() in {"1", "true", "yes"}
poll_interval = os.getenv("RPS_LLM_COACH_POLL_INTERVAL_SEC")
base_url = os.getenv("RPS_LLM_BASE_URL_COACH") or os.getenv("RPS_LLM_BASE_URL")
key_hint = "set" if os.getenv("RPS_LLM_API_KEY_COACH") or os.getenv("RPS_LLM_API_KEY") else "missing"
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
        "vector_store_ids": None,
        "allow_code_interpreter": False,
        "allow_file_search": False,
        "allow_web_search": allow_web_search,
        "allow_image_generation": False,
        "placeholder": "Ask the coach…",
        "auto_compact_turns": 3,
        "agent_name": "coach",
    }
    compact_turns = os.getenv("RPS_LLM_COACH_COMPACT_TURNS")
    if compact_turns:
        try:
            chat_kwargs["auto_compact_turns"] = int(compact_turns)
        except ValueError:
            pass
    compact_model = os.getenv("RPS_LLM_COACH_COMPACT_MODEL")
    if compact_model:
        chat_kwargs["compact_model"] = compact_model
    temperature = os.getenv("RPS_LLM_TEMPERATURE_COACH")
    if temperature and not model.startswith("gpt-5"):
        chat_kwargs["temperature"] = float(temperature)
    st.session_state.coach_chat = Chat(**chat_kwargs)

ui_log(
    f"Coach initialized with model={model} base_url={base_url or 'default'} api_key={key_hint}"
)

st.session_state.coach_chat.use_background = use_background
if poll_interval:
    try:
        st.session_state.coach_chat.poll_interval_sec = float(poll_interval)
    except ValueError:
        pass

st.session_state.coach_chat.run()
