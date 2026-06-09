"""Code-owned metadata construction for persisted artifact envelopes."""

from __future__ import annotations

import copy
import re
from datetime import UTC, datetime
from typing import Any

from rps.workspace.types import ArtifactType

JsonMap = dict[str, Any]

_SEMVER_PATTERN = re.compile(r"^[0-9]+\.[0-9]+(?:\.[0-9]+)?$")

CANONICAL_OWNER_BY_ARTIFACT: dict[ArtifactType, str] = {
    ArtifactType.SEASON_SCENARIOS: "Season-Scenario-Agent",
    ArtifactType.SEASON_SCENARIO_SELECTION: "Season-Scenario-Agent",
    ArtifactType.SEASON_PLAN: "Season-Artifact-Writer",
    ArtifactType.SEASON_PHASE_FEED_FORWARD: "Season-Artifact-Writer",
    ArtifactType.PHASE_GUARDRAILS: "Phase-Artifact-Writer",
    ArtifactType.PHASE_STRUCTURE: "Phase-Artifact-Writer",
    ArtifactType.PHASE_PREVIEW: "Phase-Artifact-Writer",
    ArtifactType.PHASE_FEED_FORWARD: "Phase-Artifact-Writer",
    ArtifactType.WEEK_PLAN: "Week-Artifact-Writer",
    ArtifactType.WEEK_WORKOUT_SELECTION_AUDIT: "Week-Selection-Auditor",
    ArtifactType.DES_ANALYSIS_REPORT: "Report-Artifact-Writer",
}


def utc_timestamp() -> str:
    """Return a canonical UTC timestamp for artifact metadata."""

    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def schema_semver(value: object, *, default: str = "1.0") -> str:
    """Return a schema-valid semantic version string."""

    rendered = str(value or "").strip()
    if _SEMVER_PATTERN.fullmatch(rendered):
        return rendered
    return default


