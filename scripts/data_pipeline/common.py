"""Shared helpers for data pipeline scripts."""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]
SYS_PATH = str(ROOT / "src")
if SYS_PATH not in sys.path:
    # Allow running scripts directly without installing the package.
    sys.path.insert(0, SYS_PATH)

from app.core.config import load_env_file  # noqa: E402
from app.workspace.index_manager import WorkspaceIndexManager  # noqa: E402


def load_env(env_path: Optional[Path] = None) -> None:
    """Load environment variables from a .env file if it exists."""
    path = env_path or (ROOT / ".env")
    load_env_file(path)


def resolve_workspace_root() -> Path:
    """Return the absolute path to the athlete workspace root."""
    raw_root = os.getenv("ATHLETE_WORKSPACE_ROOT", str(ROOT / "var/athletes"))
    root_path = Path(raw_root)
    if not root_path.is_absolute():
        root_path = (ROOT / root_path).resolve()
    return root_path


def resolve_schema_dir() -> Path:
    """Return the absolute path to the JSON schema directory."""
    raw_dir = os.getenv("SCHEMA_DIR", str(ROOT / "schemas"))
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
        year_str, week_str = value.split("-", 1)
        return {"year": int(year_str), "week": int(week_str)}
    except (ValueError, TypeError):
        return None


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
        iso_week=parse_iso_week(iso_week),
        iso_week_range=iso_week_range,
    )
