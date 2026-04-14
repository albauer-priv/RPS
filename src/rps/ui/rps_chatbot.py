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
from collections.abc import Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Literal, Protocol, TypeAlias, TypeGuard, cast

import streamlit as st

try:
    import tiktoken as _tiktoken_runtime
except Exception:  # pragma: no cover - optional dependency
    _loaded_tiktoken: object | None = None
else:
    _loaded_tiktoken = _tiktoken_runtime
from streamlit.runtime.uploaded_file_manager import UploadedFile

from rps.openai.client import get_client
from rps.openai.litellm_runtime import LiteLLMResponse
from rps.openai.response_utils import extract_text_output

if TYPE_CHECKING:  # pragma: no cover - import only for typing
    pass
JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | dict[str, object] | list[object]
JsonMap: TypeAlias = dict[str, object]
InputContentBlock: TypeAlias = dict[str, object]
InputItem: TypeAlias = dict[str, object]
ToolSpec: TypeAlias = dict[str, object]
BlockContent: TypeAlias = str | bytes
BLOCK_REPR_PREVIEW_MAX_CHARS = 30


class _HasModelDump(Protocol):
    def model_dump(self) -> dict[str, object]: ...


class _TiktokenEncoding(Protocol):
    def encode(self, text: str) -> list[int]: ...


class _TiktokenProtocol(Protocol):
    def encoding_for_model(self, model: str) -> _TiktokenEncoding: ...
    def get_encoding(self, name: str) -> _TiktokenEncoding: ...


class _OpenAIFileRef(Protocol):
    id: str


class _VectorStoreRef(Protocol):
    id: str
    status: str


class _OpenAIFileUpload(_OpenAIFileRef, Protocol):
    pass



class _VectorStoreFileManager(Protocol):
    def create(self, *, vector_store_id: str, file_id: str) -> object: ...


class _VectorStoreManager(Protocol):
    files: _VectorStoreFileManager

    def create(self, *, name: str) -> _VectorStoreRef: ...
    def retrieve(self, *, vector_store_id: str) -> _VectorStoreRef: ...


class _ClientWithVectorStores(Protocol):
    vector_stores: _VectorStoreManager


class _ResponsesManager(Protocol):
    def create(self, **payload: object) -> object: ...
    def compact(self, **payload: object) -> object: ...




class _FileContentReader(Protocol):
    def read(self) -> bytes: ...


class _ContainerFileContentManager(Protocol):
    def retrieve(self, *, file_id: str, container_id: str | None) -> _FileContentReader: ...


class _ContainerFileManager(Protocol):
    content: _ContainerFileContentManager

    def create(self, *, container_id: str, file_id: str) -> object: ...


class _ContainerRef(Protocol):
    id: str
    status: str


class _ContainerManager(Protocol):
    files: _ContainerFileManager

    def create(self, *, name: str) -> _ContainerRef: ...
    def retrieve(self, *, container_id: str | None) -> _ContainerRef: ...


class _FileManager(Protocol):
    def create(self, *, file: object, purpose: str) -> _OpenAIFileUpload: ...


class _ClientWithFilesAndContainers(_ClientWithVectorStores, Protocol):
    responses: _ResponsesManager
    files: _FileManager
    containers: _ContainerManager


_tiktoken_module = cast(_TiktokenProtocol | None, _loaded_tiktoken)
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
    "txt": "text/plain",
    "csv": "text/csv",
    "tsv": "text/tab-separated-values",
    "html": "text/html",
    "yaml": "text/yaml",
    "md": "text/markdown",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "xml": "application/xml",
    "json": "application/json",
    "pdf": "application/pdf",
    "zip": "application/zip",
    "tar": "application/x-tar",
    "gz": "application/gzip",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "ppt": "application/vnd.ms-powerpoint",
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
BlockCategory = Literal["text", "code", "reasoning", "image", "generated_image", "download", "upload"]


def _is_model_dumpable(value: object) -> TypeGuard[_HasModelDump]:
    return hasattr(value, "model_dump")


def _is_input_item(value: object) -> TypeGuard[InputItem]:
    return isinstance(value, dict)


def _require_text(value: BlockContent) -> str:
    if isinstance(value, str):
        return value
    raise TypeError("Expected text block content.")


