"""Strict tool-calling runner for multi-output tasks."""

from __future__ import annotations

import datetime
import json
import logging
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rps.agents.knowledge_injection import build_injection_block
from rps.agents.tasks import OUTPUT_SPECS, AgentTask, OutputSpec
from rps.openai.litellm_runtime import LiteLLMClient, LiteLLMResponse
from rps.openai.model_capabilities import supports_temperature
from rps.openai.reasoning import build_reasoning_payload
from rps.openai.response_utils import extract_reasoning_summaries, extract_text_output
from rps.openai.streaming import create_response
from rps.openai.vectorstore_state import VectorStoreResolver
from rps.prompts.loader import PromptLoader
from rps.schemas.bundler import SchemaBundler
from rps.tools.store_output_tools import build_strict_store_tool
from rps.tools.workspace_read_tools import ReadToolContext, read_tool_defs, read_tool_handlers
from rps.workspace.guarded_store import GuardedValidatedStore
from rps.workspace.schema_registry import SchemaValidationError
from rps.workspace.types import ArtifactType

logger = logging.getLogger(__name__)
MAX_TOOL_ITERATIONS = 30

_KNOWLEDGE_SOURCE_ROOT = Path(__file__).resolve().parents[3] / "specs" / "knowledge" / "_shared" / "sources"
ToolDef = dict[str, object]
UsageSummary = dict[str, int | None]

@dataclass(frozen=True)
class AgentRuntime:
    """Runtime dependencies for multi-output agent runs."""
    client: LiteLLMClient
    model: str
    temperature: float | None
    reasoning_effort: str | None
    reasoning_summary: str | None
    max_completion_tokens: int | None
    prompt_loader: PromptLoader
    vs_resolver: VectorStoreResolver
    schema_dir: Path
    workspace_root: Path


def _file_search_tool(agent_vs_id: str, max_num_results: int) -> ToolDef:
    """Build a knowledge_search tool payload for Responses API."""
    return {
        "type": "function",
        "name": "knowledge_search",
        "description": "Search the local knowledge vectorstore for relevant context.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer", "default": max_num_results},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    }


def _parse_csv_env(name: str) -> set[str]:
    raw = os.getenv(name, "")
    if not raw.strip():
        return set()
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


def _web_search_tool() -> ToolDef:
    tool: ToolDef = {
        "type": "web_search",
        "user_location": {
            "type": "approximate",
            "country": "US",
            "timezone": "America/New_York",
            "region": "United States",
        },
    }
    allowed_domains = [
        dom for dom in os.getenv("RPS_LLM_WEB_SEARCH_ALLOWED_DOMAINS", "").split(",") if dom.strip()
    ]
    if allowed_domains:
        tool["filters"] = {"allowed_domains": [dom.strip() for dom in allowed_domains]}
    context_size = os.getenv("RPS_LLM_WEB_SEARCH_CONTEXT_SIZE", "").strip().lower()
    if context_size in {"low", "medium", "high"}:
            filters = tool.setdefault("filters", {})
            if isinstance(filters, dict):
                filters["search_context_size"] = context_size
    external_access_raw = os.getenv("RPS_LLM_WEB_SEARCH_EXTERNAL_ACCESS")
    if external_access_raw is not None:
        tool["external_web_access"] = external_access_raw.strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
    return tool


def _web_search_enabled(agent_name: str) -> bool:
    if not _env_flag("RPS_LLM_ENABLE_WEB_SEARCH"):
        return False
    agents = _parse_csv_env("RPS_LLM_WEB_SEARCH_AGENTS")
    return not (agents and agent_name.lower() not in agents)


def _item_type(item: object) -> str | None:
    """Return the type field for response output items."""
    if isinstance(item, dict):
        return item.get("type")
    return getattr(item, "type", None)


def _item_field(item: object, name: str) -> object | None:
    """Safely read a field from a response output item."""
    if isinstance(item, dict):
        return item.get(name)
    return getattr(item, name, None)


def normalize_phase_guardrails_document(document: dict[str, Any]) -> dict[str, Any]:
    """Normalize PHASE_GUARDRAILS shape quirks before guarded store validation."""
    if not isinstance(document, dict):
        return document
    meta = document.get("meta") or {}
    if str(meta.get("artifact_type", "")).upper() != "PHASE_GUARDRAILS":
        return document
    data = document.get("data")
    if not isinstance(data, dict):
        return document
    execution_non_negotiables = data.get("execution_non_negotiables")
    if isinstance(execution_non_negotiables, dict):
        recovery_rules = execution_non_negotiables.get("recovery_protection_rules")
        if isinstance(recovery_rules, list):
            normalized_rules = [str(item).strip() for item in recovery_rules if str(item).strip()]
            execution_non_negotiables["recovery_protection_rules"] = " | ".join(normalized_rules)
        data["execution_non_negotiables"] = execution_non_negotiables
    load_guardrails = data.get("load_guardrails")
    if not isinstance(load_guardrails, dict):
        document["data"] = data
        return document

    def _widen_band(entry: dict[str, Any]) -> None:
        band = entry.get("band")
        if not isinstance(band, dict):
            return
        min_val = band.get("min")
        max_val = band.get("max")
        if isinstance(min_val, (int, float)) and isinstance(max_val, (int, float)):
            if min_val > max_val:
                min_val, max_val = max_val, min_val
            if min_val == max_val:
                base = float(min_val)
                width = max(1.0, base * 0.05)
                note = str(band.get("notes", "")).lower()
                if "deload" in note or "taper" in note:
                    new_min = max(0.0, base - width)
                    new_max = base
                else:
                    new_min = max(0.0, base - width / 2)
                    new_max = base + width / 2
                band["min"] = round(new_min, 2)
                band["max"] = round(new_max, 2)
            else:
                band["min"] = float(min_val)
                band["max"] = float(max_val)

    for key in ("weekly_kj_bands",):
        rows = load_guardrails.get(key)
        if not isinstance(rows, list):
            continue
        for entry in rows:
            if isinstance(entry, dict):
                _widen_band(entry)

    document["data"] = data
    return document


