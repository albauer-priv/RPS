"""Shared payload-coercion, diagnostics, and telemetry-wrapper helpers for CrewAI guardrail evaluation."""

from __future__ import annotations

import json
import re
from typing import Any, cast

from rps.agents.output_normalization import (
    extract_loaded_document,
    normalize_phase_guardrails_document_from_execution_context,
    normalize_phase_preview_document,
    normalize_phase_structure_document_from_execution_context,
)
from rps.crewai_runtime.guardrails_context import (
    _GUARDRAIL_CONTEXT,
    GuardrailFn,
    JsonMap,
    current_guardrail_runtime_context,
)
from rps.crewai_runtime.telemetry import emit_runtime_event
from rps.planning.phase_authority import normalize_role_week_load_bands
from rps.workspace.types import ArtifactType


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


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_map(value: Any) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    return [str(item).strip() for item in _as_list(value) if str(item).strip()]


_CADENCE_RATIONALE_FIELDS = (
    "decision_notes",
    "risk_flags",
    "event_alignment_notes",
    "kpi_guardrail_notes",
)


def _scenario_rationale_text(guidance: JsonMap) -> str:
    return " ".join(
        part
        for field in _CADENCE_RATIONALE_FIELDS
        for part in _string_list(guidance.get(field))
    ).lower()


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _future_event_runtime_context() -> JsonMap:
    return _as_map(current_guardrail_runtime_context().get("season_scenario_event_context"))


def _active_weekly_band_from_context() -> JsonMap:
    context = _week_calendar_context()
    active_band = _as_map(context.get("active_weekly_kj_band"))
    if active_band:
        return active_band
    phase_band = _as_map(context.get("phase_weekly_kj_band"))
    if phase_band:
        return phase_band
    return _as_map(context.get("active_s5_band"))


def _week_calendar_context() -> JsonMap:
    context = _GUARDRAIL_CONTEXT.get({})
    return _as_map(context.get("week_calendar_context"))


def _phase_execution_context() -> JsonMap:
    context = _GUARDRAIL_CONTEXT.get({})
    return _as_map(context.get("phase_execution_context"))


def _season_phase_slot_context() -> JsonMap:
    context = _GUARDRAIL_CONTEXT.get({})
    return _as_map(context.get("phase_slot_context"))


def _season_phase_load_context() -> JsonMap:
    context = _GUARDRAIL_CONTEXT.get({})
    return _as_map(context.get("season_phase_load_context"))


def _loaded_input_version_key(raw: object) -> str | None:
    """Return one version key from a loaded input or persisted save payload."""

    if not isinstance(raw, dict):
        return None
    version_key = raw.get("version_key")
    if isinstance(version_key, str) and version_key.strip():
        return version_key.strip()
    document = raw.get("document")
    if isinstance(document, dict):
        meta = _as_map(document.get("meta"))
        version_key = meta.get("version_key")
        if isinstance(version_key, str) and version_key.strip():
            return version_key.strip()
    meta = _as_map(raw.get("meta"))
    version_key = meta.get("version_key")
    if isinstance(version_key, str) and version_key.strip():
        return version_key.strip()
    return None


