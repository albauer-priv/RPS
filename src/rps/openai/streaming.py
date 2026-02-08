"""Streaming helpers for Responses API calls."""

from __future__ import annotations

from typing import Any
from datetime import datetime, timezone
from pathlib import Path
import os
import re
import sys
import time


def _get_attr(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def should_stream() -> bool:
    raw = os.getenv("RPS_LLM_STREAM", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def stream_reasoning_mode() -> str:
    raw = os.getenv("RPS_LLM_STREAM_REASONING", "full").strip().lower()
    if raw in ("none", "off", "0", "false", "no"):
        return "none"
    if raw in ("full", "reasoning"):
        return "full"
    return "summary"


def stream_show_output() -> bool:
    raw = os.getenv("RPS_LLM_STREAM_TEXT", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def stream_show_usage() -> bool:
    raw = os.getenv("RPS_LLM_STREAM_USAGE", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def stream_log_reasoning() -> bool:
    raw = os.getenv("RPS_LLM_STREAM_LOG_REASONING", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def stream_reasoning_italics() -> bool:
    raw = os.getenv("RPS_LLM_STREAM_ITALICS", "0").strip().lower()
    return raw not in ("0", "false", "no", "off")


def reasoning_log_path() -> str | None:
    path = os.getenv("RPS_LLM_REASONING_LOG_FILE") or os.getenv("RPS_LLM_REASONING_LOG_PATH")
    if not path:
        return None
    path = path.strip()
    return path or None


def _utc_today() -> datetime.date:
    return datetime.now(timezone.utc).date()


def _file_date(path: Path) -> datetime.date | None:
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    return datetime.fromtimestamp(mtime, tz=timezone.utc).date()


def _parse_rotate_mb(value: str | None, default_mb: int = 50) -> int:
    if value is None or value == "":
        return default_mb
    try:
        parsed = int(value)
        return parsed
    except (TypeError, ValueError):
        return default_mb


def _rotate_reasoning_log(path: Path, max_bytes: int) -> bool:
    if not path.exists():
        return False
    today = _utc_today()
    file_date = _file_date(path) or today
    try:
        needs_size_rotate = max_bytes > 0 and path.stat().st_size >= max_bytes
    except OSError:
        needs_size_rotate = False
    if file_date == today and not needs_size_rotate:
        return False
    date_key = file_date.strftime("%Y%m%d")
    stem = path.stem
    log_dir = path.parent
    pattern = f"{stem}-{date_key}-*.log"
    indices = []
    for existing in log_dir.glob(pattern):
        parts = existing.stem.split("-")
        if len(parts) < 3:
            continue
        try:
            indices.append(int(parts[-1]))
        except ValueError:
            continue
    next_idx = max(indices, default=-1) + 1
    rotated = log_dir / f"{stem}-{date_key}-{next_idx:03d}.log"
    try:
        os.replace(path, rotated)
        return True
    except OSError:
        return False


def create_response(
    client: Any,
    payload: dict[str, Any],
    logger: Any | None,
    stream_handlers: dict[str, Any] | None = None,
):
    """Create a response, optionally streaming deltas.

    When stream_handlers is provided, deltas are sent to callbacks instead of stdout.
    """
    def _parse_retry_seconds(message: str) -> float | None:
        patterns = [
            r"try again in ([0-9]+(?:\\.[0-9]+)?)s",
            r"retry after ([0-9]+(?:\\.[0-9]+)?)s",
            r"after ([0-9]+(?:\\.[0-9]+)?)s",
            r"in ([0-9]+(?:\\.[0-9]+)?)s",
            r"in ([0-9]+(?:\\.[0-9]+)?) seconds",
            r"in ([0-9]+)ms",
        ]
        lowered = message.lower()
        for pattern in patterns:
            match = re.search(pattern, lowered)
            if not match:
                continue
            value = float(match.group(1))
            if "ms" in pattern:
                return value / 1000.0
            return value
        return None

    def _should_retry_tpm(exc: Exception) -> float | None:
        message = str(exc)
        lowered = message.lower()
        if "rate limit" not in lowered:
            return None
        if "tpm" not in lowered and "tokens per minute" not in lowered:
            return None
        return _parse_retry_seconds(message) or 60.0

    def _create_with_retry(stream: bool):
        attempts = 0
        retry_count = 1
        multiplier = 2.0
        raw_retry = os.getenv("RPS_TPM_RETRY_COUNT")
        raw_multiplier = os.getenv("RPS_TPM_WAIT_MULTIPLIER")
        if raw_retry:
            try:
                retry_count = max(0, int(raw_retry))
            except ValueError:
                retry_count = 1
        if raw_multiplier:
            try:
                multiplier = max(1.0, float(raw_multiplier))
            except ValueError:
                multiplier = 2.0
        while True:
            attempts += 1
            try:
                if not stream:
                    return client.responses.create(**payload)
                payload_stream = dict(payload)
                payload_stream["stream"] = True
                return client.responses.create(**payload_stream)
            except Exception as exc:
                wait_seconds = _should_retry_tpm(exc)
                if wait_seconds is None or attempts > retry_count + 1:
                    raise
                delay = wait_seconds * multiplier
                if logger is not None:
                    logger.warning(
                        "TPM rate limit exceeded. Waiting %.1fs then retrying (attempt %s of %s).",
                        delay,
                        attempts,
                        retry_count + 1,
                    )
                time.sleep(delay)

    if payload.get("stream") is False:
        return _create_with_retry(stream=False)

    if stream_handlers is None and not should_stream():
        return _create_with_retry(stream=False)

    stream = _create_with_retry(stream=True)

    handlers = stream_handlers or {}
    on_output = handlers.get("on_output")
    on_reasoning = handlers.get("on_reasoning")
    on_summary = handlers.get("on_summary")
    reasoning_log_meta = handlers.get("reasoning_log_meta") if isinstance(handlers, dict) else None

    show_output = stream_show_output()
    reasoning_mode = stream_reasoning_mode()
    show_usage = stream_show_usage()
    log_reasoning = stream_log_reasoning()
    reasoning_italics = stream_reasoning_italics()
    reasoning_log_file = reasoning_log_path()
    wrote_any = False
    wrote_reasoning_prefix = False
    wrote_output_prefix = False
    final_response = None
    saw_full_reasoning = False
    reasoning_chunks: list[str] = []
    debug_events = os.getenv("RPS_LLM_STREAM_DEBUG", "0").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    debug_file_search = os.getenv("RPS_LLM_DEBUG_FILE_SEARCH", "0").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    ) or os.getenv("RPS_LLM_FILE_SEARCH_DEBUG", "0").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

    reasoning_log_started = False
    wrote_reasoning_log = False

    def _append_reasoning_log(delta: str) -> None:
        if not reasoning_log_file or not delta:
            return
        try:
            nonlocal reasoning_log_started, wrote_reasoning_log
            log_path = Path(reasoning_log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            max_mb = _parse_rotate_mb(os.getenv("RPS_LOG_ROTATE_MB"))
            if _rotate_reasoning_log(log_path, max_mb * 1024 * 1024):
                reasoning_log_started = False
            with open(log_path, "a", encoding="utf-8") as handle:
                if not reasoning_log_started:
                    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    agent = None
                    model = None
                    run_id = None
                    if isinstance(reasoning_log_meta, dict):
                        agent = reasoning_log_meta.get("agent")
                        model = reasoning_log_meta.get("model")
                        run_id = reasoning_log_meta.get("run_id")
                    header = f"{timestamp} reasoning"
                    if agent:
                        header += f" agent={agent}"
                    if model:
                        header += f" model={model}"
                    if run_id:
                        header += f" run_id={run_id}"
                    handle.write(header + "\n")
                    reasoning_log_started = True
                handle.write(delta)
                wrote_reasoning_log = True
        except Exception:
            if logger is not None:
                logger.debug("Failed to append reasoning log to %s", reasoning_log_file)

    if stream_handlers is not None:
        show_output = True
        if on_summary and reasoning_mode == "none":
            reasoning_mode = "summary"

    for event in stream:
        event_type = _get_attr(event, "type")
        if debug_events and logger is not None:
            logger.info("Stream event type=%s", event_type)
        if debug_file_search and logger is not None and event_type and event_type.startswith("response.file_search_call"):
            logger.info("file_search stream event=%s payload=%s", event_type, event)

        if event_type == "response.reasoning_text.delta" and reasoning_mode == "full":
            delta = _get_attr(event, "delta") or ""
            if delta:
                _append_reasoning_log(delta)
                if on_reasoning:
                    on_reasoning(delta)
                elif stream_handlers is None:
                    if not wrote_reasoning_prefix:
                        sys.stdout.write("[reasoning] ")
                        wrote_reasoning_prefix = True
                    if reasoning_italics:
                        sys.stdout.write(f"\033[3m{delta}\033[0m")
                    else:
                        sys.stdout.write(delta)
                    sys.stdout.flush()
                wrote_any = True
                saw_full_reasoning = True
                reasoning_chunks.append(delta)
        elif event_type == "response.reasoning_summary_text.delta":
            delta = _get_attr(event, "delta") or ""
            if delta and (reasoning_mode == "summary" or (reasoning_mode == "full" and not saw_full_reasoning)):
                _append_reasoning_log(delta)
                if on_summary:
                    on_summary(delta)
                elif stream_handlers is None:
                    if not wrote_reasoning_prefix:
                        sys.stdout.write("[reasoning] ")
                        wrote_reasoning_prefix = True
                    if reasoning_italics:
                        sys.stdout.write(f"\033[3m{delta}\033[0m")
                    else:
                        sys.stdout.write(delta)
                    sys.stdout.flush()
                wrote_any = True
                reasoning_chunks.append(delta)
        elif event_type == "response.output_text.delta" and show_output:
            delta = _get_attr(event, "delta") or ""
            if delta:
                if on_output:
                    on_output(delta)
                elif stream_handlers is None:
                    if not wrote_output_prefix:
                        sys.stdout.write("[output] ")
                        wrote_output_prefix = True
                    sys.stdout.write(delta)
                    sys.stdout.flush()
                wrote_any = True
        elif event_type == "response.output_item.delta":
            delta_obj = _get_attr(event, "delta")
            delta_type = _get_attr(delta_obj, "type")
            delta_text = _get_attr(delta_obj, "text") or ""
            if delta_type == "reasoning" and reasoning_mode != "none":
                if delta_text:
                    _append_reasoning_log(delta_text)
                    if on_reasoning:
                        on_reasoning(delta_text)
                    elif stream_handlers is None:
                        if not wrote_reasoning_prefix:
                            sys.stdout.write("[reasoning] ")
                            wrote_reasoning_prefix = True
                        if reasoning_italics:
                            sys.stdout.write(f"\033[3m{delta_text}\033[0m")
                        else:
                            sys.stdout.write(delta_text)
                        sys.stdout.flush()
                    wrote_any = True
                    reasoning_chunks.append(delta_text)
            elif delta_type == "text" and show_output:
                if delta_text:
                    if on_output:
                        on_output(delta_text)
                    elif stream_handlers is None:
                        if not wrote_output_prefix:
                            sys.stdout.write("[output] ")
                            wrote_output_prefix = True
                        sys.stdout.write(delta_text)
                        sys.stdout.flush()
                    wrote_any = True
        elif event_type == "response.completed":
            final_response = _get_attr(event, "response")
            if reasoning_log_file and wrote_reasoning_log:
                try:
                    with open(reasoning_log_file, "a", encoding="utf-8") as handle:
                        handle.write("\n")
                except Exception:
                    if logger is not None:
                        logger.debug("Failed to finalize reasoning log %s", reasoning_log_file)
            if logger is not None and log_reasoning and reasoning_chunks and stream_handlers is None:
                text = "".join(reasoning_chunks)
                if text.lstrip().startswith(("**", "#")):
                    text = f"\n{text}"
                logger.info("Reasoning: %s", text)
            if show_usage and final_response is not None and stream_handlers is None:
                usage = _get_attr(final_response, "usage")
                total_tokens = _get_attr(usage, "total_tokens") if usage is not None else None
                if wrote_any:
                    sys.stdout.write("\n")
                if total_tokens is not None:
                    if logger is not None:
                        logger.info("Response usage total_tokens=%s", total_tokens)
                    sys.stdout.write(f"[usage] total_tokens={total_tokens}\n")
                    sys.stdout.flush()
            break
        elif event_type == "error":
            message = _get_attr(event, "message") or "Unknown streaming error"
            if logger is not None:
                logger.error("Streaming error: %s", message)

    if final_response is None:
        raise RuntimeError("Streaming response ended without response.completed.")
    return final_response
