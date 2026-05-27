"""Deterministic quality gate for evidence curation outputs."""

from __future__ import annotations

from dataclasses import dataclass

from rps.crewai_runtime.models import EvidenceCurationModel

from .library import EvidenceEntry

_FILLER_PHRASES = {
    "summary pending",
    "tbd",
    "none",
    "n/a",
    "important study",
    "useful source",
    "relevant for planning",
}


@dataclass(frozen=True)
class EvidenceQualityGateResult:
    """Structured deterministic decision for one curation payload."""

    ok: bool
    reasons: tuple[str, ...]


def _contains_filler(value: str) -> bool:
    lowered = value.strip().lower()
    return lowered in _FILLER_PHRASES or any(phrase in lowered for phrase in _FILLER_PHRASES)


def _list_specific_enough(items: list[str], *, minimum: int) -> bool:
    cleaned = [item.strip() for item in items if item.strip()]
    if len(cleaned) < minimum:
        return False
    distinct = {item.lower() for item in cleaned}
    if len(distinct) < minimum:
        return False
    return not all(len(item.split()) <= 2 for item in cleaned)


def evaluate_curation_quality(*, entry: EvidenceEntry, curation: EvidenceCurationModel) -> EvidenceQualityGateResult:
    """Return whether one curation payload is safe to activate."""

    reasons: list[str] = []
    if not entry.record_fingerprint:
        reasons.append("Missing record_fingerprint.")
    if not entry.brief_path:
        reasons.append("Missing brief_path.")
    if not entry.curation_schema_version:
        reasons.append("Missing curation_schema_version.")

    required_text_fields = {
        "question_or_focus": curation.question_or_focus,
        "population_or_scope": curation.population_or_scope,
        "relevance_rationale": curation.relevance_assessment.relevance_rationale,
        "summary_card.focus": curation.summary_card.focus,
        "summary_card.main_takeaway": curation.summary_card.main_takeaway,
        "summary_card.main_limit": curation.summary_card.main_limit,
        "brief_sections.why_this_source_matters_for_rps": curation.brief_sections.why_this_source_matters_for_rps,
        "brief_sections.source_material_basis": curation.brief_sections.source_material_basis,
    }
    for field_name, value in required_text_fields.items():
        if not value.strip():
            reasons.append(f"Missing text field: {field_name}.")
        elif _contains_filler(value):
            reasons.append(f"Generic filler detected in {field_name}.")

    list_requirements = {
        "what_was_examined": (curation.what_was_examined, 2),
        "core_concepts": (curation.core_concepts, 3),
        "key_takeaways": (curation.key_takeaways, 3),
        "important_findings": (curation.important_findings, 3),
        "practical_implications": (curation.practical_implications, 3),
        "what_this_does_not_justify": (curation.what_this_does_not_justify, 2),
        "important_limits": (curation.important_limits, 2),
    }
    for name, (items, minimum) in list_requirements.items():
        if not _list_specific_enough(items, minimum=minimum):
            reasons.append(f"{name} failed minimum richness check.")
        if any(_contains_filler(item) for item in items):
            reasons.append(f"{name} contains placeholder or filler text.")

    if curation.relevance_assessment.overall_relevance in {"low", "reject"} and curation.relevance_assessment.activation_recommendation == "activate":
        reasons.append("Low/rejected relevance cannot recommend activation.")

    if entry.source_kind == "applied" and curation.relevance_assessment.best_use_mode == "core_scientific_support":
        reasons.append("Applied source cannot claim core scientific support mode.")

    if curation.evidence_posture == "abstract_curated":
        basis_text = curation.brief_sections.source_material_basis.lower()
        if "abstract" not in basis_text:
            reasons.append("Abstract-curated source must disclose abstract-level basis.")
        overclaim_markers = ("effect size", "causes", "proves", "demonstrates conclusively")
        all_text = " ".join(
            [
                curation.brief_sections.why_this_source_matters_for_rps,
                curation.brief_sections.research_question_or_purpose,
                *curation.important_findings,
                *curation.practical_implications,
            ]
        ).lower()
        if any(marker in all_text for marker in overclaim_markers):
            reasons.append("Abstract-curated source uses overclaiming language.")

    if entry.source_kind == "core" and curation.study_type in {"narrative_review", "systematic_review", "meta_analysis"}:
        all_text = " ".join(curation.practical_implications).lower()
        if "must" in all_text and "rps" in all_text:
            reasons.append("Conceptual/review source sounds like direct binding prescription.")

    return EvidenceQualityGateResult(ok=not reasons, reasons=tuple(reasons))
