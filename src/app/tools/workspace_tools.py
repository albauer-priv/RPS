"""Workspace tools for agent function calls."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Any, Callable

from app.workspace.api import Workspace
from app.workspace.block_from_macro import IsoWeek
from app.workspace.block_resolution import add_weeks
from app.workspace.index_exact import IndexExactQuery
from app.workspace.macro_phase_service import resolve_block_range_from_macro
from app.workspace.schema_map import ARTIFACT_SCHEMA_FILE
from app.workspace.schema_registry import SchemaValidationError
from app.rendering.auto_render import render_sidecar
from app.workspace.types import ArtifactType

logger = logging.getLogger(__name__)

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


def get_tool_defs() -> list[dict[str, Any]]:
    """Return function tool definitions for workspace access."""
    return [
        {
            "type": "function",
            "name": "workspace_get_latest",
            "description": "Load the latest version of an athlete artifact from the local workspace.",
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
            "name": "workspace_get_block_context",
            "description": (
                "Resolve the phase-aligned block range for a target ISO week and return the "
                "newest exact-range block artefacts for that range. Supports offset_blocks "
                "to shift into the next or previous block."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "year": {"type": "integer"},
                    "week": {"type": "integer"},
                    "block_len": {"type": "integer", "default": 4},
                    "offset_blocks": {"type": "integer", "default": 0},
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


def get_tool_handlers(ctx: ToolContext) -> dict[str, Callable[[dict[str, Any]], Any]]:
    """Return tool handler callables bound to the context."""
    workspace = ctx.workspace()
    index_query = IndexExactQuery(
        root=workspace.store.root,
        athlete_id=workspace.athlete_id,
    )

    def _best_exact_range_doc(artifact_type: ArtifactType, block_range) -> dict[str, Any]:
        """Load the newest exact-range artifact for a block range."""
        best_vk = index_query.best_exact_range_version(artifact_type.value, block_range)
        if not best_vk:
            return {
                "ok": False,
                "error": f"No exact-range {artifact_type.value} found for block {block_range.key}",
                "block_range_key": block_range.key,
            }
        try:
            doc = workspace.get(artifact_type, best_vk)
        except Exception as exc:
            return {
                "ok": False,
                "error": f"Found version_key={best_vk} but failed to load: {exc}",
                "version_key": best_vk,
                "block_range_key": block_range.key,
            }
        return {
            "ok": True,
            "artifact_type": artifact_type.value,
            "version_key": best_vk,
            "block_range_key": block_range.key,
            "document": doc,
        }

    def workspace_get_latest(args: dict[str, Any]) -> Any:
        """Load the latest artifact for a type."""
        artifact_type = _parse_artifact_type(args["artifact_type"])
        return workspace.get_latest(artifact_type)

    def workspace_get(args: dict[str, Any]) -> Any:
        """Load a specific artifact version."""
        artifact_type = _parse_artifact_type(args["artifact_type"])
        return workspace.get(artifact_type, args["version_key"])

    def workspace_list_versions(args: dict[str, Any]) -> Any:
        """List known versions for a type."""
        artifact_type = _parse_artifact_type(args["artifact_type"])
        return workspace.list_versions(artifact_type)

    def workspace_get_block_context(args: dict[str, Any]) -> Any:
        """Resolve a block range and return the newest exact-range block artifacts."""
        year = int(args["year"])
        week = int(args["week"])
        block_len = int(args.get("block_len", 4))
        offset_blocks = int(args.get("offset_blocks", 0))

        target = IsoWeek(year, week)
        if offset_blocks:
            target = add_weeks(target, offset_blocks * block_len)

        try:
            macro = workspace.get_latest(ArtifactType.MACRO_OVERVIEW)
        except FileNotFoundError:
            return {
                "ok": False,
                "error": "MACRO_OVERVIEW latest missing. Cannot resolve block range.",
            }

        block_range = resolve_block_range_from_macro(macro, target, block_len=block_len)

        return {
            "ok": True,
            "target_week": {"year": target.year, "week": target.week},
            "block_len": block_len,
            "offset_blocks": offset_blocks,
            "block_range": {
                "start": {"year": block_range.start.year, "week": block_range.start.week},
                "end": {"year": block_range.end.year, "week": block_range.end.week},
                "range_key": block_range.key,
            },
            "artifacts": {
                "block_governance": _best_exact_range_doc(ArtifactType.BLOCK_GOVERNANCE, block_range),
                "block_execution_arch": _best_exact_range_doc(
                    ArtifactType.BLOCK_EXECUTION_ARCH, block_range
                ),
                "block_execution_preview": _best_exact_range_doc(
                    ArtifactType.BLOCK_EXECUTION_PREVIEW, block_range
                ),
            },
        }

    def workspace_put_validated(args: dict[str, Any]) -> Any:
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

    return {
        "workspace_get_latest": workspace_get_latest,
        "workspace_get": workspace_get,
        "workspace_list_versions": workspace_list_versions,
        "workspace_get_block_context": workspace_get_block_context,
        "workspace_put_validated": workspace_put_validated,
    }
