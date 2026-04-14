"""Shared logging setup for standalone scripts."""

from __future__ import annotations

import atexit
import logging
import os
import sys
from pathlib import Path

from rps.core.logging import log_and_print, setup_logging, timestamped_log_path


def _resolve_workspace_root(root: Path) -> Path:
    """Resolve ATHLETE_WORKSPACE_ROOT relative to repo root when needed."""
    raw_root = os.getenv("ATHLETE_WORKSPACE_ROOT", str(root / "runtime/athletes"))
    root_path = Path(raw_root)
    if not root_path.is_absolute():
        root_path = (root / root_path).resolve()
    return root_path


def configure_logging(root: Path, script_name: str) -> logging.Logger:
    """Configure per-script logging to a timestamped log file."""
    log_level = os.getenv("APP_LOG_LEVEL", "INFO")
    athlete_id = os.getenv("ATHLETE_ID")
    log_dir = _resolve_workspace_root(root) / athlete_id / "logs" if athlete_id else root / "logs"
    log_file = timestamped_log_path(log_dir, script_name)
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
