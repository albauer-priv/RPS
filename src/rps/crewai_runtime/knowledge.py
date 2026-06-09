"""CrewAI knowledge-source configuration and runtime helpers."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .config import CrewAIConfigBundle
from .memory import mirror_openai_env_from_rps

JsonMap = dict[str, Any]
logger = logging.getLogger(__name__)

_KNOWLEDGE_SEARCH_GUARDS_READY = False
_KNOWLEDGE_QUERY_WORD_LIMIT = 600
_KNOWLEDGE_QUERY_CHAR_LIMIT = 4000
_QUERY_PRIORITY_MARKERS: tuple[str, ...] = (
    "Current Task:",
    "Current Step",
    "User request:",
    "Internal specialist task:",
    "The original query is:",
)


def _compact_query_text(text: str) -> str:
    """Collapse large CrewAI knowledge queries into a compact search-safe string."""

    candidate = text
    for marker in _QUERY_PRIORITY_MARKERS:
        idx = candidate.find(marker)
        if idx >= 0:
            candidate = candidate[idx:]
            break
    compact = " ".join(candidate.split())
    if not compact:
        compact = " ".join(text.split())
    words = compact.split()
    if len(words) > _KNOWLEDGE_QUERY_WORD_LIMIT:
        compact = " ".join(words[:_KNOWLEDGE_QUERY_WORD_LIMIT])
    if len(compact) > _KNOWLEDGE_QUERY_CHAR_LIMIT:
        compact = compact[:_KNOWLEDGE_QUERY_CHAR_LIMIT].rstrip()
    return compact


def _compact_knowledge_query(query: object) -> object:
    """Return a compact knowledge-search query for strings and string sequences."""

    if isinstance(query, str):
        return _compact_query_text(query)
    if isinstance(query, Sequence) and not isinstance(query, (bytes, bytearray, str)):
        compacted: list[object] = []
        for item in query:
            if isinstance(item, str):
                compacted.append(_compact_query_text(item))
            else:
                compacted.append(item)
        if isinstance(query, tuple):
            return tuple(compacted)
        return compacted
    return query


def _install_knowledge_search_guards() -> None:
    """Best-effort patch CrewAI knowledge search to compact oversized embedding queries."""

    global _KNOWLEDGE_SEARCH_GUARDS_READY
    if _KNOWLEDGE_SEARCH_GUARDS_READY:
        return
    try:
        module = __import__(
            "crewai.knowledge.storage.knowledge_storage",
            fromlist=["KnowledgeStorage"],
        )
        KnowledgeStorage = getattr(module, "KnowledgeStorage")
    except Exception:
        return

    original = getattr(KnowledgeStorage, "search", None)
    if original is None or getattr(original, "_rps_compacted", False):
        _KNOWLEDGE_SEARCH_GUARDS_READY = True
        return

    def _wrapped(self: object, *args: object, **kwargs: object) -> object:
        updated_args = list(args)
        truncated = False
        if "query" in kwargs:
            original_query = kwargs["query"]
            compacted = _compact_knowledge_query(original_query)
            truncated = compacted != original_query
            kwargs["query"] = compacted
        elif updated_args:
            original_query = updated_args[0]
            compacted = _compact_knowledge_query(original_query)
            truncated = compacted != original_query
            updated_args[0] = compacted
        if truncated:
            logger.debug("Compacted CrewAI knowledge query before embedding search.")
        return original(self, *updated_args, **kwargs)

    setattr(_wrapped, "_rps_compacted", True)
    setattr(KnowledgeStorage, "search", _wrapped)
    _KNOWLEDGE_SEARCH_GUARDS_READY = True


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
        _install_knowledge_search_guards()
        mirror_openai_env_from_rps()
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
