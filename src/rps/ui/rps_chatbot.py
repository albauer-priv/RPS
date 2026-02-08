from __future__ import annotations

import base64
import json
import logging
import os
import re
import shutil
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional, Union

import openai
import streamlit as st
try:
    import tiktoken
except Exception:  # pragma: no cover - optional dependency
    tiktoken = None
from streamlit.runtime.uploaded_file_manager import UploadedFile

from rps.openai.response_utils import extract_text_output
from rps.openai.client import get_client
LOGGER = logging.getLogger(__name__)
CHAT_HISTORY_INSTRUCTIONS = """
- This conversation was loaded from a chat history file.
- All input files uploaded so far were actually provided previously, so you should not treat them as new uploads.
"""

CODE_INTERPRETER_EXTENSIONS = [
    ".c", ".cs", ".cpp", ".csv", ".doc", ".docx", ".html", 
    ".java", ".json", ".md", ".pdf", ".php", ".pptx", ".py", 
    ".rb", ".tex", ".txt", ".css", ".js", ".sh", ".ts", ".csv", 
    ".jpeg", ".jpg", ".gif", ".pkl", ".png", ".tar", ".xlsx", 
    ".xml", ".zip"
]

FILE_SEARCH_EXTENSIONS = [
    ".c", ".cpp", ".cs", ".css", ".doc", ".docx", ".go", 
    ".html", ".java", ".js", ".json", ".md", ".pdf", ".php", 
    ".pptx", ".py", ".rb", ".sh", ".tex", ".ts", ".txt"
]

VISION_EXTENSIONS = [".png", ".jpeg", ".jpg", ".webp", ".gif"]

