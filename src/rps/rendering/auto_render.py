"""Auto-render Markdown sidecars for saved artefacts."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from rps.rendering.renderer import render_json_sidecar

logger = logging.getLogger(__name__)

_SUPPORTED_RENDER_TYPES = {
    "SEASON_PLAN",
    "PHASE_GUARDRAILS",
    "PHASE_STRUCTURE",
    "PHASE_PREVIEW",
    "PHASE_FEED_FORWARD",
    "SEASON_PHASE_FEED_FORWARD",
    "DES_ANALYSIS_REPORT",
    "ACTIVITIES_ACTUAL",
    "ACTIVITIES_TREND",
    "ZONE_MODEL",
    "WEEK_PLAN",
    "KPI_PROFILE",
    "AVAILABILITY",
    "WELLNESS",
}


def render_sidecar(json_path: Path) -> None:
    """Render a JSON artefact to a Markdown sidecar via the artefact renderer."""
    if not json_path.exists():
        logger.error("Artefact JSON not found at %s", json_path)
        return
    try:
        with json_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        artifact_type = (payload.get("meta") or {}).get("artifact_type")
        if artifact_type and artifact_type not in _SUPPORTED_RENDER_TYPES:
            return
    except Exception:  # pragma: no cover - best-effort guard
        return

    athlete_id = _detect_athlete_id(json_path)
    try:
        render_json_sidecar(json_path, athlete_id=athlete_id)
    except Exception as exc:
        logger.error("Artefact render failed path=%s error=%s", json_path, exc)
        return


def _detect_athlete_id(path: Path) -> str | None:
    """Detect athlete id from a workspace path."""
    parts = list(path.parts)
    if "athletes" not in parts:
        return None
    try:
        idx = parts.index("athletes")
    except ValueError:
        return None
    if idx + 1 >= len(parts):
        return None
    return parts[idx + 1]


def prune_rendered_sidecars(root: Path, athlete_id: str) -> int:
    """Remove rendered sidecars that no longer have a JSON artefact.

    Args:
        root: Workspace root path (runtime/athletes).
        athlete_id: Athlete workspace identifier.

    Returns:
        Number of rendered files removed.
    """
    rendered_dir = root / athlete_id / "rendered"
    if not rendered_dir.exists():
        return 0

    json_stems: set[str] = set()
    athlete_root = root / athlete_id
    for json_path in athlete_root.rglob("*.json"):
        if json_path.is_dir():
            continue
        if rendered_dir in json_path.parents:
            continue
        json_stems.add(json_path.stem)

    removed = 0
    for rendered_path in rendered_dir.glob("*.md"):
        if rendered_path.stem in json_stems:
            continue
        try:
            rendered_path.unlink()
            removed += 1
        except OSError as exc:
            logger.warning(
                "Rendered cleanup failed path=%s error=%s",
                rendered_path,
                exc,
            )
    if removed:
        logger.info(
            "Rendered cleanup removed=%s athlete_id=%s",
            removed,
            athlete_id,
        )
    return removed
