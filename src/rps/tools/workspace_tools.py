"""Workspace tools for agent function calls."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rps.rendering.auto_render import render_sidecar
from rps.tools.knowledge_search import search_knowledge
from rps.workspace.api import Workspace
from rps.workspace.index_exact import IndexExactQuery
from rps.workspace.iso_helpers import IsoWeekRange
from rps.workspace.phase_from_season_plan import IsoWeek
from rps.workspace.phase_resolution import add_weeks
from rps.workspace.schema_map import ARTIFACT_SCHEMA_FILE
from rps.workspace.schema_registry import SchemaValidationError
from rps.workspace.season_plan_service import (
    phase_context_summary,
    resolve_phase_range_from_season_plan,
)
from rps.workspace.types import ArtifactType

logger = logging.getLogger(__name__)

JsonDict = dict[str, object]
ToolHandler = Callable[[dict[str, Any]], object]
WEEK_SENSITIVE_ARTIFACTS = {
    ArtifactType.ACTIVITIES_ACTUAL,
    ArtifactType.ACTIVITIES_TREND,
    ArtifactType.WEEK_PLAN,
    ArtifactType.INTERVALS_WORKOUTS,
    ArtifactType.DES_ANALYSIS_REPORT,
    ArtifactType.SEASON_PHASE_FEED_FORWARD,
    ArtifactType.PHASE_FEED_FORWARD,
}


def _as_map(value: object) -> JsonDict:
    return value if isinstance(value, dict) else {}

def _parse_artifact_type(value: str) -> ArtifactType:
    """Normalize a user-provided artifact type string."""
    if isinstance(value, ArtifactType):
        return value
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("artifact_type is required")
    try:
        return ArtifactType(cleaned)
    except ValueError:
        key = "".join([ch if ch.isalnum() else "_" for ch in cleaned]).upper()
        return ArtifactType[key]


def _week_sensitive_latest_warning(artifact_type: ArtifactType) -> str | None:
    """Return a guidance warning when latest is ambiguous for week-scoped artefacts."""
    if artifact_type not in WEEK_SENSITIVE_ARTIFACTS:
        return None
    return (
        f"{artifact_type.value} is week-sensitive. "
        "Prefer workspace_get or workspace_get_version with an explicit ISO week version_key."
    )


def get_tool_defs() -> list[JsonDict]:
    """Return function tool definitions for workspace access."""
    return [
        {
            "type": "function",
            "name": "workspace_get_latest",
            "description": (
                "Load the latest version of an athlete artifact from the local workspace. "
                "Do not use this for week-sensitive artefacts when a specific ISO week is required; "
                "prefer workspace_get."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "artifact_type": {"type": "string"},
                },
                "required": ["artifact_type"],
            },
        },
        {
            "type": "function",
            "name": "workspace_get",
            "description": "Load a specific version of an athlete artifact from the local workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "artifact_type": {"type": "string"},
                    "version_key": {"type": "string"},
                },
                "required": ["artifact_type", "version_key"],
            },
        },
        {
            "type": "function",
            "name": "workspace_list_versions",
            "description": "List all known version keys for a given artifact type.",
            "parameters": {
                "type": "object",
                "properties": {
                    "artifact_type": {"type": "string"},
                },
                "required": ["artifact_type"],
            },
        },
        {
            "type": "function",
            "name": "workspace_get_phase_context",
            "description": (
                "Resolve the phase-aligned phase range for a target ISO week and return the "
                "newest exact-range phase artefacts for that range. Supports offset_phases "
                "to shift into the next or previous phase."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "year": {"type": "integer"},
                    "week": {"type": "integer"},
                    "phase_len": {"type": "integer", "default": 4},
                    "offset_phases": {"type": "integer", "default": 0},
                },
                "required": ["year", "week"],
            },
        },
        {
            "type": "function",
            "name": "workspace_put_validated",
            "description": "Validate (against JSON schema) and store an artifact in the local athlete workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "artifact_type": {"type": "string"},
                    "version_key": {"type": "string"},
                    "schema_file": {"type": "string"},
                    "payload": {},
                    "meta": {"type": ["object", "null"]},
                    "run_id": {"type": "string"},
                    "update_latest": {"type": "boolean"},
                },
                "required": ["artifact_type", "version_key", "payload"],
            },
        },
        {
            "type": "function",
            "name": "knowledge_search",
            "description": "Search the local knowledge vectorstore for relevant context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer", "default": 5},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    ]


@dataclass
class ToolContext:
    """Context object for workspace tool handlers."""
    athlete_id: str
    agent_name: str
    workspace_root: Path
    schema_dir: Path
    run_id: str = "run_unknown"

    def workspace(self) -> Workspace:
        """Construct a Workspace for this tool context."""
        return Workspace.for_athlete(self.athlete_id, root=self.workspace_root)


def get_tool_handlers(ctx: ToolContext) -> dict[str, ToolHandler]:
    """Return tool handler callables bound to the context."""
    workspace = ctx.workspace()
    index_query = IndexExactQuery(
        root=workspace.store.root,
        athlete_id=workspace.athlete_id,
    )

    def _best_exact_range_doc(artifact_type: ArtifactType, phase_range: IsoWeekRange) -> JsonDict:
        """Load the newest exact-range artifact for a phase range."""
        best_vk = index_query.best_exact_range_version(artifact_type.value, phase_range)
        if not best_vk:
            return {
                "ok": False,
                "error": f"No exact-range {artifact_type.value} found for phase {phase_range.key}",
                "phase_range_key": phase_range.key,
            }
        try:
            doc = workspace.get(artifact_type, best_vk)
        except Exception as exc:
            return {
                "ok": False,
                "error": f"Found version_key={best_vk} but failed to load: {exc}",
                "version_key": best_vk,
                "phase_range_key": phase_range.key,
            }
        return {
            "ok": True,
            "artifact_type": artifact_type.value,
            "version_key": best_vk,
            "phase_range_key": phase_range.key,
            "document": doc,
        }

    def workspace_get_latest(args: dict[str, Any]) -> object:
        """Load the latest artifact for a type."""
        artifact_type = _parse_artifact_type(args["artifact_type"])
        payload = workspace.get_latest(artifact_type)
        warning = _week_sensitive_latest_warning(artifact_type)
        if warning and isinstance(payload, dict):
            result = dict(payload)
            result.setdefault("_tool_warning", warning)
            return result
        return payload

    def workspace_get(args: dict[str, Any]) -> object:
        """Load a specific artifact version."""
        artifact_type = _parse_artifact_type(args["artifact_type"])
        return workspace.get(artifact_type, args["version_key"])

    def workspace_list_versions(args: dict[str, Any]) -> object:
        """List known versions for a type."""
        artifact_type = _parse_artifact_type(args["artifact_type"])
        return workspace.list_versions(artifact_type)

    def workspace_get_phase_context(args: dict[str, Any]) -> object:
        """Resolve a phase range and return the newest exact-range phase artifacts."""
        year = int(args["year"])
        week = int(args["week"])
        phase_len = int(args.get("phase_len", 4))
        offset_phases = int(args.get("offset_phases", 0))

        target = IsoWeek(year, week)
        if offset_phases:
            target = add_weeks(target, offset_phases * phase_len)

        try:
            season_plan = _as_map(workspace.get_latest(ArtifactType.SEASON_PLAN))
        except FileNotFoundError:
            return {
                "ok": False,
                "error": "SEASON_PLAN latest missing. Cannot resolve phase range.",
            }

        phase_range = resolve_phase_range_from_season_plan(
            season_plan, target, phase_len=phase_len
        )
        phase_info = phase_context_summary(season_plan, target)

        return {
            "ok": True,
            "target_week": {"year": target.year, "week": target.week},
            "phase_len": phase_len,
            "offset_phases": offset_phases,
            "phase_info": phase_info,
            "phase_range": {
                "start": {"year": phase_range.start.year, "week": phase_range.start.week},
                "end": {"year": phase_range.end.year, "week": phase_range.end.week},
                "range_key": phase_range.key,
            },
            "artifacts": {
                "phase_guardrails": _best_exact_range_doc(ArtifactType.PHASE_GUARDRAILS, phase_range),
                "phase_structure": _best_exact_range_doc(
                    ArtifactType.PHASE_STRUCTURE, phase_range
                ),
                "phase_preview": _best_exact_range_doc(
                    ArtifactType.PHASE_PREVIEW, phase_range
                ),
            },
        }

    def workspace_put_validated(args: dict[str, Any]) -> object:
        """Validate and persist an artifact using the schema registry."""
        artifact_type = _parse_artifact_type(args["artifact_type"])
        schema_file = args.get("schema_file")
        if schema_file:
            expected = ARTIFACT_SCHEMA_FILE.get(artifact_type)
            if expected and expected != schema_file:
                raise ValueError(f"schema_file mismatch for {artifact_type.value}: {schema_file} != {expected}")

        payload = args["payload"]
        payload_meta = args.get("meta")
        meta_keys = {
            "artifact_type",
            "schema_id",
            "schema_version",
            "version",
            "authority",
            "owner_agent",
            "run_id",
            "created_at",
            "trace_upstream",
            "scope",
            "iso_week",
            "iso_week_range",
            "temporal_scope",
            "trace_data",
            "trace_events",
            "notes",
        }

        if payload_meta is None and isinstance(payload, dict):
            if "meta" in payload and "data" in payload and isinstance(payload["meta"], dict):
                payload_meta = payload["meta"]
                payload = payload["data"]
            elif "data" in payload and any(key in payload for key in meta_keys):
                payload_meta = {key: payload[key] for key in meta_keys if key in payload}
                payload = payload["data"]

        run_id = args.get("run_id")
        if isinstance(payload_meta, dict) and not run_id:
            run_id = payload_meta.get("run_id")
        if not run_id:
            run_id = ctx.run_id

        try:
            path = workspace.put_validated(
                artifact_type=artifact_type,
                version_key=args["version_key"],
                payload=payload,
                payload_meta=payload_meta,
                producer_agent=ctx.agent_name,
                run_id=run_id,
                update_latest=bool(args.get("update_latest", True)),
                schema_dir=ctx.schema_dir,
            )
        except SchemaValidationError as exc:
            details = list(exc.errors or [])
            max_items = 8
            preview = details[:max_items]
            suffix = ""
            if len(details) > max_items:
                suffix = f" (+{len(details) - max_items} more)"
            summary = "; ".join(preview) + suffix if preview else "Unknown schema error."
            logger.warning("Schema validation failed for %s: %s", artifact_type.value, details)
            return {
                "ok": False,
                "error": f"Schema validation failed ({artifact_type.value}): {summary}",
                "details": details,
            }
        logger.info(
            "Stored artifact type=%s version_key=%s path=%s run_id=%s",
            artifact_type.value,
            args.get("version_key"),
            path,
            run_id,
        )
        try:
            render_sidecar(Path(path))
        except Exception:
            logger.exception("Auto-render failed for %s", path)
        return {"ok": True, "path": path}

    def knowledge_search(args: dict[str, Any]) -> object:
        """Search the local knowledge vectorstore."""
        query = str(args.get("query", "")).strip()
        max_results = args.get("max_results", 5)
        tags = args.get("tags")
        results = search_knowledge(ctx.agent_name, query, max_results=max_results, tags=tags)
        return {"ok": True, "results": results}

    return {
        "workspace_get_latest": workspace_get_latest,
        "workspace_get": workspace_get,
        "workspace_list_versions": workspace_list_versions,
        "workspace_get_phase_context": workspace_get_phase_context,
        "workspace_put_validated": workspace_put_validated,
        "knowledge_search": knowledge_search,
    }