MIME_TYPES = {
    "txt" : "text/plain",
    "csv" : "text/csv",
    "tsv" : "text/tab-separated-values",
    "html": "text/html",
    "yaml": "text/yaml",
    "md"  : "text/markdown",
    "png" : "image/png",
    "jpg" : "image/jpeg",
    "jpeg": "image/jpeg",
    "gif" : "image/gif",
    "xml" : "application/xml",
    "json": "application/json",
    "pdf" : "application/pdf",
    "zip" : "application/zip",
    "tar" : "application/x-tar",
    "gz"  : "application/gzip",
    "xls" : "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "doc" : "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "ppt" : "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}

SUMMARY_INSTRUCTIONS = """
- Your task is to provide a very concise summary (four words or fewer in English, or the equivalent in other languages) of the given conversation.
- Do not include periods at the end of the summary.
- Use title case for the summary.
- If the conversation history does not provide enough information to summarize, return "New Chat".
"""

logger = logging.getLogger(__name__)

MODEL_LIMITS = [
    ("gpt-5-mini", {"context_window": 400_000, "max_output_tokens": 128_000}),
    ("gpt-5-nano", {"context_window": 400_000, "max_output_tokens": 128_000}),
    ("gpt-5", {"context_window": 400_000, "max_output_tokens": 128_000}),
]
CONSERVATIVE_CONTEXT_FRACTION = 0.9


class CustomFunction:
    """Represents a custom function that can be invoked by the OpenAI API."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable[..., Any],
    ) -> None:
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler

    def __repr__(self) -> str:
        return f"CustomFunction(name='{self.name}')"


class RemoteMCP:
    """Represents a remote MCP server that can be used to perform tasks."""

    def __init__(
        self,
        server_label: str,
        server_url: str,
        require_approval: str = "never",
        headers: Optional[Dict[str, Any]] = None,
        allowed_tools: Optional[List[str]] = None,
    ) -> None:
        self.server_label = server_label
        self.server_url = server_url
        self.require_approval = require_approval
        self.headers = headers
        self.allowed_tools = allowed_tools

    def __repr__(self) -> str:
        return f"RemoteMCP(server_label='{self.server_label}')"

class Chat():
    """A Streamlit-based chat interface powered by OpenAI's Responses API."""
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = "gpt-4o",
        instructions: Optional[str] = None,
        temperature: Optional[float] = 1.0,
        accept_file: Union[bool, Literal["multiple"]] = "multiple",
        uploaded_files: Optional[List[str]] = None,
        functions: Optional[List[CustomFunction]] = None,
        mcps: Optional[List[RemoteMCP]] = None,
        user_avatar: Optional[str] = None,
        assistant_avatar: Optional[str] = None,
        placeholder: Optional[str] = "Your message",
        welcome_message: Optional[str] = None,
        example_messages: Optional[List[dict]] = None,
        info_message: Optional[str] = None,
        vector_store_ids: Optional[List[str]] = None,
        allow_code_interpreter: Optional[bool] = True,
        allow_file_search: Optional[bool] = True,
        allow_web_search: Optional[bool] = True,
        allow_image_generation: Optional[bool] = True,
        auto_compact_turns: Optional[int] = None,
        compact_model: Optional[str] = None,
        agent_name: Optional[str] = None,
    ) -> None:
        """
        Initializes a Chat instance.

        Args:
            api_key (str): API key for the LLM provider. If not provided, fetched from environment variable `RPS_LLM_API_KEY`.
            model (str): The model ID to use (default: "gpt-4o").
            instructions (str): Instructions for the assistant.
            temperature (float): Sampling temperature for the model (default: 1.0).
            accept_file (bool or str): Whether the chat input should accept files (True, False, or "multiple") (default: "multiple").
            uploaded_files (list): List of files to be uploaded to the assistant during initialization.
            functions (list): List of custom functions to be attached to the assistant.
            mcps (list): List of RemoteMCP objects for using remote Model Context Protocol (MPC) servers.
            user_avatar (str): An emoji, image URL, or file path that represents the user.
            assistant_avatar (str): An emoji, image URL, or file path that represents the assistant.
            placeholder (str): Placeholder text for the chat input box (default: "Your message").
            welcome_message (str): Welcome message from the assistant.
            example_messages (list): List of example messages for the user to choose from.
            info_message (str): Information message to be displayed in the chat. This message is constantly displayed at the top of the chat interface.
            vector_store_ids (list): List of vector store IDs for file search. Only used if file search is enabled. Maximum of two vector stores allowed.
            allow_code_interpreter (bool): Whether to allow code interpreter functionality (default: True).
            allow_file_search (bool): Whether to allow file search functionality (default: True).
            allow_web_search (bool): Whether to allow web search functionality (default: True).
            allow_image_generation (bool): Whether to allow image generation functionality (default: True).
            agent_name (str): Optional agent identifier for per-agent LLM config overrides.
        """
        self.api_key = os.getenv("RPS_LLM_API_KEY") if api_key is None else api_key
        self.model = model
        self.instructions = "" if instructions is None else instructions
        self.temperature = temperature
        self.accept_file = accept_file
        self.uploaded_files = uploaded_files
        self.functions = functions
        self.mcps = mcps
        self.user_avatar = user_avatar
        self.assistant_avatar = assistant_avatar
        self.placeholder = placeholder
        self.welcome_message = welcome_message
        self.example_messages = example_messages
        self.info_message = info_message
        self.vector_store_ids = vector_store_ids
        self.allow_code_interpreter = allow_code_interpreter
        self.allow_file_search = allow_file_search
        self.allow_web_search = allow_web_search
        self.allow_image_generation = allow_image_generation
        self.auto_compact_turns = auto_compact_turns
        self.compact_model = compact_model
        self.summary = "New Chat"
        self.input_tokens = 0
        self.output_tokens = 0
        if api_key:
            os.environ["RPS_LLM_API_KEY"] = api_key
        self._client = get_client(agent_name)
        self._temp_dir = tempfile.TemporaryDirectory()
        self._selected_example = None
        self._input = []
        self._tools = []
        self._previous_response_id = None
        self._container_id = None
        self._sections = []
        self._static_files = []
        self._tracked_files = []
        self._download_button_key = 0
        self._dynamic_vector_store = None
        self._conversation_items = []
        self._turn_count = 0
        self._last_compact_turn = 0

        if self.allow_web_search:
            self._tools.append({"type": "web_search"})

        if self.allow_image_generation:
            self._tools.append({"type": "image_generation", "partial_images": 3})

        if self.allow_code_interpreter:
            container = self._client.containers.create(name="streamlit-openai")
            self._container_id = container.id
            self._tools.append({"type": "code_interpreter", "container": self._container_id})

        if self.functions is not None:
            for function in self.functions:
                self._tools.append({
                    "type": "function",
                    "name": function.name,
                    "description": function.description,
                    "parameters": function.parameters,
                })

        if self.mcps is not None:
            for mcp in self.mcps:
                self._tools.append({
                    "type": "mcp",
                    "server_label": mcp.server_label,
                    "server_url": mcp.server_url,
                    "require_approval": mcp.require_approval,
                    "headers": mcp.headers,
                    "allowed_tools": mcp.allowed_tools,
                })

        # File search currently allows a maximum of two vector stores
        if allow_file_search and self.vector_store_ids is not None:
            self._tools.append({
                "type": "file_search",
                "vector_store_ids": self.vector_store_ids
            })

        # If a welcome message is provided, add it to the chat history
        if self.welcome_message is not None:
            self._input.append({"role": "assistant", "content": self.welcome_message})
            self.add_section(
                "assistant",
                blocks=[self.create_block("text", self.welcome_message)]
            )

        # If files are uploaded statically, create tracked files for them
        if self.uploaded_files is not None:
            for uploaded_file in self.uploaded_files:
                shutil.copy(uploaded_file, self._temp_dir.name)
                self.track(os.path.join(self._temp_dir.name, os.path.basename(uploaded_file)))
                self._static_files.append(self._tracked_files[-1])

    @property
    def last_section(self) -> Optional["Section"]:
        """Returns the last section of the chat."""
        return self._sections[-1] if self._sections else None

    def summarize(self) -> None:
        """Update the chat summary."""
        sections = []
        for section in self._sections:
            s = {"role": section.role, "blocks": []}
            if not section.blocks:
                continue
            for block in section.blocks:
                if block.category in ["text", "code", "reasoning"]:
                    content = block.content
                else:
                    content = "Bytes"
                s["blocks"].append({
                    "category": block.category,
                    "content": content,
                    "filename": block.filename,
                    "file_id": block.file_id
                })
            sections.append(s)
        if sections:
            summary_model = (
                os.getenv("RPS_LLM_MODEL_COACH_SUMMARY")
                or os.getenv("RPS_LLM_MODEL_SUMMARY")
                or self.model
            )
            response = self._client.responses.create(
                model=summary_model,
                input=[
                    {"role": "developer", "content": SUMMARY_INSTRUCTIONS},
                    {"role": "user", "content": json.dumps(sections, indent=2)},
                ],
            )
            self.summary = response.output_text or extract_text_output(response) or "New Chat"

    def _get_model_limits(self, model: str) -> Optional[Dict[str, int]]:
        """Return context/max-output limits for a model prefix."""
        for prefix, limits in MODEL_LIMITS:
            if model.startswith(prefix):
                return limits
        return None

    def _estimate_tokens(self, text: str, model: str) -> int:
        """Estimate token count using tiktoken for a given model."""
        if tiktoken is None:
            # Fallback heuristic: ~4 chars per token
            return max(1, len(text) // 4)
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("o200k_base")
        return len(encoding.encode(text))

    def _estimate_items_tokens(self, items: List[Any]) -> int:
        """Estimate tokens for items by encoding a compact JSON string."""
        payload = json.dumps(items, ensure_ascii=True, separators=(",", ":"), default=str)
        return self._estimate_tokens(payload, self.model)

    def _truncate_conversation_items(self, max_input_tokens: int) -> None:
        """
        Drop oldest conversation items until the token estimate fits the budget.

        Side effects:
            - Mutates self._conversation_items.
        """
        if max_input_tokens <= 0:
            self._conversation_items = []
            return
        while self._conversation_items:
            pending_items = self._conversation_items + self._input
            if self._estimate_items_tokens(pending_items) <= max_input_tokens:
                return
            self._conversation_items.pop(0)
        logger.warning("Token budget still exceeded after truncation.")

    def _ensure_token_budget(self) -> None:
        """
        Ensure that input + reserved output tokens fit within model limits.

        Uses compaction first, then truncates oldest conversation items as needed.
        """
        if tiktoken is None:
            logger.warning("tiktoken not available; skipping token budget checks.")
            return
        limits = self._get_model_limits(self.model)
        if not limits:
            return
        reserved_output = limits["max_output_tokens"]
        context_budget = int(limits["context_window"] * CONSERVATIVE_CONTEXT_FRACTION)
        pending_items = self._conversation_items + self._input
        input_tokens = self._estimate_items_tokens(pending_items)
        if input_tokens + reserved_output <= context_budget:
            return
        logger.info("Token budget exceeded; running compaction.")
        self._compact_conversation()
        pending_items = self._conversation_items + self._input
        input_tokens = self._estimate_items_tokens(pending_items)
        if input_tokens + reserved_output <= context_budget:
            return
        logger.warning("Compaction insufficient; truncating conversation items.")
        self._truncate_conversation_items(context_budget - reserved_output)

    def _normalize_items(self, items: List[Any]) -> List[Dict[str, Any]]:
        """Normalize SDK items to dicts for Responses API input."""
        normalized = []
        for item in items:
            if hasattr(item, "model_dump"):
                data = item.model_dump()
            elif isinstance(item, dict):
                data = item
            else:
                data = item
            if isinstance(data, dict) and "status" in data:
                data = {k: v for k, v in data.items() if k != "status"}
            if isinstance(data, dict) and data.get("type") == "function_call_output":
                continue
            normalized.append(data)
        return normalized

    def _message_items(self, items: List[Any]) -> List[Dict[str, Any]]:
        """Return only message-style items (role + content)."""
        messages = []
        for item in items:
            if isinstance(item, dict) and "role" in item and "content" in item:
                messages.append(self._strip_content_annotations(item))
        return messages

    def _strip_content_annotations(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Remove unsupported fields from message content blocks."""
        content = message.get("content")
        if isinstance(content, list):
            cleaned_blocks = []
            for block in content:
                if isinstance(block, dict):
                    for key in ("annotations", "logprobs"):
                        if key in block:
                            block = {k: v for k, v in block.items() if k != key}
                cleaned_blocks.append(block)
            message = {**message, "content": cleaned_blocks}
        return message

    def _compact_conversation(self) -> None:
        """
        Run a Responses API compaction pass and replace conversation items.

        Side effects:
            - Updates self._conversation_items in place.
            - Advances self._last_compact_turn when successful.
        """
        if not self._conversation_items:
            return
        compact_input = self._message_items(self._conversation_items)
        compacted = self._client.responses.compact(
            model=self.compact_model or self.model,
            input=compact_input,
            instructions=self.instructions,
        )
        output = getattr(compacted, "output", None)
        if output is None and isinstance(compacted, dict):
            output = compacted.get("output")
        if output:
            self._conversation_items = self._normalize_items(list(output))
            self._last_compact_turn = self._turn_count

    def _maybe_compact(self) -> None:
        """
        Compact the conversation when auto-compaction thresholds are met.

        Uses the Responses API /responses/compact endpoint with the current model
        (or the configured compact_model).
        """
        if not self.auto_compact_turns:
            return
        if (self._turn_count - self._last_compact_turn) < self.auto_compact_turns:
            return
        self._compact_conversation()

    def save(self, file_path: str) -> None:
        """Saves the chat history to a ZIP file."""
        if not file_path.endswith(".zip"):
            raise ValueError("File path must end with .zip")
        with tempfile.TemporaryDirectory() as t:
            sections = []
            for section in self._sections:
                s = {"role": section.role, "blocks": []}
                for block in section.blocks:
                    if block.category in ["text", "code", "reasoning"]:
                        content = block.content
                    else:
                        with open(f"{t}/{block.file_id}-{block.filename}", "wb") as f:
                            f.write(block.content)
                        content = "Bytes"
                    s["blocks"].append({
                        "category": block.category,
                        "content": content,
                        "filename": block.filename,
                        "file_id": block.file_id
                    })
                sections.append(s)
            for static_file in self._static_files:
                shutil.copy(static_file._file_path, t)
            data = {
                "model": self.model,
                "instructions": self.instructions,
                "temperature": self.temperature,
                "accept_file": self.accept_file,
                "uploaded_files": self.uploaded_files,
                "user_avatar": self.user_avatar,
                "assistant_avatar": self.assistant_avatar,
                "placeholder": self.placeholder,
                "welcome_message": self.welcome_message,
                "example_messages": self.example_messages,
                "info_message": self.info_message,
                "vector_store_ids": self.vector_store_ids,
                "allow_code_interpreter": self.allow_code_interpreter,
                "allow_file_search": self.allow_file_search,
                "allow_web_search": self.allow_web_search,
                "allow_image_generation": self.allow_image_generation,
                "sections": sections,
            }
            with open(f"{t}/data.json", "w") as f:
                json.dump(data, f, indent=4)
            with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as f:
                for root, dirs, files in os.walk(t):
                    for file in files:
                        f.write(
                            os.path.join(root, file),
                            arcname=os.path.join(os.path.basename(file_path.replace(".zip", "")), file)
                        )

    @classmethod
    def load(cls, history) -> "Chat":
        """Loads a chat history from a ZIP file."""
        if not history.endswith(".zip"):
            raise ValueError("History file must end with .zip")
        with tempfile.TemporaryDirectory() as t:
            with zipfile.ZipFile(history, "r") as f:
                f.extractall(t)
            dir_path = f"{t}/{history.replace('.zip', '')}" 
            with open(f"{dir_path}/data.json", "r") as f:
                data = json.load(f)
            chat = cls(
                model=data["model"],
                instructions=data["instructions"],
                temperature=data["temperature"],
                accept_file=data["accept_file"],
                uploaded_files=None if data["uploaded_files"] is None else [f"{dir_path}/{os.path.basename(x)}" for x in data["uploaded_files"]],
                user_avatar=data["user_avatar"],
                assistant_avatar=data["assistant_avatar"],
                placeholder=data["placeholder"],
                example_messages=data["example_messages"],
                info_message=data["info_message"],
                vector_store_ids=data["vector_store_ids"],
                allow_code_interpreter=data["allow_code_interpreter"],
                allow_file_search=data["allow_file_search"],
                allow_web_search=data["allow_web_search"],
                allow_image_generation=data["allow_image_generation"],
            )
            for section in data["sections"]:
                chat.add_section(section["role"], blocks=[])
                for block in section["blocks"]:
                    if block["category"] in ["text", "code", "reasoning"]:
                        chat._input.append({
                            "role": section["role"],
                            "content": block["content"]
                        })
                        chat._sections[-1].blocks.append(chat.create_block(
                            block["category"], block["content"]
                        ))
                    else:
                        uploaded_file = f"{dir_path}/{block['file_id']}-{block['filename']}"
                        with open(uploaded_file, "rb") as f:
                            content = f.read()
                        chat.track(uploaded_file)
                        chat._sections[-1].blocks.append(chat.create_block(
                            block["category"],
                            content,
                            filename=block["filename"],
                            file_id=block["file_id"]
                        ))
            chat._input.append({"role": "developer", "content": CHAT_HISTORY_INSTRUCTIONS})
        return chat

    def respond(self, prompt) -> None:
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
        self._ensure_token_budget()
        input_items = self._message_items(self._conversation_items) + self._input
        events1 = self._client.responses.create(
            model=self.model,
            input=input_items,
            instructions=self.instructions,
            temperature=self.temperature,
            tools=self._tools,
            stream=True,
            reasoning={"summary": "auto"},
        )
        tool_call_events = []
        assistant_text = ""
        response1_text = ""
        for event1 in events1:
            if event1.type == "response.completed":
                self._previous_response_id = event1.response.id
                self.input_tokens += event1.response.usage.input_tokens
                self.output_tokens += event1.response.usage.output_tokens
                final_text = event1.response.output_text or extract_text_output(event1.response) or ""
                response1_text = final_text
                if final_text and not assistant_text:
                    self.last_section.update_and_stream("text", final_text)
                    assistant_text += final_text
            elif event1.type == "response.output_text.delta":
                self.last_section.update_and_stream("text", event1.delta)
                assistant_text += event1.delta
                self.last_section.last_block.content = re.sub(r"!?\[([^\]]+)\]\(sandbox:/mnt/data/([^\)]+)\)", r"\1 (`\2`)", self.last_section.last_block.content)
            elif event1.type == "response.code_interpreter_call_code.delta":
                self.last_section.update_and_stream("code", event1.delta)
            elif event1.type == "response.output_item.done" and event1.item.type == "function_call":
                tool_call_events.append(event1.item)
            elif event1.type == "response.reasoning_summary_text.delta":
                self.last_section.update_and_stream("reasoning", event1.delta)
            elif event1.type == "response.reasoning_summary_text.done":
                self.last_section.last_block.content += "\n\n"
            elif event1.type == "response.image_generation_call.partial_image":
                self.last_section.update_and_stream(
                    "generated_image",
                    base64.b64decode(event1.partial_image_b64),
                    filename=f"{event1.item_id}.{event1.output_format}",
                    file_id=event1.item_id
                )
            elif event1.type == "response.output_text.annotation.added":
                if event1.annotation["type"] == "file_citation":
                    pass
                elif event1.annotation["type"] == "container_file_citation":                
                    if event1.annotation["file_id"] in event1.annotation["filename"]:
                        if Path(event1.annotation["filename"]).suffix in [".png", ".jpg", ".jpeg"]:
                            image_content = self._client.containers.files.content.retrieve(
                                file_id=event1.annotation["file_id"],
                                container_id=self._container_id
                            )
                            self.last_section.update_and_stream(
                                "image",
                                image_content.read(),
                                filename=event1.annotation["filename"],
                                file_id=event1.annotation["file_id"]
                            )
                    else:
                        cfile_content = self._client.containers.files.content.retrieve(
                            file_id=event1.annotation["file_id"],
                            container_id=self._container_id
                        )
                        self.last_section.update_and_stream(
                            "download",
                            cfile_content.read(),
                            filename=event1.annotation["filename"],
                            file_id=event1.annotation["file_id"]
                        )
        LOGGER.info(
            "Coach response1 complete text_len=%d tool_calls=%d",
            len(response1_text),
            len(tool_call_events),
        )
        self._conversation_items.extend(self._normalize_items(self._input))
        if assistant_text:
            self._conversation_items.append({"role": "assistant", "content": assistant_text})
        self._input = []

        if tool_call_events:
            for item in tool_call_events:
                handler = None
                if self.functions:
                    for fn in self.functions:
                        if fn.name == item.name:
                            handler = fn
                            break
                LOGGER.info(
                    "Coach tool call name=%s args_len=%d",
                    item.name,
                    len(item.arguments or ""),
                )
                try:
                    if handler is None:
                        raise ValueError(f"No handler for tool '{item.name}'")
                    result = handler.handler(**json.loads(item.arguments))
                    output = str(result)
                except Exception as exc:
                    output = f"Tool error: {exc}"
                LOGGER.info(
                    "Coach tool output name=%s output_len=%d",
                    item.name,
                    len(output),
                )
                self._input.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "name": item.name,
                    "output": output
                })
            events2 = self._client.responses.create(
                model=self.model,
                input=self._input,
                instructions=self.instructions,
                temperature=self.temperature,
                tools=self._tools,
                previous_response_id=self._previous_response_id,
                stream=True,
            )
            assistant_text = ""
            response2_text = ""
            for event2 in events2:
                if event2.type == "response.completed":
                    self._previous_response_id = event2.response.id
                    final_text = event2.response.output_text or extract_text_output(event2.response) or ""
                    response2_text = final_text
                    if final_text and not assistant_text:
                        self.last_section.update_and_stream("text", final_text)
                        assistant_text += final_text
                elif event2.type == "response.output_text.delta":
                    self.last_section.update_and_stream("text", event2.delta)
                    assistant_text += event2.delta
            LOGGER.info(
                "Coach response2 complete text_len=%d",
                len(response2_text),
            )
            self._conversation_items.extend(self._normalize_items(self._input))
            if assistant_text:
                self._conversation_items.append({"role": "assistant", "content": assistant_text})
            self._input = []

        self._turn_count += 1
        self._maybe_compact()

    def run(self, uploaded_files=None) -> None:
        """Runs the main assistant loop."""
        if self.info_message is not None:
            st.info(self.info_message)
        for section in self._sections:
            section.write()
        summary_placeholder = st.empty()
        chat_input = st.chat_input(placeholder=self.placeholder, accept_file=self.accept_file)
        if chat_input is not None:
            if self.accept_file in [True, "multiple"]:
                prompt = chat_input.text
                attachments = chat_input.files
                if attachments:
                    if uploaded_files is None:
                        uploaded_files = attachments
                    else:
                        uploaded_files.extend(attachments)
            else:
                prompt = chat_input
                attachments = []
            section = self.create_section("user")
            with st.chat_message("user"):
                if attachments:
                    for attachment in attachments:
                        st.markdown(f":material/attach_file: `{attachment.name}`")
                        section.update(
                            "upload",
                            attachment.getvalue(),
                            filename=attachment.name,
                            file_id=attachment.file_id
                        )
                st.markdown(prompt)
                section.update("text", prompt)
            self._sections.append(section)
            self.handle_files(uploaded_files)
            self.respond(prompt)
        else:
            if self.example_messages is not None and not any(section.role == "user" for section in self._sections):
                if self._selected_example is None:
                    selected_example = st.pills(
                        "Examples",
                        options=self.example_messages,
                        label_visibility="collapsed"
                    )
                    if selected_example:
                        self._selected_example = selected_example
                        st.rerun()
                else:
                    with st.chat_message("user"):
                            st.markdown(self._selected_example)
                    self.add_section(
                        "user",
                        blocks=[self.create_block("text", self._selected_example)]
                    )
                    self.respond(self._selected_example)
        if self.summary == "New Chat":
            self.summarize()
        summary = self.summary if self.summary else "New Chat"
        summary_placeholder.info(f"Summary: {summary}")

    def handle_files(self, uploaded_files) -> None:
        """Handles uploaded files."""
        if uploaded_files is None:
            return
        else:
            for uploaded_file in uploaded_files:
                if uploaded_file.file_id in [x.uploaded_file.file_id for x in self._tracked_files if isinstance(x, UploadedFile)]:
                    continue
                self.track(uploaded_file)

    class TrackedFile():
        """A file that is tracked by the chat."""
        def __init__(
            self,
            chat: "Chat",
            uploaded_file: Optional[Union[UploadedFile, str]]
        ) -> None:
            """
            Initializes a TrackedFile instance.
            
            Args:
                chat (Chat): The parent Chat object.
                uploaded_file (UploadedFile or str): An UploadedFile object or a string representing the file path.
            """
            self.chat = chat
            self.uploaded_file = uploaded_file
            self._file_path = None
            self._openai_file = None
            self._vision_file = None
            self._skip_file_search = False
            self._is_container_file = False

            if isinstance(self.uploaded_file, str):
                self._file_path = Path(self.uploaded_file).resolve()
            elif isinstance(self.uploaded_file, UploadedFile):
                self._file_path = Path(os.path.join(self.chat._temp_dir.name, self.uploaded_file.name))
                with open(self._file_path, "wb") as f:
                    f.write(self.uploaded_file.getvalue())
            else:
                raise ValueError("uploaded_file must be an instance of UploadedFile or a string representing the file path.")

            self.chat._input.append(
                {"role": "user", "content": [{"type": "input_text", "text": f"File locally available at: {self._file_path}"}]}
            )

            if self._file_path.suffix == ".pdf":
                if self._openai_file is None:
                    with open(self._file_path, "rb") as f:
                        self._openai_file = self.chat._client.files.create(file=f, purpose="user_data")
                try:
                    # Test if the PDF file can be processed
                    response = self.chat._client.responses.create(
                        model=self.chat.model,
                        input=[{
                            "role": "user",
                            "content": [{"type": "input_file", "file_id": self._openai_file.id
                        }]}]
                    )
                    self.chat._input.append({
                        "role": "user",
                        "content": [{"type": "input_file", "file_id": self._openai_file.id}]
                    })
                    self._skip_file_search = True
                except Exception as e:
                    pass

            if self._file_path.suffix in VISION_EXTENSIONS:
                self._vision_file = self.chat._client.files.create(file=self._file_path, purpose="vision")
                self.chat._input.append({
                    "role": "user",
                    "content": [{"type": "input_image", "file_id": self._vision_file.id}]
                })

            if self.chat.allow_code_interpreter and self._file_path.suffix in CODE_INTERPRETER_EXTENSIONS:
                # If an image file is uploaded for vision purposes but is also 
                # supported by the code interpreter, it will be automatically 
                # uploaded to the code interpreter container.
                if self._file_path.suffix in VISION_EXTENSIONS:
                    self._openai_file = self._vision_file
                if self._openai_file is None:
                    with open(self._file_path, "rb") as f:
                        self._openai_file = self.chat._client.files.create(file=f, purpose="user_data")
                self.chat._client.containers.files.create(
                    container_id=self.chat._container_id,
                    file_id=self._openai_file.id,
                )
                self._is_container_file = True

            if self.chat.allow_file_search and not self._skip_file_search and self._file_path.suffix in FILE_SEARCH_EXTENSIONS:
                if self._openai_file is None:
                    with open(self._file_path, "rb") as f:
                        self._openai_file = self.chat._client.files.create(file=f, purpose="user_data")
                if self.chat._dynamic_vector_store is None:
                    self.chat._dynamic_vector_store = self.chat._client.vector_stores.create(
                        name="streamlit-openai"
                    )
                self.chat._client.vector_stores.files.create(
                    vector_store_id=self.chat._dynamic_vector_store.id,
                    file_id=self._openai_file.id
                )
                result = self.chat._client.vector_stores.retrieve(
                    vector_store_id=self.chat._dynamic_vector_store.id,
                )
                while result.status != "completed":
                    time.sleep(1)
                    result = self.chat._client.vector_stores.retrieve(
                        vector_store_id=self.chat._dynamic_vector_store.id,
                    )
                for tool in self.chat._tools:
                    if tool["type"] == "file_search":
                        if self.chat._dynamic_vector_store.id not in tool["vector_store_ids"]:
                            tool["vector_store_ids"].append(self.chat._dynamic_vector_store.id)
                        break
                else:
                    self.chat._tools.append({
                        "type": "file_search",
                        "vector_store_ids": [self.chat._dynamic_vector_store.id]
                    })

        def __repr__(self) -> None:
            return f"TrackedFile(uploaded_file='{self._file_path.name}')"
        
    def track(self, uploaded_file) -> None:
        """Tracks a file uploaded by the user."""
        self._tracked_files.append(
            self.TrackedFile(self, uploaded_file)
        )

    class Block():
        """A block of content in the chat."""
        def __init__(
            self,
            chat: "Chat",
            category: str,
            content: Optional[Union[str, bytes, openai.File]] = None,
            filename: Optional[str] = None,
            file_id: Optional[str] = None,
        ) -> None:
            """
            Initializes a Block instance.
            
            Args:
                chat (Chat): The parent Chat object.
                category (str): The type of content ('text', 'code', 'image', 'generated_image', 'download', 'upload').
                content (str or bytes): The content of the block.
                filename (str): The name of the file if the content is bytes.
                file_id (str): The ID of the file if the content is bytes.
            """
            self.chat = chat
            self.category = category
            self.content = content
            self.filename = filename
            self.file_id = file_id

            if self.content is None:
                self.content = ""
            else:
                self.content = content

        def __repr__(self) -> None:
            """Returns a string representation of the Block."""
            if self.category in ["text", "code", "reasoning"]:
                content = self.content
                if len(content) > 30:
                    content = content[:30].strip() + "..."
                content = repr(content)
            elif self.category in ["image", "generated_image", "download", "upload"]:
                content = "Bytes"
            return f"Block(category='{self.category}', content={content}, filename='{self.filename}', file_id='{self.file_id}')"

        def iscategory(self, category) -> bool:
            """Checks if the block belongs to the specified category."""
            return self.category == category

        def write(self) -> None:
            """Renders the block's content to the chat."""
            if self.category == "text":
                st.markdown(self.content)
            elif self.category == "code":
                with st.expander("", expanded=False, icon=":material/code:"):
                    st.code(self.content)
            elif self.category == "reasoning":
                with st.expander("", expanded=False, icon=":material/lightbulb:"):
                    st.markdown(self.content)
            elif self.category in ["image", "generated_image"]:
                st.image(self.content)
            elif self.category == "download":
                _, file_extension = os.path.splitext(self.filename)
                st.download_button(
                    label=self.filename,
                    data=self.content,
                    file_name=self.filename,
                    mime=MIME_TYPES[file_extension.lstrip(".")],
                    icon=":material/download:",
                    key=self.chat._download_button_key,
                )
                self.chat._download_button_key += 1
            elif self.category == "upload":
                st.markdown(f":material/attach_file: `{self.filename}`")

    def create_block(self, category, content=None, filename=None, file_id=None) -> "Block":
        """Creates a new Block object."""
        return self.Block(
            self, category, content=content, filename=filename, file_id=file_id
        )

    class Section():
        """A section of the chat."""
        def __init__(
            self,
            chat: "Chat",
            role: str,
            blocks: Optional[List["Block"]] = None,
        ) -> None:
            """
            Initializes a Section instance.
            
            Attributes:
                chat (Chat): The parent Chat object.
                role (str): The role associated with this message (e.g., "user" or "assistant").
                blocks (list): A list of Block instances representing message segments.
            """
            self.chat = chat
            self.role = role
            self.blocks = blocks
            self.delta_generator = st.empty()
            
        def __repr__(self) -> None:
            """Returns a string representation of the Section."""
            return f"Section(role='{self.role}', blocks={self.blocks})"

        @property
        def empty(self) -> bool:
            """Returns True if the section has no blocks."""
            return self.blocks is None

        @property
        def last_block(self) -> Optional["Block"]:
            """Returns the last block in the section or None if empty."""
            return None if self.empty else self.blocks[-1]

        def update(self, category, content, filename=None, file_id=None) -> None:
            """Updates the section with new content, appending or extending existing blocks."""
            if self.empty:
                self.blocks = [self.chat.create_block(
                    category, content, filename=filename, file_id=file_id
                )]
            elif category in ["text", "code", "reasoning"] and self.last_block.iscategory(category):
                self.last_block.content += content
            elif category == "generated_image" and self.last_block.iscategory(category):
                self.last_block.content = content
            else:
                self.blocks.append(self.chat.create_block(
                    category, content, filename=filename, file_id=file_id
                ))

        def write(self) -> None:
            """Renders the section's content in the Streamlit chat interface."""
            if self.empty:
                pass
            else:
                with st.chat_message(self.role, avatar=self.chat.user_avatar if self.role == "user" else self.chat.assistant_avatar):
                    for block in self.blocks:
                        block.write()

        def update_and_stream(self, category, content, filename=None, file_id=None) -> None:
            """Updates the section and streams the update live to the UI."""
            self.update(category, content, filename=filename, file_id=file_id)
            self.stream()

        def stream(self) -> None:
            """Renders the section content using Streamlit's delta generator."""
            with self.delta_generator:
                self.write()

    def create_section(self, role, blocks=None) -> "Section":
        """Creates a new Section object."""
        return self.Section(self, role, blocks=blocks)

    def add_section(self, role, blocks=None) -> None:
        """Adds a new Section."""
        self._sections.append(
            self.Section(self, role, blocks=blocks)
        )
