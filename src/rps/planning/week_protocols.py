"""Protocol-driven week workout configuration and deterministic helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

JsonMap = dict[str, Any]


@dataclass(frozen=True)
class WeekWorkoutProtocol:
    protocol_id: str
    intensity_domain: str
    load_modality: str
    protocol_type: str
    protocol_variant: str
    allowed_day_roles: tuple[str, ...]
    allowed_phase_intents: tuple[str, ...]
    allowed_week_roles: tuple[str, ...]
    tags: frozenset[str]
    primary_axis: str
    secondary_axis: str
    redistribution_rule: str | None
    addon_policy: str
    parameters: JsonMap


@dataclass(frozen=True)
class AddOnPolicy:
    policy_id: str
    target_domain: str | None
    target: str | None
    cadence: str | None
    min_block_minutes: int
    max_block_minutes: int
    step_minutes: int
    max_share_of_session: float
    allowed_primary_protocols: tuple[str, ...]


@dataclass(frozen=True)
class WeekWorkoutProtocolConfig:
    protocols: dict[str, WeekWorkoutProtocol]
    addon_policies: dict[str, AddOnPolicy]
    by_phase_intent: dict[str, dict[str, list[str]]]
    by_day_role: dict[str, list[str]]


def load_week_workout_protocol_config(root: Path | str) -> WeekWorkoutProtocolConfig:
    """Load and validate configurable workout protocols."""

    config_path = Path(root) / "config" / "planning" / "week_workout_protocols.yaml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("week_workout_protocols.yaml must contain a top-level mapping.")

    protocols_raw = data.get("protocols")
    if not isinstance(protocols_raw, dict) or not protocols_raw:
        raise ValueError("week_workout_protocols.yaml must define at least one protocol.")
    addon_raw = data.get("addon_policies") or {}
    if not isinstance(addon_raw, dict):
        raise ValueError("addon_policies must be a mapping.")

    addon_policies: dict[str, AddOnPolicy] = {}
    for key, raw in addon_raw.items():
        if not isinstance(raw, dict):
            raise ValueError(f"Add-on policy '{key}' must be a mapping.")
        addon_policies[key.upper()] = AddOnPolicy(
            policy_id=key.upper(),
            target_domain=_normalized_str(raw.get("target_domain")) or None,
            target=_string_or_none(raw.get("target")),
            cadence=_string_or_none(raw.get("cadence")),
            min_block_minutes=int(raw.get("min_block_minutes") or 0),
            max_block_minutes=int(raw.get("max_block_minutes") or 0),
            step_minutes=max(int(raw.get("step_minutes") or 0), 1),
            max_share_of_session=float(raw.get("max_share_of_session") or 0.0),
            allowed_primary_protocols=tuple(_normalized_str(item) for item in raw.get("allowed_primary_protocols") or [] if _normalized_str(item)),
        )

    protocols: dict[str, WeekWorkoutProtocol] = {}
    for key, raw in protocols_raw.items():
        if not isinstance(raw, dict):
            raise ValueError(f"Protocol '{key}' must be a mapping.")
        protocol_id = _normalized_str(raw.get("protocol_id") or key)
        addon_policy = _normalized_str(raw.get("addon_policy") or "NONE")
        if addon_policy not in addon_policies:
            raise ValueError(f"Protocol '{protocol_id}' references unknown add-on policy '{addon_policy}'.")
        protocols[protocol_id] = WeekWorkoutProtocol(
            protocol_id=protocol_id,
            intensity_domain=_normalized_str(raw.get("intensity_domain")),
            load_modality=_normalized_str(raw.get("load_modality") or "NONE"),
            protocol_type=_normalized_str(raw.get("protocol_type")),
            protocol_variant=_normalized_str(raw.get("protocol_variant") or protocol_id),
            allowed_day_roles=tuple(_normalized_str(item) for item in raw.get("allowed_day_roles") or [] if _normalized_str(item)),
            allowed_phase_intents=tuple(_normalized_phase_intent(item) for item in raw.get("allowed_phase_intents") or [] if _normalized_phase_intent(item)),
            allowed_week_roles=tuple(_normalized_str(item) for item in raw.get("allowed_week_roles") or [] if _normalized_str(item)),
            tags=frozenset(_normalized_tag(item) for item in raw.get("tags") or [] if _normalized_tag(item)),
            primary_axis=_normalized_axis(raw.get("primary_axis")),
            secondary_axis=_normalized_axis(raw.get("secondary_axis") or "NONE"),
            redistribution_rule=_string_or_none(raw.get("redistribution_rule")),
            addon_policy=addon_policy,
            parameters={k: v for k, v in raw.items() if k not in {
                "protocol_id",
                "intensity_domain",
                "load_modality",
                "protocol_type",
                "protocol_variant",
                "allowed_day_roles",
                "allowed_phase_intents",
                "allowed_week_roles",
                "tags",
                "primary_axis",
                "secondary_axis",
                "redistribution_rule",
                "addon_policy",
            }},
        )

    policy = data.get("selection_policy") or {}
    if not isinstance(policy, dict):
        raise ValueError("selection_policy must be a mapping.")
    by_phase_intent: dict[str, dict[str, list[str]]] = {}
    phase_raw = policy.get("by_phase_intent") or {}
    if not isinstance(phase_raw, dict):
        raise ValueError("selection_policy.by_phase_intent must be a mapping.")
    for phase_intent, mapping in phase_raw.items():
        if not isinstance(mapping, dict):
            raise ValueError(f"selection policy for phase_intent '{phase_intent}' must be a mapping.")
        by_phase_intent[_normalized_phase_intent(phase_intent)] = {
            _normalized_str(day_role): [_normalized_str(item) for item in items or [] if _normalized_str(item)]
            for day_role, items in mapping.items()
        }
    by_day_role_raw = policy.get("by_day_role") or {}
    if not isinstance(by_day_role_raw, dict):
        raise ValueError("selection_policy.by_day_role must be a mapping.")
    by_day_role = {
        _normalized_str(day_role): [_normalized_str(item) for item in items or [] if _normalized_str(item)]
        for day_role, items in by_day_role_raw.items()
    }
    unknown = {
        protocol_id
        for candidates in by_day_role.values()
        for protocol_id in candidates
        if protocol_id not in protocols
    } | {
        protocol_id
        for mapping in by_phase_intent.values()
        for candidates in mapping.values()
        for protocol_id in candidates
        if protocol_id not in protocols
    }
    if unknown:
        joined = ", ".join(sorted(unknown))
        raise ValueError(f"selection policy references unknown protocols: {joined}")
    if any("FREERIDE" in protocol.parameters or protocol.parameters.get("target_domain") == "FREERIDE" for protocol in protocols.values()):
        raise ValueError("freeride is not supported in week workout protocols.")
    return WeekWorkoutProtocolConfig(
        protocols=protocols,
        addon_policies=addon_policies,
        by_phase_intent=by_phase_intent,
        by_day_role=by_day_role,
    )


def protocol_is_allowed(
    protocol: WeekWorkoutProtocol,
    *,
    day_role: str,
    phase_intent: str,
    week_role: str,
    allowed_domains: set[str],
    allowed_modalities: set[str],
    is_anchor: bool,
) -> bool:
    """Return whether a protocol is legal in the active week context."""

    if protocol.allowed_day_roles and day_role.upper() not in protocol.allowed_day_roles:
        return False
    if protocol.allowed_phase_intents and "*" not in protocol.allowed_phase_intents and phase_intent.lower() not in protocol.allowed_phase_intents:
        return False
    if protocol.allowed_week_roles and "*" not in protocol.allowed_week_roles and week_role.upper() not in protocol.allowed_week_roles:
        return False
    if protocol.intensity_domain.upper() not in allowed_domains:
        return False
    if protocol.load_modality.upper() not in allowed_modalities:
        return False
    return not (is_anchor and day_role.upper() == "ENDURANCE" and "anchor" not in protocol.tags and "long_endurance" not in protocol.tags)


def _normalized_str(value: object) -> str:
    return str(value or "").strip().upper().replace(" ", "_")


def _normalized_phase_intent(value: object) -> str:
    return str(value or "").strip().lower()


def _normalized_tag(value: object) -> str:
    return str(value or "").strip().lower()


def _normalized_axis(value: object) -> str:
    return str(value or "").strip().lower() or "none"


def _string_or_none(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None
