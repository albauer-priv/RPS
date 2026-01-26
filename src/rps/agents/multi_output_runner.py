"""Strict tool-calling runner for multi-output tasks."""

from __future__ import annotations

import datetime
import json
import math
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import OpenAI

from rps.agents.tasks import AgentTask, OUTPUT_SPECS, OutputSpec
from rps.openai.reasoning import build_reasoning_payload
from rps.openai.model_capabilities import supports_temperature
from rps.openai.response_utils import (
    extract_file_search_results,
    extract_reasoning_summaries,
    extract_text_output,
)
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

@dataclass(frozen=True)
class AgentRuntime:
    """Runtime dependencies for multi-output agent runs."""
    client: OpenAI
    model: str
    temperature: float | None
    reasoning_effort: str | None
    reasoning_summary: str | None
    prompt_loader: PromptLoader
    vs_resolver: VectorStoreResolver
    schema_dir: Path
    workspace_root: Path


def _file_search_tool(agent_vs_id: str, max_num_results: int) -> dict[str, Any]:
    """Build a file_search tool payload for Responses API."""
    return {
        "type": "file_search",
        "vector_store_ids": [agent_vs_id],
        "max_num_results": max_num_results,
    }


def _item_type(item: Any) -> str | None:
    """Return the type field for response output items."""
    if isinstance(item, dict):
        return item.get("type")
    return getattr(item, "type", None)


def _item_field(item: Any, name: str) -> Any:
    """Safely read a field from a response output item."""
    if isinstance(item, dict):
        return item.get(name)
    return getattr(item, name, None)


def _log_file_search_results(response: Any) -> None:
    """Log file_search results for debugging."""
    results = extract_file_search_results(response)
    if not results:
        logger.info("file_search results: none")
        return
    logger.info("file_search results: %d", len(results))
    for idx, result in enumerate(results, start=1):
        logger.info(
            "file_search[%d] file=%s score=%s attrs=%s",
            idx,
            result.get("filename"),
            result.get("score"),
            result.get("attributes"),
        )

