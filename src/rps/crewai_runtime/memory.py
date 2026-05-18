"""CrewAI memory-policy helpers."""

from __future__ import annotations

import os
from typing import Any

from .config import CrewAIConfigBundle

JsonMap = dict[str, Any]


def mirror_openai_env_from_rps() -> None:
    """Expose RPS OpenAI env vars under the names CrewAI/OpenAI helpers expect."""

    mappings = {
        "OPENAI_API_KEY": os.getenv("RPS_LLM_API_KEY"),
        "OPENAI_BASE_URL": os.getenv("RPS_LLM_BASE_URL"),
        "OPENAI_ORG_ID": os.getenv("RPS_LLM_ORG_ID"),
        "OPENAI_PROJECT_ID": os.getenv("RPS_LLM_PROJECT_ID"),
    }
    for key, value in mappings.items():
        if value and not os.getenv(key):
            os.environ[key] = value


def _normalize_embedder_config(embedder: JsonMap) -> JsonMap:
    """Inject missing provider credentials into the CrewAI memory embedder config."""

    normalized = dict(embedder or {})
    provider = str(normalized.get("provider") or "").strip().lower()
    raw_config = normalized.get("config")
    config = dict(raw_config) if isinstance(raw_config, dict) else {}

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("RPS_LLM_API_KEY")
        if api_key and not config.get("api_key"):
            config["api_key"] = api_key
        base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("RPS_LLM_BASE_URL")
        if base_url:
            config.setdefault("base_url", base_url)
            config.setdefault("api_base", base_url)
        org_id = os.getenv("OPENAI_ORG_ID") or os.getenv("RPS_LLM_ORG_ID")
        if org_id and not config.get("organization"):
            config["organization"] = org_id
        project_id = os.getenv("OPENAI_PROJECT_ID") or os.getenv("RPS_LLM_PROJECT_ID")
        if project_id and not config.get("project"):
            config["project"] = project_id

    normalized["config"] = config
    return normalized


def _render_template(template: str, **values: str) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", value)
    return rendered


def resolve_crew_memory_profile(
    bundle: CrewAIConfigBundle,
    *,
    crew_name: str,
    athlete_id: str,
    surface: str = "default",
) -> JsonMap:
    """Resolve shared memory configuration for a crew/surface."""

    config = bundle.memory_policy
    crew_cfg = (config.get("crews") or {}).get(crew_name) or {}
    scope_template = str(crew_cfg.get("shared_scope_template") or "")
    storage_template = str(crew_cfg.get("storage_template") or "")
    return {
        "enabled": bool(crew_cfg.get("enabled", False)),
        "scope": _render_template(scope_template, athlete_id=athlete_id, surface=surface),
        "storage": _render_template(storage_template, athlete_id=athlete_id, surface=surface),
        "embedder": dict(config.get("default_embedder") or {}),
        "llm": config.get("default_llm"),
    }


def resolve_agent_memory_profile(
    bundle: CrewAIConfigBundle,
    *,
    agent_name: str,
    athlete_id: str,
    surface: str = "default",
) -> JsonMap:
    """Resolve optional private/scoped memory view for an agent."""

    config = bundle.memory_policy
    agent_cfg = (config.get("agents") or {}).get(agent_name) or {}
    scope_template = str(agent_cfg.get("scope_template") or "")
    read_scopes = [
        _render_template(str(item), athlete_id=athlete_id, surface=surface)
        for item in (agent_cfg.get("additional_read_scopes") or [])
    ]
    return {
        "mode": str(agent_cfg.get("mode") or "scope"),
        "scope": _render_template(scope_template, athlete_id=athlete_id, surface=surface),
        "additional_read_scopes": read_scopes,
    }


def build_memory_instance(crewai_module: Any, *, storage: str | None, embedder: JsonMap, llm: str | None) -> Any:
    """Build a CrewAI Memory instance when the package is available."""

    Memory = getattr(crewai_module, "Memory", None)
    if Memory is None:
        return None
    mirror_openai_env_from_rps()
    kwargs: JsonMap = {}
    if storage:
        kwargs["storage"] = storage
    if embedder:
        kwargs["embedder"] = _normalize_embedder_config(embedder)
    if llm:
        kwargs["llm"] = llm
    return Memory(**kwargs)


def build_crew_memory_kwargs(
    crewai_module: Any,
    *,
    profile: JsonMap,
) -> JsonMap:
    """Build Crew-level memory kwargs for CrewAI construction."""

    if not profile.get("enabled"):
        return {}
    normalized_embedder = _normalize_embedder_config(profile.get("embedder") or {})
    memory = build_memory_instance(
        crewai_module,
        storage=profile.get("storage"),
        embedder=normalized_embedder,
        llm=profile.get("llm"),
    )
    if memory is None:
        return {}
    return {"memory": memory, "embedder": normalized_embedder}


def build_agent_memory_value(
    *,
    shared_memory: Any | None,
    profile: JsonMap,
) -> Any | None:
    """Build optional agent memory value or scope from the shared memory object."""

    if shared_memory is None or not profile.get("scope"):
        return None
    mode = str(profile.get("mode") or "scope")
    scope = str(profile["scope"])
    if mode == "disabled":
        return None
    if mode == "read_only":
        return shared_memory.slice(scopes=[scope], read_only=True)
    if mode == "slice_read_only":
        scopes = [scope, *[str(item) for item in profile.get("additional_read_scopes") or []]]
        return shared_memory.slice(scopes=scopes, read_only=True)
    return shared_memory.scope(scope)
