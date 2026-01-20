"""Vector store sync helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import os
import re
from typing import Any, Iterable

import yaml

from app.openai.client import get_client
from app.openai.vectorstore_state import update_state_for_store

MANAGED_BY = "sync_vectorstores"


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


def env_key_for_agent(agent: str) -> str:
    """Return the env var name used for a given agent's vector store ID."""
    agent_key = agent.strip().lstrip("_")
    agent_key = re.sub(r"[^A-Za-z0-9]+", "_", agent_key).upper()
    return f"OPENAI_VECTORSTORE_{agent_key}_ID"


def list_vector_stores(client) -> Iterable:
    """Yield all vector stores via pagination."""
    after = None
    while True:
        page = client.vector_stores.list(limit=100, after=after)
        for entry in page.data:
            yield entry
        if not getattr(page, "has_more", False):
            break
        after = page.data[-1].id


def list_files(client) -> Iterable:
    """Yield all files via pagination."""
    after = None
    while True:
        page = client.files.list(limit=100, after=after)
        for entry in page.data:
            yield entry
        if not getattr(page, "has_more", False):
            break
        after = page.data[-1].id


def list_vector_store_files(client, vector_store_id: str) -> list:
    """List all files attached to a vector store."""
    entries = []
    after = None
    while True:
        page = client.vector_stores.files.list(
            vector_store_id=vector_store_id,
            limit=100,
            after=after,
        )
        entries.extend(page.data)
        if not getattr(page, "has_more", False):
            break
        after = page.data[-1].id
    return entries


def ensure_vector_store_id(client, manifest: Manifest) -> str:
    """Return a vector store ID, creating the store if needed."""
    env_key = env_key_for_agent(manifest.agent)
    env_value = os.getenv(env_key)
    if env_value:
        return env_value

    for entry in list_vector_stores(client):
        if entry.name == manifest.vector_store_name:
            return entry.id

    created = client.vector_stores.create(
        name=manifest.vector_store_name,
        metadata={"agent": manifest.agent},
    )
    return created.id


def build_remote_index(client, vector_store_id: str) -> dict[str, dict]:
    """Build a remote index keyed by source path for delta syncing."""
    index: dict[str, dict] = {}
    for vs_file in list_vector_store_files(client, vector_store_id):
        file_obj = client.files.retrieve(vs_file.file_id)
        metadata = getattr(file_obj, "metadata", {}) or {}
        attributes = getattr(vs_file, "attributes", {}) or {}
        source_path = metadata.get("source_path") or attributes.get("path") or file_obj.filename
        tags_value = metadata.get("tags") or attributes.get("tags")
        tags: list[str] = []
        if isinstance(tags_value, str):
            tags = [item for item in tags_value.split(",") if item]
        elif isinstance(tags_value, list):
            tags = [str(item) for item in tags_value]
        index[source_path] = {
            "file_id": vs_file.file_id,
            "sha256": metadata.get("sha256") or attributes.get("sha256"),
            "managed": metadata.get("managed_by") == MANAGED_BY,
            "tags": tags,
        }
    return index


def _attach_file(
    client,
    vector_store_id: str,
    file_id: str,
    attributes: dict[str, Any],
) -> None:
    """Attach a file to a vector store, using file_batches when available."""
    if hasattr(client.vector_stores, "file_batches"):
        try:
            client.vector_stores.file_batches.create_and_poll(
                vector_store_id=vector_store_id,
                files=[{"file_id": file_id, "attributes": attributes}],
            )
            return
        except Exception:
            pass

    client.vector_stores.files.create(
        vector_store_id=vector_store_id,
        file_id=file_id,
    )


def upload_source(
    client,
    vector_store_id: str,
    source: SourceSpec,
    source_path: Path,
) -> tuple[str, str]:
    """Upload a source file and attach it to the vector store."""
    sha256 = compute_sha256(source_path)
    metadata = {
        "managed_by": MANAGED_BY,
        "source_path": source.path,
        "sha256": sha256,
    }
    if source.tags:
        metadata["tags"] = ",".join(source.tags)

    with source_path.open("rb") as handle:
        file_obj = client.files.create(
            file=handle,
            purpose="assistants",
            metadata=metadata,
        )

    attributes = {
        "path": source.path,
        "sha256": sha256,
        "tags": ",".join(source.tags) if source.tags else "",
    }
    _attach_file(client, vector_store_id, file_obj.id, attributes)
    return file_obj.id, sha256


def sync_manifest(
    manifest_path: Path,
    delete_removed: bool = False,
    dry_run: bool = False,
    state: dict[str, Any] | None = None,
) -> dict[str, int]:
    """Sync one manifest against OpenAI-hosted vector store files."""
    client = get_client()
    manifest = load_manifest(manifest_path)
    vector_store_id = ensure_vector_store_id(client, manifest)
    remote_index = build_remote_index(client, vector_store_id)

    stats = {"added": 0, "updated": 0, "removed": 0, "skipped": 0}
    desired_paths = {source.path for source in manifest.sources}

    for source in manifest.sources:
        local_path = (manifest.root / source.path).resolve()
        if not local_path.exists():
            print(f"Missing source: {local_path}")
            stats["skipped"] += 1
            continue

        local_sha = compute_sha256(local_path)
        remote = remote_index.get(source.path)
        if remote and remote.get("sha256") == local_sha:
            continue

        if remote and not remote.get("managed"):
            print(f"Skipping unmanaged remote file for {source.path}")
            stats["skipped"] += 1
            continue

        action = "update" if remote else "add"
        if dry_run:
            print(f"Would {action}: {source.path}")
        else:
            file_id, sha256 = upload_source(client, vector_store_id, source, local_path)
            if remote:
                client.vector_stores.files.delete(
                    vector_store_id=vector_store_id,
                    file_id=remote["file_id"],
                )
            remote_index[source.path] = {
                "file_id": file_id,
                "sha256": sha256,
                "managed": True,
                "tags": source.tags,
            }
        stats["updated" if remote else "added"] += 1

    if delete_removed:
        for source_path, remote in remote_index.items():
            if source_path in desired_paths:
                continue
            if not remote.get("managed"):
                continue
            if dry_run:
                print(f"Would remove: {source_path}")
            else:
                client.vector_stores.files.delete(
                    vector_store_id=vector_store_id,
                    file_id=remote["file_id"],
                )
            remote_index.pop(source_path, None)
            stats["removed"] += 1

    if state is not None:
        update_state_for_store(state, manifest.vector_store_name, vector_store_id, remote_index)

    return stats