def _log_file_search_calls(response: Any) -> None:
    """Log file_search call details when available."""
    items = getattr(response, "output", []) or []
    calls = [item for item in items if _item_type(item) == "file_search_call"]
    if not calls:
        logger.info("file_search calls: none")
        return
    for idx, item in enumerate(calls, start=1):
        payload = _item_field(item, "queries") or _item_field(item, "query") or None
        filters = _item_field(item, "filters") or _item_field(item, "filter") or None
        logger.info(
            "file_search_call[%d] queries=%s filters=%s keys=%s",
            idx,
            payload,
            filters,
            list(item.keys()) if isinstance(item, dict) else None,
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

def _extract_usage(response: Any) -> dict[str, Any]:
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


def _log_response_diagnostics(response: Any, *, label: str, elapsed_s: float) -> None:
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
) -> dict[str, Any]:
    """Run an agent that can emit multiple strict tool outputs."""
    output_specs: list[OutputSpec] = [OUTPUT_SPECS[task] for task in tasks]

    model = model_override or runtime.model
    temperature = temperature_override if temperature_override is not None else runtime.temperature
    agent_vs_id = runtime.vs_resolver.id_for_store_name(agent_vs_name)
    system_prompt = runtime.prompt_loader.combined_system_prompt(agent_name)

    def _load_load_estimation_spec_macro() -> str | None:
        root = Path(__file__).resolve().parents[3]
        path = root / "knowledge" / "_shared" / "sources" / "specs" / "load_estimation_spec.md"
        if not path.exists():
            return None
        content = path.read_text(encoding="utf-8")
        lines = content.splitlines()
        end = None
        for i, line in enumerate(lines):
            if line.startswith("## Meso"):
                end = i
                break
        section = "\n".join(lines[:end]).strip() if end else content
        return section

    def _load_mandatory_doc(name: str) -> str | None:
        root = Path(__file__).resolve().parents[3]
        path = root / "knowledge" / "_shared" / "sources" / "specs" / name
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8").strip()

    mandatory_by_schema = {
        "season_scenarios.schema.json": "mandatory_output_season_scenarios.md",
        "macro_overview.schema.json": "mandatory_output_macro_overview.md",
        "macro_meso_feed_forward.schema.json": "mandatory_output_macro_meso_feed_forward.md",
        "block_governance.schema.json": "mandatory_output_block_governance.md",
        "block_execution_arch.schema.json": "mandatory_output_block_execution_arch.md",
        "block_execution_preview.schema.json": "mandatory_output_block_execution_preview.md",
        "block_feed_forward.schema.json": "mandatory_output_block_feed_forward.md",
        "workouts_plan.schema.json": "mandatory_output_workouts_plan.md",
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

    if agent_name == "macro_planner":
        if "LoadEstimationSpec (Macro section" not in system_prompt and "load_estimation_spec.md" not in system_prompt:
            spec_section = _load_load_estimation_spec_macro()
            if spec_section:
                system_prompt = (
                    f"{system_prompt}\n"
                    "LoadEstimationSpec (Macro section; injected):\n"
                    f"\"\"\"\n{spec_section}\n\"\"\"\n"
                )

    bundler = SchemaBundler(runtime.schema_dir)
    store_tools = [build_strict_store_tool(bundler, spec) for spec in output_specs]

    read_ctx = ReadToolContext(athlete_id=athlete_id, workspace_root=runtime.workspace_root)
    read_defs = read_tool_defs()
    read_handlers = read_tool_handlers(read_ctx)

    guarded = GuardedValidatedStore(
        athlete_id=athlete_id,
        schema_dir=runtime.schema_dir,
        workspace_root=runtime.workspace_root,
    )

    if max_num_results is None:
        max_num_results = _parse_int(os.getenv("OPENAI_FILE_SEARCH_MAX_RESULTS")) or 20
    debug_file_search = (
        include_debug_file_search
        or _env_flag("OPENAI_DEBUG_FILE_SEARCH")
        or _env_flag("OPENAI_FILE_SEARCH_DEBUG")
        or logger.isEnabledFor(logging.DEBUG)
    )

    tools = [
        _file_search_tool(agent_vs_id, max_num_results),
        *read_defs,
        *store_tools,
    ]
    logger.info(
        "file_search tool: agent=%s stores=%s max_results=%s include_results=%s",
        agent_name,
        [agent_vs_id],
        max_num_results,
        debug_file_search,
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

        def _maybe_parse(value: Any) -> dict[str, Any] | None:
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
            elif isinstance(meta.get("notes"), list):
                meta["notes"] = " ".join(str(item) for item in meta.get("notes") if item is not None)
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
        elif isinstance(meta.get("notes"), list):
            meta["notes"] = " ".join(str(item) for item in meta.get("notes") if item is not None)
        document["meta"] = meta
        data = document.get("data") or {}
        if not isinstance(data, dict):
            data = {}
        allowed_data_keys = {
            "season_brief_ref",
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
                def _as_positive_int(value: Any) -> int | None:
                    if isinstance(value, bool):
                        return None
                    if isinstance(value, int) and value > 0:
                        return value
                    return None

                def _as_non_negative_int(value: Any) -> int | None:
                    if isinstance(value, bool):
                        return None
                    if isinstance(value, int) and value >= 0:
                        return value
                    return None

                def _iso_week_range_weeks(range_str: Any) -> int | None:
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

    def _normalize_workouts_plan_meta(document: dict[str, Any]) -> dict[str, Any]:
        """Coerce workouts_plan meta fields to match schema constants."""
        if not isinstance(document, dict):
            return document
        meta = document.get("meta")
        if not isinstance(meta, dict):
            return document
        meta["artifact_type"] = "WORKOUTS_PLAN"
        meta["schema_id"] = "WorkoutsPlanInterface"
        meta["schema_version"] = "1.2"
        meta["authority"] = "Binding"
        meta["owner_agent"] = "Micro-Planner"
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
                rec["scope"] = "Macro-Planner"
                data["recommendation"] = rec
            document["data"] = data
        return document

    def _normalize_block_governance(document: dict[str, Any]) -> dict[str, Any]:
        """Ensure BLOCK_GOVERNANCE weekly bands are non-degenerate."""
        if not isinstance(document, dict):
            return document
        meta = document.get("meta") or {}
        if str(meta.get("artifact_type", "")).upper() != "BLOCK_GOVERNANCE":
            return document
        data = document.get("data")
        if not isinstance(data, dict):
            return document
        load_guardrails = data.get("load_guardrails")
        if not isinstance(load_guardrails, dict):
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

        return document

    def _fill_macro_overview(document: dict[str, Any]) -> dict[str, Any]:
        """Normalize common MACRO_OVERVIEW placement issues."""
        if not isinstance(document, dict):
            return document
        meta = document.get("meta") or {}
        if str(meta.get("artifact_type", "")).upper() != "MACRO_OVERVIEW":
            return document
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
                            weekly_kj[bound] = int(round(float(val)))
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
                        expected_range[bound] = int(round(float(val)))
        document["data"] = data
        return document

    def _is_envelope(value: Any) -> bool:
        return isinstance(value, dict) and "meta" in value and "data" in value

    def _log_response_content(response_obj: Any, *, label: str) -> None:
        text_out = response_obj.output_text or extract_text_output(response_obj) or ""
        if not text_out:
            return
        max_chars = 4000
        trimmed = text_out.strip()
        if len(trimmed) > max_chars:
            trimmed = trimmed[:max_chars] + "…"
        logger.warning("Model response text (%s): %s", label, trimmed)

    def _log_no_tool_call_summary(
        response_obj: Any,
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

    def _create_response(force_search_flag: bool, forced_tool_name: str | None = None):
        payload: dict[str, Any] = {
            "model": model,
            "tools": tools,
            "input": input_list,
        }
        if debug_file_search:
            payload["include"] = ["file_search_call.results"]
        reasoning = build_reasoning_payload(
            model,
            runtime.reasoning_effort,
            runtime.reasoning_summary,
        )
        if reasoning:
            payload["reasoning"] = reasoning
        if force_search_flag:
            payload["tool_choice"] = {"type": "file_search"}
        elif forced_tool_name:
            payload["tool_choice"] = {"type": "function", "name": forced_tool_name}
        if debug_file_search:
            logger.info(
                "responses.create payload: tool_choice=%s include=%s tools=%s",
                payload.get("tool_choice"),
                payload.get("include"),
                [tool.get("type") for tool in tools],
            )
        if temperature is not None and supports_temperature(model):
            payload["temperature"] = temperature
        start = time.perf_counter()
        response = create_response(runtime.client, payload, logger)
        elapsed = time.perf_counter() - start
        label = forced_tool_name or ("file_search" if force_search_flag else "auto")
        _log_response_diagnostics(response, label=label, elapsed_s=elapsed)
        return response

    produced: dict[str, Any] = {}
    wanted_tool_names = {spec.tool_name for spec in output_specs}

    force_search = force_file_search
    seen_summaries: set[str] = set()
    response = _create_response(force_search)
    last_text = response.output_text or extract_text_output(response) or ""
    if debug_file_search:
        _log_file_search_calls(response)
        _log_file_search_results(response)
        if force_search and not extract_file_search_results(response):
            logger.warning(
                "force_file_search=True but no file_search results or calls returned"
            )
    for summary in extract_reasoning_summaries(response):
        if summary in seen_summaries:
            continue
        seen_summaries.add(summary)
        logger.info("Reasoning summary: %s", summary)
    input_list += response.output
    force_search = False

    safety = 0
    attempted_forced_store = False
    while True:
        safety += 1
        if safety > 30:
            return {"ok": False, "error": "Too many tool iterations", "produced": produced}

        function_calls = [item for item in response.output if _item_type(item) == "function_call"]
        if not function_calls:
            all_done = wanted_tool_names.issubset(set(produced.keys()))
            final_text = response.output_text or last_text
            if final_text:
                _log_response_content(response, label="no_tool_call")
            _log_no_tool_call_summary(
                response,
                attempted_store=attempted_forced_store,
                wanted_tools=wanted_tool_names,
            )
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
                    ArtifactType.MACRO_OVERVIEW,
                    ArtifactType.DES_ANALYSIS_REPORT,
                }:
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
                        logger.info("Reasoning summary: %s", summary)
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
                    parsed = _fill_macro_overview(parsed)
                    parsed = _normalize_block_governance(parsed)
                    if spec.artifact_type == ArtifactType.WORKOUTS_PLAN:
                        parsed = _normalize_workouts_plan_meta(parsed)
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
            name = _item_field(call, "name")
            args_raw = _item_field(call, "arguments") or "{}"
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

                input_list.append(
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": json.dumps(result, ensure_ascii=False),
                    }
                )
                continue

            spec = next((item for item in output_specs if item.tool_name == name), None)
            if spec is None:
                result = {"ok": False, "error": f"Unknown store tool: {name}"}
                input_list.append(
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": json.dumps(result, ensure_ascii=False),
                    }
                )
                continue

            document = _coerce_envelope_args(args) if spec.envelope else args.get("workouts")
            document = _fill_season_scenarios(document)
            document = _fill_macro_overview(document)
            document = _normalize_block_governance(document)
            if spec.artifact_type == ArtifactType.WORKOUTS_PLAN:
                document = _normalize_workouts_plan_meta(document)
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
            logger.info("Reasoning summary: %s", summary)
        input_list += response.output
    if debug_file_search:
        _log_file_search_calls(response)
        _log_file_search_results(response)
        for summary in extract_reasoning_summaries(response):
            if summary in seen_summaries:
                continue
            seen_summaries.add(summary)
            logger.info("Reasoning summary: %s", summary)
        input_list += response.output
