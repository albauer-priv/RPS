"""Vector store sync helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import os
import random
import re
import sys
import time
from typing import Any, Callable, Iterable

import yaml

from rps.openai.client import get_client
from rps.openai.vectorstore_state import update_state_for_store

MANAGED_BY = "sync_vectorstores"
_RETRY_ATTEMPTS = 5
_RETRY_BASE_SECONDS = 0.5
_RETRY_MAX_SECONDS = 6.0
_TRANSIENT_STATUS = {429, 500, 502, 503, 504}
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


def _is_transient_error(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None)
    if status in _TRANSIENT_STATUS:
        return True
    code = getattr(exc, "code", None)
    if code in {"server_error", "rate_limit_exceeded", "timeout"}:
        return True
    message = str(exc).lower()
    if "server error" in message or "rate limit" in message or "timeout" in message:
        return True
    return False


def _call_with_retry(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    for attempt in range(1, _RETRY_ATTEMPTS + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            if not _is_transient_error(exc) or attempt >= _RETRY_ATTEMPTS:
                raise
            delay = min(_RETRY_MAX_SECONDS, _RETRY_BASE_SECONDS * (2 ** (attempt - 1)))
            delay += random.uniform(0, min(0.25, delay / 2))
            print(
                f"Vector store API error (attempt {attempt}/{_RETRY_ATTEMPTS}): {exc}. "
                f"Retrying in {delay:.1f}s...",
                file=sys.stderr,
            )
            time.sleep(delay)


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


def _extract_front_matter(text: str) -> dict[str, Any] | None:
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


def _join_list(values: Any) -> str | None:
    if not values:
        return None
    if isinstance(values, list):
        items = [str(item).strip() for item in values if str(item).strip()]
    else:
        items = [str(values).strip()]
    if not items:
        return None
    return "|".join(items)


def _format_dependency(item: Any) -> str | None:
    if not isinstance(item, dict):
        value = str(item).strip()
        return value or None
    for key in ("Specification-ID", "Interface-ID", "ID"):
        value = item.get(key)
        if value:
            version = item.get("Version")
            if version:
                return f"{value}@{version}"
            return str(value)
    return None


def _flatten_header_attributes(header: dict[str, Any]) -> dict[str, str]:
    attrs: dict[str, str] = {}

    def add(key: str, value: Any) -> None:
        if value is None:
            return
        text = str(value).strip()
        if text:
            attrs[key] = text

    def add_list(key: str, value: Any) -> None:
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
    if isinstance(implements, dict):
        add("implements_interface_id", implements.get("Interface-ID"))
        add("implements_interface_version", implements.get("Version"))

    dependencies = header.get("Dependencies")
    if isinstance(dependencies, list):
        dep_values = [_format_dependency(item) for item in dependencies]
        dep_values = [item for item in dep_values if item]
        add_list("dependencies_ids", dep_values)

    binding_specs = header.get("Binding-Specs")
    if isinstance(binding_specs, list):
        spec_values = [_format_dependency(item) for item in binding_specs]
        spec_values = [item for item in spec_values if item]
        add_list("binding_specs_ids", spec_values)

    temporal_scope = header.get("Temporal-Scope")
    if isinstance(temporal_scope, dict):
        add("temporal_scope_from", temporal_scope.get("From"))
        add("temporal_scope_to", temporal_scope.get("To"))

    id_value = (
        header.get("Specification-ID")
        or header.get("Policy-ID")
        or header.get("Contract-Name")
        or header.get("Interface-ID")
        or header.get("Template-ID")
    )
    add("id", id_value)

    return attrs


def _extract_markdown_attributes(source_path: Path) -> dict[str, str]:
    try:
        text = source_path.read_text(encoding="utf-8")
    except Exception:
        return {}
    header = _extract_front_matter(text)
    if not header:
        return {}
    return _flatten_header_attributes(header)


def _extract_json_attributes(source_path: Path) -> dict[str, str]:
    try:
        data = json.loads(source_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}

    meta = data.get("meta")
    if isinstance(meta, dict) and "artifact_type" in meta:
        attrs: dict[str, str] = {"doc_type": "ArtifactJson"}
        for key in (
            "artifact_type",
            "schema_id",
            "schema_version",
            "version",
            "authority",
            "owner_agent",
            "run_id",
            "iso_week",
            "iso_week_range",
            "scope",
        ):
            value = meta.get(key)
            if value:
                attrs[key] = str(value)
        return attrs

    schema_id = data.get("$id")
    if schema_id:
        attrs = {"doc_type": "JsonSchema", "schema_id": str(schema_id), "id": str(schema_id)}
        title = data.get("title")
        if title:
            attrs["schema_title"] = str(title)
        if isinstance(schema_id, str) and schema_id.endswith(".schema.json"):
            attrs["schema_for"] = schema_id[: -len(".schema.json")]
        return attrs

    return {}


def build_source_attributes(source_path: Path) -> dict[str, str]:
    if source_path.suffix.lower() == ".md":
        return _extract_markdown_attributes(source_path)
    if source_path.suffix.lower() == ".json":
        return _extract_json_attributes(source_path)
    return {}


def _filter_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    """Limit attributes to a stable allowlist to satisfy API key count caps."""
    if not attributes:
        return {}
    filtered: dict[str, Any] = {}
    for key in _ATTRIBUTE_ALLOWLIST:
        value = attributes.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        filtered[key] = value
        if len(filtered) >= _MAX_ATTRIBUTE_KEYS:
            break
    return filtered


def env_key_for_agent(agent: str) -> str:
    """Return the env var name used for a given agent's vector store ID."""
    agent_key = agent.strip().lstrip("_")
    agent_key = re.sub(r"[^A-Za-z0-9]+", "_", agent_key).upper()
    return f"RPS_LLM_VECTORSTORE_{agent_key}_ID"


