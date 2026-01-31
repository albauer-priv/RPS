"""Auto-render Markdown sidecars for saved artefacts."""

from __future__ import annotations

import json
import logging
from pathlib import Path
import subprocess
import sys

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


def _repo_root() -> Path:
    """Return the repository root path."""
    return Path(__file__).resolve().parents[3]


def render_sidecar(json_path: Path) -> None:
    """Render a JSON artefact to a Markdown sidecar via the artefact renderer."""
    script_path = _repo_root() / "scripts" / "artefact_renderer.py"
    if not script_path.exists():
        logger.error("Artefact renderer not found at %s", script_path)
        return
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

    cmd = [sys.executable, str(script_path), str(json_path)]
    try:
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    except KeyboardInterrupt:
        logger.warning("Artefact render interrupted path=%s", json_path)
        return
    except Exception as exc:
        logger.error("Artefact render failed path=%s error=%s", json_path, exc)
        return

    if result.returncode != 0:
        logger.warning(
            "Artefact render failed path=%s exit=%s stderr=%s",
            json_path,
            result.returncode,
            (result.stderr or "").strip(),
        )


def prune_rendered_sidecars(root: Path, athlete_id: str) -> int:
    """Remove rendered sidecars that no longer have a JSON artefact.

    Args:
        root: Workspace root path (var/athletes).
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
