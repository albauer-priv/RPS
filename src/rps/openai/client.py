"""LLM client helpers."""

from __future__ import annotations

from rps.openai.litellm_runtime import LiteLLMClient, resolve_provider_config


def get_client(agent_name: str | None = None) -> LiteLLMClient:
    """Create a LiteLLM client configured from environment settings."""
    config = resolve_provider_config(agent_name)
    return LiteLLMClient(config)
