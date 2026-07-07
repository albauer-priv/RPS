"""Shared payload-coercion helpers for CrewAI guardrail evaluation."""

from __future__ import annotations

import json
from typing import Any

from rps.crewai_runtime.guardrails_context import JsonMap


def _coerce_payload(result: Any) -> Any:
    """Extract the richest payload view from a CrewAI TaskOutput-like object."""

    if result is None:
        return None
    pydantic_payload = getattr(result, "pydantic", None)
    if pydantic_payload is not None:
        return pydantic_payload
    json_payload = getattr(result, "json_dict", None)
    if json_payload is not None:
        return json_payload
    raw_payload = getattr(result, "raw", None)
    if raw_payload is not None:
        return raw_payload
    return result


def _coerce_mapping(result: Any) -> JsonMap | None:
    payload = _coerce_payload(result)
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump()
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError:
            return None
        return decoded if isinstance(decoded, dict) else None
    return None
