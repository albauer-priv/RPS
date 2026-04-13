"""Shared agent knowledge injection loader based on YAML configuration."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
INJECTION_CONFIG = ROOT / "config" / "agent_knowledge_injection.yaml"

_LOAD_SPEC_HEADINGS = {
    "terminology": "## 1) Terminology and Governance Semantics (Binding)",
    "required_inputs": "## 2) Required Inputs (Binding)",
    "per_workout": "## 3) Per-Workout Load Estimation (Binding)",
    "weekly_corridor": "## 4) Weekly Corridor Derivation (Phase-Architect) (Binding)",
    "planner_responsibilities": "## 5) Planner Responsibilities (Binding)",
    "season_responsibilities": "### 5.1 Season-Planner",
    "phase_responsibilities": "### 5.2 Phase-Architect",
    "week_responsibilities": "### 5.3 Week-Planner",
    "end": "## End of LoadEstimationSpec v2.0",
}


def _find_heading(lines: list[str], heading: str) -> int | None:
    """Return the first line index matching a heading exactly."""
    for idx, line in enumerate(lines):
        if line.strip() == heading:
            return idx
    return None


def _slice_by_indices(lines: list[str], start: int | None, end: int | None) -> str:
    """Return a trimmed text slice for the given line boundaries."""
    if start is None:
        return ""
    end_idx = len(lines) if end is None else end
    return "\n".join(lines[start:end_idx]).rstrip()


def _load_spec_prelude(lines: list[str]) -> str:
    """Return the prelude before the first numbered section."""
    first_section = _find_heading(lines, _LOAD_SPEC_HEADINGS["terminology"])
    if first_section is None:
        return "\n".join(lines).rstrip()
    return "\n".join(lines[:first_section]).rstrip()


def _extract_general_and_phase(spec_text: str) -> str:
    """Return the shared prelude plus the phase-specific sections."""
    lines = spec_text.splitlines()
    prelude = _load_spec_prelude(lines)
    terminology = _slice_by_indices(
        lines,
        _find_heading(lines, _LOAD_SPEC_HEADINGS["terminology"]),
        _find_heading(lines, _LOAD_SPEC_HEADINGS["required_inputs"]),
    )
    required_inputs = _slice_by_indices(
        lines,
        _find_heading(lines, _LOAD_SPEC_HEADINGS["required_inputs"]),
        _find_heading(lines, _LOAD_SPEC_HEADINGS["per_workout"]),
    )
    per_workout = _slice_by_indices(
        lines,
        _find_heading(lines, _LOAD_SPEC_HEADINGS["per_workout"]),
        _find_heading(lines, _LOAD_SPEC_HEADINGS["weekly_corridor"]),
    )
    weekly_corridor = _slice_by_indices(
        lines,
        _find_heading(lines, _LOAD_SPEC_HEADINGS["weekly_corridor"]),
        _find_heading(lines, _LOAD_SPEC_HEADINGS["planner_responsibilities"]),
    )
    phase_responsibilities = _slice_by_indices(
        lines,
        _find_heading(lines, _LOAD_SPEC_HEADINGS["phase_responsibilities"]),
        _find_heading(lines, _LOAD_SPEC_HEADINGS["week_responsibilities"])
        or _find_heading(lines, _LOAD_SPEC_HEADINGS["end"]),
    )
    blocks = [
        block
        for block in (
            prelude,
            terminology,
            required_inputs,
            per_workout,
            weekly_corridor,
            phase_responsibilities,
        )
        if block
    ]
    return "\n\n".join(blocks).strip()


def _extract_season_section(spec_text: str) -> str:
    """Return the shared prelude plus season-planner-relevant sections."""
    lines = spec_text.splitlines()
    prelude = _load_spec_prelude(lines)
    terminology = _slice_by_indices(
        lines,
        _find_heading(lines, _LOAD_SPEC_HEADINGS["terminology"]),
        _find_heading(lines, _LOAD_SPEC_HEADINGS["required_inputs"]),
    )
    required_inputs = _slice_by_indices(
        lines,
        _find_heading(lines, _LOAD_SPEC_HEADINGS["required_inputs"]),
        _find_heading(lines, _LOAD_SPEC_HEADINGS["per_workout"]),
    )
    per_workout = _slice_by_indices(
        lines,
        _find_heading(lines, _LOAD_SPEC_HEADINGS["per_workout"]),
        _find_heading(lines, _LOAD_SPEC_HEADINGS["weekly_corridor"]),
    )
    season_responsibilities = _slice_by_indices(
        lines,
        _find_heading(lines, _LOAD_SPEC_HEADINGS["season_responsibilities"]),
        _find_heading(lines, _LOAD_SPEC_HEADINGS["phase_responsibilities"])
        or _find_heading(lines, _LOAD_SPEC_HEADINGS["end"]),
    )
    blocks = [
        block
        for block in (
            prelude,
            terminology,
            required_inputs,
            per_workout,
            season_responsibilities,
        )
        if block
    ]
    return "\n\n".join(blocks).strip()


def extract_load_estimation_section(spec_text: str, section: str | None) -> str:
    """Return a configured subset of `load_estimation_spec.md`."""
    if not section:
        return spec_text
    section_key = section.strip().lower()
    if section_key == "general":
        lines = spec_text.splitlines()
        weekly_corridor_idx = _find_heading(lines, _LOAD_SPEC_HEADINGS["weekly_corridor"])
        if weekly_corridor_idx is None:
            return spec_text
        return "\n".join(lines[:weekly_corridor_idx]).rstrip()
    if section_key == "season":
        extracted = _extract_season_section(spec_text)
        return extracted or spec_text
    if section_key == "general+phase":
        extracted = _extract_general_and_phase(spec_text)
        return extracted or spec_text
    return spec_text


@lru_cache(maxsize=1)
def load_agent_injection_config() -> dict[str, Any]:
    """Load the YAML knowledge injection config when available."""
    if not INJECTION_CONFIG.exists():
        return {}
    try:
        import yaml
    except ImportError:
        return {}
    return yaml.safe_load(INJECTION_CONFIG.read_text(encoding="utf-8")) or {}


def _dedupe_items(items: list[Any]) -> list[Any]:
    seen: set[str] = set()
    deduped: list[Any] = []
    for item in items:
        if isinstance(item, dict):
            key = json.dumps(item, sort_keys=True, ensure_ascii=True)
        else:
            key = str(item)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def resolve_agent_injection_items(agent_name: str, mode: str | None = None) -> list[Any]:
    """Resolve injected knowledge items for an agent/mode from YAML config."""
    config = load_agent_injection_config()
    agent_cfg = (config.get("agents") or {}).get(agent_name) or {}
    base_items = list(agent_cfg.get("inject") or [])
    if not mode:
        return base_items
    modes = agent_cfg.get("modes") or {}
    mode_cfg = modes.get(mode) or {}
    bundle_id = mode_cfg.get("bundle_id")
    bundle_items: list[Any] = []
    if bundle_id:
        bundles = agent_cfg.get("bundles") or []
        bundle_cfg: dict[str, Any] = next((b for b in bundles if b.get("id") == bundle_id), {})
        bundle_items = list(bundle_cfg.get("inject") or [])
    mode_items = list(mode_cfg.get("inject") or [])
    return _dedupe_items([*base_items, *bundle_items, *mode_items])


def build_injection_block(agent_name: str, mode: str | None = None) -> str:
    """Render injected knowledge content for use in an agent prompt."""
    items = resolve_agent_injection_items(agent_name, mode=mode)
    if not items:
        return ""
    chunks: list[str] = [
        (
            "Injected mandatory knowledge "
            f"(mode={mode}; read in full; do NOT file_search these files):"
            if mode
            else "Injected mandatory knowledge (read in full; do NOT file_search these files):"
        )
    ]
    for item in items:
        path_str = None
        label = None
        section = None
        if isinstance(item, dict):
            path_str = item.get("path")
            label = item.get("label")
            section = item.get("section")
        elif isinstance(item, str):
            path_str = item
        if not path_str:
            continue
        path = (ROOT / path_str).resolve()
        header = label or str(path)
        try:
            content = path.read_text(encoding="utf-8")
            if path.name == "load_estimation_spec.md":
                content = extract_load_estimation_section(content, section)
            chunks.append(f"{header}:\n\"\"\"\n{content}\n\"\"\"\n")
        except FileNotFoundError:
            chunks.append(f"{header}: MISSING\n")
    return "\n".join(chunks)
