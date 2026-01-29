from __future__ import annotations

import logging

import streamlit as st

from rps.agents.registry import AGENTS
from rps.agents.runner import AgentRuntime, run_agent_session
from rps.orchestrator.plan_week import _build_injection_block
from rps.ui.shared import (
    SETTINGS,
    announce_log_file,
    append_system_log,
    base_runtime,
    get_athlete_id,
    init_ui_state,
    make_ui_run_id,
)

logger = logging.getLogger("rps.ui.coach")


def _is_no_session_context(exc: BaseException) -> bool:
    name = exc.__class__.__name__.lower()
    msg = str(exc).lower()
    return "nosessioncontext" in name or "nosessioncontext" in msg


def _coach_runtime() -> AgentRuntime:
    base = base_runtime()
    return AgentRuntime(
        client=base["client"],
        model=SETTINGS.model_for_agent("coach"),
        temperature=SETTINGS.temperature_for_agent("coach"),
        reasoning_effort=SETTINGS.reasoning_effort_for_agent("coach"),
        reasoning_summary=SETTINGS.reasoning_summary_for_agent("coach"),
        prompt_loader=base["prompt_loader"],
        vs_resolver=base["vs_resolver"],
    )


def _run_coach(athlete_id: str, text: str, session: dict) -> dict:
    runtime = _coach_runtime()
    spec = AGENTS["coach"]
    injection_text = _build_injection_block("coach", mode="coach")
    run_id = session.get("run_id") or make_ui_run_id("coach")
    session["run_id"] = run_id

    def _call(previous_response_id: str | None) -> dict:
        return run_agent_session(
            runtime,
            agent_name="coach",
            agent_vs_name=spec.vector_store_name,
            athlete_id=athlete_id,
            user_input=text,
            workspace_root=SETTINGS.workspace_root,
            schema_dir=SETTINGS.schema_dir,
            model_override=SETTINGS.model_for_agent("coach"),
            include_debug_file_search=False,
            force_file_search=False,
            max_num_results=SETTINGS.file_search_max_results,
            run_id=run_id,
            previous_response_id=previous_response_id,
            injection_text=injection_text,
        )

    try:
        return _call(session.get("previous_response_id"))
    except Exception as exc:
        if _is_no_session_context(exc):
            session["previous_response_id"] = None
            return _call(None)
        raise


st.set_page_config(
    page_title="RPS - Randonneur Performance System",
    layout="wide",
)

st.title("Coach")

init_ui_state()
athlete_id = get_athlete_id()
announce_log_file(athlete_id)

state = st.session_state["rps_state"]
coach_session = state.setdefault("coach_session", {"previous_response_id": None, "run_id": None})
messages: list[dict] = st.session_state.setdefault("coach_messages", [])

for message in messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask the coach"):
    messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Coach is thinking..."):
            try:
                result = _run_coach(athlete_id, prompt, coach_session)
                reply = result.get("text", "[no response]")
                coach_session["previous_response_id"] = result.get("response_id")
                st.markdown(reply)
                messages.append({"role": "assistant", "content": reply})
                append_system_log("coach", f"Coach replied ({len(reply)} chars).")
            except Exception as exc:  # pragma: no cover - UI guardrail
                logger.exception("Coach run failed")
                st.error(f"Coach failed: {exc}")
