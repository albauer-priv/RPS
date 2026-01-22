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


def setup_logging(level: str | int | None = None, log_file: str | Path | None = None) -> None:
    """Configure root logging with optional file output."""
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(_normalize_level(level))

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    formatter.converter = time.gmtime

    handlers: Iterable[logging.Handler] = []

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    handlers = [stream_handler]

    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        handlers = [*handlers, file_handler]

    for handler in handlers:
        root.addHandler(handler)