def _as_str(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _schema_meta_const(schema: JsonMap | None, key: str) -> str | None:
    if not isinstance(schema, dict):
        return None
    meta_schema = schema.get("properties", {}).get("meta", {})
    if not isinstance(meta_schema, dict):
        return None
    value_schema = meta_schema.get("properties", {}).get(key, {})
    if isinstance(value_schema, dict):
        const = value_schema.get("const")
        if isinstance(const, str) and const:
            return const
    return None


def _schema_meta_schema(schema: JsonMap | None) -> JsonMap:
    if not isinstance(schema, dict):
        return {}
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return {}
    meta_schema = properties.get("meta")
    return meta_schema if isinstance(meta_schema, dict) else {}


def _schema_meta_properties(schema: JsonMap | None) -> set[str]:
    meta_schema = _schema_meta_schema(schema)
    properties = meta_schema.get("properties")
    if not isinstance(properties, dict):
        return set()
    return {str(key) for key in properties}


def _schema_meta_is_closed(schema: JsonMap | None) -> bool:
    return _schema_meta_schema(schema).get("additionalProperties") is False


def _looks_like_envelope_schema(schema: JsonMap | None) -> bool:
    if not isinstance(schema, dict):
        return False
    properties = schema.get("properties")
    return isinstance(properties, dict) and "meta" in properties and "data" in properties


def _artifact_type_value(artifact_type: ArtifactType | str | None, schema: JsonMap | None, meta: JsonMap) -> str:
    if isinstance(artifact_type, ArtifactType):
        return artifact_type.value
    if isinstance(artifact_type, str) and artifact_type:
        return artifact_type
    const = _schema_meta_const(schema, "artifact_type")
    if const:
        return const
    return str(meta.get("artifact_type") or "").strip().upper()


def normalize_trace_reference(entry: object, *, index: int = 1) -> JsonMap | None:
    """Return a schema-valid trace reference preserving operational version keys."""

    if not isinstance(entry, dict):
        return None
    artifact = _as_str(entry.get("artifact")) or f"legacy_trace_{index}"
    run_id = _as_str(entry.get("run_id")) or f"legacy_trace_{index}"
    raw_schema_version = entry.get("schema_version")
    raw_version = entry.get("version")
    raw_version_key = entry.get("version_key")

    schema_version = schema_semver(
        raw_schema_version if raw_schema_version is not None else raw_version,
    )
    version = schema_semver(raw_version, default=schema_version)
    version_key = _as_str(raw_version_key)
    if version_key is None:
        rendered_version = _as_str(raw_version)
        version_key = rendered_version or version

    return {
        "artifact": artifact,
        "version": version,
        "schema_version": schema_version,
        "version_key": version_key,
        "run_id": run_id,
    }


def normalize_trace_references(value: object) -> list[JsonMap]:
    """Return schema-valid trace reference objects."""

    if not isinstance(value, list):
        return []
    normalized_by_key: dict[tuple[str, str], JsonMap] = {}
    insertion_order: list[tuple[str, str]] = []
    for index, item in enumerate(value, start=1):
        reference = normalize_trace_reference(item, index=index)
        if reference is not None:
            dedupe_key = (str(reference.get("artifact") or ""), str(reference.get("version_key") or ""))
            if dedupe_key not in normalized_by_key:
                insertion_order.append(dedupe_key)
                normalized_by_key[dedupe_key] = reference
                continue
            current = normalized_by_key[dedupe_key]
            current_run_id = _as_str(current.get("run_id")) or ""
            next_run_id = _as_str(reference.get("run_id")) or ""
            if current_run_id.startswith("legacy_trace_") and not next_run_id.startswith("legacy_trace_"):
                normalized_by_key[dedupe_key] = reference
    return [normalized_by_key[key] for key in insertion_order]


def canonicalize_artifact_envelope_meta(
    document: object,
    *,
    artifact_type: ArtifactType | str | None = None,
    schema: JsonMap | None = None,
    run_id: str | None = None,
    version_key: str | None = None,
    created_at: str | None = None,
) -> object:
    """Build code-owned persisted metadata for a `{meta, data}` artifact envelope."""

    if not isinstance(document, dict):
        return document
    if "data" not in document:
        if _looks_like_envelope_schema(schema):
            document = {"meta": {}, "data": document}
        else:
            return document
    elif "meta" not in document and _looks_like_envelope_schema(schema):
        document = {"meta": {}, "data": document.get("data")}

    normalized: JsonMap = copy.deepcopy(document)
    source_meta = normalized.get("meta")
    meta: JsonMap = dict(source_meta) if isinstance(source_meta, dict) else {}

    artifact_type_value = _artifact_type_value(artifact_type, schema, meta)
    if artifact_type_value:
        meta["artifact_type"] = artifact_type_value

    for key in ("schema_id", "schema_version", "authority", "owner_agent"):
        const = _schema_meta_const(schema, key)
        if const:
            meta[key] = const

    if isinstance(artifact_type, ArtifactType) and not _schema_meta_const(schema, "owner_agent"):
        owner = CANONICAL_OWNER_BY_ARTIFACT.get(artifact_type)
        if owner:
            meta["owner_agent"] = owner

    if "schema_version" in meta:
        meta["schema_version"] = schema_semver(meta.get("schema_version"))
    if "version" in meta:
        meta["version"] = schema_semver(meta.get("version"))
    else:
        meta["version"] = "1.0"
    resolved_version_key = _as_str(version_key) or _as_str(meta.get("version_key"))
    if resolved_version_key:
        meta["version_key"] = resolved_version_key

    if run_id:
        meta["run_id"] = run_id
    elif not _as_str(meta.get("run_id")):
        meta["run_id"] = "run_unknown"

    if created_at:
        meta["created_at"] = created_at
    elif not _as_str(meta.get("created_at")):
        meta["created_at"] = utc_timestamp()

    for key in ("trace_upstream", "trace_data", "trace_events"):
        meta[key] = normalize_trace_references(meta.get(key))

    if not _as_str(meta.get("scope")):
        meta["scope"] = "Season"
    if not _as_str(meta.get("iso_week")):
        meta["iso_week"] = "1970-01"
    if not _as_str(meta.get("iso_week_range")):
        iso_week = str(meta.get("iso_week"))
        meta["iso_week_range"] = f"{iso_week}--{iso_week}"
    if not isinstance(meta.get("temporal_scope"), dict):
        meta["temporal_scope"] = {"from": "1970-01-01", "to": "1970-01-04"}
    if not _as_str(meta.get("data_confidence")):
        meta["data_confidence"] = "UNKNOWN"
    notes = meta.get("notes")
    if isinstance(notes, list):
        meta["notes"] = " ".join(str(item) for item in notes if item is not None)
    elif notes is None:
        meta["notes"] = ""
    else:
        meta["notes"] = str(notes)

    if _schema_meta_is_closed(schema):
        allowed = _schema_meta_properties(schema)
        meta = {key: value for key, value in meta.items() if key in allowed}

    normalized["meta"] = meta
    return normalized