def _require_bytes(value: BlockContent) -> bytes:
    if isinstance(value, bytes):
        return value
    raise TypeError("Expected binary block content.")


class CustomFunction:
    """Represents a custom function that can be invoked by the OpenAI API."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: JsonMap,
        handler: object,
    ) -> None:
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler

    def __repr__(self) -> str:
        return f"CustomFunction(name='{self.name}')"


def _require_response(result: LiteLLMResponse | object) -> LiteLLMResponse:
    """Return a non-streaming response object or fail fast for invalid runtime output."""
    if isinstance(result, LiteLLMResponse):
        return result
    raise RuntimeError("Expected non-streaming LiteLLM response.")


def _require_event_stream(result: LiteLLMResponse | object) -> list[SimpleNamespace]:
    """Return a materialized event stream or fail fast for invalid runtime output."""
    if isinstance(result, LiteLLMResponse):
        raise RuntimeError("Expected streaming LiteLLM response events.")
    if isinstance(result, list):
        return [cast(SimpleNamespace, item) for item in result]
    return list(cast(list[SimpleNamespace], result))


class RemoteMCP:
    """Represents a remote MCP server that can be used to perform tasks."""

    def __init__(
        self,
        server_label: str,
        server_url: str,
        require_approval: str = "never",
        headers: JsonMap | None = None,
        allowed_tools: list[str] | None = None,
    ) -> None:
        self.server_label = server_label
        self.server_url = server_url
        self.require_approval = require_approval
        self.headers = headers
        self.allowed_tools = allowed_tools

    def __repr__(self) -> str:
        return f"RemoteMCP(server_label='{self.server_label}')"


class Chat:
    """A Streamlit-based chat interface powered by OpenAI's Responses API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = "gpt-4o",
        instructions: str | None = None,
        temperature: float | None = 1.0,
        accept_file: bool | str = "multiple",
        uploaded_files: list[str] | None = None,
        functions: list[CustomFunction] | None = None,
        mcps: list[RemoteMCP] | None = None,
        user_avatar: str | None = None,
        assistant_avatar: str | None = None,
        placeholder: str | None = "Your message",
        welcome_message: str | None = None,
        example_messages: list[str] | None = None,
        info_message: str | None = None,
        vector_store_ids: list[str] | None = None,
        allow_code_interpreter: bool | None = True,
        allow_file_search: bool | None = True,
        allow_web_search: bool | None = True,
        allow_image_generation: bool | None = True,
        auto_compact_turns: int | None = None,
        compact_model: str | None = None,
        agent_name: str | None = None,
    ) -> None:
        self.api_key = os.getenv("RPS_LLM_API_KEY") if api_key is None else api_key
        self.model = model or "gpt-4o"
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
        self._client = cast(_ClientWithFilesAndContainers, get_client(agent_name))
        self._temp_dir = tempfile.TemporaryDirectory()
        self._selected_example: str | None = None
        self._input: list[InputItem] = []
        self._tools: list[ToolSpec] = []
        self._previous_response_id: str | None = None
        self._container_id: str | None = None
        self._sections: list[Chat.Section] = []
        self._static_files: list[Chat.TrackedFile] = []
        self._tracked_files: list[Chat.TrackedFile] = []
        self._download_button_key = 0
        self._dynamic_vector_store: _VectorStoreRef | None = None
        self._conversation_items: list[InputItem] = []
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
                tool_spec: ToolSpec = {
                    "type": "mcp",
                    "server_label": mcp.server_label,
                    "server_url": mcp.server_url,
                    "require_approval": mcp.require_approval,
                }
                if mcp.headers is not None:
                    tool_spec["headers"] = mcp.headers
                if mcp.allowed_tools is not None:
                    tool_spec["allowed_tools"] = mcp.allowed_tools
                self._tools.append(tool_spec)

        if allow_file_search and self.vector_store_ids is not None:
            self._tools.append({"type": "file_search", "vector_store_ids": list(self.vector_store_ids)})

        if self.welcome_message is not None:
            self._input.append({"role": "assistant", "content": self.welcome_message})
            self.add_section(
                "assistant",
                blocks=[self.create_block("text", self.welcome_message)],
            )

        if self.uploaded_files is not None:
            for uploaded_file in self.uploaded_files:
                shutil.copy(uploaded_file, self._temp_dir.name)
                self.track(os.path.join(self._temp_dir.name, os.path.basename(uploaded_file)))
                self._static_files.append(self._tracked_files[-1])

    @property
    def last_section(self) -> Chat.Section | None:
        return self._sections[-1] if self._sections else None

    def summarize(self) -> None:
        sections: list[JsonMap] = []
        for section in self._sections:
            section_data: JsonMap = {"role": section.role, "blocks": []}
            blocks_data: list[JsonMap] = []
            if not section.blocks:
                continue
            for block in section.blocks:
                content: JsonValue = _require_text(block.content) if block.category in ["text", "code", "reasoning"] else "Bytes"
                blocks_data.append({
                    "category": block.category,
                    "content": content,
                    "filename": block.filename,
                    "file_id": block.file_id,
                })
            section_data["blocks"] = blocks_data
            sections.append(section_data)
        if sections:
            summary_model = (
                os.getenv("RPS_LLM_MODEL_COACH_SUMMARY")
                or os.getenv("RPS_LLM_MODEL_SUMMARY")
                or self.model
            )
            response = _require_response(
                self._client.responses.create(
                    model=summary_model,
                    input=[
                        {"role": "developer", "content": SUMMARY_INSTRUCTIONS},
                        {"role": "user", "content": json.dumps(sections, indent=2)},
                    ],
                )
            )
            self.summary = response.output_text or extract_text_output(response) or "New Chat"

    def _get_model_limits(self, model: str) -> dict[str, int] | None:
        for prefix, limits in MODEL_LIMITS:
            if model.startswith(prefix):
                return limits
        return None

    def _estimate_tokens(self, text: str, model: str) -> int:
        if _tiktoken_module is None:
            return max(1, len(text) // 4)
        try:
            encoding = _tiktoken_module.encoding_for_model(model)
        except KeyError:
            encoding = _tiktoken_module.get_encoding("o200k_base")
        return len(encoding.encode(text))

    def _estimate_items_tokens(self, items: list[InputItem]) -> int:
        payload = json.dumps(items, ensure_ascii=True, separators=(",", ":"), default=str)
        return self._estimate_tokens(payload, self.model)

    def _truncate_conversation_items(self, max_input_tokens: int) -> None:
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
        if _tiktoken_module is None:
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

    def _normalize_items(self, items: Sequence[object]) -> list[InputItem]:
        normalized: list[InputItem] = []
        for item in items:
            if _is_model_dumpable(item):
                data: object = item.model_dump()
            else:
                data = item
            if not _is_input_item(data):
                continue
            if "status" in data:
                data = {k: v for k, v in data.items() if k != "status"}
            if data.get("type") == "function_call_output":
                continue
            normalized.append(data)
        return normalized

    def _message_items(self, items: Sequence[object]) -> list[InputItem]:
        return [
            self._strip_content_annotations(item)
            for item in items
            if _is_input_item(item) and "role" in item and "content" in item
        ]

    def _strip_content_annotations(self, message: InputItem) -> InputItem:
        content = message.get("content")
        if isinstance(content, list):
            cleaned_blocks: list[JsonValue] = []
            for block in content:
                if isinstance(block, dict):
                    cleaned_block = {k: v for k, v in block.items() if k not in {"annotations", "logprobs"}}
                    cleaned_blocks.append(cleaned_block)
                else:
                    cleaned_blocks.append(block)
            message = {**message, "content": cleaned_blocks}
        return message

    def _compact_conversation(self) -> None:
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
        if isinstance(output, list):
            self._conversation_items = self._normalize_items(output)
            self._last_compact_turn = self._turn_count

    def _maybe_compact(self) -> None:
        if not self.auto_compact_turns:
            return
        if (self._turn_count - self._last_compact_turn) < self.auto_compact_turns:
            return
        self._compact_conversation()

    def save(self, file_path: str) -> None:
        if not file_path.endswith(".zip"):
            raise ValueError("File path must end with .zip")
        with tempfile.TemporaryDirectory() as temp_dir:
            sections: list[JsonMap] = []
            for section in self._sections:
                section_data: JsonMap = {"role": section.role, "blocks": []}
                blocks_data: list[JsonMap] = []
                for block in section.blocks:
                    if block.category in ["text", "code", "reasoning"]:
                        content: JsonValue = _require_text(block.content)
                    else:
                        with open(f"{temp_dir}/{block.file_id}-{block.filename}", "wb") as file_handle:
                            file_handle.write(_require_bytes(block.content))
                        content = "Bytes"
                    blocks_data.append({
                        "category": block.category,
                        "content": content,
                        "filename": block.filename,
                        "file_id": block.file_id,
                    })
                section_data["blocks"] = blocks_data
                sections.append(section_data)
            for static_file in self._static_files:
                if static_file._file_path is not None:
                    shutil.copy(static_file._file_path, temp_dir)
            data: JsonMap = {
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
            with open(f"{temp_dir}/data.json", "w") as file_handle:
                json.dump(data, file_handle, indent=4)
            with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as archive:
                for root, _, files in os.walk(temp_dir):
                    for file_name in files:
                        archive.write(
                            os.path.join(root, file_name),
                            arcname=os.path.join(os.path.basename(file_path.replace(".zip", "")), file_name),
                        )

    @classmethod
    def load(cls, history: str) -> Chat:
        if not history.endswith(".zip"):
            raise ValueError("History file must end with .zip")
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(history, "r") as archive:
                archive.extractall(temp_dir)
            dir_path = f"{temp_dir}/{history.replace('.zip', '')}"
            with open(f"{dir_path}/data.json") as file_handle:
                data = cast(JsonMap, json.load(file_handle))
            chat = cls(
                model=cast(str, data["model"]),
                instructions=cast(str, data["instructions"]),
                temperature=cast(float | None, data["temperature"]),
                accept_file=cast(bool | str, data["accept_file"]),
                uploaded_files=None if data["uploaded_files"] is None else [f"{dir_path}/{os.path.basename(cast(str, x))}" for x in cast(list[JsonValue], data["uploaded_files"])],
                user_avatar=cast(str | None, data["user_avatar"]),
                assistant_avatar=cast(str | None, data["assistant_avatar"]),
                placeholder=cast(str | None, data["placeholder"]),
                example_messages=cast(list[str] | None, data["example_messages"]),
                info_message=cast(str | None, data["info_message"]),
                vector_store_ids=cast(list[str] | None, data["vector_store_ids"]),
                allow_code_interpreter=cast(bool | None, data["allow_code_interpreter"]),
                allow_file_search=cast(bool | None, data["allow_file_search"]),
                allow_web_search=cast(bool | None, data["allow_web_search"]),
                allow_image_generation=cast(bool | None, data["allow_image_generation"]),
            )
            for section in cast(list[JsonMap], data["sections"]):
                chat.add_section(cast(str, section["role"]), blocks=[])
                for block in cast(list[JsonMap], section["blocks"]):
                    category = cast(BlockCategory, block["category"])
                    if category in ["text", "code", "reasoning"]:
                        block_content = cast(str, block["content"])
                        chat._input.append({"role": cast(str, section["role"]), "content": block_content})
                        chat._sections[-1].blocks.append(chat.create_block(category, block_content))
                    else:
                        uploaded_file = f"{dir_path}/{block['file_id']}-{block['filename']}"
                        with open(uploaded_file, "rb") as file_handle:
                            content = file_handle.read()
                        chat.track(uploaded_file)
                        chat._sections[-1].blocks.append(
                            chat.create_block(
                                category,
                                content,
                                filename=cast(str | None, block["filename"]),
                                file_id=cast(str | None, block["file_id"]),
                            )
                        )
            chat._input.append({"role": "developer", "content": CHAT_HISTORY_INSTRUCTIONS})
        return chat

    def _require_last_section(self) -> Chat.Section:
        section = self.last_section
        if section is None:
            raise RuntimeError("Chat section missing while streaming a response.")
        return section

    def respond(self, prompt: str) -> None:
        self._input.append({"role": "user", "content": prompt})
        self.add_section("assistant")
        current_section = self._require_last_section()
        if self.allow_code_interpreter:
            result = self._client.containers.retrieve(container_id=self._container_id)
            if result.status == "expired":
                container = self._client.containers.create(name="streamlit-openai")
                self._container_id = container.id
                for tracked_file in self._tracked_files:
                    if tracked_file._is_container_file and tracked_file._openai_file is not None and self._container_id is not None:
                        self._client.containers.files.create(
                            container_id=self._container_id,
                            file_id=tracked_file._openai_file.id,
                        )
            for tool in self._tools:
                if tool.get("type") == "code_interpreter":
                    tool["container"] = self._container_id or ""
        self._ensure_token_budget()
        input_items = self._message_items(self._conversation_items) + self._input
        events1 = _require_event_stream(
            self._client.responses.create(
                model=self.model,
                input=input_items,
                instructions=self.instructions,
                temperature=self.temperature,
                tools=self._tools,
                stream=True,
                reasoning={"summary": "auto"},
            )
        )
        tool_call_events: list[SimpleNamespace] = []
        assistant_text = ""
        response1_text = ""
        for event1 in events1:
            if event1.type == "response.completed":
                self._previous_response_id = event1.response.id
                usage = event1.response.usage or {}
                self.input_tokens += int(usage.get("input_tokens", 0))
                self.output_tokens += int(usage.get("output_tokens", 0))
                final_text = event1.response.output_text or extract_text_output(event1.response) or ""
                response1_text = final_text
                if final_text and not assistant_text:
                    current_section.update_and_stream("text", final_text)
                    assistant_text += final_text
            elif event1.type == "response.output_text.delta":
                current_section.update_and_stream("text", event1.delta)
                assistant_text += event1.delta
                last_block = current_section.last_block
                if last_block is not None and isinstance(last_block.content, str):
                    last_block.content = re.sub(
                        r"!?\[([^\]]+)\]\(sandbox:/mnt/data/([^\)]+)\)",
                        r"\1 (`\2`)",
                        last_block.content,
                    )
            elif event1.type == "response.code_interpreter_call_code.delta":
                current_section.update_and_stream("code", event1.delta)
            elif event1.type == "response.output_item.done" and event1.item.type == "function_call":
                tool_call_events.append(event1.item)
            elif event1.type == "response.reasoning_summary_text.delta":
                current_section.update_and_stream("reasoning", event1.delta)
            elif event1.type == "response.reasoning_summary_text.done":
                last_block = current_section.last_block
                if last_block is not None and isinstance(last_block.content, str):
                    last_block.content += "\n\n"
            elif event1.type == "response.image_generation_call.partial_image":
                current_section.update_and_stream(
                    "generated_image",
                    base64.b64decode(event1.partial_image_b64),
                    filename=f"{event1.item_id}.{event1.output_format}",
                    file_id=event1.item_id,
                )
            elif event1.type == "response.output_text.annotation.added":
                annotation = cast(dict[str, object], event1.annotation)
                annotation_type = cast(str | None, annotation.get("type"))
                annotation_file_id = cast(str | None, annotation.get("file_id"))
                annotation_filename = cast(str | None, annotation.get("filename"))
                if annotation_type == "file_citation":
                    continue
                if annotation_type == "container_file_citation" and annotation_file_id is not None and annotation_filename is not None:
                    if annotation_file_id in annotation_filename:
                        if Path(annotation_filename).suffix in [".png", ".jpg", ".jpeg"]:
                            image_content = self._client.containers.files.content.retrieve(
                                file_id=annotation_file_id,
                                container_id=self._container_id,
                            )
                            current_section.update_and_stream(
                                "image",
                                image_content.read(),
                                filename=annotation_filename,
                                file_id=annotation_file_id,
                            )
                    else:
                        cfile_content = self._client.containers.files.content.retrieve(
                            file_id=annotation_file_id,
                            container_id=self._container_id,
                        )
                        current_section.update_and_stream(
                            "download",
                            cfile_content.read(),
                            filename=annotation_filename,
                            file_id=annotation_file_id,
                        )
        LOGGER.info("Coach response1 complete text_len=%d tool_calls=%d", len(response1_text), len(tool_call_events))
        self._conversation_items.extend(self._normalize_items(self._input))
        if assistant_text:
            self._conversation_items.append({"role": "assistant", "content": assistant_text})
        self._input = []

        if tool_call_events:
            for item in tool_call_events:
                handler: CustomFunction | None = None
                if self.functions:
                    for function in self.functions:
                        if function.name == item.name:
                            handler = function
                            break
                LOGGER.info("Coach tool call name=%s args_len=%d", item.name, len(item.arguments or ""))
                try:
                    if handler is None:
                        raise ValueError(f"No handler for tool '{item.name}'")
                    if not callable(handler.handler):
                        raise TypeError(f"Handler for tool '{item.name}' is not callable")
                    result = handler.handler(**json.loads(item.arguments))
                    output = str(result)
                except Exception as exc:
                    output = f"Tool error: {exc}"
                LOGGER.info("Coach tool output name=%s output_len=%d", item.name, len(output))
                self._input.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "name": item.name,
                    "output": output,
                })
            events2 = _require_event_stream(
                self._client.responses.create(
                    model=self.model,
                    input=self._input,
                    instructions=self.instructions,
                    temperature=self.temperature,
                    tools=self._tools,
                    previous_response_id=self._previous_response_id,
                    stream=True,
                )
            )
            assistant_text = ""
            response2_text = ""
            for event2 in events2:
                if event2.type == "response.completed":
                    self._previous_response_id = event2.response.id
                    final_text = event2.response.output_text or extract_text_output(event2.response) or ""
                    response2_text = final_text
                    if final_text and not assistant_text:
                        current_section.update_and_stream("text", final_text)
                        assistant_text += final_text
                elif event2.type == "response.output_text.delta":
                    current_section.update_and_stream("text", event2.delta)
                    assistant_text += event2.delta
            LOGGER.info("Coach response2 complete text_len=%d", len(response2_text))
            self._conversation_items.extend(self._normalize_items(self._input))
            if assistant_text:
                self._conversation_items.append({"role": "assistant", "content": assistant_text})
            self._input = []

        self._turn_count += 1
        self._maybe_compact()

    def run(self, uploaded_files: list[UploadedFile] | None = None) -> None:
        if self.info_message is not None:
            st.info(self.info_message)
        for section in self._sections:
            section.write()
        summary_placeholder = st.empty()
        chat_input_obj: object
        if self.accept_file is True or self.accept_file in {"multiple", "directory"}:
            chat_input_obj = st.chat_input(
                placeholder=self.placeholder or "Your message",
                accept_file=cast(Literal[True, "multiple", "directory"], self.accept_file),
            )
        else:
            chat_input_obj = st.chat_input(placeholder=self.placeholder or "Your message")
        if chat_input_obj is not None:
            if self.accept_file in [True, "multiple"]:
                prompt = cast(str, getattr(chat_input_obj, "text", ""))
                attachments = list(cast(list[UploadedFile], getattr(chat_input_obj, "files", [])))
                if attachments:
                    if uploaded_files is None:
                        uploaded_files = attachments
                    else:
                        uploaded_files.extend(attachments)
            else:
                prompt = str(chat_input_obj)
                attachments = []
            section = self.create_section("user")
            with st.chat_message("user"):
                if attachments:
                    for attachment in attachments:
                        st.markdown(f":material/attach_file: `{attachment.name}`")
                        section.update("upload", attachment.getvalue(), filename=attachment.name, file_id=attachment.file_id)
                st.markdown(prompt)
                section.update("text", prompt)
            self._sections.append(section)
            self.handle_files(uploaded_files)
            self.respond(prompt)
        else:
            if self.example_messages is not None and not any(section.role == "user" for section in self._sections):
                if self._selected_example is None:
                    selected_example = st.pills("Examples", options=self.example_messages, label_visibility="collapsed")
                    if selected_example:
                        self._selected_example = str(selected_example)
                        st.rerun()
                else:
                    with st.chat_message("user"):
                        st.markdown(self._selected_example)
                    self.add_section("user", blocks=[self.create_block("text", self._selected_example)])
                    self.respond(self._selected_example)
        if self.summary == "New Chat":
            self.summarize()
        summary_placeholder.info(f"Summary: {self.summary or 'New Chat'}")

    def handle_files(self, uploaded_files: list[UploadedFile] | None) -> None:
        if uploaded_files is None:
            return
        for uploaded_file in uploaded_files:
            tracked_upload_ids = [
                tracked.uploaded_file.file_id
                for tracked in self._tracked_files
                if isinstance(tracked.uploaded_file, UploadedFile)
            ]
            if uploaded_file.file_id in tracked_upload_ids:
                continue
            self.track(uploaded_file)

    class TrackedFile:
        def __init__(self, chat: Chat, uploaded_file: UploadedFile | str | None) -> None:
            self.chat = chat
            self.uploaded_file = uploaded_file
            self._file_path: Path | None = None
            self._openai_file: _OpenAIFileUpload | None = None
            self._vision_file: _OpenAIFileUpload | None = None
            self._skip_file_search = False
            self._is_container_file = False

            if isinstance(self.uploaded_file, str):
                self._file_path = Path(self.uploaded_file).resolve()
            elif isinstance(self.uploaded_file, UploadedFile):
                self._file_path = Path(os.path.join(self.chat._temp_dir.name, self.uploaded_file.name))
                with open(self._file_path, "wb") as file_handle:
                    file_handle.write(self.uploaded_file.getvalue())
            else:
                raise ValueError("uploaded_file must be an instance of UploadedFile or a string representing the file path.")

            file_path = self._file_path
            self.chat._input.append({
                "role": "user",
                "content": [{"type": "input_text", "text": f"File locally available at: {file_path}"}],
            })

            if file_path.suffix == ".pdf":
                if self._openai_file is None:
                    with open(file_path, "rb") as file_handle:
                        self._openai_file = cast(_OpenAIFileUpload, self.chat._client.files.create(file=file_handle, purpose="user_data"))
                try:
                    self.chat._client.responses.create(
                        model=self.chat.model,
                        input=[{"role": "user", "content": [{"type": "input_file", "file_id": self._openai_file.id}]}],
                    )
                    self.chat._input.append({"role": "user", "content": [{"type": "input_file", "file_id": self._openai_file.id}]})
                    self._skip_file_search = True
                except Exception:
                    pass

            if file_path.suffix in VISION_EXTENSIONS:
                self._vision_file = cast(_OpenAIFileUpload, self.chat._client.files.create(file=file_path, purpose="vision"))
                self.chat._input.append({"role": "user", "content": [{"type": "input_image", "file_id": self._vision_file.id}]})

            if self.chat.allow_code_interpreter and file_path.suffix in CODE_INTERPRETER_EXTENSIONS:
                if file_path.suffix in VISION_EXTENSIONS:
                    self._openai_file = self._vision_file
                if self._openai_file is None:
                    with open(file_path, "rb") as file_handle:
                        self._openai_file = cast(_OpenAIFileUpload, self.chat._client.files.create(file=file_handle, purpose="user_data"))
                if self.chat._container_id is not None:
                    self.chat._client.containers.files.create(container_id=self.chat._container_id, file_id=self._openai_file.id)
                    self._is_container_file = True

            if self.chat.allow_file_search and not self._skip_file_search and file_path.suffix in FILE_SEARCH_EXTENSIONS:
                if self._openai_file is None:
                    with open(file_path, "rb") as file_handle:
                        self._openai_file = cast(_OpenAIFileUpload, self.chat._client.files.create(file=file_handle, purpose="user_data"))
                vector_store_client = cast(_ClientWithVectorStores, self.chat._client)
                if self.chat._dynamic_vector_store is None:
                    self.chat._dynamic_vector_store = cast(_VectorStoreRef, vector_store_client.vector_stores.create(name="streamlit-openai"))
                vector_store_client.vector_stores.files.create(
                    vector_store_id=self.chat._dynamic_vector_store.id,
                    file_id=self._openai_file.id,
                )
                result = cast(_VectorStoreRef, vector_store_client.vector_stores.retrieve(vector_store_id=self.chat._dynamic_vector_store.id))
                while result.status != "completed":
                    time.sleep(1)
                    result = cast(_VectorStoreRef, vector_store_client.vector_stores.retrieve(vector_store_id=self.chat._dynamic_vector_store.id))
                for tool in self.chat._tools:
                    if tool.get("type") == "file_search":
                        vector_store_ids = tool.setdefault("vector_store_ids", [])
                        if isinstance(vector_store_ids, list) and self.chat._dynamic_vector_store.id not in vector_store_ids:
                            vector_store_ids.append(self.chat._dynamic_vector_store.id)
                        break
                else:
                    self.chat._tools.append({"type": "file_search", "vector_store_ids": [self.chat._dynamic_vector_store.id]})

        def __repr__(self) -> str:
            file_name = self._file_path.name if self._file_path is not None else "<unknown>"
            return f"TrackedFile(uploaded_file='{file_name}')"

    def track(self, uploaded_file: UploadedFile | str) -> None:
        self._tracked_files.append(self.TrackedFile(self, uploaded_file))

    class Block:
        def __init__(
            self,
            chat: Chat,
            category: BlockCategory,
            content: BlockContent | None = None,
            filename: str | None = None,
            file_id: str | None = None,
        ) -> None:
            self.chat = chat
            self.category = category
            self.content: BlockContent = "" if content is None else content
            self.filename = filename
            self.file_id = file_id

        def __repr__(self) -> str:
            if self.category in ["text", "code", "reasoning"]:
                content = _require_text(self.content)
                if len(content) > BLOCK_REPR_PREVIEW_MAX_CHARS:
                    content = content[:BLOCK_REPR_PREVIEW_MAX_CHARS].strip() + "..."
                rendered_content = repr(content)
            else:
                rendered_content = "Bytes"
            return f"Block(category='{self.category}', content={rendered_content}, filename='{self.filename}', file_id='{self.file_id}')"

        def iscategory(self, category: BlockCategory) -> bool:
            return self.category == category

        def write(self) -> None:
            if self.category == "text":
                st.markdown(_require_text(self.content))
            elif self.category == "code":
                with st.expander("", expanded=False, icon=":material/code:"):
                    st.code(_require_text(self.content))
            elif self.category == "reasoning":
                with st.expander("", expanded=False, icon=":material/lightbulb:"):
                    st.markdown(_require_text(self.content))
            elif self.category in ["image", "generated_image"]:
                st.image(_require_bytes(self.content))
            elif self.category == "download":
                filename = self.filename or "download.bin"
                _, file_extension = os.path.splitext(filename)
                st.download_button(
                    label=filename,
                    data=_require_bytes(self.content),
                    file_name=filename,
                    mime=MIME_TYPES.get(file_extension.lstrip("."), "application/octet-stream"),
                    icon=":material/download:",
                    key=self.chat._download_button_key,
                )
                self.chat._download_button_key += 1
            elif self.category == "upload":
                st.markdown(f":material/attach_file: `{self.filename}`")

    def create_block(
        self,
        category: BlockCategory,
        content: BlockContent | None = None,
        filename: str | None = None,
        file_id: str | None = None,
    ) -> Block:
        return self.Block(self, category, content=content, filename=filename, file_id=file_id)

    class Section:
        def __init__(self, chat: Chat, role: str, blocks: list[Chat.Block] | None = None) -> None:
            self.chat = chat
            self.role = role
            self.blocks: list[Chat.Block] = blocks or []
            self.delta_generator = st.empty()

        def __repr__(self) -> str:
            return f"Section(role='{self.role}', blocks={self.blocks})"

        @property
        def empty(self) -> bool:
            return not self.blocks

        @property
        def last_block(self) -> Chat.Block | None:
            return None if self.empty else self.blocks[-1]

        def update(
            self,
            category: BlockCategory,
            content: BlockContent,
            filename: str | None = None,
            file_id: str | None = None,
        ) -> None:
            if self.empty:
                self.blocks = [self.chat.create_block(category, content, filename=filename, file_id=file_id)]
            elif (
                category in ["text", "code", "reasoning"]
                and self.last_block is not None
                and self.last_block.iscategory(category)
                and isinstance(self.last_block.content, str)
                and isinstance(content, str)
            ):
                self.last_block.content += content
            elif category == "generated_image" and self.last_block is not None and self.last_block.iscategory(category):
                self.last_block.content = content
            else:
                self.blocks.append(self.chat.create_block(category, content, filename=filename, file_id=file_id))

        def write(self) -> None:
            if not self.empty:
                with st.chat_message(self.role, avatar=self.chat.user_avatar if self.role == "user" else self.chat.assistant_avatar):
                    for block in self.blocks:
                        block.write()

        def update_and_stream(
            self,
            category: BlockCategory,
            content: BlockContent,
            filename: str | None = None,
            file_id: str | None = None,
        ) -> None:
            self.update(category, content, filename=filename, file_id=file_id)
            self.stream()

        def stream(self) -> None:
            with self.delta_generator:
                self.write()

    def create_section(self, role: str, blocks: list[Chat.Block] | None = None) -> Section:
        return self.Section(self, role, blocks=blocks)

    def add_section(self, role: str, blocks: list[Chat.Block] | None = None) -> None:
        self._sections.append(self.Section(self, role, blocks=blocks))