def list_vector_stores(client) -> Iterable:
    """Yield all vector stores via pagination."""
    after = None
    while True:
        page = _call_with_retry(client.vector_stores.list, limit=100, after=after)
        for entry in page.data:
            yield entry
        if not getattr(page, "has_more", False):
            break
        after = page.data[-1].id


def list_files(client) -> Iterable:
    """Yield all files via pagination."""
    after = None
    while True:
        page = _call_with_retry(client.files.list, limit=100, after=after)
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
        page = _call_with_retry(
            client.vector_stores.files.list,
            vector_store_id=vector_store_id,
            limit=100,
            after=after,
        )
        entries.extend(page.data)
        if not getattr(page, "has_more", False):
            break
        after = page.data[-1].id
    return entries


def _format_progress(index: int, total: int) -> str:
    if total:
        return f"[{index}/{total}]"
    return "[0/0]"


def clear_vector_store_files(
    client,
    vector_store_id: str,
    *,
    dry_run: bool = False,
    progress: bool = False,
) -> int:
    """Detach all files from a vector store."""
    entries = list_vector_store_files(client, vector_store_id)
    total = len(entries)
    removed = 0

    for index, entry in enumerate(entries, start=1):
        file_id = getattr(entry, "file_id", None) or getattr(entry, "id", None)
        if progress:
            label = file_id or "unknown"
            print(f"{_format_progress(index, total)} reset: {label}")
        if not file_id:
            continue
        if not dry_run:
            _call_with_retry(
                client.vector_stores.files.delete,
                vector_store_id=vector_store_id,
                file_id=file_id,
            )
        removed += 1
    return removed


def ensure_vector_store_id(client, manifest: Manifest) -> str:
    """Return a vector store ID, creating the store if needed."""
    env_key = env_key_for_agent(manifest.agent)
    env_value = os.getenv(env_key)
    if env_value:
        return env_value

    for entry in list_vector_stores(client):
        if entry.name == manifest.vector_store_name:
            return entry.id

    created = _call_with_retry(
        client.vector_stores.create,
        name=manifest.vector_store_name,
        metadata={"agent": manifest.agent},
    )
    return created.id


