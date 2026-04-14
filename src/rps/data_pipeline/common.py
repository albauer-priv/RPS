"""Shared helpers for data pipeline scripts."""

from __future__ import annotations

import atexit
import logging
import os
from pathlib import Path
import sys
from typing import Optional, TypeAlias

ROOT = Path(__file__).resolve().parents[3]
SYS_PATH = str(ROOT / "src")
if SYS_PATH not in sys.path:
    # Allow running scripts directly without installing the package.
    sys.path.insert(0, SYS_PATH)

from rps.core.config import load_env_file  # noqa: E402
from rps.core.logging import log_and_print, setup_logging  # noqa: E402
from rps.workspace.index_manager import WorkspaceIndexManager  # noqa: E402
from rps.rendering.auto_render import render_sidecar  # noqa: E402

logger = logging.getLogger(__name__)
JsonMap: TypeAlias = dict[str, object]

def load_env(env_path: Optional[Path] = None) -> None:
    """Load environment variables from a .env file if it exists."""
    path = env_path or (ROOT / ".env")
    load_env_file(path)


def _resolve_workspace_root() -> Path:
    """Resolve ATHLETE_WORKSPACE_ROOT relative to repo root when needed."""
    raw_root = os.getenv("ATHLETE_WORKSPACE_ROOT", str(ROOT / "runtime/athletes"))
    root_path = Path(raw_root)
    if not root_path.is_absolute():
        root_path = (ROOT / root_path).resolve()
    return root_path


def configure_logging(script_name: str) -> logging.Logger:
    """Configure logging to the shared rotating rps.log."""
    log_level = os.getenv("RPS_LOG_LEVEL", "INFO")
    athlete_id = os.getenv("ATHLETE_ID")
    if athlete_id:
        log_dir = _resolve_workspace_root() / athlete_id / "logs"
    else:
        log_dir = ROOT / "logs"
    log_file = log_dir / "rps.log"
    setup_logging(log_level, log_file=log_file)
    logger = logging.getLogger(script_name)
    log_and_print(logger, f"Start {script_name} argv={' '.join(sys.argv[1:])}")

    def _log_exit() -> None:
        log_and_print(logger, f"Finished {script_name}")

    def _excepthook(exc_type, exc, tb) -> None:
        logger.critical("Unhandled exception in %s", script_name, exc_info=(exc_type, exc, tb))
        sys.__excepthook__(exc_type, exc, tb)

    atexit.register(_log_exit)
    sys.excepthook = _excepthook
    return logger


def resolve_workspace_root() -> Path:
    """Return the absolute path to the athlete workspace root."""
    raw_root = os.getenv("ATHLETE_WORKSPACE_ROOT", str(ROOT / "runtime/athletes"))
    root_path = Path(raw_root)
    if not root_path.is_absolute():
        root_path = (ROOT / root_path).resolve()
    return root_path


def resolve_schema_dir() -> Path:
    """Return the absolute path to the JSON schema directory."""
    raw_dir = os.getenv("SCHEMA_DIR", str(ROOT / "specs/schemas"))
    dir_path = Path(raw_dir)
    if not dir_path.is_absolute():
        dir_path = (ROOT / dir_path).resolve()
    return dir_path


def require_env(name: str) -> str:
    """Return the value of a required environment variable."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required. Set it in .env or export it.")
    return value


def resolve_athlete_id() -> str:
    """Return the Intervals.icu athlete ID from the environment."""
    return require_env("ATHLETE_ID")


def athlete_root(athlete_id: str) -> Path:
    """Return the base workspace directory for an athlete."""
    return resolve_workspace_root() / athlete_id


def athlete_data_dir(athlete_id: str) -> Path:
    """Return the data pipeline output directory for an athlete."""
    return athlete_root(athlete_id) / "data"


def athlete_latest_dir(athlete_id: str) -> Path:
    """Return the latest artifact directory for an athlete."""
    return athlete_root(athlete_id) / "latest"


def parse_iso_week(value: str | None) -> dict[str, int] | None:
    """Parse YYYY-WW into a structured dict for index storage."""
    if not value:
        return None
    try:
        key = value.split("__", 1)[0]
        year_str, week_str = key.split("-", 1)
        return {"year": int(year_str), "week": int(week_str)}
    except (ValueError, TypeError):
        return None


def parse_iso_week_range(value: str | None) -> dict[str, dict[str, int]] | None:
    """Parse YYYY-WW--YYYY-WW into structured range metadata for index storage."""
    if not value:
        return None
    try:
        start_key, end_key = value.split("--", 1)
    except ValueError:
        return None
    start = parse_iso_week(start_key)
    end = parse_iso_week(end_key)
    if start is None or end is None:
        return None
    return {"start": start, "end": end}


def _iso_week_meta(value: str | None) -> JsonMap | None:
    parsed = parse_iso_week(value)
    return dict(parsed) if parsed is not None else None


def _iso_week_range_meta(value: str | None) -> JsonMap | None:
    parsed = parse_iso_week_range(value)
    if parsed is None:
        return None
    return {
        "start": dict(parsed["start"]),
        "end": dict(parsed["end"]),
    }


def record_index_write(
    *,
    athlete_id: str,
    artifact_type: str,
    version_key: str,
    path: Path,
    run_id: str,
    producer_agent: str,
    created_at: str | None = None,
    iso_week: str | None = None,
    iso_week_range: str | None = None,
) -> None:
    """Update the athlete index.json after writing an artifact."""
    root = resolve_workspace_root()
    manager = WorkspaceIndexManager(root=root, athlete_id=athlete_id)
    try:
        relative_path = str(path.resolve().relative_to(athlete_root(athlete_id)))
    except ValueError:
        relative_path = str(path)

    manager.record_write(
        artifact_type=artifact_type,
        version_key=version_key,
        relative_path=relative_path,
        run_id=run_id,
        producer_agent=producer_agent,
        created_at=created_at,
        iso_week=_iso_week_meta(iso_week),
        iso_week_range=_iso_week_range_meta(iso_week_range),
    )
    logger.info(
        "Recorded artifact write type=%s version_key=%s path=%s run_id=%s",
        artifact_type,
        version_key,
        relative_path,
        run_id,
    )
    try:
        render_sidecar(path)
    except Exception:
        logger.exception("Auto-render failed for %s", path)
