"""Streaming helpers for Responses API calls."""

from __future__ import annotations

from typing import Any
import os
import sys


def _get_attr(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def should_stream() -> bool:
    raw = os.getenv("OPENAI_STREAM", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def stream_reasoning_mode() -> str:
    raw = os.getenv("OPENAI_STREAM_REASONING", "full").strip().lower()
    if raw in ("none", "off", "0", "false", "no"):
        return "none"
    if raw in ("full", "reasoning"):
        return "full"
    return "summary"


def stream_show_output() -> bool:
    raw = os.getenv("OPENAI_STREAM_TEXT", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def stream_show_usage() -> bool:
    raw = os.getenv("OPENAI_STREAM_USAGE", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def stream_log_reasoning() -> bool:
    raw = os.getenv("OPENAI_STREAM_LOG_REASONING", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def create_response(client: Any, payload: dict[str, Any], logger: Any | None):
    """Create a response, optionally streaming deltas to stdout."""
    if not should_stream():
        return client.responses.create(**payload)

    payload = dict(payload)
    payload["stream"] = True
    stream = client.responses.create(**payload)

    show_output = stream_show_output()
    reasoning_mode = stream_reasoning_mode()
    show_usage = stream_show_usage()
    log_reasoning = stream_log_reasoning()
    wrote_any = False
    wrote_reasoning_prefix = False
    wrote_output_prefix = False
    final_response = None
    saw_full_reasoning = False
    reasoning_chunks: list[str] = []
    debug_events = os.getenv("OPENAI_STREAM_DEBUG", "0").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

    for event in stream:
        event_type = _get_attr(event, "type")
        if debug_events and logger is not None:
            logger.info("Stream event type=%s", event_type)

        if event_type == "response.reasoning_text.delta" and reasoning_mode == "full":
            delta = _get_attr(event, "delta") or ""
            if delta:
                if not wrote_reasoning_prefix:
                    sys.stdout.write("[reasoning] ")
                    wrote_reasoning_prefix = True
                sys.stdout.write(delta)
                sys.stdout.flush()
                wrote_any = True
                saw_full_reasoning = True
                reasoning_chunks.append(delta)
        elif event_type == "response.reasoning_summary_text.delta":
            delta = _get_attr(event, "delta") or ""
            if delta and (reasoning_mode == "summary" or (reasoning_mode == "full" and not saw_full_reasoning)):
                if not wrote_reasoning_prefix:
                    sys.stdout.write("[reasoning] ")
                    wrote_reasoning_prefix = True
                sys.stdout.write(delta)
                sys.stdout.flush()
                wrote_any = True
                reasoning_chunks.append(delta)
        elif event_type == "response.output_text.delta" and show_output:
            delta = _get_attr(event, "delta") or ""
            if delta:
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
                    if not wrote_reasoning_prefix:
                        sys.stdout.write("[reasoning] ")
                        wrote_reasoning_prefix = True
                    sys.stdout.write(delta_text)
                    sys.stdout.flush()
                    wrote_any = True
                    reasoning_chunks.append(delta_text)
            elif delta_type == "text" and show_output:
                if delta_text:
                    if not wrote_output_prefix:
                        sys.stdout.write("[output] ")
                        wrote_output_prefix = True
                    sys.stdout.write(delta_text)
                    sys.stdout.flush()
                    wrote_any = True
        elif event_type == "response.completed":
            final_response = _get_attr(event, "response")
            if logger is not None and log_reasoning and reasoning_chunks:
                logger.info("Reasoning: %s", "".join(reasoning_chunks))
            if show_usage and final_response is not None:
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
