"""Generic CrewAI task-output shape guardrails."""

from __future__ import annotations

from typing import Any

from rps.crewai_runtime.guardrails_context import GuardrailResult
from rps.crewai_runtime.guardrails_utilities import _coerce_payload


def typed_output_present(result: Any) -> GuardrailResult:
    payload = _coerce_payload(result)
    if payload is None:
        return (False, "Task produced no structured output payload.")
    return (True, payload)


def coaching_recommendation_text_present(result: Any) -> GuardrailResult:
    payload = _coerce_payload(result)
    recommendation = getattr(payload, "recommendation", None)
    if isinstance(payload, dict):
        recommendation = payload.get("recommendation")
    if isinstance(recommendation, str) and recommendation.strip():
        return (True, payload)
    return (False, "Coaching recommendation must contain non-empty recommendation text.")


def adjustment_intent_has_preview_message(result: Any) -> GuardrailResult:
    payload = _coerce_payload(result)
    preview_message = getattr(payload, "message_for_preview", None)
    if isinstance(payload, dict):
        preview_message = payload.get("message_for_preview")
    if isinstance(preview_message, str) and preview_message.strip():
        return (True, payload)
    return (False, "Adjustment intent must include a non-empty message_for_preview field.")


def coach_preview_summary_complete(result: Any) -> GuardrailResult:
    payload = _coerce_payload(result)
    ok_value = getattr(payload, "ok", None)
    summary = getattr(payload, "summary", None)
    if isinstance(payload, dict):
        ok_value = payload.get("ok")
        summary = payload.get("summary")
    if isinstance(ok_value, bool) and isinstance(summary, str) and summary.strip():
        return (True, payload)
    return (False, "Coach preview summary must include boolean ok and non-empty summary.")


def pending_resolution_summary_present(result: Any) -> GuardrailResult:
    payload = _coerce_payload(result)
    action = getattr(payload, "action", None)
    summary = getattr(payload, "summary", None)
    if isinstance(payload, dict):
        action = payload.get("action")
        summary = payload.get("summary")
    if isinstance(action, str) and action.strip() and isinstance(summary, str) and summary.strip():
        return (True, payload)
    return (False, "Pending-resolution result must include non-empty action and summary.")


def audit_lists_are_lists(result: Any) -> GuardrailResult:
    payload = _coerce_payload(result)
    mapping = payload.model_dump() if hasattr(payload, "model_dump") else payload
    if not isinstance(mapping, dict):
        return (False, "Audit output must decode to an object.")
    for field in ("blocking_issues", "warnings", "recommended_adjustments"):
        if field in mapping and not isinstance(mapping[field], list):
            return (False, f"Audit field '{field}' must be a list.")
    return (True, payload)