def _log_file_search_results(response: LiteLLMResponse) -> None:
    """Log knowledge_search calls for debugging."""
    items = getattr(response, "output", []) or []
    calls = [
        item
        for item in items
        if _item_type(item) == "function_call" and _item_field(item, "name") == "knowledge_search"
    ]
    if not calls:
        logger.info("knowledge_search calls: none")
        return
    logger.info("knowledge_search calls: %d", len(calls))
    for idx, call in enumerate(calls, start=1):
        logger.info(
            "knowledge_search[%d] args=%s",
            idx,
            _item_field(call, "arguments"),
        )

def _log_file_search_calls(response: LiteLLMResponse) -> None:
    """Log knowledge_search call details when available."""
    items = getattr(response, "output", []) or []
    calls = [
        item
        for item in items
        if _item_type(item) == "function_call" and _item_field(item, "name") == "knowledge_search"
    ]
    if not calls:
        logger.info("knowledge_search calls: none")
        return
    for idx, item in enumerate(calls, start=1):
        logger.info(
            "knowledge_search_call[%d] args=%s keys=%s",
            idx,
            _item_field(item, "arguments"),
            list(item.keys()) if isinstance(item, dict) else None,
        )

def _has_knowledge_search_calls(response: LiteLLMResponse) -> bool:
    items = getattr(response, "output", []) or []
    return any(
        _item_type(item) == "function_call" and _item_field(item, "name") == "knowledge_search"
        for item in items
    )

def _parse_int(value: str | None) -> int | None:
    """Parse an int from env, returning None on invalid input."""
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None

def _env_flag(name: str) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return False
    value = raw.strip().lower()
    return value in {"1", "true", "yes", "on"}

