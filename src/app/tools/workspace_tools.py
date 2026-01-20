"""Workspace tools for agent function calls."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from app.workspace.api import Workspace
from app.workspace.schema_map import ARTIFACT_SCHEMA_FILE
from app.workspace.types import ArtifactType


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
                "required": ["artifact_type", "version_key", "payload", "run_id"],
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

    def workspace(self) -> Workspace:
        """Construct a Workspace for this tool context."""
        return Workspace.for_athlete(self.athlete_id, root=self.workspace_root)


def get_tool_handlers(ctx: ToolContext) -> dict[str, Callable[[dict[str, Any]], Any]]:
    """Return tool handler callables bound to the context."""
    workspace = ctx.workspace()

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

    def workspace_put_validated(args: dict[str, Any]) -> Any:
        """Validate and persist an artifact using the schema registry."""
        artifact_type = _parse_artifact_type(args["artifact_type"])
        schema_file = args.get("schema_file")
        if schema_file:
            expected = ARTIFACT_SCHEMA_FILE.get(artifact_type)
            if expected and expected != schema_file:
                raise ValueError(f"schema_file mismatch for {artifact_type.value}: {schema_file} != {expected}")

        path = workspace.put_validated(
            artifact_type=artifact_type,
            version_key=args["version_key"],
            payload=args["payload"],
            payload_meta=args.get("meta"),
            producer_agent=ctx.agent_name,
            run_id=args["run_id"],
            update_latest=bool(args.get("update_latest", True)),
            schema_dir=ctx.schema_dir,
        )
        return {"ok": True, "path": path}

    return {
        "workspace_get_latest": workspace_get_latest,
        "workspace_get": workspace_get,
        "workspace_list_versions": workspace_list_versions,
        "workspace_put_validated": workspace_put_validated,
    }
