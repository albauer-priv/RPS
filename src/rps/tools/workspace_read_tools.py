"""Workspace read tools for agent function calls."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from rps.workspace.api import Workspace
from rps.workspace.block_from_macro import IsoWeek
from rps.workspace.block_resolution import add_weeks
from rps.workspace.index_exact import IndexExactQuery
from rps.workspace.macro_phase_service import resolve_block_range_from_macro, resolve_macro_phase_info
from rps.workspace.types import ArtifactType


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


def _find_input_file(
    athlete_root: Path,
    input_type: str,
    year: int | None = None,
) -> Path:
    patterns: list[str] = []
    if input_type == "season_brief":
        if year is not None:
            patterns.append(f"season_brief_{year}.md")
        patterns.append("season_brief_*.md")
    elif input_type == "events":
        patterns.append("events.md")
        patterns.append("events_*.md")
    else:
        raise ValueError(f"Unsupported input_type: {input_type}")

    candidates: list[Path] = []
    for folder in (athlete_root / "inputs", athlete_root / "latest"):
        if not folder.exists():
            continue
        for pattern in patterns:
            candidates.extend(folder.glob(pattern))

    if not candidates:
        raise FileNotFoundError(
            f"No input files found for {input_type}. Place files in inputs/ or latest/."
        )

    return max(candidates, key=lambda p: p.stat().st_mtime)


def read_tool_defs() -> list[dict[str, Any]]:
    """Return function tool definitions for workspace reads."""
    return [
        {
            "type": "function",
            "name": "workspace_get_latest",
            "description": "Load latest artifact JSON from athlete workspace.",
            "parameters": {
                "type": "object",
                "properties": {"artifact_type": {"type": "string"}},
                "required": ["artifact_type"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "workspace_get_version",
            "description": "Load a specific version of an artifact JSON from athlete workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "artifact_type": {"type": "string"},
                    "version_key": {"type": "string"},
                },
                "required": ["artifact_type", "version_key"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "workspace_list_versions",
            "description": "List version keys stored for an artifact type.",
            "parameters": {
                "type": "object",
                "properties": {"artifact_type": {"type": "string"}},
                "required": ["artifact_type"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "workspace_resolve_macro_phase",
            "description": "Resolve the macro phase covering a target ISO week based on MACRO_OVERVIEW latest.",
            "parameters": {
                "type": "object",
                "properties": {
                    "year": {"type": "integer"},
                    "week": {"type": "integer"},
                },
                "required": ["year", "week"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "workspace_resolve_block_range",
            "description": "Resolve the meso block ISO week range covering a target week using MACRO_OVERVIEW phase alignment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "year": {"type": "integer"},
                    "week": {"type": "integer"},
                    "block_len": {"type": "integer", "default": 4},
                },
                "required": ["year", "week"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "workspace_find_best_block_artefact",
            "description": (
                "Find and load the best exact-range block artefact for a target ISO week. "
                "Resolves the phase-aligned block range from MACRO_OVERVIEW and "
                "uses index.json to pick the newest exact-range version."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "artifact_type": {"type": "string"},
                    "year": {"type": "integer"},
                    "week": {"type": "integer"},
                    "block_len": {"type": "integer", "default": 4},
                },
                "required": ["artifact_type", "year", "week"],
                "additionalProperties": False,
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
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "workspace_get_input",
            "description": "Load athlete-specific Markdown inputs like season brief or events.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input_type": {"type": "string", "enum": ["season_brief", "events"]},
                    "year": {"type": "integer"},
                },
                "required": ["input_type"],
                "additionalProperties": False,
            },
        },
    ]


@dataclass
class ReadToolContext:
    """Context object for workspace read tools."""
    athlete_id: str
    workspace_root: Any

    def workspace(self) -> Workspace:
        """Construct a Workspace for this tool context."""
        return Workspace.for_athlete(self.athlete_id, root=self.workspace_root)


def read_tool_handlers(ctx: ReadToolContext) -> dict[str, Callable[[dict[str, Any]], Any]]:
    """Return read tool handlers bound to a workspace."""
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

    def workspace_get_version(args: dict[str, Any]) -> Any:
        """Load a specific artifact version."""
        artifact_type = _parse_artifact_type(args["artifact_type"])
        return workspace.get(artifact_type, args["version_key"])

    def workspace_list_versions(args: dict[str, Any]) -> Any:
        """List known versions for a type."""
        artifact_type = _parse_artifact_type(args["artifact_type"])
        return workspace.list_versions(artifact_type)

    def workspace_resolve_macro_phase(args: dict[str, Any]) -> Any:
        """Resolve the macro phase covering the target week."""
        year = int(args["year"])
        week = int(args["week"])
        macro = workspace.get_latest(ArtifactType.MACRO_OVERVIEW)
        info = resolve_macro_phase_info(macro, IsoWeek(year, week))
        if not info:
            return {"ok": False, "error": f"No macro phase covers {year:04d}-{week:02d}"}

        return {
            "ok": True,
            "phase": {
                "phase_id": info.phase_id,
                "phase_name": info.phase_name,
                "phase_type": info.phase_type,
                "iso_week_range": {
                    "start": {"year": info.phase_range.start.year, "week": info.phase_range.start.week},
                    "end": {"year": info.phase_range.end.year, "week": info.phase_range.end.week},
                },
            },
        }

    def workspace_resolve_block_range(args: dict[str, Any]) -> Any:
        """Resolve the block range covering the target week."""
        year = int(args["year"])
        week = int(args["week"])
        block_len = int(args.get("block_len", 4))

        macro = workspace.get_latest(ArtifactType.MACRO_OVERVIEW)
        block_range = resolve_block_range_from_macro(macro, IsoWeek(year, week), block_len=block_len)

        return {
            "ok": True,
            "block_len": block_len,
            "iso_week_range": {
                "start": {"year": block_range.start.year, "week": block_range.start.week},
                "end": {"year": block_range.end.year, "week": block_range.end.week},
            },
            "range_key": block_range.key,
        }

    def workspace_find_best_block_artefact(args: dict[str, Any]) -> Any:
        """Find and load the newest exact-range block artifact."""
        artifact_type = _parse_artifact_type(args["artifact_type"])
        year = int(args["year"])
        week = int(args["week"])
        block_len = int(args.get("block_len", 4))

        try:
            macro = workspace.get_latest(ArtifactType.MACRO_OVERVIEW)
        except FileNotFoundError:
            return {
                "ok": False,
                "error": "MACRO_OVERVIEW latest missing. Cannot resolve block range.",
            }

        block_range = resolve_block_range_from_macro(macro, IsoWeek(year, week), block_len=block_len)
        return _best_exact_range_doc(artifact_type, block_range)

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

    def workspace_get_input(args: dict[str, Any]) -> Any:
        input_type = str(args["input_type"]).strip()
        year = int(args["year"]) if args.get("year") is not None else None
        path = _find_input_file(workspace.store.athlete_root(workspace.athlete_id), input_type, year=year)
        return {
            "ok": True,
            "input_type": input_type,
            "path": str(path),
            "content": path.read_text(encoding="utf-8"),
        }

    return {
        "workspace_get_latest": workspace_get_latest,
        "workspace_get_version": workspace_get_version,
        "workspace_list_versions": workspace_list_versions,
        "workspace_resolve_macro_phase": workspace_resolve_macro_phase,
        "workspace_resolve_block_range": workspace_resolve_block_range,
        "workspace_find_best_block_artefact": workspace_find_best_block_artefact,
        "workspace_get_block_context": workspace_get_block_context,
        "workspace_get_input": workspace_get_input,
    }
