from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path

import streamlit as st

try:
    from streamlit_openai import Chat
    from streamlit_openai.chat import DEVELOPER_MESSAGE
    from streamlit_openai.utils import CustomFunction
except Exception as exc:  # pragma: no cover - UI fallback
    st.error(f"streamlit-openai not available: {exc}")
    st.stop()

from rps.agents.registry import AGENTS
from rps.orchestrator.plan_week import _build_injection_block
from rps.prompts.loader import PromptLoader
from rps.tools.workspace_read_tools import ReadToolContext, read_tool_defs, read_tool_handlers
from rps.ui.shared import SETTINGS, base_runtime, get_athlete_id, get_iso_year_week, init_ui_state


class RPSChat(Chat):
    """Chat wrapper that omits unsupported params for GPT-5 models."""

    def respond(self, prompt) -> None:  # noqa: D401 - subclass behavior
        self._input.append({"role": "user", "content": prompt})
        self.add_section("assistant")

        if self.allow_code_interpreter:
            result = self._client.containers.retrieve(container_id=self._container_id)
            if result.status == "expired":
                container = self._client.containers.create(name="streamlit-openai")
                self._container_id = container.id
                for tracked_file in self._tracked_files:
                    if tracked_file._is_container_file:
                        self._client.containers.files.create(
                            container_id=self._container_id,
                            file_id=tracked_file._openai_file.id,
                        )
            for tool in self._tools:
                if tool["type"] == "code_interpreter":
                    tool["container"] = self._container_id

        response_kwargs = {
            "model": self.model,
            "input": self._input,
            "instructions": DEVELOPER_MESSAGE + self.instructions,
            "tools": self._tools,
            "previous_response_id": self._previous_response_id,
            "stream": True,
            "reasoning": {"summary": "auto"},
        }
        if self.temperature is not None and not self.model.startswith("gpt-5"):
            response_kwargs["temperature"] = self.temperature

        events1 = self._client.responses.create(**response_kwargs)
        self._input = []
        tool_calls = {}
        for event1 in events1:
            if event1.type == "response.completed":
                self._previous_response_id = event1.response.id
                self.input_tokens += event1.response.usage.input_tokens
                self.output_tokens += event1.response.usage.output_tokens
            elif event1.type == "response.output_text.delta":
                self.last_section.update_and_stream("text", event1.delta)
                self.last_section.last_block.content = re.sub(
                    r"!?\[([^\]]+)\]\(sandbox:/mnt/data/([^\)]+)\)",
                    r"\1 (`\2`)",
                    self.last_section.last_block.content,
                )
            elif event1.type == "response.code_interpreter_call_code.delta":
                self.last_section.update_and_stream("code", event1.delta)
            elif event1.type == "response.output_item.done" and event1.item.type == "function_call":
                tool_calls[event1.item.name] = event1
            elif event1.type == "response.reasoning_summary_text.delta":
                self.last_section.update_and_stream("reasoning", event1.delta)
            elif event1.type == "response.reasoning_summary_text.done":
                self.last_section.last_block.content += "\n\n"
            elif event1.type == "response.image_generation_call.partial_image":
                self.last_section.update_and_stream(
                    "generated_image",
                    base64.b64decode(event1.partial_image_b64),
                    filename=f"{event1.item_id}.{event1.output_format}",
                    file_id=event1.item_id,
                )
            elif event1.type == "response.output_text.annotation.added":
                if event1.annotation["type"] == "file_citation":
                    pass
                elif event1.annotation["type"] == "container_file_citation":
                    if event1.annotation["file_id"] in event1.annotation["filename"]:
                        if Path(event1.annotation["filename"]).suffix in [".png", ".jpg", ".jpeg"]:
                            image_content = self._client.containers.files.content.retrieve(
                                file_id=event1.annotation["file_id"],
                                container_id=self._container_id,
                            )
                            self.last_section.update_and_stream(
                                "image",
                                image_content.read(),
                                filename=event1.annotation["filename"],
                                file_id=event1.annotation["file_id"],
                            )
                    else:
                        cfile_content = self._client.containers.files.content.retrieve(
                            file_id=event1.annotation["file_id"],
                            container_id=self._container_id,
                        )
                        self.last_section.update_and_stream(
                            "download",
                            cfile_content.read(),
                            filename=event1.annotation["filename"],
                            file_id=event1.annotation["file_id"],
                        )

        if tool_calls:
            for tool in tool_calls:
                function = [x for x in self.functions if x.name == tool][0]
                result = function.handler(**json.loads(tool_calls[tool].item.arguments))
                self._input.append(
                    {
                        "type": "function_call_output",
                        "call_id": tool_calls[tool].item.call_id,
                        "output": str(result),
                    }
                )
            response_kwargs.pop("reasoning", None)
            events2 = self._client.responses.create(**response_kwargs)
            self._input = []
            for event2 in events2:
                if event2.type == "response.completed":
                    self._previous_response_id = event2.response.id
                elif event2.type == "response.output_text.delta":
                    self.last_section.update_and_stream("text", event2.delta)


init_ui_state()
athlete_id = get_athlete_id()
year, _ = get_iso_year_week()

st.title("Coach")
st.caption(f"Athlete: {athlete_id}")

base = base_runtime()
vs_id = None
try:
    vs_id = base["vs_resolver"].id_for_store_name(AGENTS["coach"].vector_store_name)
except Exception:
    vs_id = None

ctx = ReadToolContext(
    athlete_id=athlete_id,
    workspace_root=SETTINGS.workspace_root,
    schema_dir=SETTINGS.schema_dir,
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
    }
    temperature = os.getenv("OPENAI_TEMPERATURE_COACH")
    if temperature and not model.startswith("gpt-5"):
        chat_kwargs["temperature"] = float(temperature)
    st.session_state.coach_chat = RPSChat(**chat_kwargs)

st.session_state.coach_chat.run()
