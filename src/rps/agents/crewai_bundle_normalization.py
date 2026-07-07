"""Season/phase bundle normalization and semantic sanitization for CrewAI planning."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from rps.agents.output_normalization import (
    _replace_canonical_trace_entries_from_documents,
    extract_loaded_document,
    normalize_phase_structure_upstream_constraints,
)
from rps.crewai_runtime.guardrails import current_guardrail_runtime_context
from rps.evidence.library import canonical_reference_locator
from rps.planning.contracts import derive_expected_average_weekly_kj_range
from rps.planning.phase_authority import (
    format_role_week_load_bands,
    normalize_role_week_load_bands,
    role_week_band_by_week,
)
from rps.workspace.artifact_metadata import normalize_trace_reference
from rps.workspace.intensity_domains import normalize_intensity_domain_list
from rps.workspace.phase_intents import (
    PHASE_TAXONOMY_VERSION,
    normalize_phase_semantics,
    phase_semantic_contract_payload,
    phase_type_for_intent,
    season_phase_allowed_domains,
    season_phase_forbidden_domains,
    semantic_allowed_load_modalities,
    validate_phase_semantics,
)
from rps.workspace.types import ArtifactType

JsonMap = dict[str, Any]

_SEASON_FORBIDDEN_DOMAIN_POSITIVE_CUES: tuple[str, ...] = (
    "appears",
    "support",
    "remains secondary",
    "kept secondary",
    "maintenance",
    "led",
)
_SEASON_FORBIDDEN_DOMAIN_NEGATIVE_CUES: tuple[str, ...] = (
    "remains excluded",
    "is excluded",
    "remains forbidden",
    "is forbidden",
    "suppressed",
    "remains suppressed",
    "excluded",
    "forbidden",
)

_SEASON_PLAN_REQUIRED_TRACE_DATA_ARTIFACTS: tuple[ArtifactType, ...] = (
    ArtifactType.ATHLETE_PROFILE,
    ArtifactType.KPI_PROFILE,
    ArtifactType.AVAILABILITY,
    ArtifactType.LOGISTICS,
    ArtifactType.ZONE_MODEL,
)
_SEASON_PLAN_REQUIRED_TRACE_EVENT_ARTIFACTS: tuple[ArtifactType, ...] = (
    ArtifactType.PLANNING_EVENTS,
)


def _as_map(value: object) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _as_int(value: object) -> int | None:
    """Return an integer for int-like values, otherwise ``None``."""

    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            return None
    return None


def _canonicalize_phase_semantics_for_bundle(
    *,
    phase_type: object,
    phase_intent: object,
    build_subtype: object | None = None,
    warnings: list[str] | None = None,
    warning_prefix: str | None = None,
) -> tuple[str, str, str | None]:
    """Return canonical phase semantics for normalized Season/Phase bundles.

    The normalized bundle is Python-owned. When a valid canonical phase intent is
    paired with the wrong phase type, prefer the canonical type for that intent
    and record a warning. Unknown or unrecoverable values remain untouched so
    downstream contract validation can fail closed.
    """

    raw_build_subtype = str(build_subtype).strip() if isinstance(build_subtype, str) and str(build_subtype).strip() else None

    semantics = normalize_phase_semantics(
        phase_type=phase_type,
        phase_intent=phase_intent,
        build_subtype=build_subtype,
    )
    if semantics is not None:
        return semantics.phase_type, semantics.phase_intent, semantics.build_subtype

    canonical_phase_type = phase_type_for_intent(phase_intent)
    if not canonical_phase_type:
        return str(phase_type or ""), str(phase_intent or ""), raw_build_subtype

    semantics = normalize_phase_semantics(
        phase_type=canonical_phase_type,
        phase_intent=phase_intent,
        build_subtype=build_subtype,
    )
    if semantics is None:
        return str(phase_type or ""), str(phase_intent or ""), raw_build_subtype

    if warnings is not None:
        prefix = f"{warning_prefix}: " if warning_prefix else ""
        warning = (
            f"{prefix}canonicalized phase_type from {phase_type!r} to {canonical_phase_type!r} "
            f"for phase_intent {phase_intent!r}."
        )
        if warning not in warnings:
            warnings.append(warning)
    return semantics.phase_type, semantics.phase_intent, semantics.build_subtype


def _trace_reference_from_payload(artifact_type: ArtifactType, payload: object) -> JsonMap | None:
    """Return a normalized trace reference for a loaded artifact payload when possible."""

    if not isinstance(payload, dict):
        return None
    meta = _as_map(payload.get("meta"))
    version_key = str(meta.get("version_key") or "").strip()
    run_id = str(meta.get("run_id") or "").strip()
    if not version_key or not run_id:
        return None
    reference = normalize_trace_reference(
        {
            "artifact": artifact_type.value,
            "version": meta.get("version"),
            "schema_version": meta.get("schema_version"),
            "version_key": version_key,
            "run_id": run_id,
        }
    )
    return {key: str(value) for key, value in reference.items()} if reference is not None else None


def _merge_trace_reference_lists(existing: object, additions: list[JsonMap], *, allowed: set[str]) -> list[JsonMap]:
    """Merge trace references while preserving order and removing duplicates."""

    normalized: list[JsonMap] = []
    seen_indices: dict[tuple[str, str], int] = {}

    def _append(entry: object) -> None:
        if not isinstance(entry, dict):
            return
        artifact = str(entry.get("artifact") or "").strip().upper()
        if artifact not in allowed:
            return
        reference = normalize_trace_reference(entry)
        if reference is None:
            return
        token = (
            str(reference.get("artifact") or ""),
            str(reference.get("version_key") or ""),
        )
        existing_index = seen_indices.get(token)
        if existing_index is not None:
            normalized[existing_index] = {key: str(value) for key, value in reference.items()}
            return
        seen_indices[token] = len(normalized)
        normalized.append({key: str(value) for key, value in reference.items()})

    if isinstance(existing, list):
        for item in existing:
            _append(item)
    for item in additions:
        _append(item)
    return normalized


def _normalize_publication_link(title: object, link: object) -> str:
    """Return a verified canonical publication link when the local library knows it."""

    canonical_link = canonical_reference_locator(title)
    if canonical_link:
        return canonical_link
    return ""


def _fill_season_plan(document: JsonMap) -> JsonMap:
    """Normalize common SEASON_PLAN placement issues."""

    if not isinstance(document, dict):
        return document
    meta = document.get("meta") or {}
    if str(meta.get("artifact_type", "")).upper() != "SEASON_PLAN":
        return document
    if not meta.get("data_confidence"):
        meta["data_confidence"] = "UNKNOWN"
    document["meta"] = meta
    data = document.get("data") or {}
    if not isinstance(data, dict):
        return document
    if "explicit_forbidden_content" not in data or not isinstance(
        data.get("explicit_forbidden_content"), list
    ):
        data["explicit_forbidden_content"] = [
            "phase definitions (phase plans)",
            "weekly schedules",
            "day-by-day structure",
            "workouts or interval prescriptions",
            "numeric progression rules",
            "daily or session-level kJ targets",
        ]
    if "self_check" not in data or not isinstance(data.get("self_check"), dict):
        data["self_check"] = {
            "planning_horizon_is_at_least_8_weeks": True,
            "every_phase_defines_weekly_kj_corridor": True,
            "every_phase_includes_kj_per_kg_guardrails_and_reference_mass": True,
            "every_phase_maps_to_cycle_and_deload_intent": True,
            "every_phase_includes_narrative_and_metabolic_focus": True,
            "every_phase_includes_evaluation_focus_and_exit_assumptions": True,
            "season_load_envelope_and_assumptions_documented": True,
            "principles_and_scientific_foundation_documented": True,
            "allowed_forbidden_domains_listed": True,
            "no_phase_or_week_planning_content": True,
            "header_includes_implements_iso_week_range_trace": True,
        }
    document["data"] = data
    return document


def _season_has_positive_forbidden_domain_mention(text: object, domain: str) -> bool:
    """Return True when text frames a forbidden domain positively."""

    normalized = str(text or "").strip().lower()
    token = str(domain or "").strip().lower()
    if not normalized or not token or token not in normalized:
        return False
    if (
        f"no {token}" in normalized
        or f"without {token}" in normalized
        or any(f"{token} {cue}" in normalized for cue in _SEASON_FORBIDDEN_DOMAIN_NEGATIVE_CUES)
    ):
        return False
    return any(
        f"{token} {cue}" in normalized or f"{token}-{cue}" in normalized
        for cue in _SEASON_FORBIDDEN_DOMAIN_POSITIVE_CUES
    )


def _humanize_intensity_domain(domain: str) -> str:
    return str(domain).strip().lower().replace("_", " ")


def _join_humanized_domains(domains: list[str]) -> str:
    items = [_humanize_intensity_domain(item) for item in domains if str(item).strip()]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _season_legal_domain_focus_phrase(allowed_domains: object) -> str:
    """Return a compact positive framing that stays inside legal domains."""

    domains = [
        item
        for item in normalize_intensity_domain_list(allowed_domains)
        if item not in {"NONE", "RECOVERY"}
    ]
    if not domains:
        return "recovery-protected aerobic continuity"
    primary = _humanize_intensity_domain(domains[0])
    secondary = domains[1:]
    if not secondary:
        return f"{primary}-led work"
    return f"{primary}-led work with controlled {_join_humanized_domains(secondary)} support"


def _season_phase_narrative_replacements(
    *,
    phase_type: object,
    phase_intent: object,
    allowed_domains: object,
) -> JsonMap:
    """Return deterministic legal-domain narrative replacements for one phase."""

    intent = str(phase_intent or "").strip()
    phase_type_text = str(phase_type or "").strip().title() or "Phase"
    focus_phrase = _season_legal_domain_focus_phrase(allowed_domains)
    replacements: JsonMap = {
        "narrative": f"{phase_type_text} work stays inside {focus_phrase}.",
        "metabolic_focus": f"{focus_phrase.capitalize()} aligned to the active phase intent.",
        "typical_focus": "Legal-domain execution aligned to the active phase role and recovery context.",
        "intensity_distribution": f"{focus_phrase.capitalize()} with no reliance on forbidden-domain progression.",
        "expected_adaptations": [
            f"Improved execution through {focus_phrase} aligned to the active phase intent."
        ],
    }
    if intent in {"transition_recovery", "preparation_re_entry", "shortened_re_entry"}:
        replacements.update(
            {
                "narrative": "Recovery-protected re-entry rebuilding continuity, freshness, and stable routine.",
                "metabolic_focus": "Aerobic continuity and freshness restoration without build-led escalation.",
                "typical_focus": "Routine rebuild, recovery protection, and low-risk continuity.",
                "intensity_distribution": "Recovery-protected endurance continuity with only light legal support.",
                "expected_adaptations": [
                    "Improved freshness, continuity, and stable return to legal training density."
                ],
            }
        )
    elif intent in {"general_base", "aerobic_base", "strength_endurance_base", "sweet_spot_base"}:
        replacements.update(
            {
                "narrative": f"Base work consolidates durable aerobic support through {focus_phrase}.",
                "metabolic_focus": f"Aerobic base support through {focus_phrase}.",
                "typical_focus": "Sustainable base loading, continuity, and durable routine-building.",
                "intensity_distribution": f"{focus_phrase.capitalize()} supporting broad base development.",
                "expected_adaptations": [
                    f"Improved aerobic support and sustainable routine through {focus_phrase}."
                ],
            }
        )
    elif intent == "vo2_build":
        replacements.update(
            {
                "narrative": f"Build work raises ceiling and repeatability through {focus_phrase}.",
                "metabolic_focus": f"Aerobic ceiling support through {focus_phrase}.",
                "typical_focus": "Ceiling-oriented quality with recovery-bounded execution.",
                "intensity_distribution": f"{focus_phrase.capitalize()} with recovery-bounded ceiling support.",
                "expected_adaptations": [
                    f"Improved ceiling support and repeatable quality through {focus_phrase}."
                ],
            }
        )
    elif intent == "threshold_build":
        replacements.update(
            {
                "narrative": f"Build work improves sustained power and repeatable structure through {focus_phrase}.",
                "metabolic_focus": f"Sustained-power support through {focus_phrase}.",
                "typical_focus": "Repeatable steady pressure and sustained-power tolerance.",
                "intensity_distribution": f"{focus_phrase.capitalize()} supporting sustained-power build logic.",
                "expected_adaptations": [
                    f"Improved sustained power and repeatable load tolerance through {focus_phrase}."
                ],
            }
        )
    elif intent == "sst_build":
        replacements.update(
            {
                "narrative": f"Build work develops extensive sub-threshold capacity through {focus_phrase}.",
                "metabolic_focus": f"Extensive sub-threshold support through {focus_phrase}.",
                "typical_focus": "Steady sub-threshold capacity and controlled pressure tolerance.",
                "intensity_distribution": f"{focus_phrase.capitalize()} with extensive sub-threshold emphasis.",
                "expected_adaptations": [
                    f"Improved sub-threshold capacity and steady pressure tolerance through {focus_phrase}."
                ],
            }
        )
    elif intent == "durability_build":
        replacements.update(
            {
                "narrative": (
                    f"Durability-led build emphasizing fatigue resistance, hard-late stability, preload, "
                    f"and long-ride kJ tolerance through {focus_phrase}."
                ),
                "metabolic_focus": f"Durability-first pressure through {focus_phrase}.",
                "typical_focus": "Hard-late stability, preload, back-to-back resilience, and long-ride tolerance.",
                "intensity_distribution": f"{focus_phrase.capitalize()} supporting durability-first build logic.",
                "expected_adaptations": [
                    f"Improved fatigue resistance and long-ride stability through {focus_phrase}."
                ],
            }
        )
    elif intent == "specificity_build":
        replacements.update(
            {
                "narrative": (
                    f"Event-near specificity build emphasizing pacing, fueling, terrain handling, "
                    f"and logistics through {focus_phrase}."
                ),
                "metabolic_focus": f"Event-near specificity through {focus_phrase}.",
                "typical_focus": "Pacing, fueling, terrain handling, and logistics under event-near specificity.",
                "intensity_distribution": f"{focus_phrase.capitalize()} supporting event-near specificity.",
                "expected_adaptations": [
                    f"Improved pacing, fueling, and terrain-specific execution through {focus_phrase}."
                ],
            }
        )
    elif intent == "vlamax_lowering":
        replacements.update(
            {
                "narrative": f"Efficiency-oriented build emphasizing controlled pressure through {focus_phrase}.",
                "metabolic_focus": f"Efficiency support through {focus_phrase}.",
                "typical_focus": "Controlled glycolytic demand and durable efficiency work.",
                "intensity_distribution": f"{focus_phrase.capitalize()} with efficiency-oriented pressure.",
                "expected_adaptations": [
                    f"Improved durable efficiency and controlled pressure tolerance through {focus_phrase}."
                ],
            }
        )
    elif intent == "peak_sharpening":
        replacements.update(
            {
                "narrative": "Peak sharpening preserves readiness, specificity, and freshness without new build escalation.",
                "metabolic_focus": "Readiness preservation and event-near sharpening inside legal domains.",
                "typical_focus": "Sharpening, freshness protection, and event-near readiness.",
                "intensity_distribution": f"{focus_phrase.capitalize()} with sharpening-only intent.",
                "expected_adaptations": [
                    "Improved event-near readiness and sharpening without new build-style escalation."
                ],
            }
        )
    elif intent == "taper_freshening":
        replacements.update(
            {
                "narrative": "Freshness-first taper preserves readiness while reducing pre-event training load.",
                "metabolic_focus": "Freshness preservation and event-near readiness.",
                "typical_focus": "Reduced load, freshness protection, and event-near readiness.",
                "intensity_distribution": f"{focus_phrase.capitalize()} with taper-contained sharpening only.",
                "expected_adaptations": [
                    "Improved freshness and event-near readiness without new build-style escalation."
                ],
            }
        )
    elif intent == "race_execution":
        replacements.update(
            {
                "narrative": "Race-execution work centers on pacing, fueling, and logistics for the target event.",
                "metabolic_focus": "Execution readiness and event-specific pacing control.",
                "typical_focus": "Pacing, fueling, logistics, and execution stability.",
                "intensity_distribution": f"{focus_phrase.capitalize()} serving event-execution demands.",
                "expected_adaptations": [
                    "Improved event-execution stability, pacing, and fueling discipline."
                ],
            }
        )
    return replacements


def _sanitize_season_phase_narrative_fields(
    phase: JsonMap,
    *,
    phase_type: object,
    phase_intent: object,
    allowed_domains: object,
    forbidden_domains: object,
    justification: JsonMap | None = None,
) -> None:
    """Strip or replace positive forbidden-domain prose with legal intent-coherent text."""

    forbidden = normalize_intensity_domain_list(forbidden_domains)
    if not forbidden:
        return
    replacements = _season_phase_narrative_replacements(
        phase_type=phase_type,
        phase_intent=phase_intent,
        allowed_domains=allowed_domains,
    )

    def _has_forbidden_positive(text: object) -> bool:
        return any(_season_has_positive_forbidden_domain_mention(text, domain) for domain in forbidden)

    narrative = str(phase.get("narrative") or "").strip()
    if _has_forbidden_positive(narrative):
        phase["narrative"] = replacements["narrative"]

    overview = _as_map(phase.get("overview"))
    metabolic_focus = str(overview.get("metabolic_focus") or "").strip()
    if _has_forbidden_positive(metabolic_focus):
        overview["metabolic_focus"] = replacements["metabolic_focus"]

    expected_adaptations = [
        str(item).strip()
        for item in _as_list(overview.get("expected_adaptations"))
        if str(item).strip()
    ]
    if expected_adaptations:
        adaptations_changed = False
        kept_adaptations = [item for item in expected_adaptations if not _has_forbidden_positive(item)]
        if len(kept_adaptations) != len(expected_adaptations) and not kept_adaptations:
            kept_adaptations = list(replacements["expected_adaptations"])
            adaptations_changed = True
        if len(kept_adaptations) != len(expected_adaptations):
            adaptations_changed = True
        if adaptations_changed:
            overview["expected_adaptations"] = kept_adaptations

    non_negotiables = [
        str(item).strip()
        for item in _as_list(overview.get("non_negotiables"))
        if str(item).strip()
    ]
    if non_negotiables:
        kept_non_negotiables = [item for item in non_negotiables if not _has_forbidden_positive(item)]
        if len(kept_non_negotiables) != len(non_negotiables):
            for domain in forbidden:
                line = f"{domain} remains forbidden in this phase identity."
                if line not in kept_non_negotiables:
                    kept_non_negotiables.append(line)
            overview["non_negotiables"] = kept_non_negotiables
    if overview:
        phase["overview"] = overview

    structural_emphasis = _as_map(phase.get("structural_emphasis"))
    typical_focus = str(structural_emphasis.get("typical_focus") or "").strip()
    if _has_forbidden_positive(typical_focus):
        structural_emphasis["typical_focus"] = replacements["typical_focus"]
    if structural_emphasis:
        phase["structural_emphasis"] = structural_emphasis

    if justification is not None:
        intensity_distribution = str(justification.get("intensity_distribution") or "").strip()
        if _has_forbidden_positive(intensity_distribution):
            justification["intensity_distribution"] = replacements["intensity_distribution"]


def _derive_season_semantic_notes(*, planning_bundle: JsonMap) -> list[str]:
    """Return deterministic season-level notes that the writer must preserve."""

    notes: list[str] = []
    event_priority = _as_map(planning_bundle.get("event_priority"))
    primary_a_events = [str(item).strip() for item in _as_list(event_priority.get("primary_a_events")) if str(item).strip()]
    if primary_a_events:
        notes.append(
            "Frame the season objective against the primary A event(s): "
            + ", ".join(primary_a_events)
            + ". If longer-distance durability reserve is mentioned, present it as support for the A event rather than a conflicting primary target."
        )
    notes.append(
        "Use durability-first, ceiling-constrained wording. Do not describe the season as ceiling-first when VO2MAX authority is absent or forbidden."
    )
    notes.append(
        "B-event rehearsal load must replace a specificity anchor when noted, not add a second full anchor on top of the normal build load."
    )
    notes.append(
        "When taper weeks include event kJ, describe that load as event work inside taper with reduced pre-event training load, not as a normal reload week."
    )
    notes.append(
        "Within taper_freshening, LOAD_1, LOAD_2, and RELOAD are load-band labels only; they do not authorize Build-like workout selection."
    )
    return notes


def _derive_season_load_envelope_counts(*, phase_blueprints: list[JsonMap]) -> tuple[int, int]:
    """Return deterministic high-load and deload/low-load week counts.

    Counts are derived from canonical cadence-week roles so the persisted season
    envelope is complete even when the draft bundle omits these summary fields.
    """

    high_load_roles = {"LOAD_2", "RELOAD", "SHORTENED_RELOAD"}
    low_load_roles = {
        "DELOAD",
        "MINI_RESET",
        "SHORTENED_MINI_RESET",
        "SHORTENED_RE_ENTRY",
        "TRANSITION",
        "RECOVERY",
    }
    high_load_weeks = 0
    low_load_weeks = 0
    for blueprint in phase_blueprints:
        for role in _as_list(_as_map(blueprint).get("cadence_week_roles")):
            normalized_role = str(role or "").strip().upper().replace(" ", "_")
            if normalized_role in high_load_roles:
                high_load_weeks += 1
            if normalized_role in low_load_roles:
                low_load_weeks += 1
    return high_load_weeks, low_load_weeks


def _normalize_progression_trace(value: object) -> list[str]:
    """Normalize deterministic progression trace payloads to list form."""

    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, dict):
        return [f"{key}: {val}" for key, val in value.items() if str(val).strip()]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def _append_sentence(base: object, sentence: str) -> str:
    """Append one sentence to a text field if it is not already present."""

    existing = str(base or "").strip()
    addition = sentence.strip()
    if not addition:
        return existing
    if addition in existing:
        return existing
    if not existing:
        return addition
    separator = "" if existing.endswith((" ", "\n")) else " "
    return f"{existing}{separator}{addition}"


def _append_unique_item(items: object, item: str) -> list[str]:
    """Return a stripped string list with one unique appended item."""

    normalized = [str(entry).strip() for entry in _as_list(items) if str(entry).strip()]
    if item not in normalized:
        normalized.append(item)
    return normalized


def _format_role_week_guardrail_sentence(entries: Sequence[object]) -> str:
    """Render structured role-week bands into one audit sentence."""

    rendered = format_role_week_load_bands(entries)
    if not rendered:
        return ""
    return (
        "Inherited role-week load guardrails (season-level, not week prescriptions): "
        + "; ".join(rendered)
        + "."
    )


def _season_event_constraint_text(event_type: str) -> str:
    """Return deterministic season-phase event handling text for one event type."""

    normalized = str(event_type or "").strip().upper()
    if normalized == "A":
        return "A event receives dedicated taper-contained event handling."
    if normalized == "B":
        return (
            "B event receives rehearsal/minor-load-adjustment handling only and may replace "
            "a planned specificity anchor rather than adding a second peak."
        )
    return "C event remains inside normal structure without taper."


def _extract_km_values(text: object) -> list[int]:
    """Return kilometer values mentioned in a free-text objective or event label."""

    values: list[int] = []
    for match in re.finditer(r"(\d{2,4})(?:\s*[-/]\s*(\d{2,4}))?\s*km", str(text or ""), flags=re.IGNORECASE):
        first = int(match.group(1))
        second = match.group(2)
        values.append(first)
        if second is not None:
            values.append(int(second))
    return values


def _derive_objective_event_mismatch_warning(*, season_objective: object, a_events: list[JsonMap]) -> str | None:
    """Return a non-blocking warning when objective distance conflicts with the A event."""

    objective = str(season_objective or "").strip()
    objective_km = _extract_km_values(objective)
    if not objective or not objective_km or not a_events:
        return None
    highest_a_event = max(
        a_events,
        key=lambda item: (
            str(item.get("date") or ""),
            str(item.get("week") or ""),
            str(item.get("name") or ""),
        ),
    )
    event_parts = [
        str(part).strip()
        for part in (highest_a_event.get("name"), highest_a_event.get("date"))
        if str(part or "").strip()
    ]
    event_label = " ".join(event_parts).strip()
    event_km = _extract_km_values(event_label)
    if not event_km:
        return None
    if any(abs(event_distance - objective_distance) <= 25 for event_distance in event_km for objective_distance in objective_km):
        return None
    event_distance_label = "/".join(str(value) for value in event_km)
    objective_distance_label = "/".join(str(value) for value in objective_km)
    event_name = str(highest_a_event.get("name") or "the highest-priority A event").strip()
    return (
        "Warning: primary season objective references "
        f"{objective_distance_label} km demands while {event_name} targets approximately "
        f"{event_distance_label} km. Reconcile the objective upstream/input-side if this is intentional."
    )


def _normalize_final_season_plan_semantics(document: JsonMap) -> JsonMap:
    """Apply code-owned season semantics to the final SEASON_PLAN document."""

    if not isinstance(document, dict):
        return document
    meta = _as_map(document.get("meta"))
    if str(meta.get("artifact_type") or "").upper() != "SEASON_PLAN":
        return document
    context = current_guardrail_runtime_context()
    season_phase_load_context = _as_map(context.get("season_phase_load_context"))
    selected_scenario_contract = _as_map(context.get("selected_scenario_contract"))
    approved_bundle = _as_map(context.get("approved_planning_bundle"))
    trace_data_additions = [
        ref
        for artifact_type in _SEASON_PLAN_REQUIRED_TRACE_DATA_ARTIFACTS
        for ref in [_trace_reference_from_payload(artifact_type, context.get(f"{artifact_type.value.lower()}_payload"))]
        if ref is not None
    ]
    trace_event_additions = [
        ref
        for artifact_type in _SEASON_PLAN_REQUIRED_TRACE_EVENT_ARTIFACTS
        for ref in [_trace_reference_from_payload(artifact_type, context.get(f"{artifact_type.value.lower()}_payload"))]
        if ref is not None
    ]
    meta["trace_data"] = _merge_trace_reference_lists(
        meta.get("trace_data"),
        trace_data_additions,
        allowed={artifact.value for artifact in _SEASON_PLAN_REQUIRED_TRACE_DATA_ARTIFACTS}
        | {"ACTIVITIES_ACTUAL", "ACTIVITIES_TREND"},
    )
    meta["trace_events"] = _merge_trace_reference_lists(
        meta.get("trace_events"),
        trace_event_additions,
        allowed={artifact.value for artifact in _SEASON_PLAN_REQUIRED_TRACE_EVENT_ARTIFACTS},
    )
    trace_upstream_artifacts = {
        str(_as_map(item).get("artifact") or "").strip().upper()
        for item in _as_list(meta.get("trace_upstream"))
        if str(_as_map(item).get("artifact") or "").strip()
    } | {"SEASON_SCENARIO_SELECTION", "SEASON_SCENARIOS"}
    trace_upstream = _replace_canonical_trace_entries_from_documents(
        meta.get("trace_upstream"),
        documents=[
            ("SEASON_SCENARIO_SELECTION", _as_map(context.get("season_scenario_selection_payload"))),
            ("SEASON_SCENARIOS", _as_map(context.get("season_scenarios_payload"))),
        ],
    )
    meta["trace_upstream"] = _merge_trace_reference_lists(
        trace_upstream,
        [],
        allowed=trace_upstream_artifacts,
    )
    data = _as_map(document.get("data"))
    if selected_scenario_contract:
        data["selected_scenario_contract"] = selected_scenario_contract
    phases = [_as_map(item) for item in _as_list(data.get("phases"))]
    deterministic_by_phase_id = {
        str(_as_map(item).get("phase_id") or ""): _as_map(item)
        for item in _as_list(season_phase_load_context.get("phases"))
        if str(_as_map(item).get("phase_id") or "").strip()
    }
    bundle_by_phase_id = {
        str(_as_map(item).get("phase_id") or ""): _as_map(item)
        for item in _as_list(approved_bundle.get("phase_blueprints"))
        if str(_as_map(item).get("phase_id") or "").strip()
    }
    all_a_events: list[JsonMap] = []
    phase_justifications = {
        str(_as_map(item).get("phase_id") or ""): _as_map(item)
        for item in _as_list(_as_map(data.get("justification")).get("phase_justifications"))
        if str(_as_map(item).get("phase_id") or "").strip()
    }
    for phase in phases:
        phase_id = str(phase.get("phase_id") or "").strip()
        deterministic = deterministic_by_phase_id.get(phase_id, {})
        approved = bundle_by_phase_id.get(phase_id, {})
        phase_intent = deterministic.get("phase_intent") or phase.get("phase_intent")
        phase_type = deterministic.get("phase_type") or phase.get("phase_type")
        build_subtype = deterministic.get("build_subtype")
        if build_subtype is None:
            build_subtype = phase.get("build_subtype")
        phase["phase_type"] = phase_type
        phase["phase_intent"] = phase_intent
        phase["build_subtype"] = build_subtype
        justification = phase_justifications.get(phase_id)

        semantics = _as_map(phase.get("allowed_forbidden_semantics"))
        phase["allowed_forbidden_semantics"] = semantics
        semantics["allowed_intensity_domains"] = list(
            approved.get("allowed_domains")
            or season_phase_allowed_domains(
                phase_intent=phase_intent,
                season_allowed_domains=season_phase_load_context.get("season_allowed_intensity_domains"),
            )
        )
        semantics["forbidden_intensity_domains"] = list(
            approved.get("forbidden_domains")
            or season_phase_forbidden_domains(
                phase_intent=phase_intent,
                season_allowed_domains=season_phase_load_context.get("season_allowed_intensity_domains"),
            )
        )
        semantics["allowed_load_modalities"] = list(
            approved.get("allowed_load_modalities") or semantic_allowed_load_modalities(phase_intent)
        )
        _sanitize_season_phase_narrative_fields(
            phase,
            phase_type=phase_type,
            phase_intent=phase_intent,
            allowed_domains=semantics.get("allowed_intensity_domains"),
            forbidden_domains=semantics.get("forbidden_intensity_domains"),
            justification=justification,
        )

        structured_role_week_bands = normalize_role_week_load_bands(
            _as_list(deterministic.get("role_week_load_bands"))
        )
        if structured_role_week_bands:
            phase["role_week_load_bands"] = structured_role_week_bands
        role_week_sentence = _format_role_week_guardrail_sentence(structured_role_week_bands)
        weekly_kj = _as_map(_as_map(phase.get("weekly_load_corridor")).get("weekly_kj"))
        if weekly_kj:
            weekly_kj["notes"] = _append_sentence(weekly_kj.get("notes"), role_week_sentence)
        if justification is not None and role_week_sentence:
            justification["kJ_first_statement"] = _append_sentence(
                justification.get("kJ_first_statement"),
                role_week_sentence,
            )

        trace_events = [
            _as_map(event)
            for event in _as_list(_as_map(deterministic.get("event_taper_trace")).get("events"))
            if str(_as_map(event).get("type") or "").strip().upper() in {"A", "B", "C"}
        ]
        phase["events_constraints"] = [
            {
                "window": str(event.get("date") or event.get("week") or "").strip(),
                "type": str(event.get("type") or "").strip().upper(),
                "constraint": _season_event_constraint_text(str(event.get("type") or "")),
            }
            for event in trace_events
            if str(event.get("date") or event.get("week") or "").strip()
        ]
        all_a_events.extend(event for event in trace_events if str(event.get("type") or "").strip().upper() == "A")

        overview = _as_map(phase.get("overview"))
        non_negotiables = [str(item).strip() for item in _as_list(overview.get("non_negotiables")) if str(item).strip()]
        if str(phase_intent).strip() == "durability_build":
            readiness_line = (
                "If this is the first Build entry after shortened, base, or re-entry context, start conservatively and "
                "gate corridor entry by stable recovery and readiness rather than catch-up loading."
            )
            if readiness_line not in non_negotiables:
                non_negotiables.append(readiness_line)
        if str(phase_intent).strip() == "taper_freshening":
            taper_lines = (
                "Treat LOAD_1, LOAD_2, and RELOAD as load-band labels only, not as authority for Build-like workout selection.",
                "Treat any final-week RELOAD wording as event-containing load inside taper, not as a normal training reload.",
            )
            for line in taper_lines:
                if line not in non_negotiables:
                    non_negotiables.append(line)
            if weekly_kj:
                weekly_kj["notes"] = _append_sentence(
                    weekly_kj.get("notes"),
                    "Within taper_freshening, LOAD_1 / LOAD_2 / RELOAD are load-band labels only; final-week RELOAD means event-containing load inside taper.",
                )
        if non_negotiables:
            overview["non_negotiables"] = non_negotiables
            phase["overview"] = overview

    season_objective = _as_map(data.get("season_intent_principles")).get("season_objective")
    objective_warning = _derive_objective_event_mismatch_warning(
        season_objective=season_objective,
        a_events=all_a_events,
    )
    assumptions_unknowns = _as_map(data.get("assumptions_unknowns"))
    data["assumptions_unknowns"] = assumptions_unknowns
    if objective_warning:
        assumptions_unknowns["revisit_items"] = _append_unique_item(
            assumptions_unknowns.get("revisit_items"),
            objective_warning,
        )

    scientific_foundation = _as_map(_as_map(data.get("principles_scientific_foundation")).get("scientific_foundation"))
    publications = [_as_map(item) for item in _as_list(scientific_foundation.get("publications"))]
    for publication in publications:
        canonical_link = _normalize_publication_link(publication.get("title"), publication.get("link"))
        if canonical_link:
            publication["link"] = canonical_link
    needs_durability_source = any(
        str(_as_map(phase).get("phase_intent") or "").strip() == "durability_build"
        for phase in phases
    ) or any(
        "durability" in str(_as_map(item).get("principle") or "").lower()
        for item in _as_list(_as_map(data.get("principles_scientific_foundation")).get("principle_applications"))
    )
    has_durability_source = any(
        "durability" in str(item.get("title") or "").lower() or "maunder" in str(item.get("authors") or "").lower()
        for item in publications
    )
    if needs_durability_source and not has_durability_source:
        publications.append(
            {
                "authors": "Maunder, E., Kilding, A. E. & Plews, D. J.",
                "year": 2021,
                "title": "The Importance of 'Durability' in the Physiological Profiling of Endurance Athletes",
                "link": "https://pubmed.ncbi.nlm.nih.gov/33886100/",
            }
        )
    scientific_foundation["publications"] = publications

    transitions = _as_map(data.get("phase_transitions_guardrails"))
    conservative_triggers = [str(item).strip() for item in _as_list(transitions.get("conservative_triggers")) if str(item).strip()]
    readiness_trigger = (
        "Entry into the first Build phase after shortened, base, or re-entry context is conditional on stable recovery; "
        "if readiness deteriorates, start at the lower corridor edge and keep workout selection base-like without catch-up load."
    )
    if readiness_trigger not in conservative_triggers:
        conservative_triggers.append(readiness_trigger)
    transitions["conservative_triggers"] = conservative_triggers
    absolute_no_go_rules = [str(item).strip() for item in _as_list(transitions.get("absolute_no_go_rules")) if str(item).strip()]
    taper_rule = (
        "Within taper_freshening, LOAD_1 / LOAD_2 / RELOAD are load-band labels only and must not authorize Build-like workout selection."
    )
    if taper_rule not in absolute_no_go_rules:
        absolute_no_go_rules.append(taper_rule)
    transitions["absolute_no_go_rules"] = absolute_no_go_rules
    data["phase_transitions_guardrails"] = transitions

    required_trace_artifacts = {"ATHLETE_PROFILE", "KPI_PROFILE", "AVAILABILITY", "PLANNING_EVENTS"}
    present_trace_artifacts = {
        str(_as_map(item).get("artifact") or "").strip().upper()
        for item in _as_list(meta.get("trace_data")) + _as_list(meta.get("trace_events"))
    }
    if required_trace_artifacts - present_trace_artifacts and str(meta.get("data_confidence") or "").strip().upper() == "HIGH":
        meta["data_confidence"] = "MEDIUM"

    document["meta"] = meta
    document["data"] = data
    return document


def normalize_season_plan_draft_bundle(planning_bundle: JsonMap) -> JsonMap:
    """Convert a raw season planning draft into a deterministic normalized bundle."""

    if not isinstance(planning_bundle, dict):
        return planning_bundle
    context = current_guardrail_runtime_context()
    season_phase_load_context = _as_map(context.get("season_phase_load_context"))
    selected_scenario_contract = _as_map(context.get("selected_scenario_contract"))
    phase_context_by_id = {
        str(_as_map(item).get("phase_id") or ""): _as_map(item)
        for item in _as_list(season_phase_load_context.get("phases"))
        if str(_as_map(item).get("phase_id") or "").strip()
    }
    phase_context_by_range = {
        str(_as_map(item).get("iso_week_range") or ""): _as_map(item)
        for item in _as_list(season_phase_load_context.get("phases"))
        if str(_as_map(item).get("iso_week_range") or "").strip()
    }
    season_allowed_domains = list(season_phase_load_context.get("season_allowed_intensity_domains") or [])
    normalized_bundle = dict(planning_bundle)
    normalized_bundle["season_allowed_domains"] = list(season_allowed_domains)
    if selected_scenario_contract:
        normalized_bundle["selected_scenario_contract"] = selected_scenario_contract
    normalized_blueprints: list[JsonMap] = []
    for blueprint in [_as_map(item) for item in _as_list(planning_bundle.get("phase_blueprints"))]:
        phase_id = str(blueprint.get("phase_id") or "").strip()
        iso_week_range = str(blueprint.get("iso_week_range") or "").strip()
        deterministic = phase_context_by_id.get(phase_id) or phase_context_by_range.get(iso_week_range) or {}
        phase_intent = deterministic.get("phase_intent") or blueprint.get("phase_intent")
        phase_type = deterministic.get("phase_type") or blueprint.get("phase_type")
        build_subtype = deterministic.get("build_subtype")
        if build_subtype is None:
            build_subtype = blueprint.get("build_subtype")
        recommended_corridor = _as_map(deterministic.get("recommended_phase_corridor"))
        availability_cap = _as_map(deterministic.get("availability_cap_kj"))
        warnings = [str(item) for item in _as_list(blueprint.get("warnings")) if str(item).strip()]
        phase_type, phase_intent, build_subtype = _canonicalize_phase_semantics_for_bundle(
            phase_type=phase_type,
            phase_intent=phase_intent,
            build_subtype=build_subtype,
            warnings=warnings,
            warning_prefix=f"{phase_id or iso_week_range or 'phase blueprint'}",
        )
        for error in validate_phase_semantics(
            phase_type=phase_type,
            phase_intent=phase_intent,
            build_subtype=build_subtype,
        ):
            if error not in warnings:
                warnings.append(error)
        normalized_blueprint = {
            **blueprint,
            "phase_type": phase_type,
            "phase_intent": phase_intent,
            "build_subtype": build_subtype,
            "phase_taxonomy_version": PHASE_TAXONOMY_VERSION,
            "season_phase_role": deterministic.get("season_phase_role") or blueprint.get("season_phase_role"),
            "scenario_cadence": deterministic.get("scenario_cadence") or blueprint.get("scenario_cadence"),
            "cadence_week_roles": list(
                deterministic.get("cadence_week_roles") or blueprint.get("cadence_week_roles") or []
            ),
            "load_corridor_min": recommended_corridor.get("min", blueprint.get("load_corridor_min")),
            "load_corridor_max": recommended_corridor.get("max", blueprint.get("load_corridor_max")),
            "availability_cap_kj": availability_cap.get("typical", blueprint.get("availability_cap_kj")),
            "baseline_load_kj": deterministic.get("baseline_load_kj", blueprint.get("baseline_load_kj")),
            "role_week_load_bands": normalize_role_week_load_bands(
                _as_list(deterministic.get("role_week_load_bands"))
            )
            or normalize_role_week_load_bands(blueprint.get("role_week_load_bands")),
            "progression_trace": _normalize_progression_trace(
                deterministic.get("progression_trace") or blueprint.get("progression_trace")
            ),
            "allowed_domains": season_phase_allowed_domains(
                phase_intent=phase_intent,
                season_allowed_domains=season_allowed_domains,
            ),
            "allowed_load_modalities": semantic_allowed_load_modalities(phase_intent),
            "forbidden_domains": season_phase_forbidden_domains(
                phase_intent=phase_intent,
                season_allowed_domains=season_allowed_domains,
            ),
            "semantic_contract": phase_semantic_contract_payload(phase_intent=phase_intent),
            "warnings": warnings,
        }
        _sanitize_season_phase_narrative_fields(
            normalized_blueprint,
            phase_type=phase_type,
            phase_intent=phase_intent,
            allowed_domains=normalized_blueprint.get("allowed_domains"),
            forbidden_domains=normalized_blueprint.get("forbidden_domains"),
        )
        normalized_blueprints.append(normalized_blueprint)
    normalized_bundle["phase_blueprints"] = normalized_blueprints
    candidate_document = {
        "data": {
            "phases": [
                {
                    "iso_week_range": item.get("iso_week_range"),
                    "role_week_load_bands": item.get("role_week_load_bands"),
                    "weekly_load_corridor": {
                        "weekly_kj": {
                            "min": item.get("load_corridor_min"),
                            "max": item.get("load_corridor_max"),
                        }
                    },
                }
                for item in normalized_blueprints
            ]
        }
    }
    expected_envelope = derive_expected_average_weekly_kj_range(season_plan_payload=candidate_document)
    existing_envelope = _as_map(planning_bundle.get("season_load_envelope"))
    if expected_envelope:
        expected_high_load_weeks_count, expected_deload_or_low_load_weeks_count = _derive_season_load_envelope_counts(
            phase_blueprints=normalized_blueprints
        )
        existing_high_load_weeks_count = _as_int(existing_envelope.get("expected_high_load_weeks_count"))
        existing_deload_or_low_load_weeks_count = _as_int(
            existing_envelope.get("expected_deload_or_low_load_weeks_count")
        )
        normalized_bundle["season_load_envelope"] = {
            "expected_average_weekly_kj_range": expected_envelope,
            "expected_high_load_weeks_count": (
                existing_high_load_weeks_count
                if existing_high_load_weeks_count is not None
                else expected_high_load_weeks_count
            ),
            "expected_deload_or_low_load_weeks_count": (
                existing_deload_or_low_load_weeks_count
                if existing_deload_or_low_load_weeks_count is not None
                else expected_deload_or_low_load_weeks_count
            ),
        }
    normalized_bundle["season_semantic_notes"] = _derive_season_semantic_notes(planning_bundle=normalized_bundle)
    return normalized_bundle


def normalize_phase_draft_bundle(planning_bundle: JsonMap) -> JsonMap:
    """Convert a raw phase planning draft into a deterministic normalized bundle."""

    if not isinstance(planning_bundle, dict):
        return planning_bundle
    context = current_guardrail_runtime_context()
    phase_execution_context = _as_map(context.get("phase_execution_context"))
    loaded_inputs = context.get("loaded_inputs")
    loaded_inputs = loaded_inputs if isinstance(loaded_inputs, dict) else {}
    season_plan_document = extract_loaded_document(loaded_inputs.get("season_plan"))
    inherited_scenario_contract = _as_map(phase_execution_context.get("inherited_scenario_contract"))
    normalized_bundle = dict(planning_bundle)
    normalized_bundle["phase_id"] = phase_execution_context.get("phase_id", planning_bundle.get("phase_id"))
    normalized_bundle["phase_range"] = phase_execution_context.get("phase_iso_week_range", planning_bundle.get("phase_range"))
    execution_phase_intent = phase_execution_context.get("phase_intent")
    if not str(execution_phase_intent or "").strip():
        raise RuntimeError("Deterministic phase_execution_context.phase_intent is missing.")
    phase_type, phase_intent, build_subtype = _canonicalize_phase_semantics_for_bundle(
        phase_type=phase_execution_context.get("phase_type", planning_bundle.get("phase_type")),
        phase_intent=execution_phase_intent,
        build_subtype=phase_execution_context.get("build_subtype", planning_bundle.get("build_subtype")),
    )
    if not phase_intent:
        raise RuntimeError("Deterministic phase_execution_context.phase_intent could not be canonicalized.")
    if not inherited_scenario_contract:
        raise RuntimeError("Deterministic phase_execution_context.inherited_scenario_contract is missing.")
    normalized_bundle["phase_type"] = phase_type
    normalized_bundle["phase_intent"] = phase_intent
    normalized_bundle["build_subtype"] = build_subtype
    normalized_bundle["inherited_scenario_contract"] = inherited_scenario_contract
    for field in ("guardrails", "structure", "preview"):
        nested = _as_map(normalized_bundle.get(field))
        if nested:
            normalized_bundle[field] = {
                **nested,
                "phase_intent": phase_intent,
                "inherited_scenario_contract": inherited_scenario_contract,
            }
    structure = _as_map(normalized_bundle.get("structure"))
    if structure:
        upstream_intent = _as_map(structure.get("upstream_intent"))
        upstream_intent["constraints"] = normalize_phase_structure_upstream_constraints(
            upstream_intent.get("constraints"),
            season_plan_document=season_plan_document,
        )
        structure["upstream_intent"] = upstream_intent
        normalized_bundle["structure"] = structure
    week_role_by_iso_week = _as_map(phase_execution_context.get("week_role_by_iso_week"))
    exact_band_by_week = role_week_band_by_week(phase_execution_context.get("phase_role_week_load_bands"))
    if not exact_band_by_week:
        exact_band_by_week = {
            str(_as_map(entry).get("week") or ""): _as_map(_as_map(entry).get("band"))
            for entry in _as_list(phase_execution_context.get("phase_s5_bands"))
            if str(_as_map(entry).get("week") or "").strip()
        }
    normalized_weeks: list[JsonMap] = []
    for blueprint in [_as_map(item) for item in _as_list(planning_bundle.get("week_blueprints"))]:
        week = str(blueprint.get("week") or "").strip()
        band = exact_band_by_week.get(week, {})
        normalized_weeks.append(
            {
                **blueprint,
                "phase_role": phase_execution_context.get("phase_role") or phase_execution_context.get("phase_type") or blueprint.get("phase_role"),
                "phase_intent": phase_intent,
                "week_role": week_role_by_iso_week.get(week, blueprint.get("week_role")),
                "s5_band_min": band.get("min", blueprint.get("s5_band_min")),
                "s5_band_max": band.get("max", blueprint.get("s5_band_max")),
            }
        )
    normalized_bundle["week_blueprints"] = normalized_weeks
    if phase_execution_context.get("phase_primary_objective"):
        normalized_bundle["phase_primary_objective"] = phase_execution_context.get("phase_primary_objective")
    return normalized_bundle
