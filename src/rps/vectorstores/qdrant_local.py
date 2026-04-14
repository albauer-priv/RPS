"""Local Qdrant vectorstore helpers."""

from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import litellm
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchAny

from rps.core.config import load_settings


@dataclass(frozen=True)
class EmbeddingConfig:
    """Embedding configuration resolved from the environment."""

    model: str
    api_key: str
    base_url: str | None
    org_id: str | None
    project_id: str | None


def resolve_embedding_config() -> EmbeddingConfig:
    """Resolve embedding settings from environment variables."""
    settings = load_settings()
    model = os.getenv("RPS_LLM_EMBEDDING_MODEL", "text-embedding-3-small").strip()
    if not model:
        raise RuntimeError("RPS_LLM_EMBEDDING_MODEL is required")
    return EmbeddingConfig(
        model=model,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        org_id=settings.openai_org_id,
        project_id=settings.openai_project_id,
    )


def resolve_qdrant_path() -> str | None:
    """Return the configured Qdrant local path or None for in-memory."""
    raw = os.getenv("RPS_LLM_VECTORSTORE_PATH", ".cache/qdrant").strip()
    if not raw or raw.lower() in {"memory", ":memory:", "in-memory"}:
        return None
    return raw


@lru_cache(maxsize=4)
def _build_qdrant_client(path_key: str) -> QdrantClient:
    """Build and cache one Qdrant client per storage path."""
    if path_key == ":memory:":
        return QdrantClient(":memory:")
    return QdrantClient(path=path_key)


def get_qdrant_client() -> QdrantClient:
    """Return a local Qdrant client using the configured path."""
    path = resolve_qdrant_path()
    if path is None:
        return _build_qdrant_client(":memory:")
    return _build_qdrant_client(str(Path(path)))


def embed_texts(texts: Iterable[str], config: EmbeddingConfig | None = None) -> list[list[float]]:
    """Embed a sequence of texts using LiteLLM."""
    payload = list(texts)
    if not payload:
        return []
    cfg = config or resolve_embedding_config()
    response: Any = litellm.embedding(
        model=cfg.model,
        input=payload,
        api_key=cfg.api_key,
        api_base=cfg.base_url,
        organization=cfg.org_id,
        project=cfg.project_id,
    )
    data = response["data"] if isinstance(response, dict) else getattr(response, "data", [])
    return [item["embedding"] for item in data]


def build_tag_filter(tags: list[str] | None) -> Filter | None:
    """Return a Qdrant filter for tag matching, or None."""
    if not tags:
        return None
    cleaned = [tag.strip() for tag in tags if tag and tag.strip()]
    if not cleaned:
        return None
    return Filter(must=[FieldCondition(key="tags", match=MatchAny(any=cleaned))])


def search_points(
    client: QdrantClient,
    *,
    collection_name: str,
    query_vector: list[float],
    limit: int,
    with_payload: bool,
    query_filter: Filter | None = None,
):
    """Search a collection, supporting old/new Qdrant client APIs."""
    if hasattr(client, "search"):
        return client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            with_payload=with_payload,
            query_filter=query_filter,
        )
    response = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=limit,
        with_payload=with_payload,
        query_filter=query_filter,
    )
    if hasattr(response, "points"):
        return response.points
    if isinstance(response, dict) and "points" in response:
        return response["points"]
    return response
