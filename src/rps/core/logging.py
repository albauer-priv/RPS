"""Logging setup helpers."""

from __future__ import annotations

import logging
from pathlib import Path
import sys
import time
from typing import Iterable


_LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}


def _normalize_level(level: str | int | None) -> int:
    """Normalize a log level value to a logging module constant."""
    if isinstance(level, int):
        return level
    if not level:
        return logging.INFO
    return _LEVELS.get(level.strip().upper(), logging.INFO)


import os


def timestamped_log_path(log_dir: Path, base_name: str) -> Path:
    """Return a timestamped log path for a script or CLI run."""
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    safe_name = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in base_name)
    return log_dir / f"{safe_name}_{timestamp}.log"


def setup_logging(
    level: str | int | None = None,
    log_file: str | Path | None = None,
    *,
    log_stdout: bool | None = None,
    file_level: str | int | None = None,
    console_level: str | int | None = None,
) -> None:
    """Configure root logging with optional file output."""
    root = logging.getLogger()
    root.handlers.clear()
    env_file_level = os.getenv("RPS_LOG_LEVEL_FILE")
    env_console_level = os.getenv("RPS_LOG_LEVEL_CONSOLE")
    file_level_value = _normalize_level(file_level or env_file_level or level or logging.INFO)
    console_level_value = _normalize_level(console_level or env_console_level or logging.WARNING)
    root.setLevel(min(file_level_value, console_level_value, logging.DEBUG))

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    formatter.converter = time.gmtime

    handlers: Iterable[logging.Handler] = []
    if log_stdout is None:
        env = os.getenv("APP_LOG_STDOUT")
        if env is None:
            log_stdout = False
        else:
            log_stdout = env.strip().lower() not in {"0", "false", "no"}
    if log_stdout:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(console_level_value)
        handlers = [stream_handler]

    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(file_level_value)
        handlers = [*handlers, file_handler]

    if not handlers:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(console_level_value)
        handlers = [stream_handler]

    for handler in handlers:
        root.addHandler(handler)

    if log_file:
        announce_level = max(file_level_value, console_level_value)
        logging.getLogger("rps.logging").log(announce_level, "Log file: %s", log_file)


def log_and_print(logger: logging.Logger, message: str, level: int = logging.INFO) -> None:
    """Log message and mirror to stdout."""
    logger.log(_normalize_level(level), message)
    print(message)
