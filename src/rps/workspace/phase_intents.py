"""Canonical planning semantic enums and normalization helpers."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from rps.workspace.intensity_domains import (
    CANONICAL_INTENSITY_DOMAINS,
    normalize_intensity_domain_list,
)

PHASE_TAXONOMY_VERSION = "canonical_phase_taxonomy_v1"

CANONICAL_SEASON_ARCHETYPES = ("none", "ceiling_first_durability")
CANONICAL_PHASE_TYPES = (
    "TRANSITION",
    "PREPARATION",
    "BASE",
    "BUILD",
    "PEAK",
    "TAPER",
    "RACE",
)
CANONICAL_PHASE_INTENTS = (
    "transition_recovery",
    "preparation_re_entry",
    "shortened_re_entry",
    "general_base",
    "aerobic_base",
    "strength_endurance_base",
    "sweet_spot_base",
    "vo2_build",
    "threshold_build",
    "sst_build",
    "durability_build",
    "specificity_build",
    "vlamax_lowering",
    "peak_sharpening",
    "taper_freshening",
    "race_execution",
)
CANONICAL_BUILD_SUBTYPES = (
    "vo2_build",
    "threshold_build",
    "sst_build",
    "durability_build",
    "specificity_build",
    "vlamax_lowering",
)

PHASE_TYPE_INTENT_MAP = {
    "TRANSITION": ("transition_recovery",),
    "PREPARATION": ("preparation_re_entry",),
    "BASE": (
        "shortened_re_entry",
        "general_base",
        "aerobic_base",
        "strength_endurance_base",
        "sweet_spot_base",
    ),
    "BUILD": CANONICAL_BUILD_SUBTYPES,
    "PEAK": ("peak_sharpening",),
    "TAPER": ("taper_freshening",),
    "RACE": ("race_execution",),
}

PHASE_INTENT_TO_TYPE = {
    intent: phase_type
    for phase_type, intents in PHASE_TYPE_INTENT_MAP.items()
    for intent in intents
}

LEGACY_PHASE_TYPE_MAP = {
    "base": "BASE",
    "build": "BUILD",
    "peak": "PEAK",
    "transition": "TRANSITION",
    "preparation": "PREPARATION",
    "prep": "PREPARATION",
    "foundation": "PREPARATION",
    "race": "RACE",
    "taper": "TAPER",
    "specialty": "BUILD",
}

LEGACY_PHASE_INTENT_MAP = {
    "recovery_reset": "transition_recovery",
    "shortened_re_entry": "shortened_re_entry",
    "shortened_consolidation": "general_base",
    "transition_consolidation": "preparation_re_entry",
    "foundation": "aerobic_base",
    "general_build": "threshold_build",
    "build_progression": "sst_build",
    "ceiling_support": "vo2_build",
    "transition_coupling": "durability_build",
    "durability_build": "durability_build",
    "specificity_build": "specificity_build",
    "b_event_rehearsal": "specificity_build",
    "peak_preparation": "peak_sharpening",
    "a_event_peak_taper": "taper_freshening",
}

RISKY_LEGACY_INTENT_MAPS = {"general_build", "build_progression", "transition_coupling"}

PHASE_TYPE_LABELS = {
    "TRANSITION": "Transition",
    "PREPARATION": "Preparation",
    "BASE": "Base",
    "BUILD": "Build",
    "PEAK": "Peak",
    "TAPER": "Taper",
    "RACE": "Race",
}

PHASE_INTENT_LABELS = {
    "transition_recovery": "Transition Recovery",
    "preparation_re_entry": "Preparation Re-entry",
    "shortened_re_entry": "Shortened Re-entry",
    "general_base": "General Base",
    "aerobic_base": "Aerobic Base",
    "strength_endurance_base": "Strength Endurance Base",
    "sweet_spot_base": "Sweet Spot Base",
    "vo2_build": "VO2 Build",
    "threshold_build": "Threshold Build",
    "sst_build": "SST Build",
    "durability_build": "Durability Build",
    "specificity_build": "Specificity Build",
    "vlamax_lowering": "VLamax Lowering",
    "peak_sharpening": "Peak Sharpening",
    "taper_freshening": "Taper Freshening",
    "race_execution": "Race Execution",
}

SEASON_ARCHETYPE_LABELS = {
    "none": "None",
    "ceiling_first_durability": "Ceiling-First Durability",
}


@dataclass(frozen=True)
class PhaseSemanticProfile:
    """Code-owned semantic contract for one canonical phase intent."""

    phase_type: str
    max_allowed_intensity_domains: tuple[str, ...]
    optional_intensity_domains: tuple[str, ...]
    forbidden_intensity_domains: tuple[str, ...]
    methodology_family: str
    threshold_role: str
    event_load_policy: str
    taper_policy: str
    writer_semantic_notes: tuple[str, ...]


PHASE_SEMANTIC_PROFILES: dict[str, PhaseSemanticProfile] = {
    "transition_recovery": PhaseSemanticProfile(
        phase_type="TRANSITION",
        max_allowed_intensity_domains=("RECOVERY", "ENDURANCE"),
        optional_intensity_domains=(),
        forbidden_intensity_domains=("SWEET_SPOT", "THRESHOLD", "VO2MAX"),
        methodology_family="recovery_first_reset",
        threshold_role="forbidden",
        event_load_policy="no_event_load_exception",
        taper_policy="not_applicable",
        writer_semantic_notes=(
            "Describe this phase as recovery-first and freshness-restoring, not as a build block.",
            "Do not imply threshold, VO2MAX, or heavy specificity work in this phase.",
        ),
    ),
    "preparation_re_entry": PhaseSemanticProfile(
        phase_type="PREPARATION",
        max_allowed_intensity_domains=("ENDURANCE", "TEMPO"),
        optional_intensity_domains=("TEMPO",),
        forbidden_intensity_domains=("SWEET_SPOT", "THRESHOLD", "VO2MAX"),
        methodology_family="structural_reentry",
        threshold_role="forbidden",
        event_load_policy="no_event_load_exception",
        taper_policy="not_applicable",
        writer_semantic_notes=(
            "Frame this phase as structural re-entry before full base work.",
            "Keep tempo optional and light; do not present threshold as part of the phase identity.",
        ),
    ),
    "shortened_re_entry": PhaseSemanticProfile(
        phase_type="BASE",
        max_allowed_intensity_domains=("ENDURANCE", "TEMPO", "SWEET_SPOT"),
        optional_intensity_domains=("TEMPO", "SWEET_SPOT"),
        forbidden_intensity_domains=("THRESHOLD", "VO2MAX"),
        methodology_family="compressed_reentry",
        threshold_role="forbidden",
        event_load_policy="no_event_load_exception",
        taper_policy="not_applicable",
        writer_semantic_notes=(
            "Frame this phase as controlled re-entry with recovery protection and continuity rebuild.",
            "If pressure work is mentioned, keep it subordinate to endurance continuity and freshness protection.",
        ),
    ),
    "general_base": PhaseSemanticProfile(
        phase_type="BASE",
        max_allowed_intensity_domains=("ENDURANCE", "TEMPO", "SWEET_SPOT"),
        optional_intensity_domains=("SWEET_SPOT",),
        forbidden_intensity_domains=("THRESHOLD", "VO2MAX"),
        methodology_family="broad_aerobic_base",
        threshold_role="suppressed",
        event_load_policy="no_event_load_exception",
        taper_policy="not_applicable",
        writer_semantic_notes=(
            "Describe this phase as general-base consolidation, not as preparation or threshold-led work.",
            "Keep threshold out of the phase allowance and out of the dominant narrative.",
        ),
    ),
    "aerobic_base": PhaseSemanticProfile(
        phase_type="BASE",
        max_allowed_intensity_domains=("ENDURANCE", "TEMPO"),
        optional_intensity_domains=("TEMPO",),
        forbidden_intensity_domains=("SWEET_SPOT", "THRESHOLD", "VO2MAX"),
        methodology_family="aerobic_groundwork",
        threshold_role="forbidden",
        event_load_policy="no_event_load_exception",
        taper_policy="not_applicable",
        writer_semantic_notes=(
            "Describe this phase as low-risk aerobic groundwork and routine-building.",
            "Do not imply threshold or VO2MAX progression in this phase.",
        ),
    ),
    "strength_endurance_base": PhaseSemanticProfile(
        phase_type="BASE",
        max_allowed_intensity_domains=("ENDURANCE", "TEMPO", "SWEET_SPOT"),
        optional_intensity_domains=("SWEET_SPOT",),
        forbidden_intensity_domains=("THRESHOLD", "VO2MAX"),
        methodology_family="torque_durability_base",
        threshold_role="suppressed",
        event_load_policy="no_event_load_exception",
        taper_policy="not_applicable",
        writer_semantic_notes=(
            "Describe this phase as structure- and torque-oriented base work with controlled pressure.",
            "Keep threshold work clearly secondary if it is mentioned at all.",
        ),
    ),
    "sweet_spot_base": PhaseSemanticProfile(
        phase_type="BASE",
        max_allowed_intensity_domains=("ENDURANCE", "TEMPO", "SWEET_SPOT"),
        optional_intensity_domains=(),
        forbidden_intensity_domains=("THRESHOLD", "VO2MAX"),
        methodology_family="subthreshold_base",
        threshold_role="suppressed",
        event_load_policy="no_event_load_exception",
        taper_policy="not_applicable",
        writer_semantic_notes=(
            "Describe this phase as sustainable sub-threshold base work, not as a threshold build.",
            "Do not imply frequent threshold or VO2MAX progression.",
        ),
    ),
    "vo2_build": PhaseSemanticProfile(
        phase_type="BUILD",
        max_allowed_intensity_domains=("ENDURANCE", "TEMPO", "VO2MAX"),
        optional_intensity_domains=("TEMPO",),
        forbidden_intensity_domains=("THRESHOLD",),
        methodology_family="aerobic_ceiling_build",
        threshold_role="suppressed",
        event_load_policy="event_load_support_only",
        taper_policy="not_applicable",
        writer_semantic_notes=(
            "Describe VO2MAX as the primary build objective when this intent is active.",
            "Do not rewrite this build into a threshold-led or durability-led block.",
        ),
    ),
    "threshold_build": PhaseSemanticProfile(
        phase_type="BUILD",
        max_allowed_intensity_domains=("ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"),
        optional_intensity_domains=("SWEET_SPOT",),
        forbidden_intensity_domains=("VO2MAX",),
        methodology_family="threshold_build",
        threshold_role="leading",
        event_load_policy="event_load_support_only",
        taper_policy="not_applicable",
        writer_semantic_notes=(
            "Describe threshold as the primary quality method in this build.",
            "Do not dilute this build into generic durability or random high-intensity density.",
        ),
    ),
    "sst_build": PhaseSemanticProfile(
        phase_type="BUILD",
        max_allowed_intensity_domains=("ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"),
        optional_intensity_domains=("THRESHOLD",),
        forbidden_intensity_domains=("VO2MAX",),
        methodology_family="extensive_subthreshold_build",
        threshold_role="secondary",
        event_load_policy="event_load_support_only",
        taper_policy="not_applicable",
        writer_semantic_notes=(
            "Describe this build as extensive sub-threshold capacity work with controlled pressure.",
            "If threshold is mentioned, keep it clearly secondary to SST-led work.",
        ),
    ),
    "durability_build": PhaseSemanticProfile(
        phase_type="BUILD",
        max_allowed_intensity_domains=("ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"),
        optional_intensity_domains=("THRESHOLD",),
        forbidden_intensity_domains=("VO2MAX",),
        methodology_family="durability_first_build",
        threshold_role="secondary",
        event_load_policy="event_load_support_only",
        taper_policy="not_applicable",
        writer_semantic_notes=(
            "Describe this build as durability-/tempo-led with hard-late, pre-fatigue, back-to-back, or long-ride pressure logic.",
            "Threshold may appear only as controlled support; do not describe the phase as threshold-leading.",
        ),
    ),
    "specificity_build": PhaseSemanticProfile(
        phase_type="BUILD",
        max_allowed_intensity_domains=("ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"),
        optional_intensity_domains=("THRESHOLD",),
        forbidden_intensity_domains=("VO2MAX",),
        methodology_family="event_specific_build",
        threshold_role="secondary",
        event_load_policy="event_load_replaces_anchor_not_adds",
        taper_policy="not_applicable",
        writer_semantic_notes=(
            "Describe this build as event-near specificity without taper semantics.",
            "When a B event is present, say that its load may replace a specificity anchor rather than adding to it.",
        ),
    ),
    "vlamax_lowering": PhaseSemanticProfile(
        phase_type="BUILD",
        max_allowed_intensity_domains=("ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"),
        optional_intensity_domains=("THRESHOLD",),
        forbidden_intensity_domains=("VO2MAX",),
        methodology_family="efficiency_build",
        threshold_role="secondary",
        event_load_policy="event_load_support_only",
        taper_policy="not_applicable",
        writer_semantic_notes=(
            "Describe this build as efficiency-oriented with controlled glycolytic suppression.",
            "Do not imply anaerobic or VO2MAX-heavy escalation.",
        ),
    ),
    "peak_sharpening": PhaseSemanticProfile(
        phase_type="PEAK",
        max_allowed_intensity_domains=("ENDURANCE", "TEMPO", "SWEET_SPOT"),
        optional_intensity_domains=("TEMPO", "SWEET_SPOT"),
        forbidden_intensity_domains=("THRESHOLD", "VO2MAX"),
        methodology_family="peak_sharpening",
        threshold_role="suppressed",
        event_load_policy="event_load_support_only",
        taper_policy="sharpening_without_new_load",
        writer_semantic_notes=(
            "Describe this phase as event-near sharpening and readiness preservation.",
            "Do not imply new threshold blocks, heavy reload language, or VO2MAX build work.",
        ),
    ),
    "taper_freshening": PhaseSemanticProfile(
        phase_type="TAPER",
        max_allowed_intensity_domains=("RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"),
        optional_intensity_domains=("TEMPO", "SWEET_SPOT"),
        forbidden_intensity_domains=("THRESHOLD", "VO2MAX"),
        methodology_family="freshness_first_taper",
        threshold_role="forbidden",
        event_load_policy="a_event_load_must_be_described_as_event_kj_not_training_reload",
        taper_policy="event_kj_inside_taper_requires_explicit_reduction_language",
        writer_semantic_notes=(
            "Describe this phase as freshness-first tapering with reduced pre-event training load.",
            "If the final week includes event kJ, explain that this is event work inside taper, not a normal reload week.",
        ),
    ),
    "race_execution": PhaseSemanticProfile(
        phase_type="RACE",
        max_allowed_intensity_domains=("RECOVERY", "ENDURANCE", "TEMPO"),
        optional_intensity_domains=("TEMPO",),
        forbidden_intensity_domains=("SWEET_SPOT", "THRESHOLD", "VO2MAX"),
        methodology_family="event_execution",
        threshold_role="forbidden",
        event_load_policy="event_execution_primary",
        taper_policy="event_window_only",
        writer_semantic_notes=(
            "Describe this phase as event execution and recovery control, not as another training build.",
            "Do not imply new load accumulation beyond the event window itself.",
        ),
    ),
}


@dataclass(frozen=True)
class NormalizedPhaseSemantics:
    """Normalized canonical phase semantics with migration trace information."""

    phase_type: str
    phase_intent: str
    build_subtype: str | None
    phase_taxonomy_version: str = PHASE_TAXONOMY_VERSION
    legacy_phase_intent_raw: str | None = None
    normalized_phase_intent: str | None = None
    normalization_source: str = "direct"
    normalization_warning: str | None = None


def _normalize_token(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def normalize_season_archetype(value: object) -> str:
    """Return a canonical season archetype."""

    text = _normalize_token(value)
    return text if text in CANONICAL_SEASON_ARCHETYPES else "none"


def normalize_phase_type(value: object) -> str:
    """Return a canonical phase type or an empty string."""

    raw = str(value or "").strip()
    if raw in CANONICAL_PHASE_TYPES:
        return raw
    token = _normalize_token(value)
    return LEGACY_PHASE_TYPE_MAP.get(token, "")


def normalize_phase_intent(value: object) -> str:
    """Return a canonical phase intent or an empty string."""

    token = _normalize_token(value)
    if token in CANONICAL_PHASE_INTENTS:
        return token
    return LEGACY_PHASE_INTENT_MAP.get(token, "")


def normalize_phase_intent_list(values: Iterable[object] | None) -> list[str]:
    """Return canonical phase intents preserving order and removing duplicates."""

    seen: set[str] = set()
    result: list[str] = []
    for value in values or []:
        normalized = normalize_phase_intent(value)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def phase_type_for_intent(value: object) -> str:
    """Return the canonical phase type for a canonical or legacy intent."""

    normalized = normalize_phase_intent(value)
    return PHASE_INTENT_TO_TYPE.get(normalized, "")


def normalize_build_subtype(
    value: object,
    *,
    phase_type: object | None = None,
    phase_intent: object | None = None,
) -> str:
    """Return a canonical build subtype or an empty string."""

    normalized = normalize_phase_intent(value)
    if normalized not in CANONICAL_BUILD_SUBTYPES:
        return ""
    normalized_phase_type = normalize_phase_type(phase_type) if phase_type is not None else ""
    normalized_phase_intent = normalize_phase_intent(phase_intent) if phase_intent is not None else ""
    if normalized_phase_type and normalized_phase_type != "BUILD":
        return ""
    if normalized_phase_intent and normalized != normalized_phase_intent:
        return ""
    return normalized


def normalize_phase_semantics(
    *,
    phase_type: object,
    phase_intent: object,
    build_subtype: object | None = None,
) -> NormalizedPhaseSemantics | None:
    """Return normalized canonical phase semantics or ``None`` if invalid."""

    raw_phase_type = str(phase_type or "").strip()
    raw_phase_intent = str(phase_intent or "").strip()
    normalized_phase_type = normalize_phase_type(phase_type)
    normalized_phase_intent = normalize_phase_intent(phase_intent)
    if not normalized_phase_intent:
        return None
    if not normalized_phase_type:
        normalized_phase_type = phase_type_for_intent(normalized_phase_intent)
    if not normalized_phase_type:
        return None
    legal_intents = PHASE_TYPE_INTENT_MAP.get(normalized_phase_type, ())
    if normalized_phase_intent not in legal_intents:
        return None
    normalized_build_subtype = ""
    if normalized_phase_type == "BUILD":
        candidate = build_subtype if build_subtype not in (None, "") else normalized_phase_intent
        normalized_build_subtype = normalize_build_subtype(
            candidate,
            phase_type=normalized_phase_type,
            phase_intent=normalized_phase_intent,
        )
        if normalized_build_subtype != normalized_phase_intent:
            return None
    elif build_subtype not in (None, "", "null"):
        return None

    raw_intent_token = _normalize_token(phase_intent)
    raw_type_token = _normalize_token(phase_type)
    normalization_source = "direct"
    if (
        raw_intent_token in LEGACY_PHASE_INTENT_MAP and raw_intent_token not in CANONICAL_PHASE_INTENTS
    ) or (
        raw_type_token in LEGACY_PHASE_TYPE_MAP and raw_phase_type not in CANONICAL_PHASE_TYPES
    ):
        normalization_source = "legacy_mapping"
    normalization_warning = None
    if raw_intent_token in RISKY_LEGACY_INTENT_MAPS:
        normalization_warning = (
            f"legacy phase_intent {raw_phase_intent!r} requires rollout validation against prior plan semantics."
        )
    legacy_phase_intent_raw = raw_phase_intent if normalization_source == "legacy_mapping" else None
    return NormalizedPhaseSemantics(
        phase_type=normalized_phase_type,
        phase_intent=normalized_phase_intent,
        build_subtype=normalized_build_subtype or None,
        legacy_phase_intent_raw=legacy_phase_intent_raw,
        normalized_phase_intent=normalized_phase_intent,
        normalization_source=normalization_source,
        normalization_warning=normalization_warning,
    )


def validate_phase_semantics(
    *,
    phase_type: object,
    phase_intent: object,
    build_subtype: object | None = None,
) -> list[str]:
    """Return validation errors for phase semantics."""

    errors: list[str] = []
    semantics = normalize_phase_semantics(
        phase_type=phase_type,
        phase_intent=phase_intent,
        build_subtype=build_subtype,
    )
    if semantics is None:
        normalized_type = normalize_phase_type(phase_type)
        normalized_intent = normalize_phase_intent(phase_intent)
        if not normalized_type:
            errors.append(f"Unknown phase_type {phase_type!r}.")
        if not normalized_intent:
            errors.append(f"Unknown phase_intent {phase_intent!r}.")
        if normalized_type and normalized_intent:
            errors.append(
                f"phase_intent {normalized_intent!r} is not legal for phase_type {normalized_type!r}."
            )
        if normalized_type == "BUILD":
            normalized_build_subtype = normalize_build_subtype(
                build_subtype,
                phase_type=normalized_type,
                phase_intent=normalized_intent,
            )
            if not normalized_build_subtype:
                errors.append("BUILD phases require build_subtype matching phase_intent.")
        elif build_subtype not in (None, "", "null"):
            errors.append("Non-BUILD phases must not define build_subtype.")
        return errors
    if semantics.phase_type == "BUILD" and semantics.build_subtype != semantics.phase_intent:
        errors.append("BUILD phases require build_subtype equal to phase_intent.")
    return errors


def semantic_profile_for_phase_intent(value: object) -> PhaseSemanticProfile | None:
    """Return the code-owned semantic profile for one canonical phase intent."""

    normalized = normalize_phase_intent(value)
    if not normalized:
        return None
    return PHASE_SEMANTIC_PROFILES.get(normalized)


def semantic_allowed_intensity_domains(value: object) -> list[str]:
    """Return the maximum allowed intensity-domain set for one phase intent."""

    profile = semantic_profile_for_phase_intent(value)
    if profile is None:
        return []
    return list(profile.max_allowed_intensity_domains)


def semantic_forbidden_intensity_domains(value: object) -> list[str]:
    """Return the default forbidden intensity-domain set for one phase intent."""

    profile = semantic_profile_for_phase_intent(value)
    if profile is None:
        return []
    return list(profile.forbidden_intensity_domains)


def season_phase_allowed_domains(*, phase_intent: object, season_allowed_domains: Iterable[object] | None) -> list[str]:
    """Return deterministic phase allowance from scenario authority intersected with semantic maxima."""

    season_domains = normalize_intensity_domain_list(list(season_allowed_domains or []))
    profile = semantic_profile_for_phase_intent(phase_intent)
    if profile is None:
        return []
    allowed_set = set(profile.max_allowed_intensity_domains)
    return [domain for domain in season_domains if domain in allowed_set]


def season_phase_forbidden_domains(*, phase_intent: object, season_allowed_domains: Iterable[object] | None) -> list[str]:
    """Return deterministic forbidden domains for one phase intent under scenario authority."""

    allowed = set(season_phase_allowed_domains(phase_intent=phase_intent, season_allowed_domains=season_allowed_domains))
    profile = semantic_profile_for_phase_intent(phase_intent)
    if profile is None:
        return []
    explicit = [domain for domain in profile.forbidden_intensity_domains if domain not in allowed]
    semantic_max = set(profile.max_allowed_intensity_domains)
    blocked_by_profile = [
        domain
        for domain in CANONICAL_INTENSITY_DOMAINS
        if domain not in {"NONE"} and domain not in semantic_max and domain not in allowed
    ]
    result: list[str] = []
    seen: set[str] = set()
    for domain in [*explicit, *blocked_by_profile]:
        if domain not in seen:
            seen.add(domain)
            result.append(domain)
    return result


def phase_semantic_contract_payload(*, phase_intent: object) -> dict[str, object]:
    """Return the structured semantic-contract payload used in Season bundles."""

    profile = semantic_profile_for_phase_intent(phase_intent)
    if profile is None:
        return {}
    return {
        "methodology_family": profile.methodology_family,
        "threshold_role": profile.threshold_role,
        "event_load_policy": profile.event_load_policy,
        "taper_policy": profile.taper_policy,
        "writer_semantic_notes": list(profile.writer_semantic_notes),
    }


def phase_intent_label(value: object) -> str:
    """Return a human-readable phase-intent label."""

    normalized = normalize_phase_intent(value)
    if normalized:
        return PHASE_INTENT_LABELS.get(normalized, normalized.replace("_", " ").title())
    return str(value or "")


def phase_type_label(value: object) -> str:
    """Return a human-readable phase-type label."""

    normalized = normalize_phase_type(value)
    if normalized:
        return PHASE_TYPE_LABELS.get(normalized, normalized.title())
    return str(value or "")


def season_archetype_label(value: object) -> str:
    """Return a human-readable season-archetype label."""

    normalized = normalize_season_archetype(value)
    return SEASON_ARCHETYPE_LABELS.get(normalized, normalized.replace("_", " ").title())
