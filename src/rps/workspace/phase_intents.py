"""Canonical planning semantic enums for season archetypes and phase intents."""

from __future__ import annotations

from collections.abc import Iterable

CANONICAL_SEASON_ARCHETYPES = ("none", "ceiling_first_durability")
CANONICAL_PHASE_INTENTS = (
    "recovery_reset",
    "shortened_re_entry",
    "shortened_consolidation",
    "transition_consolidation",
    "foundation",
    "general_build",
    "build_progression",
    "ceiling_support",
    "transition_coupling",
    "durability_build",
    "specificity_build",
    "b_event_rehearsal",
    "peak_preparation",
    "a_event_peak_taper",
)

PHASE_INTENT_LABELS = {
    "recovery_reset": "Recovery Reset",
    "shortened_re_entry": "Shortened Re-entry",
    "shortened_consolidation": "Shortened Consolidation",
    "transition_consolidation": "Transition Consolidation",
    "foundation": "Foundation",
    "general_build": "General Build",
    "build_progression": "Build Progression",
    "ceiling_support": "Ceiling Support",
    "transition_coupling": "Transition Coupling",
    "durability_build": "Durability Build",
    "specificity_build": "Specificity Build",
    "b_event_rehearsal": "B-Event Rehearsal",
    "peak_preparation": "Peak Preparation",
    "a_event_peak_taper": "A-Event Peak/Taper",
}

SEASON_ARCHETYPE_LABELS = {
    "none": "None",
    "ceiling_first_durability": "Ceiling-First Durability",
}


def normalize_season_archetype(value: object) -> str:
    """Return a canonical season archetype."""

    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return text if text in CANONICAL_SEASON_ARCHETYPES else "none"


def normalize_phase_intent(value: object) -> str:
    """Return a canonical phase intent or an empty string."""

    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return text if text in CANONICAL_PHASE_INTENTS else ""


def normalize_phase_intent_list(values: Iterable[object] | None) -> list[str]:
    """Return canonical phase intents preserving order and removing duplicates."""

    seen: set[str] = set()
    result: list[str] = []
    for value in values or []:
        normalized = normalize_phase_intent(value)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def phase_intent_label(value: object) -> str:
    """Return a human-readable phase-intent label."""

    normalized = normalize_phase_intent(value)
    if normalized:
        return PHASE_INTENT_LABELS.get(normalized, normalized.replace("_", " ").title())
    return str(value or "")


def season_archetype_label(value: object) -> str:
    """Return a human-readable season-archetype label."""

    normalized = normalize_season_archetype(value)
    return SEASON_ARCHETYPE_LABELS.get(normalized, normalized.replace("_", " ").title())
