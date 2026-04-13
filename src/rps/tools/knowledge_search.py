"""Knowledge search tool backed by local Qdrant."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from qdrant_client.models import Filter

from rps.agents.registry import AGENTS
from rps.openai.vectorstore_state import DEFAULT_STATE_PATH, VectorStoreResolver, load_state, write_state
from rps.openai.vectorstores import compute_manifest_hash, iter_manifest_paths, load_manifest, sync_manifest
from rps.vectorstores.qdrant_local import (
    build_tag_filter,
    embed_texts,
    get_qdrant_client,
    resolve_embedding_config,
    search_points,
)


def _resolve_collection(agent_name: str) -> str:
    spec = AGENTS.get(agent_name)
    if not spec:
        raise ValueError(f"Unknown agent: {agent_name}")
    resolver = VectorStoreResolver()
    return resolver.id_for_store_name(spec.vector_store_name)


def _manifest_for_store(store_name: str) -> Path:
    knowledge_root = Path("specs/knowledge")
    for manifest_path in iter_manifest_paths(knowledge_root):
        manifest = load_manifest(manifest_path)
        if manifest.vector_store_name == store_name:
            return manifest_path
    raise FileNotFoundError(f"Manifest not found for vector store {store_name}")


def _rebuild_collection_for_agent(agent_name: str) -> None:
    spec = AGENTS.get(agent_name)
    if not spec:
        raise ValueError(f"Unknown agent: {agent_name}")
    manifest_path = _manifest_for_store(spec.vector_store_name)
    state = load_state(DEFAULT_STATE_PATH)
    sync_manifest(
        manifest_path=manifest_path,
        delete_removed=True,
        reset=True,
        progress=False,
        state=state,
    )
    store_entry = state.setdefault("vectorstores", {}).setdefault(spec.vector_store_name, {})
    store_entry["manifest_hash"] = compute_manifest_hash(manifest_path)
    write_state(DEFAULT_STATE_PATH, state)


def _is_missing_collection_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "not found" in text and "collection" in text


def search_knowledge(
    agent_name: str,
    query: str,
    max_results: int = 5,
    tags: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Search the local vectorstore for a query."""
    if not query or not query.strip():
        return []
    client = get_qdrant_client()
    config = resolve_embedding_config()
    vector = embed_texts([query], config)[0]
    tag_filter: Filter | None = build_tag_filter(tags)
    limit = max(1, min(int(max_results), 20))
    collection = _resolve_collection(agent_name)
    try:
        results = search_points(
            client,
            collection_name=collection,
            query_vector=vector,
            limit=limit,
            with_payload=True,
            query_filter=tag_filter,
        )
    except Exception as exc:
        if not _is_missing_collection_error(exc):
            raise
        _rebuild_collection_for_agent(agent_name)
        collection = _resolve_collection(agent_name)
        results = search_points(
            client,
            collection_name=collection,
            query_vector=vector,
            limit=limit,
            with_payload=True,
            query_filter=tag_filter,
        )
    output: list[dict[str, Any]] = []
    for result in results:
        payload = result.payload or {}
        output.append(
            {
                "text": payload.get("text"),
                "source_path": payload.get("source_path"),
                "score": result.score,
                "tags": payload.get("tags"),
                "attributes": payload.get("attributes"),
                "chunk_index": payload.get("chunk_index"),
            }
        )
    return output
