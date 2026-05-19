"""Workspace read tools for agent function calls."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rps.crewai_runtime.guardrails import current_guardrail_runtime_context
from rps.workspace.api import Workspace
from rps.workspace.index_exact import IndexExactQuery
from rps.workspace.iso_helpers import IsoWeekRange
from rps.workspace.local_store import normalize_loaded_document
from rps.workspace.phase_from_season_plan import IsoWeek
from rps.workspace.phase_resolution import add_weeks
from rps.workspace.season_plan_service import (
    phase_context_summary,
    resolve_phase_range_from_season_plan,
    resolve_season_plan_phase_info,
)
from rps.workspace.types import ArtifactType

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
    ArtifactType.CURRENT_WEEK_STATUS_SNAPSHOT,
    ArtifactType.ADVISORY_MEMORY,
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
        "Prefer workspace_get_version with an explicit ISO week version_key."
    )


def _compact_wellness_payload(payload: object) -> object:
    """Return a smaller wellness payload for LLM-facing tool responses."""

    if not isinstance(payload, dict):
        return payload
    data = payload.get("data")
    if not isinstance(data, dict):
        return payload
    entries = data.get("entries")
    if not isinstance(entries, list):
        return payload

    def _has_signal(entry: object) -> bool:
        if not isinstance(entry, dict):
            return False
        for key, value in entry.items():
            if key in {"date", "updated_at", "source"}:
                continue
            if value is not None:
                return True
        return False

    signaled_entries = [entry for entry in entries if _has_signal(entry)]
    kept_entries = signaled_entries[-14:] if signaled_entries else entries[-7:]

    latest_entry_date = None
    latest_weight_kg = None
    for entry in reversed(entries):
        if not isinstance(entry, dict):
            continue
        if latest_entry_date is None and isinstance(entry.get("date"), str):
            latest_entry_date = entry["date"]
        weight_kg = entry.get("weight_kg")
        if latest_weight_kg is None and isinstance(weight_kg, (int, float)):
            latest_weight_kg = float(weight_kg)
        if latest_entry_date is not None and latest_weight_kg is not None:
            break

    compact_data = dict(data)
    compact_data["entries"] = kept_entries
    compact_data["entries_total"] = len(entries)
    compact_data["entries_truncated"] = len(kept_entries) != len(entries)
    if latest_entry_date is not None:
        compact_data["latest_entry_date"] = latest_entry_date
    if latest_weight_kg is not None:
        compact_data["latest_weight_kg"] = latest_weight_kg

    compact_payload = dict(payload)
    compact_payload["data"] = compact_data
    return compact_payload


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
            "description": (
                "Load latest artifact JSON from athlete workspace. "
                "Do not use this for week-sensitive artefacts when a specific ISO week is required; "
                "prefer workspace_get_version."
            ),
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
            "name": "workspace_get_phase_slot_contract",
            "description": (
                "Load the code-owned deterministic season phase-slot contract bound to the current run. "
                "Use this instead of searching workspace artifacts for inherited season cadence, phase ids, "
                "phase order, or phase ISO-week coverage."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "workspace_get_season_phase_load_context",
            "description": (
                "Load the code-owned deterministic season phase-load context bound to the current run. "
                "Use this for recommended_phase_corridor values, availability caps, role-week load bands, "
                "and taper/load feasibility instead of searching for a persisted recommendation artifact."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "workspace_get_phase_execution_context",
            "description": (
                "Load the code-owned deterministic phase execution context bound to the current run. "
                "Use this for phase week roles, exact phase range, active S5 bands, and phase-level execution authority."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "workspace_get_week_calendar_context",
            "description": (
                "Load the code-owned deterministic week calendar and availability context bound to the current run. "
                "Use this for active week role, active weekly band, Mon-Sun dates, availability caps, fixed rest days, and allowed domains."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
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
            "description": (
                "Load athlete-specific inputs (athlete_profile, planning_events, logistics, availability) "
                "from inputs/ or latest/. Accepts `input_type`; `artifact_type` is also accepted as a "
                "backward-compatible alias."
            ),
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
                    "artifact_type": {
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
                "anyOf": [
                    {"required": ["input_type"]},
                    {"required": ["artifact_type"]},
                ],
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
        payload = workspace.get_latest(artifact_type)
        if artifact_type == ArtifactType.WELLNESS:
            payload = _compact_wellness_payload(payload)
        warning = _week_sensitive_latest_warning(artifact_type)
        if warning and isinstance(payload, dict):
            result = dict(payload)
            result.setdefault("_tool_warning", warning)
            return result
        return payload

    def workspace_get_version(args: dict[str, Any]) -> object:
        """Load a specific artifact version."""
        artifact_type = _parse_artifact_type(args["artifact_type"])
        return workspace.get(artifact_type, args["version_key"])

    def workspace_list_versions(args: dict[str, Any]) -> object:
        """List known versions for a type."""
        artifact_type = _parse_artifact_type(args["artifact_type"])
        return workspace.list_versions(artifact_type)

    def _contract_payload(context_key: str, label: str) -> JsonDict:
        context = current_guardrail_runtime_context()
        payload = _as_map(context.get(context_key))
        if not payload:
            return {
                "ok": False,
                "context_name": label,
                "error": (
                    f"{label} is not bound in the current runtime context. "
                    "Do not invent or rediscover this contract from workspace artifacts."
                ),
            }
        return {"ok": True, "context_name": label, "contract": payload}

    def workspace_get_phase_slot_contract(args: dict[str, Any]) -> object:
        """Return the bound deterministic season phase-slot contract."""

        del args
        return _contract_payload("phase_slot_context", "phase_slot_context")

    def workspace_get_season_phase_load_context(args: dict[str, Any]) -> object:
        """Return the bound deterministic season phase-load contract."""

        del args
        return _contract_payload("season_phase_load_context", "season_phase_load_context")

    def workspace_get_phase_execution_context(args: dict[str, Any]) -> object:
        """Return the bound deterministic phase execution context."""

        del args
        return _contract_payload("phase_execution_context", "phase_execution_context")

    def workspace_get_week_calendar_context(args: dict[str, Any]) -> object:
        """Return the bound deterministic week calendar context."""

        del args
        return _contract_payload("week_calendar_context", "week_calendar_context")

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

    def workspace_get_input(args: dict[str, Any]) -> object:
        raw_input_type = args.get("input_type", args.get("artifact_type"))
        if not isinstance(raw_input_type, str) or not raw_input_type.strip():
            raise ValueError("input_type is required")
        input_type = raw_input_type.strip()
        year = int(args["year"]) if args.get("year") is not None else None
        path = _find_input_file(workspace.store.athlete_root(workspace.athlete_id), input_type, year=year)
        raw_content = path.read_text(encoding="utf-8")
        parsed_content: object | None = None
        try:
            parsed_content = normalize_loaded_document(json.loads(raw_content))
        except Exception:
            parsed_content = None
        return {
            "ok": True,
            "input_type": input_type,
            "path": str(path),
            "content": (
                json.dumps(parsed_content, ensure_ascii=False, indent=2)
                if parsed_content is not None
                else raw_content
            ),
            "document": parsed_content,
        }

    return {
        "workspace_get_latest": workspace_get_latest,
        "workspace_get_version": workspace_get_version,
        "workspace_list_versions": workspace_list_versions,
        "workspace_get_phase_slot_contract": workspace_get_phase_slot_contract,
        "workspace_get_season_phase_load_context": workspace_get_season_phase_load_context,
        "workspace_get_phase_execution_context": workspace_get_phase_execution_context,
        "workspace_get_week_calendar_context": workspace_get_week_calendar_context,
        "workspace_resolve_season_phase": workspace_resolve_season_phase,
        "workspace_resolve_phase_range": workspace_resolve_phase_range,
        "workspace_find_best_phase_artefact": workspace_find_best_phase_artefact,
        "workspace_get_phase_context": workspace_get_phase_context,
        "workspace_get_input": workspace_get_input,
    }
