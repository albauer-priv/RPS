"""Helpers for resolving deterministic planner context before agent calls."""

from __future__ import annotations

from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType


def build_resolved_kpi_context_block(store: LocalArtifactStore, athlete_id: str) -> str:
    """Build a deterministic KPI context block from latest KPI profile + selection."""
    selection = store.load_latest(athlete_id, ArtifactType.SEASON_SCENARIO_SELECTION)
    profile = store.load_latest(athlete_id, ArtifactType.KPI_PROFILE)

    selection_data = selection.get("data") if isinstance(selection, dict) else None
    selection_map = selection_data if isinstance(selection_data, dict) else {}
    selected = selection_map.get("kpi_moving_time_rate_guidance_selection")

    profile_data = profile.get("data") if isinstance(profile, dict) else None
    durability = (profile_data or {}).get("durability") if isinstance(profile_data, dict) else {}
    if not isinstance(durability, dict):
        durability = {}
    mt_guidance = durability.get("moving_time_rate_guidance") or {}
    if not isinstance(mt_guidance, dict):
        mt_guidance = {}
    bands = mt_guidance.get("bands") or []
    if not isinstance(bands, list):
        bands = []

    lines: list[str] = []
    if isinstance(selected, dict):
        segment = selected.get("segment")
        w_per_kg = selected.get("w_per_kg") or {}
        kj_per_kg = selected.get("kj_per_kg_per_hour") or {}
        if (
            segment
            and isinstance(w_per_kg, dict)
            and isinstance(kj_per_kg, dict)
            and "min" in w_per_kg
            and "max" in w_per_kg
            and "min" in kj_per_kg
            and "max" in kj_per_kg
        ):
            lines.extend(
                [
                    "**Resolved KPI Context**",
                    "Use these resolved KPI values directly; do not search, infer, or reinterpret KPI ranges when they are provided here.",
                    (
                        f"selected_kpi_rate_band_selector: {segment} "
                        f"(w_per_kg {w_per_kg.get('min')} - {w_per_kg.get('max')}, "
                        f"kj_per_kg_per_hour {kj_per_kg.get('min')} - {kj_per_kg.get('max')})"
                    ),
                ]
            )

    derived_from = mt_guidance.get("derived_from")
    notes = mt_guidance.get("notes")
    available_lines: list[str] = []
    for band in bands:
        if not isinstance(band, dict):
            continue
        segment = band.get("segment")
        w_per_kg = band.get("w_per_kg") or {}
        kj_per_kg = band.get("kj_per_kg_per_hour") or {}
        basis = band.get("basis")
        if (
            not segment
            or not isinstance(w_per_kg, dict)
            or not isinstance(kj_per_kg, dict)
            or "min" not in w_per_kg
            or "max" not in w_per_kg
            or "min" not in kj_per_kg
            or "max" not in kj_per_kg
        ):
            continue
        basis_text = f", basis {basis}" if isinstance(basis, str) and basis else ""
        available_lines.append(
            f"- {segment}: w_per_kg {w_per_kg.get('min')} - {w_per_kg.get('max')}, "
            f"kj_per_kg_per_hour {kj_per_kg.get('min')} - {kj_per_kg.get('max')}{basis_text}"
        )

    if available_lines:
        if not lines:
            lines.append("**Resolved KPI Context**")
            lines.append(
                "Use these resolved KPI values directly; do not search, infer, or reinterpret KPI ranges when they are provided here."
            )
        if isinstance(derived_from, str) and derived_from:
            lines.append(f"kpi_profile_moving_time_rate_guidance.derived_from: {derived_from}")
        if isinstance(notes, str) and notes:
            lines.append(f"kpi_profile_moving_time_rate_guidance.notes: {notes}")
        lines.append("kpi_profile_moving_time_rate_guidance.available_bands:")
        lines.extend(available_lines)

    return "\n".join(lines) + ("\n" if lines else "")