def _phase_guardrails_weekly_bands(document: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Return stored phase-guardrails weekly bands when present."""

    load_guardrails = _as_map(_as_map(document).get("data")).get("load_guardrails")
    bands = _as_map(load_guardrails).get("weekly_kj_bands")
    return [entry for entry in _as_list(bands) if isinstance(entry, dict)]


def canonicalize_season_bundle_shape_aliases(mapping: dict[str, Any]) -> dict[str, Any]:
    """Project known Season bundle alias drift into canonical plural audit slots."""

    normalized = dict(mapping)
    constraints_raw = normalized.get("constraints", [])
    if isinstance(constraints_raw, dict):
        constraints: list[Any] = [constraints_raw]
    else:
        constraints = list(_as_list(constraints_raw))
    singular_constraint = normalized.pop("constraint_audit", None)
    if singular_constraint is not None:
        constraints.append(singular_constraint)
    normalized["constraints"] = constraints

    governance_raw = normalized.get("load_governance", [])
    if isinstance(governance_raw, dict):
        load_governance: list[Any] = [governance_raw]
    else:
        load_governance = list(_as_list(governance_raw))
    singular_governance = normalized.pop("load_governance_audit", None)
    if singular_governance is not None:
        load_governance.append(singular_governance)
    normalized["load_governance"] = load_governance
    return normalized


def decode_json_object_from_text(text: str) -> dict[str, Any] | None:
    """Decode one JSON object from plain or fenced text without accepting arrays or scalars."""

    stripped = text.strip()
    if not stripped:
        return None
    try:
        decoded = json.loads(stripped)
    except json.JSONDecodeError:
        decoded = None
    if isinstance(decoded, dict):
        return decoded

    fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, flags=re.DOTALL | re.IGNORECASE)
    if fenced_match:
        candidate = fenced_match.group(1).strip()
        try:
            decoded = json.loads(candidate)
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, dict):
            return decoded

    decoder = json.JSONDecoder()
    for index, char in enumerate(stripped):
        if char != "{":
            continue
        try:
            decoded, _end = decoder.raw_decode(stripped[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(decoded, dict):
            return decoded
    return None


def _season_finalize_candidate_mapping(result: Any) -> dict[str, Any] | None:
    """Decode and canonicalize known Season-finalizer shape drift before task guardrails evaluate it."""

    payload = _coerce_payload(result)
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump()
    if isinstance(payload, dict):
        return canonicalize_season_bundle_shape_aliases(payload)
    if isinstance(payload, str):
        decoded = decode_json_object_from_text(payload)
        if isinstance(decoded, dict):
            return canonicalize_season_bundle_shape_aliases(decoded)
    return None


def normalize_artifact_candidate_for_task_guardrails(result: Any) -> Any:
    """Project exact persisted phase authority before writer-task guardrails evaluate candidates."""

    context = current_guardrail_runtime_context()
    task_name = str(context.get("task_name") or "").strip()
    if task_name == "season_plan_finalize":
        mapping = _season_finalize_candidate_mapping(result)
        return mapping if isinstance(mapping, dict) else result
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return result
    artifact_type = str(context.get("artifact_type") or "").strip().upper()
    loaded_inputs = context.get("loaded_inputs")
    if not isinstance(loaded_inputs, dict):
        loaded_inputs = {}
    phase_execution_context = context.get("phase_execution_context")
    if artifact_type == ArtifactType.PHASE_GUARDRAILS.value:
        if not normalize_role_week_load_bands(_as_map(phase_execution_context).get("phase_role_week_load_bands")):
            raise ValueError(
                "PHASE_GUARDRAILS pre-guardrail normalization requires phase_execution_context.phase_role_week_load_bands."
            )
        return normalize_phase_guardrails_document_from_execution_context(
            dict(mapping),
            phase_execution_context=phase_execution_context if isinstance(phase_execution_context, dict) else None,
            season_plan_document=extract_loaded_document(loaded_inputs.get("season_plan")),
            season_scenario_selection_document=extract_loaded_document(loaded_inputs.get("season_scenario_selection")),
            season_scenarios_document=extract_loaded_document(loaded_inputs.get("season_scenarios")),
        )
    if artifact_type == ArtifactType.PHASE_STRUCTURE.value:
        phase_guardrails_document = extract_loaded_document(loaded_inputs.get("phase_guardrails"))
        if not _string_list(_as_map(phase_execution_context).get("phase_allowed_intensity_domains")):
            raise ValueError(
                "PHASE_STRUCTURE pre-guardrail normalization requires phase_execution_context.phase_allowed_intensity_domains."
            )
        if not _as_map(_as_map(phase_execution_context).get("inherited_scenario_contract")):
            raise ValueError(
                "PHASE_STRUCTURE pre-guardrail normalization requires phase_execution_context.inherited_scenario_contract."
            )
        if not _phase_guardrails_weekly_bands(phase_guardrails_document):
            raise ValueError(
                "PHASE_STRUCTURE pre-guardrail normalization requires phase_guardrails.data.load_guardrails.weekly_kj_bands."
            )
        return normalize_phase_structure_document_from_execution_context(
            dict(mapping),
            phase_execution_context=phase_execution_context if isinstance(phase_execution_context, dict) else None,
            season_plan_document=extract_loaded_document(loaded_inputs.get("season_plan")),
            season_scenario_selection_document=extract_loaded_document(loaded_inputs.get("season_scenario_selection")),
            season_scenarios_document=extract_loaded_document(loaded_inputs.get("season_scenarios")),
            phase_guardrails_document=phase_guardrails_document,
            phase_guardrails_version_key=_loaded_input_version_key(loaded_inputs.get("phase_guardrails")),
        )
    if artifact_type == ArtifactType.PHASE_PREVIEW.value:
        return normalize_phase_preview_document(
            dict(mapping),
            phase_structure_document=extract_loaded_document(loaded_inputs.get("phase_structure")),
            phase_structure_version_key=_loaded_input_version_key(loaded_inputs.get("phase_structure")),
        )
    return result


def _phase_structure_guardrail_diagnostics(normalized_result: Any) -> str:
    """Return a compact diagnostic string for PHASE_STRUCTURE legality mismatches."""

    mapping = _coerce_mapping(normalized_result)
    if not isinstance(mapping, dict):
        return ""
    context = current_guardrail_runtime_context()
    loaded_inputs = context.get("loaded_inputs")
    loaded_inputs = loaded_inputs if isinstance(loaded_inputs, dict) else {}
    phase_execution_context = _as_map(context.get("phase_execution_context"))
    structural = _as_map(_as_map(mapping.get("data")).get("structural_phase_elements"))
    observed = _string_list(structural.get("allowed_intensity_domains"))
    expected = _string_list(phase_execution_context.get("phase_allowed_intensity_domains"))
    return (
        "phase_structure_diag="
        f"execution_context={'yes' if phase_execution_context else 'no'},"
        f"phase_guardrails={'yes' if extract_loaded_document(loaded_inputs.get('phase_guardrails')) else 'no'},"
        f"season_plan={'yes' if extract_loaded_document(loaded_inputs.get('season_plan')) else 'no'},"
        f"observed_allowed={observed},"
        f"expected_allowed={expected}"
    )


def _first_contract_mismatch_path(candidate: object, authority: object, *, prefix: str) -> str:
    """Return the first nested mismatch path between two JSON-like contract values."""

    if isinstance(candidate, dict) and isinstance(authority, dict):
        keys = sorted(set(candidate) | set(authority))
        for key in keys:
            child = _first_contract_mismatch_path(
                candidate.get(key),
                authority.get(key),
                prefix=f"{prefix}.{key}",
            )
            if child:
                return child
        return ""
    if isinstance(candidate, list) and isinstance(authority, list):
        if len(candidate) != len(authority):
            return f"{prefix}[len]"
        for index, (left, right) in enumerate(zip(candidate, authority, strict=True)):
            child = _first_contract_mismatch_path(
                left,
                right,
                prefix=f"{prefix}[{index}]",
            )
            if child:
                return child
        return ""
    return "" if candidate == authority else prefix


def _phase_structure_contract_diagnostics(raw_result: Any, normalized_result: Any) -> str:
    """Return a compact diagnostic string for PHASE_STRUCTURE inherited-contract mismatches."""

    raw_mapping = _coerce_mapping(raw_result)
    mapping = _coerce_mapping(normalized_result)
    if not isinstance(mapping, dict):
        return ""
    context = current_guardrail_runtime_context()
    loaded_inputs = context.get("loaded_inputs")
    loaded_inputs = loaded_inputs if isinstance(loaded_inputs, dict) else {}
    phase_execution_context = _as_map(context.get("phase_execution_context"))
    phase_guardrails_document = extract_loaded_document(loaded_inputs.get("phase_guardrails"))
    raw_structure_contract = _as_map(_as_map(_as_map(raw_mapping).get("structure")).get("inherited_scenario_contract"))
    raw_candidate_contract = _as_map(_as_map(_as_map(raw_mapping).get("data")).get("inherited_scenario_contract"))
    bundle_contract = _as_map(_as_map(mapping.get("inherited_scenario_contract")))
    observed = _as_map(_as_map(mapping.get("data")).get("inherited_scenario_contract"))
    expected = _as_map(phase_execution_context.get("inherited_scenario_contract"))
    guardrails_contract = _as_map(_as_map(phase_guardrails_document).get("data")).get("inherited_scenario_contract")
    mismatch_path = _first_contract_mismatch_path(
        observed,
        expected,
        prefix="data.inherited_scenario_contract",
    )
    source = "missing"
    if observed and observed == expected:
        source = "execution_context"
    elif observed and guardrails_contract and observed == _as_map(guardrails_contract):
        source = "phase_guardrails_fallback"
    elif observed:
        source = "candidate_or_late_rewrite"
    return (
        "phase_contract_diag="
        f"execution_context_contract={'yes' if expected else 'no'},"
        f"bundle_contract={'yes' if bundle_contract else 'no'},"
        f"raw_structure_contract={'yes' if raw_structure_contract else 'no'},"
        f"raw_candidate_contract={'yes' if raw_candidate_contract else 'no'},"
        f"pre_guardrail_normalized={'yes' if isinstance(mapping, dict) else 'no'},"
        f"phase_guardrails={'yes' if phase_guardrails_document else 'no'},"
        f"phase_guardrails_contract={'yes' if _as_map(guardrails_contract) else 'no'},"
        f"source={source},"
        f"mismatch_path={mismatch_path or 'none'}"
    )


def _compose_guardrail_failure_reason(base_reason: str, diagnostics_parts: list[str], *, limit: int = 500) -> str:
    """Combine a guardrail failure reason with compact diagnostics without truncating them away."""

    if not diagnostics_parts:
        return base_reason[:limit]
    diagnostics = " | ".join(part for part in diagnostics_parts if part)
    if not diagnostics:
        return base_reason[:limit]
    suffix = f" | {diagnostics}"
    if len(suffix) >= limit:
        return diagnostics[:limit]
    available = limit - len(suffix)
    return f"{base_reason[:available]}{suffix}"


def _with_guardrail_telemetry(task_name: str, guardrail_name: str, guardrail_fn: GuardrailFn) -> GuardrailFn:
    """Wrap one guardrail so failures become compact retry-relevant runtime events."""

    def _wrapped(result: Any):
        if guardrail_name == "typed_output_present":
            # This guardrail checks whether CrewAI's own output_pydantic binding
            # populated `.pydantic` on the raw TaskOutput -- a property of the
            # binding step itself, not of content shape. Every other guardrail
            # here validates *content*, so pre-normalizing through
            # `normalize_artifact_candidate_for_task_guardrails` (which projects
            # `.pydantic`/`.json_dict`/`.raw` down to a plain dict via
            # `_coerce_mapping`) is exactly right for them and exactly wrong for
            # this one: a dict never has a `.pydantic` attribute, so checking it
            # post-normalization would fail unconditionally regardless of whether
            # the binding actually succeeded.
            normalized_result = result
        else:
            try:
                normalized_result = normalize_artifact_candidate_for_task_guardrails(result)
            except Exception as exc:
                context = _GUARDRAIL_CONTEXT.get({})
                emit_runtime_event(
                    root=context.get("root"),
                    athlete_id=context.get("athlete_id"),
                    run_id=context.get("run_id"),
                    event_type="CREW_TASK_GUARDRAIL_FAILED",
                    component=context.get("component") or f"task:{task_name}",
                    task=task_name,
                    guardrail=guardrail_name,
                    reason=f"pre_guardrail_normalization_failed: {exc}"[:500],
                )
                return (False, f"pre_guardrail_normalization_failed: {exc}")
        ok, payload = guardrail_fn(normalized_result)
        if not ok:
            context = _GUARDRAIL_CONTEXT.get({})
            reason = str(payload)[:500]
            artifact_type = str(context.get("artifact_type") or "").strip().upper()
            if (
                artifact_type == ArtifactType.PHASE_STRUCTURE.value
                and guardrail_name == "phase_execution_context_match"
            ):
                diagnostics_parts: list[str] = []
                if "phase_structural_allowed_domains_mismatch" in str(payload):
                    diagnostics = _phase_structure_guardrail_diagnostics(normalized_result)
                    if diagnostics:
                        diagnostics_parts.append(diagnostics)
                if "phase_inherited_scenario_contract_mismatch" in str(payload):
                    diagnostics = _phase_structure_contract_diagnostics(result, normalized_result)
                    if diagnostics:
                        diagnostics_parts.append(diagnostics)
                if diagnostics_parts:
                    reason = _compose_guardrail_failure_reason(reason, diagnostics_parts, limit=500)
            emit_runtime_event(
                root=context.get("root"),
                athlete_id=context.get("athlete_id"),
                run_id=context.get("run_id"),
                event_type="CREW_TASK_GUARDRAIL_FAILED",
                component=context.get("component") or f"task:{task_name}",
                task=task_name,
                guardrail=guardrail_name,
                reason=reason,
            )
        return (ok, payload)

    return cast(GuardrailFn, _wrapped)
