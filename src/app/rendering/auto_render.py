"""Auto-render Markdown sidecars for saved artefacts."""

from __future__ import annotations

import logging
from pathlib import Path
import subprocess
import sys

logger = logging.getLogger(__name__)


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

    cmd = [sys.executable, str(script_path), str(json_path)]
    try:
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
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
