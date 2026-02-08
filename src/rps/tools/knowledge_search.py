"""Knowledge search tool backed by local Qdrant."""

from __future__ import annotations

from typing import Any

from qdrant_client.models import Filter

from rps.agents.registry import AGENTS
from rps.openai.vectorstore_state import VectorStoreResolver
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


def search_knowledge(
    agent_name: str,
    query: str,
    max_results: int = 5,
    tags: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Search the local vectorstore for a query."""
    if not query or not query.strip():
        return []
    collection = _resolve_collection(agent_name)
    client = get_qdrant_client()
    config = resolve_embedding_config()
    vector = embed_texts([query], config)[0]
    tag_filter: Filter | None = build_tag_filter(tags)
    results = search_points(
        client,
        collection_name=collection,
        query_vector=vector,
        limit=max(1, min(int(max_results), 20)),
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
