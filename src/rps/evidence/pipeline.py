"""End-to-end curation, quality-gate, activation, and rendering pipeline."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

from rps.ui.run_store import append_event, update_run

from .curation import build_source_package, curate_source_package
from .library import CURATION_SCHEMA_VERSION, EvidenceEntry
from .quality_gate import evaluate_curation_quality
from .trusted_sources import match_trusted_source


def _stage_event(root, athlete_id: str, run_id: str, *, stage: str, entry: EvidenceEntry, message: str) -> None:
    if not run_id:
        return
    append_event(
        root,
        athlete_id,
        run_id,
        {
            "stage": stage,
            "entry_id": entry.id,
            "title": entry.title,
            "message": message,
        },
    )
    update_run(root, athlete_id, run_id, {"current_step": f"{stage}: {entry.id}"})


def _curation_to_entry(
    entry: EvidenceEntry,
    curation,
    *,
    trusted_source_match: bool,
    trusted_match_reason: str,
    source_material_level: str,
    source_material_basis: str,
) -> EvidenceEntry:
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    activation_status = "curated"
    if (
        curation.relevance_assessment.activation_recommendation == "activate"
        and curation.relevance_assessment.overall_relevance in {"high", "medium"}
    ):
        activation_status = "active"
    elif curation.relevance_assessment.activation_recommendation == "reject":
        activation_status = "rejected"
    return replace(
        entry,
        question_or_focus=curation.question_or_focus,
        population_or_scope=curation.population_or_scope,
        study_type=curation.study_type,
        what_was_examined=tuple(curation.what_was_examined),
        core_concepts=tuple(curation.core_concepts),
        key_takeaways=tuple(curation.key_takeaways),
        important_findings=tuple(curation.important_findings),
        practical_implications=tuple(curation.practical_implications),
        what_this_does_not_justify=tuple(curation.what_this_does_not_justify),
        important_limits=tuple(curation.important_limits),
        allowed_uses=tuple(curation.allowed_uses),
        evidence_posture=curation.evidence_posture,
        summary_card=curation.summary_card.model_dump(),
        relevance_assessment=curation.relevance_assessment.model_dump(),
        brief_sections=curation.brief_sections.model_dump(),
        brief_status="generated",
        activation_status=activation_status,
        trusted_source_match=trusted_source_match,
        trusted_match_reason=trusted_match_reason,
        legacy_active=False,
        curation_schema_version=CURATION_SCHEMA_VERSION,
        source_material_level=source_material_level,
        source_material_basis=source_material_basis,
        curated_at=now,
        activated_at=now if activation_status == "active" else "",
    )


def run_entry_pipeline(
    entry: EvidenceEntry,
    *,
    athlete_id: str,
    run_id: str,
    workspace_root,
    abstract_text: str = "",
    oa_excerpt_text: str = "",
    oa_fulltext_text: str = "",
) -> tuple[EvidenceEntry, dict[str, Any]]:
    """Run the full curation pipeline for one evidence entry."""

    trusted_source_match, trusted_match_reason = match_trusted_source(
        authors=entry.authors,
        outlet=entry.journal_or_outlet,
    )
    _stage_event(workspace_root, athlete_id, run_id, stage="VERIFIED", entry=entry, message="Verified source entering curation.")
    package = build_source_package(
        entry,
        trusted_source_match=trusted_source_match,
        trusted_match_reason=trusted_match_reason,
        abstract_text=abstract_text,
        oa_excerpt_text=oa_excerpt_text,
        oa_fulltext_text=oa_fulltext_text,
    )
    _stage_event(workspace_root, athlete_id, run_id, stage="CURATION_STARTED", entry=entry, message=package.source_material_level)
    curation = curate_source_package(package, athlete_id=athlete_id, run_id=run_id)
    updated = _curation_to_entry(
        entry,
        curation,
        trusted_source_match=trusted_source_match,
        trusted_match_reason=trusted_match_reason,
        source_material_level=package.source_material_level,
        source_material_basis=package.source_material_basis,
    )
    gate = evaluate_curation_quality(entry=updated, curation=curation)
    if not gate.ok:
        if entry.legacy_active or entry.activation_status == "legacy_active":
            fallback = replace(entry, trusted_source_match=trusted_source_match, trusted_match_reason=trusted_match_reason)
            _stage_event(
                workspace_root,
                athlete_id,
                run_id,
                stage="QUALITY_GATE_FAILED",
                entry=entry,
                message="; ".join(gate.reasons),
            )
            return fallback, {"status": "legacy_retained", "reasons": list(gate.reasons)}
        rejected = replace(updated, activation_status="rejected", activated_at="")
        _stage_event(
            workspace_root,
            athlete_id,
            run_id,
            stage="QUALITY_GATE_FAILED",
            entry=entry,
            message="; ".join(gate.reasons),
        )
        return rejected, {"status": "rejected", "reasons": list(gate.reasons)}
    final_entry = updated
    stage = "ACTIVATED" if final_entry.activation_status == "active" else "REJECTED" if final_entry.activation_status == "rejected" else "CURATED"
    _stage_event(workspace_root, athlete_id, run_id, stage=stage, entry=entry, message=final_entry.activation_status)
    return final_entry, {
        "status": final_entry.activation_status,
        "trusted_source_match": trusted_source_match,
        "trusted_match_reason": trusted_match_reason,
        "source_material_level": package.source_material_level,
    }
