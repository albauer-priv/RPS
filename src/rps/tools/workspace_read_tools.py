"""Workspace read tools for agent function calls."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from rps.workspace.api import Workspace
from rps.workspace.iso_helpers import IsoWeekRange
from rps.workspace.phase_from_season_plan import IsoWeek
from rps.workspace.phase_resolution import add_weeks
from rps.workspace.index_exact import IndexExactQuery
from rps.workspace.season_plan_service import resolve_phase_range_from_season_plan, resolve_season_plan_phase_info
from rps.workspace.types import ArtifactType
from rps.tools.knowledge_search import search_knowledge

JsonDict = dict[str, object]
ToolHandler = Callable[[dict[str, Any]], object]


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


def _find_input_file(
    athlete_root: Path,
    input_type: str,
    year: int | None = None,
) -> Path:
    patterns: list[str] = []
    if input_type == "athlete_profile":
        patterns.append("athlete_profile*.json")
    elif input_type == "availability":
        patterns.append("availability*.json")
    elif input_type == "logistics":
        patterns.append("logistics*.json")
    elif input_type == "planning_events":
        patterns.append("planning_events*.json")
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


def read_tool_defs() -> list[JsonDict]:
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
            "name": "workspace_resolve_season_phase",
            "description": "Resolve the season plan phase covering a target ISO week based on SEASON_PLAN latest.",
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
            "name": "workspace_resolve_phase_range",
            "description": "Resolve the phase ISO week range covering a target week using SEASON_PLAN phase alignment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "year": {"type": "integer"},
                    "week": {"type": "integer"},
                    "phase_len": {"type": "integer", "default": 4},
                },
                "required": ["year", "week"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "workspace_find_best_phase_artefact",
            "description": (
                "Find and load the best exact-range phase artefact for a target ISO week. "
                "Resolves the phase-aligned phase range from SEASON_PLAN and "
                "uses index.json to pick the newest exact-range version."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "artifact_type": {"type": "string"},
                    "year": {"type": "integer"},
                    "week": {"type": "integer"},
                    "phase_len": {"type": "integer", "default": 4},
                },
                "required": ["artifact_type", "year", "week"],
                "additionalProperties": False,
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
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "workspace_get_input",
            "description": "Load athlete-specific inputs (athlete_profile, planning_events, logistics, availability) from inputs/ or latest/.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input_type": {
                        "type": "string",
                        "enum": [
                            "athlete_profile",
                            "availability",
                            "logistics",
                            "planning_events",
                        ],
                    },
                    "year": {"type": "integer"},
                },
                "required": ["input_type"],
                "additionalProperties": False,
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
class ReadToolContext:
    """Context object for workspace read tools."""
    athlete_id: str
    workspace_root: Path
    agent_name: str = "coach"

    def workspace(self) -> Workspace:
        """Construct a Workspace for this tool context."""
        return Workspace.for_athlete(self.athlete_id, root=self.workspace_root)


def read_tool_handlers(ctx: ReadToolContext) -> dict[str, ToolHandler]:
    """Return read tool handlers bound to a workspace."""
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
        return workspace.get_latest(artifact_type)

    def workspace_get_version(args: dict[str, Any]) -> object:
        """Load a specific artifact version."""
        artifact_type = _parse_artifact_type(args["artifact_type"])
        return workspace.get(artifact_type, args["version_key"])

    def workspace_list_versions(args: dict[str, Any]) -> object:
        """List known versions for a type."""
        artifact_type = _parse_artifact_type(args["artifact_type"])
        return workspace.list_versions(artifact_type)

    def workspace_resolve_season_phase(args: dict[str, Any]) -> object:
        """Resolve the season plan phase covering the target week."""
        year = int(args["year"])
        week = int(args["week"])
        season_plan = _as_map(workspace.get_latest(ArtifactType.SEASON_PLAN))
        info = resolve_season_plan_phase_info(season_plan, IsoWeek(year, week))
        if not info:
            return {"ok": False, "error": f"No season plan phase covers {year:04d}-{week:02d}"}

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

    def workspace_resolve_phase_range(args: dict[str, Any]) -> object:
        """Resolve the phase range covering the target week."""
        year = int(args["year"])
        week = int(args["week"])
        phase_len = int(args.get("phase_len", 4))

        season_plan = _as_map(workspace.get_latest(ArtifactType.SEASON_PLAN))
        phase_range = resolve_phase_range_from_season_plan(
            season_plan, IsoWeek(year, week), phase_len=phase_len
        )

        return {
            "ok": True,
            "phase_len": phase_len,
            "iso_week_range": {
                "start": {"year": phase_range.start.year, "week": phase_range.start.week},
                "end": {"year": phase_range.end.year, "week": phase_range.end.week},
            },
            "range_key": phase_range.key,
        }

    def workspace_find_best_phase_artefact(args: dict[str, Any]) -> object:
        """Find and load the newest exact-range phase artifact."""
        artifact_type = _parse_artifact_type(args["artifact_type"])
        year = int(args["year"])
        week = int(args["week"])
        phase_len = int(args.get("phase_len", 4))

        try:
            season_plan = _as_map(workspace.get_latest(ArtifactType.SEASON_PLAN))
        except FileNotFoundError:
            return {
                "ok": False,
                "error": "SEASON_PLAN latest missing. Cannot resolve phase range.",
            }

        phase_range = resolve_phase_range_from_season_plan(
            season_plan, IsoWeek(year, week), phase_len=phase_len
        )
        return _best_exact_range_doc(artifact_type, phase_range)

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

        return {
            "ok": True,
            "target_week": {"year": target.year, "week": target.week},
            "phase_len": phase_len,
            "offset_phases": offset_phases,
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

    def workspace_get_input(args: dict[str, Any]) -> object:
        input_type = str(args["input_type"]).strip()
        year = int(args["year"]) if args.get("year") is not None else None
        path = _find_input_file(workspace.store.athlete_root(workspace.athlete_id), input_type, year=year)
        return {
            "ok": True,
            "input_type": input_type,
            "path": str(path),
            "content": path.read_text(encoding="utf-8"),
        }

    def knowledge_search(args: dict[str, Any]) -> object:
        query = str(args.get("query", "")).strip()
        max_results = args.get("max_results", 5)
        tags = args.get("tags")
        results = search_knowledge(ctx.agent_name, query, max_results=max_results, tags=tags)
        return {"ok": True, "results": results}

    return {
        "workspace_get_latest": workspace_get_latest,
        "workspace_get_version": workspace_get_version,
        "workspace_list_versions": workspace_list_versions,
        "workspace_resolve_season_phase": workspace_resolve_season_phase,
        "workspace_resolve_phase_range": workspace_resolve_phase_range,
        "workspace_find_best_phase_artefact": workspace_find_best_phase_artefact,
        "workspace_get_phase_context": workspace_get_phase_context,
        "workspace_get_input": workspace_get_input,
        "knowledge_search": knowledge_search,
    }