def build_remote_index(client, vector_store_id: str) -> dict[str, dict]:
    """Build a remote index keyed by source path for delta syncing."""
    index: dict[str, dict] = {}
    for vs_file in list_vector_store_files(client, vector_store_id):
        attributes = getattr(vs_file, "attributes", {}) or {}
        file_id = getattr(vs_file, "file_id", None)
        vs_file_id = getattr(vs_file, "id", None)
        file_obj = None
        metadata: dict[str, Any] = {}
        if file_id:
            file_obj = _call_with_retry(client.files.retrieve, file_id)
            metadata = (getattr(file_obj, "metadata", {}) or {})
        source_path = (
            attributes.get("source_path")
            or attributes.get("path")
            or metadata.get("source_path")
            or metadata.get("path")
        )
        if not source_path and file_obj is not None:
            source_path = file_obj.filename
        if not source_path:
            continue
        tags_value = attributes.get("tags") or metadata.get("tags")
        tags: list[str] = []
        if isinstance(tags_value, str):
            tags = [item for item in tags_value.split(",") if item]
        elif isinstance(tags_value, list):
            tags = [str(item) for item in tags_value]
        index[source_path] = {
            "file_id": file_id,
            "vs_file_id": vs_file_id,
            "sha256": attributes.get("sha256") or metadata.get("sha256"),
            "managed": (
                attributes.get("managed_by") == MANAGED_BY
                or metadata.get("managed_by") == MANAGED_BY
            ),
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
            _call_with_retry(
                client.vector_stores.file_batches.create_and_poll,
                vector_store_id=vector_store_id,
                files=[{"file_id": file_id, "attributes": attributes}],
            )
            return
        except Exception:
            pass

    _call_with_retry(
        client.vector_stores.files.create,
        vector_store_id=vector_store_id,
        file_id=file_id,
        attributes=attributes,
    )


def upload_source(
    client,
    vector_store_id: str,
    source: SourceSpec,
    source_path: Path,
) -> tuple[str, str]:
    """Upload a source file and attach it to the vector store."""
    sha256 = compute_sha256(source_path)

    def _create_file():
        with source_path.open("rb") as handle:
            return client.files.create(
                file=handle,
                purpose="assistants",
            )

    file_obj = _call_with_retry(_create_file)

    attributes = {
        "managed_by": MANAGED_BY,
        "sha256": sha256,
        "tags": ",".join(source.tags) if source.tags else "",
    }
    attributes.update(build_source_attributes(source_path))
    attributes = _filter_attributes(attributes)
    _attach_file(client, vector_store_id, file_obj.id, attributes)
    return file_obj.id, sha256


def sync_manifest(
    manifest_path: Path,
    delete_removed: bool = False,
    dry_run: bool = False,
    reset: bool = False,
    progress: bool = False,
    state: dict[str, Any] | None = None,
) -> dict[str, int]:
    """Sync one manifest against OpenAI-hosted vector store files."""
    client = get_client()
    manifest = load_manifest(manifest_path)
    vector_store_id = ensure_vector_store_id(client, manifest)

    stats = {"added": 0, "updated": 0, "removed": 0, "skipped": 0}
    if progress:
        print(f"Syncing store: {manifest.vector_store_name}")

    if reset:
        if progress:
            print(f"Clearing vector store: {vector_store_id}")
        stats["removed"] += clear_vector_store_files(
            client,
            vector_store_id,
            dry_run=dry_run,
            progress=progress,
        )
        remote_index: dict[str, dict] = {}
    else:
        remote_index = build_remote_index(client, vector_store_id)
    desired_paths = {source.path for source in manifest.sources}
    total_sources = len(manifest.sources)

    for index, source in enumerate(manifest.sources, start=1):
        local_path = (manifest.root / source.path).resolve()
        if not local_path.exists():
            if progress:
                print(f"{_format_progress(index, total_sources)} missing: {source.path}")
            else:
                print(f"Missing source: {local_path}")
            stats["skipped"] += 1
            continue

        local_sha = compute_sha256(local_path)
        remote = remote_index.get(source.path)
        if remote and remote.get("sha256") == local_sha:
            if progress:
                print(f"{_format_progress(index, total_sources)} ok: {source.path}")
            continue

        if remote and not remote.get("managed"):
            if progress:
                print(f"{_format_progress(index, total_sources)} skip unmanaged: {source.path}")
            else:
                print(f"Skipping unmanaged remote file for {source.path}")
            stats["skipped"] += 1
            continue

        action = "update" if remote else "add"
        if dry_run:
            if progress:
                print(f"{_format_progress(index, total_sources)} would {action}: {source.path}")
            else:
                print(f"Would {action}: {source.path}")
        else:
            file_id, sha256 = upload_source(client, vector_store_id, source, local_path)
            if remote:
                delete_id = remote.get("vs_file_id") or remote.get("file_id")
                if delete_id:
                    _call_with_retry(
                        client.vector_stores.files.delete,
                        vector_store_id=vector_store_id,
                        file_id=delete_id,
                    )
            remote_index[source.path] = {
                "file_id": file_id,
                "vs_file_id": None,
                "sha256": sha256,
                "managed": True,
                "tags": source.tags,
            }
            if progress:
                print(f"{_format_progress(index, total_sources)} {action}: {source.path}")
        stats["updated" if remote else "added"] += 1

    if delete_removed:
        removals = [
            (source_path, remote)
            for source_path, remote in remote_index.items()
            if source_path not in desired_paths and remote.get("managed")
        ]
        total_removals = len(removals)
        for index, (source_path, remote) in enumerate(removals, start=1):
            if dry_run:
                if progress:
                    print(
                        f"{_format_progress(index, total_removals)} would remove: {source_path}"
                    )
                else:
                    print(f"Would remove: {source_path}")
            else:
                delete_id = remote.get("vs_file_id") or remote.get("file_id")
                if delete_id:
                    _call_with_retry(
                        client.vector_stores.files.delete,
                        vector_store_id=vector_store_id,
                        file_id=delete_id,
                    )
                if progress:
                    print(f"{_format_progress(index, total_removals)} removed: {source_path}")
            remote_index.pop(source_path, None)
            stats["removed"] += 1

    if state is not None:
        update_state_for_store(state, manifest.vector_store_name, vector_store_id, remote_index)

    return stats
