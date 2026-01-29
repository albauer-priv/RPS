from __future__ import annotations

import base64
import json
import os
import re
import time
from pathlib import Path

import streamlit as st
from streamlit_openai import Chat
from streamlit_openai.chat import DEVELOPER_MESSAGE

from rps.openai.response_utils import extract_text_output

SUMMARY_INSTRUCTIONS = """
- Your task is to provide a very concise summary (four words or fewer in English, or the equivalent in other languages) of the given conversation.
- Do not include periods at the end of the summary.
- Use title case for the summary.
- If the conversation history does not provide enough information to summarize, return "New Chat".
"""


class RPSChat(Chat):
    """Chat wrapper that avoids hard-coded summary model usage."""

    def summarize(self) -> None:
        """Override default summarize to avoid streamlit-openai summary logic."""
        if not getattr(self, "_sections", None):
            self.summary = "New Chat"
            return
        self._update_summary()

    def _update_summary(self) -> None:
        """Update the chat summary using a configurable model."""
        sections = []
        for section in self._sections:
            s = {"role": section.role, "blocks": []}
            for block in section.blocks:
                if block.category in ["text", "code", "reasoning"]:
                    content = block.content
                else:
                    content = "Bytes"
                s["blocks"].append(
                    {
                        "category": block.category,
                        "content": content,
                        "filename": block.filename,
                        "file_id": block.file_id,
                    }
                )
            sections.append(s)

        if not sections:
            self.summary = "New Chat"
            return

        summary_model = os.getenv("OPENAI_MODEL_COACH_SUMMARY", "gpt-5-nano")
        response = self._client.responses.create(
            model=summary_model,
            input=[
                {"role": "developer", "content": SUMMARY_INSTRUCTIONS},
                {"role": "user", "content": json.dumps(sections, indent=2)},
            ],
        )
        self.summary = response.output_text or extract_text_output(response) or "New Chat"

    def respond(self, prompt) -> None:  # noqa: D401 - subclass behavior
        """Sends the user prompt to the assistant and streams the response."""
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
            "instructions": self.instructions,
            "tools": self._tools,
            "previous_response_id": self._previous_response_id,
            "stream": True,
            "reasoning": {"summary": "auto"},
        }
        if self.temperature is not None and not self.model.startswith("gpt-5"):
            response_kwargs["temperature"] = self.temperature

        if getattr(self, "use_background", False):
            response_kwargs.pop("stream", None)
            response_kwargs["background"] = True
            response = self._client.responses.create(**response_kwargs)
            status_box = st.status("Running...", expanded=True)
            status_box.write(f"Current status: {response.status}")
            while response.status in {"queued", "in_progress"}:
                time.sleep(getattr(self, "poll_interval_sec", 2))
                response = self._client.responses.retrieve(response.id)
                status_box.write(f"Current status: {response.status}")
            status_box.update(
                label=f"Finished: {response.status}",
                state="complete" if response.status == "completed" else "error",
            )
            final_text = response.output_text or extract_text_output(response) or ""
            if final_text:
                self.last_section.update_and_stream("text", final_text)
            self._input = []
            return

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
