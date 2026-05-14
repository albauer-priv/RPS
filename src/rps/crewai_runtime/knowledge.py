"""CrewAI knowledge-source configuration and runtime helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import CrewAIConfigBundle

JsonMap = dict[str, Any]


def _bundle_sources(bundle_cfg: JsonMap, bundle_name: str) -> list[JsonMap]:
    bundles = bundle_cfg.get("bundles") or {}
    source_bundle = bundles.get(bundle_name) or {}
    sources = source_bundle.get("sources") or []
    return [dict(item) for item in sources if isinstance(item, dict)]


def resolve_agent_knowledge_profile(
    bundle: CrewAIConfigBundle,
    *,
    agent_name: str,
) -> JsonMap:
    """Resolve configured static knowledge sources for one agent."""

    config = bundle.knowledge_sources
    agents = config.get("agents") or {}
    agent_cfg = agents.get(agent_name) or {}
    bundle_names = [str(item) for item in (agent_cfg.get("bundles") or [])]
    sources: list[JsonMap] = []
    seen_paths: set[str] = set()
    for bundle_name in bundle_names:
        for source in _bundle_sources(config, bundle_name):
            path = str(source.get("path") or "")
            if not path or path in seen_paths:
                continue
            seen_paths.add(path)
            sources.append(source)
    return {
        "sources": sources,
        "knowledge_config": dict(agent_cfg.get("knowledge_config") or {}),
        "bundles": bundle_names,
    }


def resolve_crew_knowledge_profile(
    bundle: CrewAIConfigBundle,
    *,
    crew_name: str,
) -> JsonMap:
    """Resolve configured shared static knowledge sources for one crew."""

    config = bundle.knowledge_sources
    crews = config.get("crews") or {}
    crew_cfg = crews.get(crew_name) or {}
    bundle_names = [str(item) for item in (crew_cfg.get("bundles") or [])]
    sources: list[JsonMap] = []
    seen_paths: set[str] = set()
    for bundle_name in bundle_names:
        for source in _bundle_sources(config, bundle_name):
            path = str(source.get("path") or "")
            if not path or path in seen_paths:
                continue
            seen_paths.add(path)
            sources.append(source)
    return {
        "sources": sources,
        "knowledge_config": dict(crew_cfg.get("knowledge_config") or {}),
        "bundles": bundle_names,
    }


def build_crewai_knowledge_kwargs(
    *,
    root: Path,
    profile: JsonMap,
) -> JsonMap:
    """Build CrewAI knowledge_sources / knowledge_config kwargs when runtime is available."""

    kwargs: JsonMap = {}
    sources = profile.get("sources") or []
    if sources:
        try:
            knowledge_source_module = __import__(
                "crewai.knowledge.source.string_knowledge_source",
                fromlist=["StringKnowledgeSource"],
            )
            StringKnowledgeSource = getattr(knowledge_source_module, "StringKnowledgeSource")
        except Exception:
            StringKnowledgeSource = None
        if StringKnowledgeSource is not None:
            kwargs["knowledge_sources"] = [
                StringKnowledgeSource(content=(root / str(source["path"])).read_text(encoding="utf-8"))
                for source in sources
            ]
    knowledge_cfg = profile.get("knowledge_config") or {}
    if knowledge_cfg:
        try:
            knowledge_cfg_module = __import__(
                "crewai.knowledge.knowledge_config",
                fromlist=["KnowledgeConfig"],
            )
            KnowledgeConfig = getattr(knowledge_cfg_module, "KnowledgeConfig")
            kwargs["knowledge_config"] = KnowledgeConfig(**knowledge_cfg)
        except Exception:
            kwargs["knowledge_config"] = knowledge_cfg
    return kwargs