def _extract_usage(response: LiteLLMResponse) -> UsageSummary:
    """Best-effort extraction of token usage from a response."""
    usage = getattr(response, "usage", None)
    if isinstance(usage, dict):
        return usage
    if usage is None:
        return {}
    return {
        "input_tokens": getattr(usage, "input_tokens", None),
        "output_tokens": getattr(usage, "output_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }


def _load_knowledge_source(relative_dir: str, filename: str) -> str | None:
    """Return a shared knowledge source file content when it exists."""
    path = _KNOWLEDGE_SOURCE_ROOT / relative_dir / filename
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8").strip()


def injection_mode_for_tasks(tasks: list[AgentTask]) -> str | None:
    """Resolve a single injection mode from the requested task list."""
    mapping = {
        AgentTask.CREATE_SEASON_SCENARIOS: "scenario",
        AgentTask.CREATE_SEASON_SCENARIO_SELECTION: "scenario",
        AgentTask.CREATE_SEASON_PLAN: "season_plan",
        AgentTask.CREATE_SEASON_PHASE_FEED_FORWARD: "feed_forward",
        AgentTask.CREATE_PHASE_GUARDRAILS: "phase_guardrails",
        AgentTask.CREATE_PHASE_STRUCTURE: "phase_structure",
        AgentTask.CREATE_PHASE_PREVIEW: "phase_preview",
        AgentTask.CREATE_PHASE_FEED_FORWARD: "phase_feed_forward",
        AgentTask.CREATE_WEEK_PLAN: "week_plan",
        AgentTask.CREATE_INTERVALS_WORKOUTS_EXPORT: "intervals_workouts",
        AgentTask.CREATE_DES_ANALYSIS_REPORT: "des_analysis_report",
    }
    modes = {mapping[task] for task in tasks if task in mapping}
    if len(modes) != 1:
        return None
    return next(iter(modes))


def _log_response_diagnostics(response: LiteLLMResponse, *, label: str, elapsed_s: float) -> None:
    """Log timing + shape info for a response."""
    try:
        outputs = response.output or []
    except Exception:
        outputs = []
    function_calls = [item for item in outputs if _item_type(item) == "function_call"]
    usage = _extract_usage(response)
    output_text = getattr(response, "output_text", None) or extract_text_output(response) or ""
    logger.debug(
        "responses.create[%s]: %.2fs outputs=%d function_calls=%d text_len=%d usage=%s",
        label,
        elapsed_s,
        len(outputs),
        len(function_calls),
        len(output_text),
        usage or {},
    )

def run_agent_multi_output(
    runtime: AgentRuntime,
    *,
    agent_name: str,
    agent_vs_name: str,
    athlete_id: str,
    tasks: list[AgentTask],
    user_input: str,
    run_id: str,
    model_override: str | None = None,
    temperature_override: float | None = None,
    include_debug_file_search: bool = False,
    force_file_search: bool = True,
    max_num_results: int | None = None,
    stream_handlers: dict[str, object] | None = None,
) -> dict[str, object]:
    """Run an agent that can emit multiple strict tool outputs."""
    output_specs: list[OutputSpec] = [OUTPUT_SPECS[task] for task in tasks]

    model = model_override or runtime.model
    temperature = temperature_override if temperature_override is not None else runtime.temperature
    agent_vs_id = runtime.vs_resolver.id_for_store_name(agent_vs_name)
    system_prompt = runtime.prompt_loader.combined_system_prompt(agent_name)
    client_config = getattr(runtime.client, "config", None)
    base_url = getattr(client_config, "base_url", None) if client_config else None
    is_groq = bool(str(model).startswith("groq/")) or (
        isinstance(base_url, str) and "api.groq.com" in base_url
    )

    def _load_mandatory_doc(name: str) -> str | None:
        return _load_knowledge_source("specs", name)

    mandatory_by_schema = {
        "season_scenarios.schema.json": "mandatory_output_season_scenarios.md",
        "season_scenario_selection.schema.json": "mandatory_output_season_scenario_selection.md",
        "season_plan.schema.json": "mandatory_output_season_plan.md",
        "season_phase_feed_forward.schema.json": "mandatory_output_season_phase_feed_forward.md",
        "phase_guardrails.schema.json": "mandatory_output_phase_guardrails.md",
        "phase_structure.schema.json": "mandatory_output_phase_structure.md",
        "phase_preview.schema.json": "mandatory_output_phase_preview.md",
        "phase_feed_forward.schema.json": "mandatory_output_phase_feed_forward.md",
        "week_plan.schema.json": "mandatory_output_week_plan.md",
        "workouts.schema.json": "mandatory_output_intervals_workouts.md",
        "des_analysis_report.schema.json": "mandatory_output_des_analysis_report.md",
    }

    for spec in output_specs:
        doc_name = mandatory_by_schema.get(spec.schema_file)
        if not doc_name:
            continue
        if doc_name in system_prompt or doc_name in user_input:
            continue
        mandatory = _load_mandatory_doc(doc_name)
        if mandatory:
            system_prompt = (
                f"{system_prompt}\n"
                f"Mandatory JSON Output ({spec.artifact_type.value}; injected from {doc_name}):\n"
                f"\"\"\"\n{mandatory}\n\"\"\"\n"
            )

    mode = injection_mode_for_tasks(tasks)
    injected_block = build_injection_block(agent_name, mode=mode)
    if injected_block and injected_block not in system_prompt:
        system_prompt = f"{system_prompt}\n{injected_block}"

    bundler = SchemaBundler(runtime.schema_dir)
    store_tools = [build_strict_store_tool(bundler, spec) for spec in output_specs]
    store_tools_by_name: dict[str, ToolDef] = {}
    for tool in store_tools:
        name = tool.get("name")
        if not isinstance(name, str):
            function_def = tool.get("function")
            if isinstance(function_def, dict):
                function_name = function_def.get("name")
                name = function_name if isinstance(function_name, str) else None
        if isinstance(name, str) and name:
            store_tools_by_name[name] = tool

    read_ctx = ReadToolContext(athlete_id=athlete_id, workspace_root=runtime.workspace_root, agent_name=agent_name)
    read_defs = read_tool_defs()
    read_handlers = read_tool_handlers(read_ctx)

    guarded = GuardedValidatedStore(
        athlete_id=athlete_id,
        schema_dir=runtime.schema_dir,
        workspace_root=runtime.workspace_root,
    )

    if max_num_results is None:
        max_num_results = _parse_int(os.getenv("RPS_LLM_FILE_SEARCH_MAX_RESULTS")) or 20
    debug_file_search = (
        include_debug_file_search
        or _env_flag("RPS_LLM_DEBUG")
        or logger.isEnabledFor(logging.DEBUG)
    )

    tools_read: list[ToolDef] = []
    web_search_enabled = _web_search_enabled(agent_name)
    if web_search_enabled:
        tools_read.append(_web_search_tool())
    tools_read += [*read_defs]
    tools_all = [*tools_read, *store_tools]
    logger.info(
        "tools: agent=%s stores=%s max_results=%s web_search=%s",
        agent_name,
        [agent_vs_id],
        max_num_results,
        web_search_enabled,
    )

    input_list: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]

    def _coerce_envelope_args(args: dict[str, Any]) -> dict[str, Any]:
        """Try to recover an envelope object from common tool-arg shapes."""
        if "meta" in args and "data" in args:
            return args
        if "meta" in args and "payload" in args and isinstance(args.get("payload"), dict):
            return {"meta": args.get("meta"), "data": args.get("payload")}
        if "meta" in args and "document" in args and isinstance(args.get("document"), dict):
            return {"meta": args.get("meta"), "data": args.get("document")}

        def _maybe_parse(value: object) -> dict[str, Any] | None:
            if isinstance(value, dict) and "meta" in value and "data" in value:
                return value
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                except json.JSONDecodeError:
                    return None
                if isinstance(parsed, dict) and "meta" in parsed and "data" in parsed:
                    return parsed
            return None

        if len(args) == 1:
            recovered = _maybe_parse(next(iter(args.values())))
            if recovered:
                return recovered

        for key in ("document", "payload", "envelope", "json", "content"):
            if key in args:
                recovered = _maybe_parse(args[key])
                if recovered:
                    return recovered

        return args

    def _fill_season_scenarios(document: dict[str, Any]) -> dict[str, Any]:
        """Ensure required season_scenarios fields exist to satisfy strict schema."""
        if not isinstance(document, dict):
            return document
        meta = document.get("meta") or {}
        artifact_type = str(meta.get("artifact_type", "")).upper()
        if artifact_type == "SEASON_SCENARIO_SELECTION":
            if meta.get("authority") != "Informational":
                meta["authority"] = "Informational"
            if meta.get("owner_agent") != "Season-Scenario-Agent":
                meta["owner_agent"] = "Season-Scenario-Agent"
            if meta.get("schema_id") != "SeasonScenarioSelectionInterface":
                meta["schema_id"] = "SeasonScenarioSelectionInterface"
            if meta.get("schema_version") != "1.0":
                meta["schema_version"] = "1.0"
            if "notes" not in meta:
                meta["notes"] = ""
            else:
                notes_value = meta.get("notes")
                if isinstance(notes_value, list):
                    meta["notes"] = " ".join(str(item) for item in notes_value if item is not None)
            document["meta"] = meta
            data = document.get("data") or {}
            if not isinstance(data, dict):
                data = {}
            data.setdefault("selection_rationale", "")
            data.setdefault("notes", [])
            document["data"] = data
            return document
        if artifact_type != "SEASON_SCENARIOS":
            return document
        if meta.get("authority") != "Informational":
            meta["authority"] = "Informational"
        if meta.get("owner_agent") != "Season-Scenario-Agent":
            meta["owner_agent"] = "Season-Scenario-Agent"
        if meta.get("schema_id") != "SeasonScenariosInterface":
            meta["schema_id"] = "SeasonScenariosInterface"
        if meta.get("schema_version") != "1.0":
            meta["schema_version"] = "1.0"
        if "notes" not in meta:
            meta["notes"] = ""
        else:
            notes_value = meta.get("notes")
            if isinstance(notes_value, list):
                meta["notes"] = " ".join(str(item) for item in notes_value if item is not None)
        document["meta"] = meta
        data = document.get("data") or {}
        if not isinstance(data, dict):
            data = {}
        allowed_data_keys = {
            "kpi_profile_ref",
            "athlete_profile_ref",
            "planning_horizon_weeks",
            "scenarios",
            "notes",
        }
        data = {key: value for key, value in data.items() if key in allowed_data_keys}
        data.setdefault("notes", [])
        scenarios = data.get("scenarios") or []
        cleaned_scenarios: list[dict[str, Any]] = []
        if isinstance(scenarios, list):
            for scenario in scenarios:
                if not isinstance(scenario, dict):
                    continue
                allowed_scenario_keys = {
                    "scenario_id",
                    "name",
                    "core_idea",
                    "load_philosophy",
                    "risk_profile",
                    "key_differences",
                    "best_suited_if",
                    "scenario_guidance",
                }
                scenario = {key: value for key, value in scenario.items() if key in allowed_scenario_keys}
                guidance = scenario.get("scenario_guidance") or {}
                if not isinstance(guidance, dict):
                    guidance = {}
                allowed_guidance_keys = {
                    "deload_cadence",
                    "phase_length_weeks",
                    "phase_count_expected",
                    "max_shortened_phases",
                    "shortening_budget_weeks",
                    "phase_plan_summary",
                    "event_alignment_notes",
                    "risk_flags",
                    "fixed_rest_days",
                    "constraint_summary",
                    "kpi_guardrail_notes",
                    "decision_notes",
                    "intensity_guidance",
                    "assumptions",
                    "unknowns",
                }
                guidance = {key: value for key, value in guidance.items() if key in allowed_guidance_keys}
                def _as_positive_int(value: object) -> int | None:
                    if isinstance(value, bool):
                        return None
                    if isinstance(value, int) and value > 0:
                        return value
                    return None

                def _as_non_negative_int(value: object) -> int | None:
                    if isinstance(value, bool):
                        return None
                    if isinstance(value, int) and value >= 0:
                        return value
                    return None

                def _iso_week_range_weeks(range_str: object) -> int | None:
                    if not isinstance(range_str, str) or "--" not in range_str:
                        return None
                    start_str, end_str = range_str.split("--", 1)
                    try:
                        sy, sw = (int(part) for part in start_str.split("-", 1))
                        ey, ew = (int(part) for part in end_str.split("-", 1))
                    except ValueError:
                        return None
                    try:
                        start_date = datetime.date.fromisocalendar(sy, sw, 1)
                        end_date = datetime.date.fromisocalendar(ey, ew, 7)
                    except ValueError:
                        return None
                    return ((end_date - start_date).days // 7) + 1

                phase_len = _as_positive_int(guidance.get("phase_length_weeks"))
                planning_weeks = _as_positive_int(data.get("planning_horizon_weeks"))
                if planning_weeks is None:
                    planning_weeks = _as_positive_int(_iso_week_range_weeks(meta.get("iso_week_range")))
                if phase_len and planning_weeks:
                    phase_count_default = math.ceil(planning_weeks / phase_len)
                    shortening_budget_default = max(0, (phase_count_default * phase_len) - planning_weeks)
                else:
                    phase_count_default = 1
                    shortening_budget_default = 0

                guidance["phase_count_expected"] = _as_positive_int(
                    guidance.get("phase_count_expected")
                ) or phase_count_default
                guidance["max_shortened_phases"] = _as_non_negative_int(
                    guidance.get("max_shortened_phases")
                ) or 2
                guidance["shortening_budget_weeks"] = _as_non_negative_int(
                    guidance.get("shortening_budget_weeks")
                ) or shortening_budget_default
                phase_summary = guidance.get("phase_plan_summary")
                if not isinstance(phase_summary, dict):
                    phase_summary = {}
                full_phases = phase_summary.get("full_phases")
                if not isinstance(full_phases, int) or full_phases < 0:
                    full_phases = guidance["phase_count_expected"]
                shortened = phase_summary.get("shortened_phases")
                if not isinstance(shortened, list):
                    shortened = []
                cleaned_shortened = []
                for item in shortened:
                    if not isinstance(item, dict):
                        continue
                    length = item.get("len")
                    count = item.get("count")
                    if isinstance(length, int) and length > 0 and isinstance(count, int) and count > 0:
                        cleaned_shortened.append({"len": length, "count": count})
                guidance["phase_plan_summary"] = {
                    "full_phases": full_phases,
                    "shortened_phases": cleaned_shortened,
                }
                guidance.setdefault("event_alignment_notes", [])
                guidance.setdefault("risk_flags", [])
                guidance.setdefault("fixed_rest_days", [])
                guidance.setdefault("constraint_summary", [])
                guidance.setdefault("kpi_guardrail_notes", [])
                guidance.setdefault("decision_notes", [])
                guidance.setdefault("assumptions", [])
                guidance.setdefault("unknowns", [])
                guidance.setdefault("intensity_guidance", {"allowed_domains": [], "avoid_domains": []})
                scenario["scenario_guidance"] = guidance
                cleaned_scenarios.append(scenario)
        data["scenarios"] = cleaned_scenarios
        document["data"] = data
        return document

    def _normalize_week_plan_meta(document: dict[str, Any]) -> dict[str, Any]:
        """Coerce week_plan meta fields to match schema constants."""
        if not isinstance(document, dict):
            return document
        meta = document.get("meta")
        if not isinstance(meta, dict):
            return document
        meta["artifact_type"] = "WEEK_PLAN"
        meta["schema_id"] = "WeekPlanInterface"
        meta["schema_version"] = "1.2"
        meta["authority"] = "Binding"
        meta["owner_agent"] = "Week-Planner"
        if "notes" not in meta or meta.get("notes") is None:
            meta["notes"] = ""
        document["meta"] = meta
        return document

    def _normalize_des_analysis_report(document: dict[str, Any]) -> dict[str, Any]:
        """Coerce DES analysis report constants to match schema."""
        if not isinstance(document, dict):
            return document
        meta = document.get("meta")
        if isinstance(meta, dict):
            meta["artifact_type"] = "DES_ANALYSIS_REPORT"
            meta["schema_id"] = "DESAnalysisInterface"
            meta["schema_version"] = "1.1"
            meta["authority"] = "Binding"
            meta["owner_agent"] = "Performance-Analyst"
            if "notes" not in meta or meta.get("notes") is None:
                meta["notes"] = ""
            document["meta"] = meta
        data = document.get("data")
        if isinstance(data, dict):
            rec = data.get("recommendation")
            if isinstance(rec, dict):
                rec["type"] = "advisory"
                rec["scope"] = "Season-Planner"
                data["recommendation"] = rec
            document["data"] = data
        return document

    def _normalize_phase_guardrails(document: dict[str, Any]) -> dict[str, Any]:
        return normalize_phase_guardrails_document(document)

    def _fill_season_plan(document: dict[str, Any]) -> dict[str, Any]:
        """Normalize common SEASON_PLAN placement issues."""
        if not isinstance(document, dict):
            return document
        meta = document.get("meta") or {}
        if str(meta.get("artifact_type", "")).upper() != "SEASON_PLAN":
            return document
        if not meta.get("data_confidence"):
            meta["data_confidence"] = "UNKNOWN"
        document["meta"] = meta
        data = document.get("data") or {}
        if not isinstance(data, dict):
            return document
        body = data.get("body_metadata") or {}
        if isinstance(body, dict):
            mt_guidance = body.get("moving_time_rate_guidance") or {}
            if isinstance(mt_guidance, dict):
                for key in ("w_per_kg", "kj_per_kg_per_hour"):
                    band = mt_guidance.get(key)
                    if isinstance(band, dict):
                        for bound in ("min", "max"):
                            val = band.get(bound)
                            if isinstance(val, (int, float)):
                                band[bound] = round(float(val), 1)
        phases = data.get("phases")
        if isinstance(phases, list):
            top_semantics = data.get("allowed_forbidden_semantics")
            if isinstance(top_semantics, dict):
                for phase in phases:
                    if isinstance(phase, dict) and "allowed_forbidden_semantics" not in phase:
                        phase["allowed_forbidden_semantics"] = top_semantics
                data.pop("allowed_forbidden_semantics", None)
            for phase in phases:
                if not isinstance(phase, dict):
                    continue
                weekly_kj = (
                    phase.get("weekly_load_corridor", {}).get("weekly_kj")
                    if isinstance(phase.get("weekly_load_corridor"), dict)
                    else None
                )
                if isinstance(weekly_kj, dict):
                    for bound in ("min", "max"):
                        val = weekly_kj.get(bound)
                        if isinstance(val, (int, float)):
                            weekly_kj[bound] = round(float(val))
                    for bound in ("kj_per_kg_min", "kj_per_kg_max"):
                        val = weekly_kj.get(bound)
                        if isinstance(val, (int, float)):
                            weekly_kj[bound] = round(float(val), 2)
                overview = phase.get("overview")
                if isinstance(overview, dict) and "non-negotiables" in overview:
                    overview["non_negotiables"] = overview.pop("non-negotiables")
        season_load = data.get("season_load_envelope") or {}
        if isinstance(season_load, dict):
            expected_range = season_load.get("expected_average_weekly_kj_range")
            if isinstance(expected_range, dict):
                for bound in ("min", "max"):
                    val = expected_range.get(bound)
                    if isinstance(val, (int, float)):
                        expected_range[bound] = round(float(val))
        global_constraints = data.get("global_constraints")
        if isinstance(global_constraints, dict):
            recovery = global_constraints.get("recovery_protection")
            if isinstance(recovery, dict):
                notes = recovery.get("notes")
                if isinstance(notes, str):
                    recovery["notes"] = [notes]
                elif notes is None:
                    recovery["notes"] = []
                global_constraints["recovery_protection"] = recovery
            data["global_constraints"] = global_constraints
        if "explicit_forbidden_content" not in data or not isinstance(
            data.get("explicit_forbidden_content"), list
        ):
            data["explicit_forbidden_content"] = [
                "phase definitions (phase plans)",
                "weekly schedules",
                "day-by-day structure",
                "workouts or interval prescriptions",
                "numeric progression rules",
                "daily or session-level kJ targets",
            ]
        if "self_check" not in data or not isinstance(data.get("self_check"), dict):
            data["self_check"] = {
                "planning_horizon_is_at_least_8_weeks": True,
                "every_phase_defines_weekly_kj_corridor": True,
                "every_phase_includes_kj_per_kg_guardrails_and_reference_mass": True,
                "every_phase_maps_to_cycle_and_deload_intent": True,
                "every_phase_includes_narrative_and_metabolic_focus": True,
                "every_phase_includes_evaluation_focus_and_exit_assumptions": True,
                "season_load_envelope_and_assumptions_documented": True,
                "principles_and_scientific_foundation_documented": True,
                "allowed_forbidden_domains_listed": True,
                "no_phase_or_week_planning_content": True,
                "header_includes_implements_iso_week_range_trace": True,
            }
        if "principles_scientific_foundation" not in data or not isinstance(
            data.get("principles_scientific_foundation"), dict
        ):
            logger.warning(
                "SEASON_PLAN missing principles_scientific_foundation; leaving for model to supply."
            )
        document["data"] = data
        return document

    def _is_envelope(value: object) -> bool:
        return isinstance(value, dict) and "meta" in value and "data" in value

    def _format_heading_for_log(text: str) -> str:
        stripped = text.lstrip()
        if stripped.startswith(("**", "#")):
            return f"\n{text}"
        return text

    def _log_response_content(response_obj: LiteLLMResponse, *, label: str) -> None:
        text_out = response_obj.output_text or extract_text_output(response_obj) or ""
        if not text_out:
            return
        max_chars = 4000
        trimmed = text_out.strip()
        if len(trimmed) > max_chars:
            trimmed = trimmed[:max_chars] + "…"
        logger.warning("Model response text (%s): %s", label, _format_heading_for_log(trimmed))

    def _log_no_tool_call_summary(
        response_obj: LiteLLMResponse,
        *,
        attempted_store: bool,
        wanted_tools: set[str],
    ) -> None:
        text_out = response_obj.output_text or extract_text_output(response_obj) or ""
        summary = {
            "attempted_forced_store": attempted_store,
            "wanted_tools": sorted(wanted_tools),
            "final_text_preview": (text_out.strip()[:200] + "…") if text_out else "",
        }
        logger.warning("No-tool-call summary: %s", json.dumps(summary, ensure_ascii=False))

    def _is_terminal_stop_text(text: str) -> bool:
        """Return True when the model text is an explicit stop/blocker response."""
        normalized = text.strip().lower()
        if not normalized:
            return False
        stop_markers = (
            "stop_reason:",
            "missing_binding_artefacts:",
            "next_action:",
            "schema-invalid",
            "invalid/missing",
            "required binding artefact",
            "required predecessor artefact is missing",
            "required exact-range",
            "cannot proceed",
        )
        if any(marker in normalized for marker in stop_markers):
            return True
        return normalized.startswith("stop:")

    def _terminal_stop_result(final_text: str) -> dict[str, object]:
        """Return a terminal error result for explicit model stop responses."""
        return {
            "ok": False,
            "produced": produced,
            "final_text": final_text,
            "error": "MODEL_STOPPED_ON_BLOCKER",
            "details": [
                "Model reported explicit blocking validation or dependency issues.",
                "Forced store and fallback store were skipped.",
            ],
        }

    def _create_response(
        force_search_flag: bool,
        forced_tool_name: str | None = None,
        force_json_only: bool = False,
        force_store_only: bool = False,
        force_read_only: bool = False,
    ):
        if forced_tool_name:
            selected_tool = store_tools_by_name.get(forced_tool_name)
            tools_for_call = [selected_tool] if selected_tool else store_tools
        elif force_store_only:
            tools_for_call = store_tools
        elif force_read_only:
            tools_for_call = tools_read
        elif force_json_only:
            tools_for_call = store_tools
        elif force_search_flag:
            tools_for_call = tools_read
        else:
            tools_for_call = tools_all
        payload: dict[str, Any] = {
            "model": model,
            "tools": tools_for_call,
            "input": input_list,
        }
        if is_groq and tools_for_call:
            payload["stream"] = False
        reasoning = build_reasoning_payload(
            model,
            runtime.reasoning_effort,
            runtime.reasoning_summary,
        )
        if reasoning:
            payload["reasoning"] = reasoning
        # NOTE(temporary): Disabled forced knowledge_search tool_choice due to Groq
        # tool_choice mismatch errors (2026-02-08). Re-enable when Groq tool
        # routing is stable again.
        # if force_search_flag:
        #     payload["tool_choice"] = {"type": "function", "name": "knowledge_search"}
        elif forced_tool_name:
            payload["tool_choice"] = {"type": "function", "name": forced_tool_name}
        if debug_file_search:
            logger.info(
                "responses.create payload: tool_choice=%s tools=%s",
                payload.get("tool_choice"),
                [tool.get("type") for tool in tools_for_call],
            )
        if temperature is not None and supports_temperature(model):
            payload["temperature"] = temperature
        if runtime.max_completion_tokens is not None:
            payload["max_completion_tokens"] = runtime.max_completion_tokens
        start = time.perf_counter()
        local_handlers: dict[str, object] = dict(stream_handlers) if stream_handlers else {}
        if "reasoning_log_meta" not in local_handlers:
            local_handlers["reasoning_log_meta"] = {
                "agent": agent_name,
                "model": model,
                "run_id": run_id,
            }
        response = create_response(runtime.client, payload, logger, stream_handlers=local_handlers or None)
        elapsed = time.perf_counter() - start
        label = forced_tool_name or ("knowledge_search" if force_search_flag else "auto")
        _log_response_diagnostics(response, label=label, elapsed_s=elapsed)
        return response

    produced: dict[str, object] = {}
    wanted_tool_names = {spec.tool_name for spec in output_specs}

    force_search = force_file_search
    seen_summaries: set[str] = set()
    response = _create_response(force_search)
    last_text = response.output_text or extract_text_output(response) or ""
    if debug_file_search:
        _log_file_search_calls(response)
        _log_file_search_results(response)
        if force_search and not _has_knowledge_search_calls(response):
            logger.warning(
                "force_file_search=True but no knowledge_search calls returned"
            )
    for summary in extract_reasoning_summaries(response):
        if summary in seen_summaries:
            continue
        seen_summaries.add(summary)
        logger.info("Reasoning summary: %s", _format_heading_for_log(summary))
    input_list += response.output
    force_search = False

    safety = 0
    attempted_forced_store = False
    required_artifacts: set[str] = set()
    required_ready = False
    if agent_name == "season_planner":
        required_artifacts = {
            "athlete_profile",
            "planning_events",
            "logistics",
            "KPI_PROFILE",
            "ZONE_MODEL",
            "AVAILABILITY",
            "WELLNESS",
        }

    def _mark_required_loaded(tool_name: str | None, args: dict[str, Any], result: object) -> None:
        nonlocal required_ready
        if not required_artifacts:
            return
        if not isinstance(result, dict) or not result.get("ok", False):
            return
        if tool_name == "workspace_get_input":
            key = args.get("input_type") or args.get("input_name")
            if isinstance(key, str):
                required_artifacts.discard(key)
        elif tool_name == "workspace_get_latest":
            key = args.get("artifact_type")
            if isinstance(key, str):
                required_artifacts.discard(key)
        required_ready = not required_artifacts

    def _log_tool_warning(tool_name: str | None, args: dict[str, Any], result: object) -> None:
        """Log workspace tool warnings surfaced by read handlers."""
        if not isinstance(result, dict):
            return
        warning = result.get("_tool_warning")
        if not isinstance(warning, str) or not warning.strip():
            return
        logger.warning(
            "Tool warning %s artifact=%s: %s",
            tool_name,
            args.get("artifact_type"),
            warning.strip(),
        )
    while True:
        safety += 1
        if safety > MAX_TOOL_ITERATIONS:
            return {"ok": False, "error": "Too many tool iterations", "produced": produced}

        function_calls = [item for item in response.output if _item_type(item) == "function_call"]
        if not function_calls:
            all_done = wanted_tool_names.issubset(set(produced.keys()))
            final_text = response.output_text or last_text
            terminal_stop = bool(final_text) and _is_terminal_stop_text(final_text)
            if final_text:
                _log_response_content(response, label="no_tool_call")
            _log_no_tool_call_summary(
                response,
                attempted_store=attempted_forced_store,
                wanted_tools=wanted_tool_names,
            )
            if not all_done and terminal_stop:
                logger.warning("Terminal model stop detected; skipping forced store and fallback store.")
                return _terminal_stop_result(final_text)
            if (
                not all_done
                and len(output_specs) == 1
                and output_specs[0].envelope
                and attempted_forced_store
            ):
                return {
                    "ok": False,
                    "produced": produced,
                    "final_text": final_text,
                    "error": "STOP_TOOL_CALL_REQUIRED",
                    "details": [
                        "Model did not call the required store tool.",
                        "Retry with an explicit tool call instruction or fix prompt/tool usage.",
                    ],
                }
            if (
                not all_done
                and len(output_specs) == 1
                and output_specs[0].envelope
                and not attempted_forced_store
            ):
                spec = output_specs[0]
                if spec.artifact_type in {
                    ArtifactType.SEASON_SCENARIOS,
                    ArtifactType.SEASON_SCENARIO_SELECTION,
                    ArtifactType.SEASON_PLAN,
                    ArtifactType.DES_ANALYSIS_REPORT,
                }:
                    if is_groq:
                        if required_ready:
                            attempted_forced_store = True
                            logger.info(
                                "Groq detected: switching to store-only phase.",
                            )
                            input_list.append(
                                {
                                    "role": "user",
                                    "content": (
                                        "Return only a schema-compliant JSON envelope and call the "
                                        f"{spec.tool_name} tool. Do not include any other text."
                                    ),
                                }
                            )
                            response = _create_response(False, force_store_only=True)
                        else:
                            logger.info(
                                "Groq detected: switching to read-only phase (load required artefacts).",
                            )
                            input_list.append(
                                {
                                    "role": "user",
                                    "content": (
                                        "Load all required artefacts using the workspace_get_* tools now. "
                                        "Do not answer with final output yet."
                                    ),
                                }
                            )
                            response = _create_response(False, force_read_only=True)
                    else:
                        attempted_forced_store = True
                        input_list.append(
                            {
                                "role": "user",
                                "content": (
                                    "Return only a schema-compliant JSON envelope and call the "
                                    f"{spec.tool_name} tool. Do not include any other text."
                                ),
                            }
                        )
                        response = _create_response(False, forced_tool_name=spec.tool_name)
                    if response.output_text:
                        last_text = response.output_text
                    else:
                        text_out = extract_text_output(response)
                        if text_out:
                            last_text = text_out
                    if debug_file_search:
                        _log_file_search_calls(response)
                        _log_file_search_results(response)
                    for summary in extract_reasoning_summaries(response):
                        if summary in seen_summaries:
                            continue
                        seen_summaries.add(summary)
                        logger.info("Reasoning summary: %s", _format_heading_for_log(summary))
                    input_list += response.output
                    continue
            if (
                not all_done
                and len(output_specs) == 1
                and output_specs[0].envelope
                and final_text
            ):
                spec = output_specs[0]
                try:
                    parsed = json.loads(final_text.strip())
                except json.JSONDecodeError:
                    logger.warning("Fallback store skipped: response text was not valid JSON.")
                else:
                    parsed = _fill_season_scenarios(parsed)
                    parsed = _fill_season_plan(parsed)
                    parsed = _normalize_phase_guardrails(parsed)
                    if spec.artifact_type == ArtifactType.WEEK_PLAN:
                        parsed = _normalize_week_plan_meta(parsed)
                    if spec.artifact_type == ArtifactType.DES_ANALYSIS_REPORT:
                        parsed = _normalize_des_analysis_report(parsed)
                    try:
                        saved = guarded.guard_put_validated(
                            output_spec=spec,
                            document=parsed,
                            run_id=run_id,
                            producer_agent=agent_name,
                            update_latest=True,
                        )
                        produced[spec.tool_name] = saved
                        logger.warning(
                            "Fallback store used for %s (missing tool call).",
                            spec.artifact_type.value,
                        )
                        return {"ok": True, "produced": produced}
                    except SchemaValidationError as exc:
                        logger.warning(
                            "Fallback schema validation failed for %s: %s",
                            spec.artifact_type.value,
                            exc.errors,
                        )
                        return {
                            "ok": False,
                            "produced": produced,
                            "final_text": final_text,
                            "error": "Schema validation failed",
                            "details": exc.errors,
                        }
                    except Exception as exc:
                        logger.warning(
                            "Fallback store failed for %s: %s",
                            spec.artifact_type.value,
                            exc,
                        )
                        return {
                            "ok": False,
                            "produced": produced,
                            "final_text": final_text,
                            "error": str(exc),
                        }
            return {"ok": all_done, "produced": produced, "final_text": final_text}

        for call in function_calls:
            raw_name = _item_field(call, "name")
            name = raw_name if isinstance(raw_name, str) else None
            args_raw_obj = _item_field(call, "arguments")
            args_raw = args_raw_obj if isinstance(args_raw_obj, str) else "{}"
            call_id = _item_field(call, "call_id")
            try:
                args = json.loads(args_raw)
            except json.JSONDecodeError:
                args = {}

            logger.debug("Tool call %s args=%s", name, args)

            if name in read_handlers:
                try:
                    result = read_handlers[name](args)
                except Exception as exc:
                    result = {"ok": False, "error": str(exc)}
                    logger.warning("Read tool failed %s: %s", name, exc)
                _log_tool_warning(name, args, result)
                _mark_required_loaded(name, args, result)

                input_list.append(
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "name": name,
                        "output": json.dumps(result, ensure_ascii=False),
                    }
                )
                continue

            spec_match = next((item for item in output_specs if item.tool_name == name), None)
            if spec_match is None:
                result = {"ok": False, "error": f"Unknown store tool: {name}"}
                input_list.append(
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "name": name,
                        "output": json.dumps(result, ensure_ascii=False),
                    }
                )
                continue
            spec = spec_match

            document = _coerce_envelope_args(args) if spec.envelope else args.get("workouts")
            document = _fill_season_scenarios(document)
            document = _fill_season_plan(document)
            document = _normalize_phase_guardrails(document)
            if spec.artifact_type == ArtifactType.WEEK_PLAN:
                document = _normalize_week_plan_meta(document)
            if spec.artifact_type == ArtifactType.DES_ANALYSIS_REPORT:
                document = _normalize_des_analysis_report(document)
            if spec.envelope and not _is_envelope(document):
                result = {
                    "ok": False,
                    "error": "Envelope artefact must be an object with meta and data",
                    "details": [
                        "Expected top-level keys: meta, data",
                        "Do not wrap the envelope inside payload/document/envelope keys",
                    ],
                }
                input_list.append(
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "name": name,
                        "output": json.dumps(result, ensure_ascii=False),
                    }
                )
                continue
            try:
                saved = guarded.guard_put_validated(
                    output_spec=spec,
                    document=document,
                    run_id=run_id,
                    producer_agent=agent_name,
                    update_latest=True,
                )
                if name is not None:
                    produced[name] = saved
                result = saved
            except SchemaValidationError as exc:
                details = list(exc.errors or [])
                max_items = 8
                preview = details[:max_items]
                suffix = ""
                if len(details) > max_items:
                    suffix = f" (+{len(details) - max_items} more)"
                summary = "; ".join(preview) + suffix if preview else "Unknown schema error."
                result = {
                    "ok": False,
                    "error": f"Schema validation failed ({spec.artifact_type.value}): {summary}",
                    "details": details,
                }
                logger.warning("Schema validation failed for %s: %s", spec.artifact_type.value, details)
            except Exception as exc:
                result = {"ok": False, "error": str(exc)}
                logger.warning("Store failed for %s: %s", spec.artifact_type.value, exc)

            input_list.append(
                {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "name": name,
                    "output": json.dumps(result, ensure_ascii=False),
                }
            )

        if wanted_tool_names.issubset(set(produced.keys())):
            return {"ok": True, "produced": produced}

        response = _create_response(force_search)
        if response.output_text:
            last_text = response.output_text
        else:
            text_out = extract_text_output(response)
            if text_out:
                last_text = text_out
        if debug_file_search:
            _log_file_search_calls(response)
            _log_file_search_results(response)
        for summary in extract_reasoning_summaries(response):
            if summary in seen_summaries:
                continue
            seen_summaries.add(summary)
            logger.info("Reasoning summary: %s", _format_heading_for_log(summary))
        input_list += response.output
    if debug_file_search:
        _log_file_search_calls(response)
        _log_file_search_results(response)
        for summary in extract_reasoning_summaries(response):
            if summary in seen_summaries:
                continue
            seen_summaries.add(summary)
            logger.info("Reasoning summary: %s", _format_heading_for_log(summary))
        input_list += response.output
    return {"ok": False, "produced": produced, "final_text": last_text, "error": "UNEXPECTED_LOOP_EXIT"}
