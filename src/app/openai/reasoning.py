"""Helpers for Responses API reasoning settings."""

from __future__ import annotations

from typing import Any


def _is_reasoning_model(model: str) -> bool:
    """Return True if the model name is likely to support reasoning params."""
    cleaned = model.strip().lower()
    return cleaned.startswith(("o1", "o3", "o4"))


def build_reasoning_payload(
    model: str,
    effort: str | None,
    summary: str | None,
) -> dict[str, Any] | None:
    """Build a reasoning payload if configured and supported by model."""
    if not effort and not summary:
        return None
    if not _is_reasoning_model(model):
        return None
    payload: dict[str, Any] = {}
    if effort:
        payload["effort"] = effort
    if summary:
        payload["summary"] = summary
    return payload or None
