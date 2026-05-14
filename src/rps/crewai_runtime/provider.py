"""Direct CrewAI provider configuration resolved from RPS environment variables."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass


def _agent_env_key(agent_name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", agent_name).strip("_")
    return cleaned.upper() or "AGENT"


def _resolve_env(base_key: str, agent_name: str | None) -> str | None:
    if agent_name:
        agent_key = _agent_env_key(agent_name)
        override = os.getenv(f"{base_key}_{agent_key}")
        if override:
            return override
    return os.getenv(base_key)


def _resolve_bool_env(base_key: str, scope_name: str | None) -> bool | None:
    raw = _resolve_env(base_key, scope_name)
    if raw is None:
        return None
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return None


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
    """Resolve CrewAI/OpenAI provider settings directly from RPS env vars."""

    api_key = _resolve_env("RPS_LLM_API_KEY", agent_name)
    if not api_key:
        raise RuntimeError("RPS_LLM_API_KEY is required")
    model = (
        model_override
        or _resolve_env("RPS_LLM_MODEL", agent_name)
        or "openai/gpt-5-mini"
    )

    temperature = temperature_override
    if temperature is None:
        raw_temperature = _resolve_env("RPS_LLM_TEMPERATURE", agent_name)
        if raw_temperature:
            temperature = float(raw_temperature)

    reasoning_effort = reasoning_effort_override or _resolve_env("RPS_LLM_REASONING_EFFORT", agent_name)
    reasoning_summary = reasoning_summary_override or _resolve_env("RPS_LLM_REASONING_SUMMARY", agent_name)

    max_completion_tokens = max_completion_tokens_override
    if max_completion_tokens is None:
        raw_max = _resolve_env("RPS_LLM_MAX_COMPLETION_TOKENS", agent_name)
        if raw_max:
            max_completion_tokens = int(raw_max)

    return CrewAIProviderConfig(
        api_key=api_key,
        model=model,
        base_url=_resolve_env("RPS_LLM_BASE_URL", agent_name),
        org_id=_resolve_env("RPS_LLM_ORG_ID", agent_name),
        project_id=_resolve_env("RPS_LLM_PROJECT_ID", agent_name),
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
    """Resolve optional env override for CrewAI crew-level planning."""

    override = _resolve_bool_env("RPS_CREW_PLANNING", crew_name)
    if override is None:
        return default_enabled
    return override


def resolve_crewai_planning_model(
    crew_name: str,
    *,
    default_model: str | None,
) -> str | None:
    """Resolve the crew-level planning model with dedicated overrides."""

    return _resolve_env("RPS_CREW_PLANNING_LLM", crew_name) or default_model


def build_crewai_planning_llm_kwargs(
    crew_name: str,
    *,
    default_model: str | None,
) -> dict[str, object] | None:
    """Build keyword arguments for a crew-level planning LLM."""

    model = resolve_crewai_planning_model(crew_name, default_model=default_model)
    if not model:
        return None
    api_key = _resolve_env("RPS_LLM_API_KEY", None)
    if not api_key:
        raise RuntimeError("RPS_LLM_API_KEY is required")
    kwargs: dict[str, object] = {
        "model": model,
        "api_key": api_key,
    }
    base_url = _resolve_env("RPS_LLM_BASE_URL", None)
    org_id = _resolve_env("RPS_LLM_ORG_ID", None)
    project_id = _resolve_env("RPS_LLM_PROJECT_ID", None)
    if base_url:
        kwargs["base_url"] = base_url
    if org_id:
        kwargs["organization"] = org_id
    if project_id:
        kwargs["project"] = project_id
    return kwargs
