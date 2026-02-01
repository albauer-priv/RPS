"""Season-level orchestration helpers for scenario + plan actions."""

from __future__ import annotations

import logging
import re
from typing import Callable

from rps.agents.multi_output_runner import AgentRuntime, run_agent_multi_output
from rps.agents.registry import AGENTS
from rps.agents.tasks import AgentTask
from rps.data_pipeline.season_brief_availability import load_season_brief
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType
from rps.orchestrator.plan_week import _build_injection_block

logger = logging.getLogger(__name__)


def _extract_season_brief_user_data(season_text: str) -> dict[str, object]:
    """Extract optional user-provided planning fields from Season Brief text."""
    anchor_match = re.search(
        r"^-\\s*Endurance-Anchor-W\\s*:\\s*([0-9]+(?:\\.[0-9]+)?)",
        season_text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    range_match = re.search(
        r"^-\\s*Ambition-IF-Range\\s*:\\s*([0-9]+(?:\\.[0-9]+)?)\\s*,\\s*([0-9]+(?:\\.[0-9]+)?)",
        season_text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    anchor = float(anchor_match.group(1)) if anchor_match else None
    ambition = None
    if range_match:
        ambition = (float(range_match.group(1)), float(range_match.group(2)))
    return {"endurance_anchor_w": anchor, "ambition_if_range": ambition}


def _format_user_data_block(user_data: dict[str, object]) -> str:
    """Format user-provided data for prompt injection."""
    anchor = user_data.get("endurance_anchor_w")
    ambition = user_data.get("ambition_if_range")
    lines = ["**User Provided Data**"]
    if isinstance(anchor, (int, float)):
        lines.append(f"endurance_anchor_w: {anchor} W")
    else:
        lines.append("endurance_anchor_w: n/a")
    if isinstance(ambition, tuple) and len(ambition) == 2:
        lines.append(f"ambition_if_range: [{ambition[0]}, {ambition[1]}]")
    else:
        lines.append("ambition_if_range: n/a")
    lines.append("kpi_profile: xxx")
    return "\n".join(lines) + "\n"


def create_season_scenarios(
    runtime_for: Callable[[str], AgentRuntime],
    *,
    athlete_id: str,
    year: int,
    week: int,
    run_id: str,
    override_text: str | None = None,
    force_file_search: bool = True,
    max_num_results: int = 20,
    model_resolver: Callable[[str], str] | None = None,
    temperature_resolver: Callable[[str], float | None] | None = None,
) -> dict:
    """Create season scenarios for the target ISO week."""
    spec = AGENTS["season_scenario"]
    injected_block = _build_injection_block("season_scenario", mode="scenario")
    override_line = f"Override: {override_text.strip()}. " if override_text else ""
    user_input = (
        "Mode A. Generate the pre-decision scenarios. "
        f"Target ISO week: {year}-{week:02d}. "
        "Use workspace_get_input for Season Brief and Events. "
        f"{override_line}"
        f"{injected_block}"
        "Follow the Mandatory Output Chapter for SEASON_SCENARIOS."
    )
    logger.info("Creating season scenarios athlete=%s iso_week=%04d-W%02d", athlete_id, year, week)
    return run_agent_multi_output(
        runtime_for(spec.name),
        agent_name=spec.name,
        agent_vs_name=spec.vector_store_name,
        athlete_id=athlete_id,
        tasks=[AgentTask.CREATE_SEASON_SCENARIOS],
        user_input=user_input,
        run_id=run_id,
        model_override=model_resolver(spec.name) if model_resolver else None,
        temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
        force_file_search=force_file_search,
        max_num_results=max_num_results,
    )


def select_season_scenario(
    runtime_for: Callable[[str], AgentRuntime],
    *,
    athlete_id: str,
    year: int,
    week: int,
    run_id: str,
    selected: str,
    rationale: str | None,
    kpi_selection: dict | None = None,
    force_file_search: bool = True,
    max_num_results: int = 20,
    model_resolver: Callable[[str], str] | None = None,
    temperature_resolver: Callable[[str], float | None] | None = None,
) -> dict:
    """Select a season scenario for the target ISO week."""
    spec = AGENTS["season_scenario"]
    injected_block = _build_injection_block("season_scenario", mode="scenario")
    rationale_line = f"Rationale: {rationale.strip()}. " if rationale else ""
    kpi_line = ""
    if isinstance(kpi_selection, dict):
        segment = kpi_selection.get("segment")
        w_per_kg = kpi_selection.get("w_per_kg") or {}
        kj_per_kg = kpi_selection.get("kj_per_kg_per_hour") or {}
        if segment and w_per_kg and kj_per_kg:
            kpi_line = (
                "KPI moving_time_rate_guidance selection: "
                f"{segment} "
                f"(w_per_kg {w_per_kg.get('min')} - {w_per_kg.get('max')}, "
                f"kj_per_kg_per_hour {kj_per_kg.get('min')} - {kj_per_kg.get('max')}). "
            )
    user_input = (
        f"Select Scenario {selected.upper()} for ISO week {year}-{week:02d}. "
        "Use the latest SEASON_SCENARIOS as context. "
        f"{rationale_line}"
        f"{kpi_line}"
        f"{injected_block}"
        "Follow the Mandatory Output Chapter for SEASON_SCENARIO_SELECTION. "
        "Always include kpi_moving_time_rate_guidance_selection (set to null if not provided)."
    )
    logger.info(
        "Selecting season scenario athlete=%s iso_week=%04d-W%02d scenario=%s",
        athlete_id,
        year,
        week,
        selected,
    )
    return run_agent_multi_output(
        runtime_for(spec.name),
        agent_name=spec.name,
        agent_vs_name=spec.vector_store_name,
        athlete_id=athlete_id,
        tasks=[AgentTask.CREATE_SEASON_SCENARIO_SELECTION],
        user_input=user_input,
        run_id=run_id,
        model_override=model_resolver(spec.name) if model_resolver else None,
        temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
        force_file_search=force_file_search,
        max_num_results=max_num_results,
    )


def create_season_plan(
    runtime_for: Callable[[str], AgentRuntime],
    *,
    athlete_id: str,
    year: int,
    week: int,
    run_id: str,
    selected: str | None,
    override_text: str | None = None,
    force_file_search: bool = True,
    max_num_results: int = 20,
    model_resolver: Callable[[str], str] | None = None,
    temperature_resolver: Callable[[str], float | None] | None = None,
) -> dict:
    """Create the season plan for the selected scenario."""
    spec = AGENTS["season_planner"]
    injected_block = _build_injection_block("season_planner", mode="season_plan")
    scenario_line = f"Scenario {selected.upper()}. " if selected else ""
    override_line = f"Override: {override_text.strip()}. " if override_text else ""
    user_data_block = ""
    try:
        athlete_root = runtime_for(spec.name).workspace_root / athlete_id
        _season_path, season_text = load_season_brief(athlete_root, year, None)
        user_data = _extract_season_brief_user_data(season_text)
        user_data_block = _format_user_data_block(user_data)
    except Exception:
        user_data_block = _format_user_data_block({})
    kpi_block = ""
    try:
        store = LocalArtifactStore(root=runtime_for(spec.name).workspace_root)
        selection = store.load_latest(athlete_id, ArtifactType.SEASON_SCENARIO_SELECTION)
        kpi_sel = (selection.get("data") or {}).get("kpi_moving_time_rate_guidance_selection")
        if isinstance(kpi_sel, dict):
            segment = kpi_sel.get("segment")
            w_per_kg = kpi_sel.get("w_per_kg") or {}
            kj_per_kg = kpi_sel.get("kj_per_kg_per_hour") or {}
            if segment and w_per_kg and kj_per_kg:
                kpi_block = (
                    "Selected KPI guidance: "
                    f"kpi_rate_band_selector {segment} "
                    f"(w_per_kg {w_per_kg.get('min')} - {w_per_kg.get('max')}, "
                    f"kj_per_kg_per_hour {kj_per_kg.get('min')} - {kj_per_kg.get('max')}). "
                )
    except Exception:
        kpi_block = ""
    user_input = (
        f"{scenario_line}Mode A. Create the SEASON_PLAN. "
        f"Target ISO week: {year}-{week:02d}. "
        "Use the latest SEASON_SCENARIO_SELECTION and SEASON_SCENARIOS as context. "
        f"{user_data_block}"
        f"{kpi_block}"
        f"{override_line}"
        f"{injected_block}"
        "Follow the Mandatory Output Chapter for SEASON_PLAN."
    )
    logger.info(
        "Creating season plan athlete=%s iso_week=%04d-W%02d scenario=%s",
        athlete_id,
        year,
        week,
        selected or "latest",
    )
    return run_agent_multi_output(
        runtime_for(spec.name),
        agent_name=spec.name,
        agent_vs_name=spec.vector_store_name,
        athlete_id=athlete_id,
        tasks=[AgentTask.CREATE_SEASON_PLAN],
        user_input=user_input,
        run_id=run_id,
        model_override=model_resolver(spec.name) if model_resolver else None,
        temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
        force_file_search=force_file_search,
        max_num_results=max_num_results,
    )
