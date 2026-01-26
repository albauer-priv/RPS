"""Runtime helpers for prompts and vector store attachment."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import logging
import os
import re

import yaml

from rps.openai.client import get_client
from rps.openai.model_capabilities import supports_temperature
from rps.openai.reasoning import build_reasoning_payload
from rps.openai.streaming import create_response
from rps.openai.vectorstore_state import DEFAULT_STATE_PATH, load_vectorstore_id
from rps.prompts.loader import agent_system_prompt


DEFAULT_KNOWLEDGE_ROOT = Path("knowledge")
logger = logging.getLogger(__name__)


def _load_vectorstore_name(manifest_path: Path) -> str:
    """Read vector_store_name from a manifest file."""
    raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    name = raw.get("vector_store_name")
    if not name:
        raise ValueError(f"Missing vector_store_name in {manifest_path}")
    return str(name)


def resolve_vectorstore_names(
    agent_name: str,
    knowledge_root: Path = DEFAULT_KNOWLEDGE_ROOT,
) -> list[str]:
    """Resolve vector store names for an agent."""
    names: list[str] = []
    knowledge_root = knowledge_root.resolve()

    unified_manifest = knowledge_root / "all_agents" / "manifest.yaml"
    if unified_manifest.exists():
        names.append(_load_vectorstore_name(unified_manifest))
        return names

    agent_manifest = knowledge_root / agent_name / "manifest.yaml"
    if not agent_manifest.exists():
        raise FileNotFoundError(f"Manifest not found: {agent_manifest}")
    names.append(_load_vectorstore_name(agent_manifest))

    return names


def resolve_vectorstore_ids(
    agent_name: str,
    *,
    knowledge_root: Path = DEFAULT_KNOWLEDGE_ROOT,
    state_path: Path = DEFAULT_STATE_PATH,
) -> list[str]:
    """Resolve vector store IDs using the sync state file."""
    names = resolve_vectorstore_names(agent_name, knowledge_root)
    return [load_vectorstore_id(name, state_path=state_path) for name in names]


def build_file_search_tool(
    agent_name: str,
    *,
    knowledge_root: Path = DEFAULT_KNOWLEDGE_ROOT,
    state_path: Path = DEFAULT_STATE_PATH,
    max_num_results: int = 5,
) -> dict[str, Any]:
    """Build a file_search tool payload for the Responses API."""
    vector_store_ids = resolve_vectorstore_ids(
        agent_name,
        knowledge_root=knowledge_root,
        state_path=state_path,
    )
    return {
        "type": "file_search",
        "vector_store_ids": vector_store_ids,
        "max_num_results": max_num_results,
    }


def _parse_float(value: str | None) -> float | None:
    """Parse a float from env, returning None on invalid input."""
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_int(value: str | None) -> int | None:
    """Parse an int from env, returning None on invalid input."""
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def run_agent(
    agent_name: str,
    user_input: str,
    *,
    model: str | None = None,
    temperature: float | None = None,
    knowledge_root: Path = DEFAULT_KNOWLEDGE_ROOT,
    state_path: Path = DEFAULT_STATE_PATH,
    max_num_results: int | None = None,
    include_results: bool = False,
    force_file_search: bool = True,
    prompts_dir: Path = Path("prompts"),
):
    """Run a simple Responses API request with file_search attached."""
    if model is None:
        key = re.sub(r"[^A-Za-z0-9]+", "_", agent_name).upper()
        model = os.getenv(f"OPENAI_MODEL_{key}") or os.getenv("OPENAI_MODEL", "gpt-4.1")
    if temperature is None:
        key = re.sub(r"[^A-Za-z0-9]+", "_", agent_name).upper()
        temperature = _parse_float(
            os.getenv(f"OPENAI_TEMPERATURE_{key}") or os.getenv("OPENAI_TEMPERATURE")
        )
    key = re.sub(r"[^A-Za-z0-9]+", "_", agent_name).upper()
    reasoning_effort = os.getenv(f"OPENAI_REASONING_EFFORT_{key}") or os.getenv("OPENAI_REASONING_EFFORT")
    reasoning_summary = os.getenv(f"OPENAI_REASONING_SUMMARY_{key}") or os.getenv("OPENAI_REASONING_SUMMARY")
    if max_num_results is None:
        max_num_results = _parse_int(os.getenv("OPENAI_FILE_SEARCH_MAX_RESULTS")) or 5
    client = get_client()
    system_prompt = agent_system_prompt(agent_name, prompts_dir=prompts_dir)
    tool = build_file_search_tool(
        agent_name,
        knowledge_root=knowledge_root,
        state_path=state_path,
        max_num_results=max_num_results,
    )

    payload: dict[str, Any] = {
        "model": model,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
        "tools": [tool],
    }
    if force_file_search:
        payload["tool_choice"] = {"type": "file_search"}
    if include_results:
        payload["include"] = ["file_search_call.results"]
    if temperature is not None and supports_temperature(model):
        payload["temperature"] = temperature
    reasoning = build_reasoning_payload(model, reasoning_effort, reasoning_summary)
    if reasoning:
        payload["reasoning"] = reasoning
    return create_response(client, payload, logger)
