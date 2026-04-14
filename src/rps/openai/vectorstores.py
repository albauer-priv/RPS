"""Vector store sync helpers."""

from __future__ import annotations

import hashlib
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml
from qdrant_client.models import Distance, PointStruct, VectorParams

from rps.openai.vectorstore_state import update_state_for_store
from rps.vectorstores.qdrant_local import embed_texts, get_qdrant_client, resolve_embedding_config

MANAGED_BY = "sync_vectorstores"
_MAX_ATTRIBUTE_KEYS = 16
_ATTRIBUTE_ALLOWLIST = [
    "managed_by",
    "id",
    "doc_type",
    "type",
    "scope",
    "authority",
    "applies_to",
    "tags",
]

AttributeMap = dict[str, str]
RemoteIndexEntry = dict[str, object]
ChunkPayload = dict[str, object]
FrontMatter = dict[str, object]
ChunkRecord = dict[str, str | ChunkPayload]


@dataclass(frozen=True)
class SourceSpec:
    """Local source definition loaded from a knowledge manifest."""

    path: str
    tags: list[str]


@dataclass(frozen=True)
class Manifest:
    """Parsed manifest describing an agent's vector store sources."""

    agent: str
    vector_store_name: str
    description: str
    sources: list[SourceSpec]
    root: Path


def iter_manifest_paths(knowledge_root: Path) -> list[Path]:
    """Return all manifest.yaml paths under the knowledge root."""
    unified = knowledge_root / "all_agents" / "manifest.yaml"
    if unified.exists():
        return [unified]
    return sorted(knowledge_root.glob("**/manifest.yaml"))


def load_manifest(path: Path) -> Manifest:
    """Parse a manifest.yaml into a Manifest object."""
    raw = yaml.safe_load(path.read_text()) or {}
    agent = str(raw.get("agent", "")).strip()
    vector_store_name = str(raw.get("vector_store_name", "")).strip()
    description = str(raw.get("description", "")).strip()
    sources_raw = raw.get("sources") or []

    sources: list[SourceSpec] = []
    for item in sources_raw:
        if not isinstance(item, dict):
            continue
        source_path = str(item.get("path", "")).strip()
        if not source_path:
            continue
        tags = item.get("tags") or []
        if not isinstance(tags, list):
            tags = [str(tags)]
        sources.append(SourceSpec(path=source_path, tags=[str(tag) for tag in tags]))

    if not agent:
        raise ValueError(f"Missing agent in {path}")
    if not vector_store_name:
        raise ValueError(f"Missing vector_store_name in {path}")

    return Manifest(
        agent=agent,
        vector_store_name=vector_store_name,
        description=description,
        sources=sources,
        root=path.parent,
    )


