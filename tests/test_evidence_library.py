from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from rps.crewai_runtime.models import (
    EvidenceBriefSectionsModel,
    EvidenceCurationModel,
    EvidenceRelevanceAssessmentModel,
    EvidenceSummaryCardModel,
)
from rps.evidence.library import (
    DECOMMISSIONED_SHARED_BIBLIOGRAPHY,
    DISCOVERY_STATE_PATH,
    LIBRARY_MANIFEST_PATH,
    ROOT,
    load_core_studies,
    save_core_studies,
    save_discovery_state,
    sync_reference_library_outputs,
)
from rps.evidence.quality_gate import evaluate_curation_quality
from rps.evidence.refresh import refresh_evidence_library
from rps.evidence.trusted_sources import (
    canonical_author_name,
    canonical_outlet_name,
    match_trusted_source,
)


def test_canonical_evidence_library_contains_verified_core_sources() -> None:
    entries = load_core_studies()

    assert entries
    assert all(entry.id for entry in entries)
    assert all(entry.verification_status for entry in entries)
    assert any(entry.title == "Scientific bases for precompetition tapering strategies" for entry in entries)
    assert any(entry.reference_locator == "https://pubmed.ncbi.nlm.nih.gov/12840640/" for entry in entries)


def test_sync_reference_library_outputs_updates_generated_views() -> None:
    sync_reference_library_outputs()

    assert LIBRARY_MANIFEST_PATH.exists()
    assert DECOMMISSIONED_SHARED_BIBLIOGRAPHY.exists()
    detail_text = (
        Path("skills/shared/durability-methodology/references/library/studies/dur_core_001.md")
        .read_text(encoding="utf-8")
    )
    manifest_text = LIBRARY_MANIFEST_PATH.read_text(encoding="utf-8")
    decommissioned_text = DECOMMISSIONED_SHARED_BIBLIOGRAPHY.read_text(encoding="utf-8")
    assert "canonical local evidence library" in manifest_text
    assert "Decommissioned as an operative evidence source" in decommissioned_text
    assert "## Why This Source Matters for RPS" in detail_text
    assert "## Relevance to RPS" in detail_text
    assert "## Core Concepts" in detail_text
    assert "## Important Findings" in detail_text
    assert "## Practical Implications for RPS" in detail_text
    assert "Curation schema version" in detail_text


def test_refresh_evidence_library_activates_verified_primary_source_candidates(monkeypatch) -> None:
    original_entries = load_core_studies()
    original_state = DISCOVERY_STATE_PATH.read_text(encoding="utf-8") if DISCOVERY_STATE_PATH.exists() else None
    now = datetime(2026, 5, 27, 10, 0, tzinfo=UTC)
    try:
        save_discovery_state(
            {
                "version": 1,
                "last_attempt_at": None,
                "last_success_at": "2026-05-01T00:00:00Z",
                "last_search_date": "2026-05-01",
                "stats": {},
            }
        )

        monkeypatch.setattr(
            "rps.evidence.refresh._search_pubmed",
            lambda query, start_date, end_date, retmax=10: ["99999999"],
        )
        monkeypatch.setattr(
            "rps.evidence.refresh._summaries_pubmed",
            lambda ids: [
                {
                    "uid": "99999999",
                    "title": "A new durability paper for testing.",
                    "authors": [{"name": "Test, A."}, {"name": "Example, B."}],
                    "pubdate": "2026 May",
                    "articleids": [{"idtype": "doi", "value": "10.1000/test-durability"}],
                    "fulljournalname": "Journal of Testing",
                }
            ],
        )
        monkeypatch.setattr(
            "rps.evidence.refresh._fetch_pubmed_abstract",
            lambda pmid: "This abstract describes durability under accumulated work in cycling and relevant practical implications.",
        )
        monkeypatch.setattr(
            "rps.evidence.refresh.run_entry_pipeline",
            lambda entry, athlete_id, run_id, workspace_root, abstract_text="", oa_excerpt_text="", oa_fulltext_text="": (
                replace(
                    entry,
                    activation_status="active",
                    legacy_active=False,
                    source_material_level="abstract_only",
                    source_material_basis="Curated from abstract-level material.",
                ),
                {"status": "active"},
            ),
        )

        result = refresh_evidence_library(
            now=now,
            refresh_interval_days=7,
            retmax=1,
            athlete_id="system",
            workspace_root=ROOT / "runtime" / "athletes",
            run_id="",
        )
        refreshed_entries = load_core_studies()
        added = [entry for entry in refreshed_entries if entry.title == "A new durability paper for testing"]

        assert result["status"] == "done"
        assert result["stats"]["activated_entries"] >= 1
        assert added
        assert added[0].reference_locator == "https://doi.org/10.1000/test-durability"
        assert added[0].verification_status == "verified"
        assert added[0].activation_status == "active"
    finally:
        save_core_studies(original_entries)
        if original_state is None:
            DISCOVERY_STATE_PATH.unlink(missing_ok=True)
        else:
            DISCOVERY_STATE_PATH.write_text(original_state, encoding="utf-8")
        sync_reference_library_outputs()


def test_trusted_source_matching_uses_author_and_outlet_normalization() -> None:
    assert canonical_author_name("Seiler, S.") == "stephen seiler"
    assert canonical_outlet_name("Medicine & Science in Sports & Exercise") == "medicine and science in sports and exercise"
    matched, reason = match_trusted_source(
        authors="Seiler, S., Someone, A.",
        outlet="Sports Med",
    )
    assert matched is True
    assert "trusted" in reason.lower()


def test_quality_gate_rejects_generic_filler() -> None:
    entry = load_core_studies()[0]
    payload = EvidenceCurationModel(
        question_or_focus="Important study",
        population_or_scope="Relevant athletes",
        study_type="narrative_review",
        what_was_examined=["Useful source", "Useful source"],
        core_concepts=["important study", "important study", "important study"],
        key_takeaways=["important study", "important study", "important study"],
        important_findings=["important study", "important study", "important study"],
        practical_implications=["important study", "important study", "important study"],
        what_this_does_not_justify=["important study", "important study"],
        important_limits=["important study", "important study"],
        allowed_uses=["background_only"],
        evidence_posture="abstract_curated",
        relevance_assessment=EvidenceRelevanceAssessmentModel(
            overall_relevance="medium",
            relevance_rationale="useful source",
            rps_domains_supported=["durability"],
            target_audiences_supported=["background_knowledge"],
            best_use_mode="background_only",
            activation_recommendation="hold",
        ),
        summary_card=EvidenceSummaryCardModel(
            focus="important study",
            main_takeaway="important study",
            main_limit="important study",
        ),
        brief_sections=EvidenceBriefSectionsModel(
            why_this_source_matters_for_rps="important study",
            research_question_or_purpose="important study",
            study_type="important study",
            population_or_context="important study",
            what_was_actually_examined="important study",
            core_concepts=["important study", "important study", "important study"],
            key_takeaways=["important study", "important study", "important study"],
            important_findings=["important study", "important study", "important study"],
            practical_implications_for_rps=["important study", "important study", "important study"],
            what_this_source_does_not_justify=["important study", "important study"],
            limits_and_transfer_boundaries=["important study", "important study"],
            allowed_uses_in_rps=["background_only"],
            evidence_posture="abstract_curated",
            source_material_basis="Curated from abstract-level material.",
        ),
    )
    result = evaluate_curation_quality(entry=entry, curation=payload)
    assert result.ok is False
    assert result.reasons
