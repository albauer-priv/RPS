"""Direct CrewAI provider configuration from a minimal global RPS env surface."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class CrewAIProviderConfig:
    """Resolved provider configuration for a single CrewAI agent."""

    api_key: str
    model: str
    base_url: str | None
    org_id: str | None
    project_id: str | None
    temperature: float | None
    reasoning_effort: str | None
    reasoning_summary: str | None
    max_completion_tokens: int | None


def resolve_crewai_provider_config(
    agent_name: str,
    *,
    model_override: str | None = None,
    temperature_override: float | None = None,
    reasoning_effort_override: str | None = None,
    reasoning_summary_override: str | None = None,
    max_completion_tokens_override: int | None = None,
) -> CrewAIProviderConfig:
    """Resolve CrewAI/OpenAI provider settings from global RPS env vars only."""

    del agent_name

    api_key = os.getenv("RPS_LLM_API_KEY")
    if not api_key:
        raise RuntimeError("RPS_LLM_API_KEY is required")

    model = model_override or os.getenv("RPS_LLM_MODEL") or "openai/gpt-5-mini"

    temperature = temperature_override
    if temperature is None:
        raw_temperature = os.getenv("RPS_LLM_TEMPERATURE")
        if raw_temperature:
            temperature = float(raw_temperature)

    reasoning_effort = reasoning_effort_override or os.getenv("RPS_LLM_REASONING_EFFORT")
    reasoning_summary = reasoning_summary_override or os.getenv("RPS_LLM_REASONING_SUMMARY")

    max_completion_tokens = max_completion_tokens_override
    if max_completion_tokens is None:
        raw_max = os.getenv("RPS_LLM_MAX_COMPLETION_TOKENS")
        if raw_max:
            max_completion_tokens = int(raw_max)

    return CrewAIProviderConfig(
        api_key=api_key,
        model=model,
        base_url=os.getenv("RPS_LLM_BASE_URL"),
        org_id=os.getenv("RPS_LLM_ORG_ID"),
        project_id=os.getenv("RPS_LLM_PROJECT_ID"),
        temperature=temperature,
        reasoning_effort=reasoning_effort,
        reasoning_summary=reasoning_summary,
        max_completion_tokens=max_completion_tokens,
    )


def build_crewai_llm_kwargs(
    agent_name: str,
    *,
    model_override: str | None = None,
    temperature_override: float | None = None,
    reasoning_effort_override: str | None = None,
    reasoning_summary_override: str | None = None,
    max_completion_tokens_override: int | None = None,
) -> dict[str, object]:
    """Build keyword arguments for ``crewai.LLM(...)``."""

    config = resolve_crewai_provider_config(
        agent_name,
        model_override=model_override,
        temperature_override=temperature_override,
        reasoning_effort_override=reasoning_effort_override,
        reasoning_summary_override=reasoning_summary_override,
        max_completion_tokens_override=max_completion_tokens_override,
    )
    kwargs: dict[str, object] = {
        "model": config.model,
        "api_key": config.api_key,
    }
    if config.base_url:
        kwargs["base_url"] = config.base_url
    if config.org_id:
        kwargs["organization"] = config.org_id
    if config.project_id:
        kwargs["project"] = config.project_id
    if config.temperature is not None:
        kwargs["temperature"] = config.temperature
    if config.reasoning_effort:
        kwargs["reasoning_effort"] = config.reasoning_effort
    if config.max_completion_tokens is not None:
        kwargs["max_completion_tokens"] = config.max_completion_tokens
    return kwargs


def resolve_crewai_planning_enabled(crew_name: str, *, default_enabled: bool) -> bool:
    """Return the configured planning-enabled default unchanged."""

    del crew_name
    return default_enabled


def resolve_crewai_planning_model(
    crew_name: str,
    *,
    default_model: str | None,
) -> str | None:
    """Return the configured planning-model default unchanged."""

    del crew_name
    return default_model


def build_crewai_planning_llm_kwargs(
    crew_name: str,
    *,
    default_model: str | None,
) -> dict[str, object] | None:
    """Build keyword arguments for a crew-level planning LLM."""

    model = resolve_crewai_planning_model(crew_name, default_model=default_model)
    if not model:
        return None
    api_key = os.getenv("RPS_LLM_API_KEY")
    if not api_key:
        raise RuntimeError("RPS_LLM_API_KEY is required")
    kwargs: dict[str, object] = {
        "model": model,
        "api_key": api_key,
    }
    base_url = os.getenv("RPS_LLM_BASE_URL")
    org_id = os.getenv("RPS_LLM_ORG_ID")
    project_id = os.getenv("RPS_LLM_PROJECT_ID")
    if base_url:
        kwargs["base_url"] = base_url
    if org_id:
        kwargs["organization"] = org_id
    if project_id:
        kwargs["project"] = project_id
    return kwargs
