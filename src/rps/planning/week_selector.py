"""Deterministic, auditable week-level workout selector."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rps.crewai_runtime.models import WeekWorkoutBlueprintModel
from rps.orchestrator.context_snapshots import _trace_ref
from rps.planning.week_protocols import (
    WeekWorkoutProtocol,
    WeekWorkoutProtocolConfig,
    protocol_is_allowed,
)
from rps.planning.week_selection_rules import (
    WeekWorkoutSelectionRule,
    WeekWorkoutSelectionRuleConfig,
    best_matching_rule,
    matching_rules,
)
from rps.workouts.progression_history import match_progression_signature
from rps.workspace.phase_intents import normalize_phase_type
from rps.workspace.types import ArtifactType
from rps.workspace.validated_api import ValidatedWorkspace

JsonMap = dict[str, Any]

SELECTOR_VERSION = "1.0"
REVIEW_BUCKET_SCORE = {
    "SOLL": 25.0,
    "KANN": 0.0,
    "NUR_WENN": -45.0,
    "VERMEIDEN": -250.0,
}


@dataclass(frozen=True)
class CandidateAuditRow:
    row: JsonMap


@dataclass(frozen=True)
class SelectionArtifact:
    payload: JsonMap
    csv_rows: list[JsonMap]


def select_workouts_for_week(
    *,
    athlete_id: str,
    target_iso_week: str,
    day_blueprints: list[Any],
    protocol_config: WeekWorkoutProtocolConfig,
    selection_rules: WeekWorkoutSelectionRuleConfig,
    progression_history: list[JsonMap],
    week_calendar_context: JsonMap,
    phase_preview_payload: JsonMap,
    phase_intent: str,
    phase_type: str,
    season_archetype: str,
    forced_quality_family: str | None,
    preserve_sat_anchor: bool,
) -> tuple[list[WeekWorkoutBlueprintModel], list[str], SelectionArtifact]:
    """Select workout protocols for the week and emit auditable candidate rows."""

    allowed_domains = {str(item).strip().upper() for item in week_calendar_context.get("allowed_intensity_domains") or []}
    allowed_modalities = {str(item).strip().upper() for item in week_calendar_context.get("allowed_load_modalities") or []}
    week_role = str(week_calendar_context.get("phase_week_role") or "").strip().upper()
    true_quality_cap = int(week_calendar_context.get("quality_day_cap") or 0)
    preview_hints = _phase_preview_hints(
        phase_preview_payload=phase_preview_payload,
        target_week=target_iso_week,
    )
    warnings: list[str] = []
    audit_rows: list[JsonMap] = []
    selected_quality_variants: list[str] = []
    selected_stimulus_classes: list[str] = []
    selected_monotony_groups: list[str] = []
    selected_protocol_types: list[str] = []
    true_quality_used = 0
    quality_index = 0
    workout_blueprints: list[WeekWorkoutBlueprintModel] = []
    for day in day_blueprints:
        if day.fixed_rest_day or not day.workout_id:
            continue
        is_anchor = day.day == "Sat" or (day.day == "Sun" and not preserve_sat_anchor)
        preview_hint = preview_hints.get(day.day, {})
        forced = forced_quality_family if day.day_role == "QUALITY" and quality_index == 0 else None
        result = _select_protocol_for_day(
            athlete_id=athlete_id,
            target_iso_week=target_iso_week,
            day=day.day,
            day_role=day.day_role,
            protocol_config=protocol_config,
            selection_rules=selection_rules,
            progression_history=progression_history,
            phase_intent=phase_intent,
            phase_type=phase_type,
            week_role=week_role,
            season_archetype=season_archetype,
            allowed_domains=allowed_domains,
            allowed_modalities=allowed_modalities,
            is_anchor=is_anchor,
            preview_hint=preview_hint,
            forced_quality_family=forced,
            remaining_true_quality_budget=max(true_quality_cap - true_quality_used, 0),
            selected_quality_variants=selected_quality_variants,
            selected_stimulus_classes=selected_stimulus_classes,
            selected_monotony_groups=selected_monotony_groups,
            selected_protocol_types=selected_protocol_types,
        )
        audit_rows.extend(result["audit_rows"])
        warnings.extend(result["warnings"])
        protocol: WeekWorkoutProtocol = result["protocol"]
        selected_rule: WeekWorkoutSelectionRule = result["rule"]
        previous_signature = result["previous_signature"]
        if day.day_role == "QUALITY":
            quality_index += 1
        if str(protocol.parameters.get("quality_cost") or "endurance_only").strip().lower() == "true_quality":
            true_quality_used += 1
            selected_quality_variants.append(protocol.protocol_variant)
            selected_stimulus_classes.append(selected_rule.stimulus_class)
            selected_monotony_groups.append(selected_rule.monotony_group)
            selected_protocol_types.append(protocol.protocol_type)
        progression_parameters = dict(protocol.parameters)
        addon_policy = protocol_config.addon_policies.get(protocol.addon_policy)
        if addon_policy is not None and addon_policy.policy_id != "NONE":
            progression_parameters.update(
                {
                    "addon_target_domain": addon_policy.target_domain,
                    "addon_target": addon_policy.target,
                    "addon_cadence": addon_policy.cadence,
                    "addon_min_block_minutes": addon_policy.min_block_minutes,
                    "addon_max_block_minutes": addon_policy.max_block_minutes,
                    "addon_step_minutes": addon_policy.step_minutes,
                    "addon_max_share_of_session": addon_policy.max_share_of_session,
                }
            )
        if selected_rule.reentry_dampening_flag:
            progression_parameters["selector_reentry_dampening"] = True
        workout_blueprints.append(
            WeekWorkoutBlueprintModel(
                workout_id=day.workout_id,
                date=day.date,
                phase_intent=phase_intent,
                day_role=day.day_role,
                intensity_domain=protocol.intensity_domain,
                workout_family=protocol.intensity_domain,
                family_variant=protocol.protocol_variant,
                protocol_type=protocol.protocol_type,
                protocol_variant=protocol.protocol_variant,
                load_modality=protocol.load_modality,
                stimulus_class=selected_rule.stimulus_class,
                monotony_group=selected_rule.monotony_group,
                selection_score=float(result["score"]),
                selection_rule_row_ids=[selected_rule.row_id],
                generator_profile=protocol.protocol_type,
                addon_policy=protocol.addon_policy,
                target_kj=0,
                progression_state={
                    "primary_axis": protocol.primary_axis,
                    "secondary_axis": protocol.secondary_axis,
                    "progression_priority": list(protocol.parameters.get("progression_priority") or []),
                    "redistribution_rule": protocol.redistribution_rule,
                    "count_tiz_as": str(protocol.parameters.get("count_tiz_as") or "full_work"),
                    "quality_cost": str(protocol.parameters.get("quality_cost") or "endurance_only"),
                    "previous_signature": dict(previous_signature) if previous_signature else {},
                    "selector_rule_row_ids": [selected_rule.row_id],
                    "selector_score": float(result["score"]),
                },
                selection_reason=result["selection_reason"],
                activation_required="activation_capable" in protocol.tags,
                low_end_endurance="recovery_like" in protocol.tags,
                progression_parameters=progression_parameters,
                phase_legality_status="legal",
                planned_duration_minutes=0,
                planned_kj=0,
                required_sections=["Warmup", "Main Set", "Cooldown"],
                exportability_status="pending",
                warnings=list(result["selected_warnings"]),
            )
        )
    artifact = SelectionArtifact(
        payload={
            "target_iso_week": target_iso_week,
            "selector_version": SELECTOR_VERSION,
            "rules_version": selection_rules.version,
            "source_versions": {},
            "csv_filename": f"week_workout_selection_audit_{target_iso_week}.csv",
            "rows": audit_rows,
        },
        csv_rows=audit_rows,
    )
    return workout_blueprints, warnings, artifact


def persist_selection_audit(
    *,
    workspace_root: Path,
    schema_dir: Path,
    athlete_id: str,
    version_key: str,
    run_id: str,
    target_week_start: str,
    target_week_end: str,
    payload: JsonMap,
    trace_upstream: list[JsonMap],
    source_versions: JsonMap,
) -> tuple[str, str]:
    """Persist the JSON audit artefact and a CSV sidecar."""

    document_payload = dict(payload)
    document_payload["source_versions"] = source_versions
    workspace = ValidatedWorkspace.for_athlete(athlete_id, schema_dir=schema_dir, root=workspace_root)
    json_path = workspace.put_validated(
        ArtifactType.WEEK_WORKOUT_SELECTION_AUDIT,
        version_key,
        document_payload,
        payload_meta={
            "schema_id": "WeekWorkoutSelectionAuditInterface",
            "schema_version": "1.0",
            "version": "1.0",
            "authority": "Derived",
            "owner_agent": "Week-Selection-Auditor",
            "scope": "Week",
            "iso_week": version_key,
            "iso_week_range": f"{version_key}--{version_key}",
            "temporal_scope": {"from": target_week_start, "to": target_week_end},
            "trace_upstream": trace_upstream,
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "HIGH",
            "notes": "Deterministic week workout selection audit.",
        },
        producer_agent="week_selector",
        run_id=f"{run_id}_selector_audit",
        update_latest=True,
    )
    csv_path = Path(json_path).with_suffix(".csv")
    _write_csv(csv_path, payload.get("rows") or [])
    latest_json_path = workspace.store.latest_path(athlete_id, ArtifactType.WEEK_WORKOUT_SELECTION_AUDIT)
    latest_csv_path = latest_json_path.with_suffix(".csv")
    latest_csv_path.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(latest_csv_path, payload.get("rows") or [])
    return json_path, str(csv_path)


def build_trace_upstream(payloads: list[tuple[ArtifactType, JsonMap]]) -> list[JsonMap]:
    """Return canonical trace references for selector audit artefacts."""

    refs: list[JsonMap] = []
    for artifact_type, payload in payloads:
        ref = _trace_ref(artifact_type, payload)
        if ref is not None:
            refs.append(ref)
    return refs


def build_source_versions_map(entries: list[tuple[str, JsonMap]]) -> JsonMap:
    """Return compact source-version labels for the selector audit."""

    out: JsonMap = {}
    for label, payload in entries:
        meta = payload.get("meta") if isinstance(payload, dict) else None
        version_key = meta.get("version_key") if isinstance(meta, dict) else None
        if isinstance(version_key, str):
            out[label] = version_key
    return out


def _select_protocol_for_day(
    *,
    athlete_id: str,
    target_iso_week: str,
    day: str,
    day_role: str,
    protocol_config: WeekWorkoutProtocolConfig,
    selection_rules: WeekWorkoutSelectionRuleConfig,
    progression_history: list[JsonMap],
    phase_intent: str,
    phase_type: str,
    week_role: str,
    season_archetype: str,
    allowed_domains: set[str],
    allowed_modalities: set[str],
    is_anchor: bool,
    preview_hint: JsonMap,
    forced_quality_family: str | None,
    remaining_true_quality_budget: int,
    selected_quality_variants: list[str],
    selected_stimulus_classes: list[str],
    selected_monotony_groups: list[str],
    selected_protocol_types: list[str],
) -> JsonMap:
    role = day_role.upper()
    candidate_ids = _candidate_ids_for_day(
        protocol_config=protocol_config,
        day_role=role,
        phase_intent=phase_intent,
        forced_quality_family=forced_quality_family,
    )
    evaluated: list[JsonMap] = []
    preview_domain = str(preview_hint.get("intensity_domain") or "").strip().upper()
    preview_modality = str(preview_hint.get("load_modality") or "").strip().upper()
    for protocol_id in candidate_ids:
        protocol = protocol_config.protocols[protocol_id]
        legal, filtered_codes = _legality_reasons(
            protocol=protocol,
            day_role=role,
            phase_intent=phase_intent,
            week_role=week_role,
            allowed_domains=allowed_domains,
            allowed_modalities=allowed_modalities,
            is_anchor=is_anchor,
            remaining_true_quality_budget=remaining_true_quality_budget,
        )
        candidate_rules = matching_rules(
            selection_rules.rules,
            protocol_variant=protocol.protocol_variant,
            protocol_type=protocol.protocol_type,
            intensity_domain=protocol.intensity_domain,
            load_modality=protocol.load_modality,
            season_archetype=season_archetype,
            phase_type=phase_type,
            phase_intent=phase_intent,
            week_role=week_role,
            day_role=role,
        )
        selected_rule = best_matching_rule(candidate_rules)
        if selected_rule is None:
            legal = False
            filtered_codes.append("NO_SELECTION_RULE")
        previous_signature = match_progression_signature(
            signatures=progression_history,
            protocol_type=protocol.protocol_type,
            protocol_variant=protocol.protocol_variant,
            workout_family=protocol.intensity_domain,
            day_role=role,
        )
        bonus_codes: list[str] = []
        penalty_codes: list[str] = []
        score = float("-inf")
        selected_warnings: list[str] = []
        if legal and selected_rule is not None:
            score = 1000.0 - (selected_rule.base_priority * 10)
            score += _specificity_bonus(selected_rule, season_archetype=season_archetype, phase_type=phase_type, phase_intent=phase_intent, week_role=week_role)
            bucket_adjustment = REVIEW_BUCKET_SCORE.get(selected_rule.review_bucket, 0.0)
            if bucket_adjustment > 0:
                bonus_codes.append(f"REVIEW_BUCKET_{selected_rule.review_bucket}")
            elif bucket_adjustment < 0:
                penalty_codes.append(f"REVIEW_BUCKET_{selected_rule.review_bucket}")
            score += bucket_adjustment
            prior_bonus = _prior_progression_bonus(protocol=protocol, previous_signature=previous_signature)
            if prior_bonus:
                bonus_codes.append("PRIOR_PROGRESSION_MATCH")
                score += prior_bonus
            if preview_domain and preview_domain == protocol.intensity_domain:
                bonus_codes.append("PREVIEW_DOMAIN_ALIGNMENT")
                score += selected_rule.preview_alignment_bonus
            if preview_modality and preview_modality == protocol.load_modality:
                bonus_codes.append("PREVIEW_MODALITY_ALIGNMENT")
                score += max(selected_rule.preview_alignment_bonus // 2, 1)
            if selected_rule.preferred_after_protocol_variant and selected_rule.preferred_after_protocol_variant in selected_quality_variants:
                if selected_rule.pairing_bonus_points:
                    bonus_codes.append(selected_rule.pairing_bonus_code or "PAIRING_BONUS")
                    score += selected_rule.pairing_bonus_points
            if selected_rule.forbidden_with_protocol_variant and selected_rule.forbidden_with_protocol_variant in selected_quality_variants:
                penalty_codes.append(selected_rule.pairing_penalty_code or "FORBIDDEN_PAIRING")
                score -= max(selected_rule.pairing_penalty_points, 999)
            if protocol.protocol_variant in selected_quality_variants:
                penalty_codes.append("DUPLICATE_PROTOCOL_VARIANT")
                score -= selected_rule.duplicate_penalty
            if selected_rule.stimulus_class in selected_stimulus_classes:
                penalty_codes.append("SAME_STIMULUS_CLASS")
                score -= selected_rule.same_stimulus_penalty
            if selected_rule.monotony_group in selected_monotony_groups:
                penalty_codes.append("SAME_MONOTONY_GROUP")
                score -= selected_rule.same_monotony_penalty
            if protocol.protocol_type in selected_protocol_types:
                penalty_codes.append("SAME_PROTOCOL_TYPE")
                score -= selected_rule.same_protocol_penalty
            if selected_rule.reentry_dampening_flag:
                selected_warnings.append("selector_reentry_dampening: selected row requests a lighter repeated re-entry quality dose.")
        evaluated.append(
            {
                "protocol": protocol,
                "rule": selected_rule,
                "previous_signature": previous_signature,
                "row": {
                    "row_id": selected_rule.row_id if selected_rule is not None else "NO_RULE",
                    "athlete_id": athlete_id,
                    "iso_week": target_iso_week,
                    "day": day,
                    "day_role": role,
                    "selected": False,
                    "protocol_id": protocol.protocol_id,
                    "protocol_variant": protocol.protocol_variant,
                    "protocol_type": protocol.protocol_type,
                    "intensity_domain": protocol.intensity_domain,
                    "load_modality": protocol.load_modality,
                    "stimulus_class": selected_rule.stimulus_class if selected_rule is not None else "unknown",
                    "monotony_group": selected_rule.monotony_group if selected_rule is not None else "unknown",
                    "phase_type": phase_type,
                    "phase_intent": phase_intent,
                    "week_role": week_role,
                    "season_archetype": season_archetype,
                    "review_bucket": selected_rule.review_bucket if selected_rule is not None else "KANN",
                    "preview_domain_hint": preview_domain,
                    "preview_modality_hint": preview_modality,
                    "allowed_domains_snapshot": sorted(allowed_domains),
                    "allowed_modalities_snapshot": sorted(allowed_modalities),
                    "previous_signature_match": str((previous_signature or {}).get("protocol_variant_guess") or ""),
                    "legal": legal,
                    "filtered_reason_codes": filtered_codes,
                    "base_priority": selected_rule.base_priority if selected_rule is not None else 999,
                    "bonus_codes": bonus_codes,
                    "penalty_codes": penalty_codes,
                    "score": float(score if score != float("-inf") else -999999.0),
                    "tie_break_key": f"{protocol.protocol_variant}:{protocol.protocol_id}",
                    "tie_break_position": 0,
                    "selection_reason": "",
                    "warnings": list(selected_warnings),
                },
            }
        )
    ranked = sorted(
        evaluated,
        key=lambda item: (
            -float(item["row"]["score"]),
            int(item["row"]["base_priority"]),
            str(item["row"]["tie_break_key"]),
        ),
    )
    for index, item in enumerate(ranked, start=1):
        item["row"]["tie_break_position"] = index
    winner = next((item for item in ranked if bool(item["row"]["legal"])), None)
    if winner is None:
        details = ", ".join(f"{item['row']['protocol_variant']}:{'|'.join(item['row']['filtered_reason_codes']) or 'NO_LEGAL_PATH'}" for item in ranked)
        raise ValueError(f"No legal workout protocol available for {day} {role}. Evaluated candidates: {details}")
    winner["row"]["selected"] = True
    winner["row"]["selection_reason"] = _selection_reason(
        protocol=winner["protocol"],
        rule=winner["rule"],
        score=float(winner["row"]["score"]),
        previous_signature=winner["previous_signature"],
    )
    return {
        "protocol": winner["protocol"],
        "rule": winner["rule"],
        "previous_signature": winner["previous_signature"],
        "score": winner["row"]["score"],
        "selection_reason": winner["row"]["selection_reason"],
        "selected_warnings": winner["row"]["warnings"],
        "warnings": [],
        "audit_rows": [item["row"] for item in ranked],
    }


def _candidate_ids_for_day(
    *,
    protocol_config: WeekWorkoutProtocolConfig,
    day_role: str,
    phase_intent: str,
    forced_quality_family: str | None,
) -> list[str]:
    if forced_quality_family:
        return [forced_quality_family.upper()]
    candidates = list(protocol_config.by_phase_intent.get(phase_intent.lower(), {}).get(day_role, []))
    candidates.extend(protocol_config.by_day_role.get(day_role, []))
    seen: set[str] = set()
    ordered: list[str] = []
    for protocol_id in candidates:
        if protocol_id in seen:
            continue
        seen.add(protocol_id)
        ordered.append(protocol_id)
    return ordered


def _legality_reasons(
    *,
    protocol: WeekWorkoutProtocol,
    day_role: str,
    phase_intent: str,
    week_role: str,
    allowed_domains: set[str],
    allowed_modalities: set[str],
    is_anchor: bool,
    remaining_true_quality_budget: int,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if protocol.allowed_day_roles and day_role.upper() not in protocol.allowed_day_roles:
        reasons.append("DAY_ROLE_BLOCKED")
    if protocol.allowed_phase_intents and "*" not in protocol.allowed_phase_intents and phase_intent.lower() not in protocol.allowed_phase_intents:
        reasons.append("PHASE_INTENT_BLOCKED")
    if protocol.allowed_week_roles and "*" not in protocol.allowed_week_roles and week_role.upper() not in protocol.allowed_week_roles:
        reasons.append("WEEK_ROLE_BLOCKED")
    if protocol.intensity_domain.upper() not in allowed_domains:
        reasons.append("INTENSITY_DOMAIN_BLOCKED")
    if protocol.load_modality.upper() not in allowed_modalities:
        reasons.append("LOAD_MODALITY_BLOCKED")
    if is_anchor and day_role.upper() == "ENDURANCE" and "anchor" not in protocol.tags and "long_endurance" not in protocol.tags:
        reasons.append("ANCHOR_TAG_REQUIRED")
    if not is_anchor and day_role.upper() == "ENDURANCE" and ("anchor" in protocol.tags or "long_endurance" in protocol.tags):
        reasons.append("NON_ANCHOR_LONG_ENDURANCE_BLOCKED")
    quality_cost = str(protocol.parameters.get("quality_cost") or "endurance_only").strip().lower()
    if quality_cost == "true_quality" and remaining_true_quality_budget <= 0:
        reasons.append("QUALITY_BUDGET_EXHAUSTED")
    if str(protocol.protocol_type or "").upper() == "DAY_TYPE_ONLY":
        reasons.append("DAY_TYPE_ONLY_NOT_RENDERABLE")
    return not reasons and protocol_is_allowed(
        protocol,
        day_role=day_role,
        phase_intent=phase_intent,
        week_role=week_role,
        allowed_domains=allowed_domains,
        allowed_modalities=allowed_modalities,
        is_anchor=is_anchor,
    ), reasons


def _specificity_bonus(
    rule: WeekWorkoutSelectionRule,
    *,
    season_archetype: str,
    phase_type: str,
    phase_intent: str,
    week_role: str,
) -> float:
    bonus = 0.0
    if rule.season_archetype != "*" and rule.season_archetype == season_archetype.lower():
        bonus += 10
    normalized_phase_type = normalize_phase_type(phase_type) or phase_type.replace(" ", "_").upper()
    if rule.phase_type != "*" and rule.phase_type == normalized_phase_type:
        bonus += 10
    if rule.phase_intent != "*" and rule.phase_intent == phase_intent.lower():
        bonus += 12
    if rule.week_role != "*" and rule.week_role == week_role:
        bonus += 8
    return bonus


def _prior_progression_bonus(*, protocol: WeekWorkoutProtocol, previous_signature: JsonMap | None) -> float:
    if not previous_signature:
        return 0.0
    guess = str(previous_signature.get("protocol_variant_guess") or "").upper()
    if guess == protocol.protocol_variant:
        return 25.0
    if str(previous_signature.get("protocol_type") or "").upper() == protocol.protocol_type:
        return 10.0
    return 0.0


def _selection_reason(
    *,
    protocol: WeekWorkoutProtocol,
    rule: WeekWorkoutSelectionRule | None,
    score: float,
    previous_signature: JsonMap | None,
) -> str:
    parts = [f"Selected {protocol.protocol_id} via deterministic selector"]
    if rule is not None:
        parts.append(f"rule {rule.row_id}")
    parts.append(f"score {score:.1f}")
    if previous_signature:
        parts.append(
            "prior progression matched "
            f"{str(previous_signature.get('protocol_variant_guess') or previous_signature.get('protocol_type') or 'protocol history')}"
        )
    return ". ".join(parts) + "."


def _phase_preview_hints(*, phase_preview_payload: JsonMap, target_week: str) -> dict[str, JsonMap]:
    data = phase_preview_payload.get("data") if isinstance(phase_preview_payload, dict) else None
    if not isinstance(data, dict):
        return {}
    for week in data.get("weekly_agenda_preview") or []:
        week_map = week if isinstance(week, dict) else {}
        if str(week_map.get("week") or "").strip() != target_week:
            continue
        return {
            str((item if isinstance(item, dict) else {}).get("day_of_week") or "").strip(): (item if isinstance(item, dict) else {})
            for item in week_map.get("days") or []
            if str((item if isinstance(item, dict) else {}).get("day_of_week") or "").strip()
        }
    return {}


def _write_csv(path: Path, rows: list[JsonMap]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "row_id",
        "athlete_id",
        "iso_week",
        "day",
        "day_role",
        "selected",
        "protocol_id",
        "protocol_variant",
        "protocol_type",
        "intensity_domain",
        "load_modality",
        "stimulus_class",
        "monotony_group",
        "phase_type",
        "phase_intent",
        "week_role",
        "season_archetype",
        "review_bucket",
        "preview_domain_hint",
        "preview_modality_hint",
        "allowed_domains_snapshot",
        "allowed_modalities_snapshot",
        "previous_signature_match",
        "legal",
        "filtered_reason_codes",
        "base_priority",
        "bonus_codes",
        "penalty_codes",
        "score",
        "tie_break_key",
        "tie_break_position",
        "selection_reason",
        "warnings",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            flat = dict(row)
            for key in ("allowed_domains_snapshot", "allowed_modalities_snapshot", "filtered_reason_codes", "bonus_codes", "penalty_codes", "warnings"):
                value = flat.get(key)
                if isinstance(value, list):
                    flat[key] = "|".join(str(item) for item in value)
            writer.writerow(flat)