def compute_sha256(path: Path) -> str:
    """Compute a SHA-256 hash for a file on disk."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compute_manifest_hash(manifest_path: Path) -> str:
    """Return a deterministic hash for a manifest + its source files."""
    manifest = load_manifest(manifest_path)
    entries: list[str] = [f"manifest:{compute_sha256(manifest_path)}"]
    for source in manifest.sources:
        source_path = (manifest.root / source.path).resolve()
        if source_path.exists():
            entries.append(f"{source.path}:{compute_sha256(source_path)}")
        else:
            entries.append(f"{source.path}:missing")
    digest = hashlib.sha256()
    digest.update("\n".join(sorted(entries)).encode("utf-8"))
    return digest.hexdigest()


def _extract_front_matter(text: str) -> FrontMatter | None:
    lines = text.splitlines()
    if not lines:
        return None
    if lines[0].strip() != "---":
        return None
    end_index = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_index = idx
            break
    if end_index is None:
        return None
    raw = "\n".join(lines[1:end_index])
    try:
        data = yaml.safe_load(raw) or {}
    except Exception:
        return None
    if isinstance(data, dict):
        return data
    return None


def _join_list(values: object) -> str | None:
    if not values:
        return None
    if isinstance(values, list):
        items = [str(item).strip() for item in values if str(item).strip()]
    else:
        items = [str(values).strip()]
    if not items:
        return None
    return "|".join(items)


def _format_dependency(item: object) -> str | None:
    if not isinstance(item, dict):
        text_value = str(item).strip()
        return text_value or None
    for key in ("Specification-ID", "Interface-ID", "ID"):
        raw_value = item.get(key)
        if raw_value:
            version = item.get("Version")
            if version:
                return f"{raw_value}@{version}"
            return str(raw_value)
    return None


def _flatten_header_attributes(header: FrontMatter) -> AttributeMap:
    attrs: AttributeMap = {}

    def add(key: str, value: object) -> None:
        if value is None:
            return
        text = str(value).strip()
        if text:
            attrs[key] = text

    def add_list(key: str, value: object) -> None:
        joined = _join_list(value)
        if joined:
            attrs[key] = joined

    add("doc_type", "Markdown")
    add("type", header.get("Type"))
    add("specification_for", header.get("Specification-For"))
    add("specification_id", header.get("Specification-ID"))
    add("policy_id", header.get("Policy-ID"))
    add("interface_for", header.get("Interface-For"))
    add("interface_id", header.get("Interface-ID"))
    add("template_for", header.get("Template-For"))
    add("template_id", header.get("Template-ID"))
    add("contract_name", header.get("Contract-Name"))
    add("status", header.get("Status"))
    add("scope", header.get("Scope"))
    add("authority", header.get("Authority"))
    add("version", header.get("Version"))
    add("normative_role", header.get("Normative-Role"))
    add("decision_authority", header.get("Decision-Authority"))
    add("owner_agent", header.get("Owner-Agent"))
    add("from_agent", header.get("From-Agent"))
    add("to_agent", header.get("To-Agent"))

    add_list("applies_to", header.get("Applies-To"))
    add_list("explicitly_not_for", header.get("Explicitly-Not-For"))
    add_list("related_evidence", header.get("Related-Evidence"))

    implements = header.get("Implements")
    if implements:
        if isinstance(implements, list):
            formatted = [
                item for item in (_format_dependency(entry) for entry in implements) if item
            ]
            if formatted:
                attrs["implements"] = "|".join(formatted)
        else:
            value = _format_dependency(implements)
            if value:
                attrs["implements"] = value

    return attrs


def _resolve_qdrant_vector_size(collection_info: Any) -> int | None:
    """Return the configured vector size from a Qdrant collection info object."""
    try:
        vectors = collection_info.config.params.vectors
    except AttributeError:
        return None
    if isinstance(vectors, dict):
        first = next(iter(vectors.values()), None)
        return getattr(first, "size", None)
    return getattr(vectors, "size", None)


def _trim_attributes(attrs: AttributeMap) -> AttributeMap:
    if len(attrs) <= _MAX_ATTRIBUTE_KEYS:
        return attrs
    trimmed: AttributeMap = {}
    for key in _ATTRIBUTE_ALLOWLIST:
        if key in attrs:
            trimmed[key] = attrs[key]
    return trimmed


def _chunk_text(text: str, max_chars: int = 1200, overlap: int = 200) -> list[str]:
    """Chunk text into overlapping segments."""
    raw = text.strip()
    if not raw:
        return []
    paragraphs = [p.strip() for p in raw.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_chars:
            current = f"{current}\n\n{para}".strip()
            continue
        if current:
            chunks.append(current)
        if len(para) <= max_chars:
            current = para
        else:
            start = 0
            while start < len(para):
                end = min(len(para), start + max_chars)
                chunks.append(para[start:end])
                start = end - overlap if end < len(para) else end
            current = ""
    if current:
        chunks.append(current)
    return chunks


def _build_local_index(
    manifest: Manifest,
    reset: bool,
    client: Any | None = None,
) -> tuple[str, dict[str, RemoteIndexEntry], dict[str, int]]:
    """(Re)build a local Qdrant collection for a manifest."""
    client = client or get_qdrant_client()
    config = resolve_embedding_config()
    collection = manifest.vector_store_name

    chunks: list[ChunkRecord] = []
    remote_index: dict[str, RemoteIndexEntry] = {}
    stats = {"added": 0, "updated": 0, "removed": 0, "skipped": 0}

    for source in manifest.sources:
        local_path = (manifest.root / source.path).resolve()
        if not local_path.exists():
            stats["skipped"] += 1
            continue
        text = local_path.read_text(encoding="utf-8")
        sha256 = compute_sha256(local_path)
        header = _extract_front_matter(text)
        attrs = _flatten_header_attributes(header) if header else {}
        if source.tags:
            attrs["tags"] = "|".join(source.tags)
        attrs["source_path"] = source.path
        attrs["sha256"] = sha256
        attrs["managed_by"] = MANAGED_BY
        attrs = _trim_attributes(attrs)

        parts = _chunk_text(text)
        for idx, chunk in enumerate(parts):
            chunks.append(
                {
                    "id": str(uuid.uuid4()),
                    "text": chunk,
                    "payload": {
                        "text": chunk,
                        "source_path": source.path,
                        "sha256": sha256,
                        "tags": source.tags,
                        "attributes": attrs,
                        "chunk_index": idx,
                    },
                }
            )
        remote_index[source.path] = {
            "file_id": None,
            "sha256": sha256,
            "tags": source.tags,
            "managed": True,
        }
        stats["added"] += 1

    if reset:
        try:
            client.delete_collection(collection, timeout=30, wait=True)
        except (TypeError, AssertionError):
            client.delete_collection(collection, timeout=30)

    if not chunks:
        return collection, remote_index, stats

    batch_size = int(os.getenv("RPS_LLM_EMBEDDING_BATCH_SIZE", "32"))
    if batch_size < 1:
        batch_size = 32

    first_batch = chunks[:batch_size]
    first_vectors = embed_texts([cast(str, item["text"]) for item in first_batch], config)
    if not first_vectors:
        raise RuntimeError("Embedding model returned no vectors.")

    vector_size = len(first_vectors[0])
    if reset:
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
    else:
        try:
            existing = client.get_collection(collection)
        except Exception:
            existing = None
        if existing:
            current_size = _resolve_qdrant_vector_size(existing)
            if current_size != vector_size:
                client.recreate_collection(
                    collection_name=collection,
                    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
                )
        else:
            client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )

    def _upsert(batch: list[ChunkRecord], vectors: list[list[float]]) -> None:
        points = [
            PointStruct(
                id=str(item["id"]),
                vector=vector,
                payload=cast(dict[str, Any], item["payload"]),
            )
            for item, vector in zip(batch, vectors, strict=True)
        ]
        client.upsert(collection_name=collection, points=points, wait=True)

    _upsert(first_batch, first_vectors)
    for idx in range(batch_size, len(chunks), batch_size):
        batch = chunks[idx : idx + batch_size]
        vectors = embed_texts([cast(str, item["text"]) for item in batch], config)
        _upsert(batch, vectors)

    return collection, remote_index, stats


def sync_manifest(
    manifest_path: Path,
    delete_removed: bool = True,
    reset: bool = False,
    progress: bool = False,
    state: dict[str, Any] | None = None,
    client: Any | None = None,
) -> dict[str, int]:
    """Sync a manifest to a local Qdrant collection."""
    manifest = load_manifest(manifest_path)
    collection, remote_index, stats = _build_local_index(
        manifest,
        reset=reset,
        client=client,
    )

    if state is not None:
        update_state_for_store(state, manifest.vector_store_name, collection, remote_index)

    return stats
