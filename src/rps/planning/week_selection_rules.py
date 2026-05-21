"""Flat, auditable selector-rule registry for week workout selection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from rps.workspace.phase_intents import normalize_phase_intent, normalize_phase_type

JsonMap = dict[str, Any]


@dataclass(frozen=True)
class WeekWorkoutSelectionRule:
    """One flat selector-policy row used for candidate scoring and auditing."""

    row_id: str
    protocol_variant: str
    protocol_type: str
    intensity_domain: str
    load_modality: str
    stimulus_class: str
    monotony_group: str
    quality_cost: str
    season_archetype: str
    phase_type: str
    phase_intent: str
    week_role: str
    day_role: str
    review_bucket: str
    allowed: bool
    base_priority: int
    pairing_group: str
    pairing_bonus_code: str
    pairing_bonus_points: int
    pairing_penalty_code: str
    pairing_penalty_points: int
    duplicate_penalty: int
    same_stimulus_penalty: int
    same_monotony_penalty: int
    same_protocol_penalty: int
    preview_alignment_bonus: int
    reentry_dampening_flag: bool
    requires_modality: str
    forbidden_with_protocol_variant: str
    preferred_after_protocol_variant: str
    notes: str
    audit_reason_code: str


@dataclass(frozen=True)
class WeekWorkoutSelectionRuleConfig:
    """Loaded selector-rule config."""

    version: str
    rules: tuple[WeekWorkoutSelectionRule, ...]


def load_week_workout_selection_rule_config(root: Path | str) -> WeekWorkoutSelectionRuleConfig:
    """Load and validate the flat week selection rule table."""

    config_path = Path(root) / "config" / "planning" / "week_workout_selection_rules.yaml"
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("week_workout_selection_rules.yaml must contain a top-level mapping.")

    version = str(payload.get("version") or "1.0").strip() or "1.0"
    raw_rules = payload.get("rules")
    if not isinstance(raw_rules, list) or not raw_rules:
        raise ValueError("week_workout_selection_rules.yaml must define a non-empty rules list.")

    rules: list[WeekWorkoutSelectionRule] = []
    seen_ids: set[str] = set()
    required_keys = {
        "row_id",
        "protocol_variant",
        "protocol_type",
        "intensity_domain",
        "load_modality",
        "stimulus_class",
        "monotony_group",
        "quality_cost",
        "season_archetype",
        "phase_type",
        "phase_intent",
        "week_role",
        "day_role",
        "allowed",
        "base_priority",
        "pairing_group",
        "pairing_bonus_code",
        "pairing_bonus_points",
        "pairing_penalty_code",
        "pairing_penalty_points",
        "duplicate_penalty",
        "same_stimulus_penalty",
        "same_monotony_penalty",
        "same_protocol_penalty",
        "preview_alignment_bonus",
        "reentry_dampening_flag",
        "requires_modality",
        "forbidden_with_protocol_variant",
        "preferred_after_protocol_variant",
        "notes",
        "audit_reason_code",
    }
    for index, raw in enumerate(raw_rules, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"selection rule row {index} must be a mapping.")
        missing = sorted(required_keys - set(raw))
        if missing:
            raise ValueError(f"selection rule row {index} missing keys: {', '.join(missing)}")
        row_id = _upper(raw.get("row_id"))
        if row_id in seen_ids:
            raise ValueError(f"Duplicate selection rule row_id '{row_id}'.")
        seen_ids.add(row_id)
        rules.append(
            WeekWorkoutSelectionRule(
                row_id=row_id,
                protocol_variant=_upper(raw.get("protocol_variant")),
                protocol_type=_upper(raw.get("protocol_type")),
                intensity_domain=_upper(raw.get("intensity_domain")),
                load_modality=_upper(raw.get("load_modality")),
                stimulus_class=_lower_token(raw.get("stimulus_class")),
                monotony_group=_lower_token(raw.get("monotony_group")),
                quality_cost=_lower_token(raw.get("quality_cost")),
                season_archetype=_lower_or_wildcard(raw.get("season_archetype")),
                phase_type=_string_or_wildcard(raw.get("phase_type")),
                phase_intent=_lower_or_wildcard(raw.get("phase_intent")),
                week_role=_string_or_wildcard(raw.get("week_role")),
                day_role=_upper(raw.get("day_role")),
                review_bucket=_upper(raw.get("review_bucket") or "KANN"),
                allowed=bool(raw.get("allowed")),
                base_priority=int(raw.get("base_priority") or 0),
                pairing_group=_lower_token(raw.get("pairing_group")),
                pairing_bonus_code=str(raw.get("pairing_bonus_code") or "").strip().upper(),
                pairing_bonus_points=int(raw.get("pairing_bonus_points") or 0),
                pairing_penalty_code=str(raw.get("pairing_penalty_code") or "").strip().upper(),
                pairing_penalty_points=int(raw.get("pairing_penalty_points") or 0),
                duplicate_penalty=int(raw.get("duplicate_penalty") or 0),
                same_stimulus_penalty=int(raw.get("same_stimulus_penalty") or 0),
                same_monotony_penalty=int(raw.get("same_monotony_penalty") or 0),
                same_protocol_penalty=int(raw.get("same_protocol_penalty") or 0),
                preview_alignment_bonus=int(raw.get("preview_alignment_bonus") or 0),
                reentry_dampening_flag=bool(raw.get("reentry_dampening_flag")),
                requires_modality=_upper(raw.get("requires_modality") or "NONE"),
                forbidden_with_protocol_variant=_upper(raw.get("forbidden_with_protocol_variant")),
                preferred_after_protocol_variant=_upper(raw.get("preferred_after_protocol_variant")),
                notes=str(raw.get("notes") or "").strip(),
                audit_reason_code=str(raw.get("audit_reason_code") or "").strip().upper(),
            )
        )
    return WeekWorkoutSelectionRuleConfig(version=version, rules=tuple(rules))


def matching_rules(
    rules: tuple[WeekWorkoutSelectionRule, ...],
    *,
    protocol_variant: str,
    protocol_type: str,
    intensity_domain: str,
    load_modality: str,
    season_archetype: str,
    phase_type: str,
    phase_intent: str,
    week_role: str,
    day_role: str,
) -> list[WeekWorkoutSelectionRule]:
    """Return all rows that match one candidate context."""

    target_variant = _upper(protocol_variant)
    target_type = _upper(protocol_type)
    target_domain = _upper(intensity_domain)
    target_modality = _upper(load_modality)
    target_archetype = _lower_or_wildcard(season_archetype)
    target_phase_type = _string_or_wildcard(phase_type)
    target_intent = _lower_or_wildcard(phase_intent)
    target_week_role = _string_or_wildcard(week_role)
    target_day_role = _upper(day_role)
    out: list[WeekWorkoutSelectionRule] = []
    for rule in rules:
        if rule.protocol_variant != target_variant:
            continue
        if rule.protocol_type != target_type:
            continue
        if rule.intensity_domain != target_domain:
            continue
        if rule.load_modality != target_modality:
            continue
        if rule.day_role != target_day_role:
            continue
        if not _field_matches(rule.season_archetype, target_archetype):
            continue
        if not _field_matches(rule.phase_type, target_phase_type):
            continue
        if not _field_matches(rule.phase_intent, target_intent):
            continue
        if not _field_matches(rule.week_role, target_week_role):
            continue
        out.append(rule)
    return out


def best_matching_rule(rules: list[WeekWorkoutSelectionRule]) -> WeekWorkoutSelectionRule | None:
    """Resolve overlapping rule rows deterministically."""

    if not rules:
        return None
    ordered = sorted(
        rules,
        key=lambda item: (
            -_specificity(item),
            item.base_priority,
            item.row_id,
        ),
    )
    return ordered[0]


def _specificity(rule: WeekWorkoutSelectionRule) -> int:
    return sum(
        1
        for value in (
            rule.season_archetype,
            rule.phase_type,
            rule.phase_intent,
            rule.week_role,
        )
        if value != "*"
    )


def _field_matches(rule_value: str, target_value: str) -> bool:
    return rule_value == "*" or rule_value == target_value


def _upper(value: object) -> str:
    return str(value or "").strip().upper().replace(" ", "_")


def _lower_token(value: object) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def _lower_or_wildcard(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "*"
    if text == "*":
        return "*"
    return normalize_phase_intent(text) or text.lower().replace(" ", "_")


def _string_or_wildcard(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "*"
    if text == "*":
        return "*"
    normalized = normalize_phase_type(text)
    return normalized or text.replace(" ", "_").upper()
