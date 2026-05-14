"""Guardrail registry and helpers for CrewAI task construction."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

JsonMap = dict[str, Any]
GuardrailResult = tuple[bool, Any]
GuardrailFn = Callable[[Any], GuardrailResult]


@dataclass(frozen=True)
class TaskExecutionPolicy:
    """Resolved task execution policy merged from config defaults and overrides."""

    output_mode: str
    guardrails: tuple[str, ...]
    guardrail_max_retries: int


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


def phase_bundle_integrity(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Phase bundle must decode to an object.")
    required = ("phase_range", "guardrails", "structure", "preview", "constraint_audit", "load_governance_audit")
    missing = [field for field in required if field not in mapping]
    if missing:
        return (False, f"Phase bundle missing required keys: {', '.join(missing)}")
    return (True, mapping)


def artifact_envelope_basic(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Artifact output must decode to a JSON object.")
    meta = mapping.get("meta")
    data = mapping.get("data")
    if not isinstance(meta, dict) or not isinstance(data, dict):
        return (False, "Artifact output must include top-level 'meta' and 'data' objects.")
    return (True, mapping)


def artifact_meta_data_present(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Artifact output must decode to a JSON object.")
    meta = mapping.get("meta")
    if not isinstance(meta, dict):
        return (False, "Artifact output missing meta object.")
    required = ("artifact_type", "schema_id")
    missing = [field for field in required if not meta.get(field)]
    if missing:
        return (False, f"Artifact meta missing required fields: {', '.join(missing)}")
    if not isinstance(mapping.get("data"), dict):
        return (False, "Artifact output missing data object.")
    return (True, mapping)


REGISTRY: dict[str, GuardrailFn] = {
    "typed_output_present": typed_output_present,
    "coaching_recommendation_text_present": coaching_recommendation_text_present,
    "adjustment_intent_has_preview_message": adjustment_intent_has_preview_message,
    "coach_preview_summary_complete": coach_preview_summary_complete,
    "pending_resolution_summary_present": pending_resolution_summary_present,
    "audit_lists_are_lists": audit_lists_are_lists,
    "phase_bundle_integrity": phase_bundle_integrity,
    "artifact_envelope_basic": artifact_envelope_basic,
    "artifact_meta_data_present": artifact_meta_data_present,
}


def resolve_guardrail(name: str) -> GuardrailFn:
    """Return a registered guardrail callable by symbolic name."""

    try:
        return REGISTRY[name]
    except KeyError as exc:  # pragma: no cover - config validation catches this in tests
        raise ValueError(f"Unknown CrewAI guardrail: {name}") from exc


def resolve_task_policy(task_blueprint: Any, task_policies: JsonMap) -> TaskExecutionPolicy:
    """Resolve the merged task execution policy from config defaults and overrides."""

    defaults = task_policies.get("defaults") or {}
    kind_defaults = defaults.get(task_blueprint.config.get("kind") or "") or {}
    task_overrides = (task_policies.get("tasks") or {}).get(task_blueprint.name) or {}

    output_mode = str(task_overrides.get("output_mode") or kind_defaults.get("output_mode") or "pydantic")
    guardrails_raw = task_overrides.get("guardrails")
    if guardrails_raw is None:
        guardrails_raw = kind_defaults.get("guardrails") or []
    guardrails = tuple(str(item) for item in guardrails_raw)
    guardrail_max_retries = int(
        task_overrides.get("guardrail_max_retries")
        or kind_defaults.get("guardrail_max_retries")
        or 3
    )
    return TaskExecutionPolicy(
        output_mode=output_mode,
        guardrails=guardrails,
        guardrail_max_retries=guardrail_max_retries,
    )


def build_task_guardrail_kwargs(task_blueprint: Any, task_policies: JsonMap) -> JsonMap:
    """Return CrewAI Task kwargs for guardrails and output-mode policy."""

    policy = resolve_task_policy(task_blueprint, task_policies)
    kwargs: JsonMap = {"guardrail_max_retries": policy.guardrail_max_retries}
    if policy.guardrails:
        guardrail_fns = [resolve_guardrail(name) for name in policy.guardrails]
        if len(guardrail_fns) == 1:
            kwargs["guardrail"] = guardrail_fns[0]
        else:
            kwargs["guardrails"] = guardrail_fns
    kwargs["_resolved_output_mode"] = policy.output_mode
    return kwargs
