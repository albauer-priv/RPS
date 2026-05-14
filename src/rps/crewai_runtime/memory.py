"""CrewAI memory-policy helpers."""

from __future__ import annotations

from typing import Any

from .config import CrewAIConfigBundle

JsonMap = dict[str, Any]


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
    kwargs: JsonMap = {}
    if storage:
        kwargs["storage"] = storage
    if embedder:
        kwargs["embedder"] = embedder
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
    memory = build_memory_instance(
        crewai_module,
        storage=profile.get("storage"),
        embedder=profile.get("embedder") or {},
        llm=profile.get("llm"),
    )
    if memory is None:
        return {}
    return {"memory": memory, "embedder": profile.get("embedder") or {}}


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
    if mode == "slice_read_only":
        scopes = [scope, *[str(item) for item in profile.get("additional_read_scopes") or []]]
        return shared_memory.slice(scopes=scopes, read_only=True)
    return shared_memory.scope(scope)
