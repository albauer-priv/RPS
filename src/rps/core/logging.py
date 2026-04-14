"""Logging setup helpers."""

from __future__ import annotations

import datetime as dt
import logging
import sys
import time
from collections.abc import Iterable
from pathlib import Path

MIN_ROTATED_LOG_STEM_PARTS = 3

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


def _is_disabled(value: str | int | None) -> bool:
    if value is None:
        return False
    if isinstance(value, int):
        return value <= 0
    return value.strip().lower() in {"0", "false", "no", "off", "none"}


def _utc_today() -> dt.date:
    return dt.datetime.now(dt.UTC).date()


def _file_date(path: Path) -> dt.date | None:
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    return dt.datetime.fromtimestamp(mtime, tz=dt.UTC).date()


def _parse_rotate_mb(value: str | None, default_mb: int = 50) -> int:
    if value is None or value == "":
        return default_mb
    try:
        return int(value)
    except (TypeError, ValueError):
        return default_mb


class DailySizeRotatingFileHandler(logging.FileHandler):
    """Rotate logs on day change or max size, keeping rps-YYYYMMDD-NNN.log archives."""

    def __init__(self, path: Path, max_bytes: int) -> None:
        self._base_path = Path(path)
        self._max_bytes = max_bytes if max_bytes and max_bytes > 0 else 0
        self._current_date = _utc_today()
        if self._base_path.exists():
            file_date = _file_date(self._base_path)
            if file_date:
                self._current_date = file_date
        super().__init__(self._base_path, encoding="utf-8")

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if self._should_rotate():
                self._rotate()
        except Exception:
            pass
        super().emit(record)

    def _should_rotate(self) -> bool:
        today = _utc_today()
        if self._current_date != today:
            return True
        if self._max_bytes and self._base_path.exists():
            try:
                if self._base_path.stat().st_size >= self._max_bytes:
                    return True
            except OSError:
                return False
        return False

    def _rotate(self) -> None:
        if self.stream:
            self.stream.close()
        date_key = self._current_date.strftime("%Y%m%d")
        stem = self._base_path.stem
        log_dir = self._base_path.parent
        pattern = f"{stem}-{date_key}-*.log"
        indices = []
        for path in log_dir.glob(pattern):
            parts = path.stem.split("-")
            if len(parts) < MIN_ROTATED_LOG_STEM_PARTS:
                continue
            try:
                indices.append(int(parts[-1]))
            except ValueError:
                continue
        next_idx = max(indices, default=-1) + 1
        rotated = log_dir / f"{stem}-{date_key}-{next_idx:03d}.log"
        if self._base_path.exists():
            os.replace(self._base_path, rotated)
        self._current_date = _utc_today()
        self.stream = self._open()


def timestamped_log_path(log_dir: Path, base_name: str) -> Path:
    """Return a timestamped log path for a script or CLI run."""
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    safe_name = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in base_name)
    return log_dir / f"{safe_name}_{timestamp}.log"


def setup_logging(
    level: str | int | None = None,
    log_file: str | Path | None = None,
    *,
    file_level: str | int | None = None,
    console_level: str | int | None = None,
) -> None:
    """Configure root logging with optional file output."""
    class _DropLiteLLMDebugFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            if record.levelno > logging.DEBUG:
                return True
            if os.getenv("RPS_LLM_DEBUG", "0").strip().lower() in ("1", "true", "yes", "on"):
                return True
            name = record.name
            return not (name.startswith("litellm") or name.startswith("LiteLLM"))

    root = logging.getLogger()
    root.handlers.clear()
    env_default_level = os.getenv("RPS_LOG_LEVEL")
    env_file_level = os.getenv("RPS_LOG_FILE")
    env_console_level = os.getenv("RPS_LOG_CONSOLE")
    file_level_value = _normalize_level(file_level or env_file_level or level or env_default_level or logging.INFO)
    console_level_raw = console_level or env_console_level or level or env_default_level or logging.WARNING
    console_disabled = _is_disabled(console_level_raw)
    console_level_value = _normalize_level(console_level_raw)
    root_levels = [file_level_value, logging.DEBUG]
    if not console_disabled:
        root_levels.append(console_level_value)
    root.setLevel(min(root_levels))

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    formatter.converter = time.gmtime

    handlers: Iterable[logging.Handler] = []
    if not console_disabled:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(console_level_value)
        stream_handler.addFilter(_DropLiteLLMDebugFilter())
        handlers = [stream_handler]

    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        max_mb = _parse_rotate_mb(os.getenv("RPS_LOG_ROTATE_MB"))
        file_handler = DailySizeRotatingFileHandler(path, max_mb * 1024 * 1024)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(file_level_value)
        handlers = [*handlers, file_handler]

    if not handlers:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(console_level_value)
        stream_handler.addFilter(_DropLiteLLMDebugFilter())
        handlers = [stream_handler]

    for handler in handlers:
        root.addHandler(handler)

    # Silence verbose LiteLLM debug unless explicitly raised elsewhere.
    for name in ("litellm", "LiteLLM"):
        llm_logger = logging.getLogger(name)
        llm_logger.setLevel(logging.WARNING)
        llm_logger.propagate = False
        llm_logger.handlers.clear()

    if log_file:
        announce_level = max(file_level_value, console_level_value)
        logging.getLogger("rps.logging").log(announce_level, "Log file: %s", log_file)


def log_and_print(logger: logging.Logger, message: str, level: int = logging.INFO) -> None:
    """Log message and mirror to stdout."""
    logger.log(_normalize_level(level), message)
    print(message)


def prune_old_logs(log_dir: Path, retention_days: int) -> int:
    """Delete log files older than retention_days; returns count removed."""
    if retention_days <= 0:
        return 0
    cutoff = dt.datetime.now(dt.UTC) - dt.timedelta(days=retention_days)
    removed = 0
    if not log_dir.exists():
        return removed
    for path in log_dir.glob("*.log"):
        if path.name == "rps.log":
            continue
        try:
            mtime = dt.datetime.fromtimestamp(path.stat().st_mtime, tz=dt.UTC)
        except OSError:
            continue
        if mtime < cutoff:
            try:
                path.unlink()
                removed += 1
            except OSError:
                continue
    return removed
