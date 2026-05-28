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
    load_applied_sources,
    load_core_studies,
    save_applied_sources,
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
    original_applied = load_applied_sources()
    original_state = DISCOVERY_STATE_PATH.read_text(encoding="utf-8") if DISCOVERY_STATE_PATH.exists() else None
    now = datetime(2026, 5, 27, 10, 0, tzinfo=UTC)
    try:
        save_core_studies([])
        save_applied_sources([])
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
        save_applied_sources(original_applied)
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


def test_metadata_only_quality_gate_rejects_tag_leakage_and_title_paraphrase_findings() -> None:
    entry = replace(
        load_core_studies()[0],
        title="One-step synthesis of a mechanically robust anti-reflective coating",
        journal_or_outlet="Nanoscale",
        source_kind="core",
    )
    payload = EvidenceCurationModel(
        question_or_focus="Mechanically robust coating with durability-adjacent language; metadata only.",
        population_or_scope="Materials context only; no athlete population is provided.",
        study_type="other",
        what_was_examined=[
            "Verified title, year, and outlet metadata for a materials paper.",
            "Whether the package contains extractable source text beyond metadata.",
        ],
        core_concepts=[
            "mechanically robust coating",
            "anti-reflective coating",
            "cycling_endurance",
        ],
        key_takeaways=[
            "The source package is metadata-only.",
            "The title suggests a materials durability topic.",
            "No extractable findings are available from the package.",
        ],
        important_findings=[
            "The title explicitly includes mechanical robustness.",
            "The source is tagged with durability and cycling_endurance.",
            "The metadata-only package confirms the title and outlet.",
        ],
        practical_implications=[
            "Background-only mention of durability-adjacent language.",
            "No RPS training or coaching use is supported.",
            "No athlete-performance transfer should be inferred.",
        ],
        what_this_does_not_justify=[
            "It does not justify endurance-training prescriptions.",
            "It does not justify claims about athlete fatigue resistance or fueling.",
        ],
        important_limits=[
            "Metadata-only package; no abstract or full text is provided.",
            "The source is off-domain for endurance training and coaching.",
        ],
        allowed_uses=["background_only"],
        evidence_posture="metadata_only_not_activatable",
        relevance_assessment=EvidenceRelevanceAssessmentModel(
            overall_relevance="low",
            relevance_rationale="Weak background relevance only.",
            rps_domains_supported=["durability"],
            target_audiences_supported=["background_knowledge"],
            best_use_mode="background_only",
            activation_recommendation="hold",
        ),
        summary_card=EvidenceSummaryCardModel(
            focus="Materials paper with durability-adjacent title language.",
            main_takeaway="Verified metadata exist but no extractable findings are available.",
            main_limit="Metadata-only package with off-domain transfer risk.",
        ),
        brief_sections=EvidenceBriefSectionsModel(
            why_this_source_matters_for_rps="It is at most a weak background durability analogy and not an endurance evidence source.",
            research_question_or_purpose="Develop a mechanically robust anti-reflective coating.",
            study_type="peer-reviewed article; metadata only",
            population_or_context="Materials/coatings research context.",
            what_was_actually_examined="Only title-level metadata are available in the package.",
            core_concepts=[
                "mechanically robust coating",
                "anti-reflective coating",
                "cycling_endurance",
            ],
            key_takeaways=[
                "Metadata-only package.",
                "Title-level topic hints only.",
                "No extractable findings are available.",
            ],
            important_findings=[
                "The title signals a durability angle.",
                "The source is tagged with cycling_endurance.",
                "No results are actually provided in the package.",
            ],
            practical_implications_for_rps=[
                "Background-only mention.",
                "No training application.",
                "No performance inference.",
            ],
            what_this_source_does_not_justify=[
                "No endurance-training claims.",
                "No athlete physiology claims.",
            ],
            limits_and_transfer_boundaries=[
                "Metadata-only package.",
                "Off-domain materials context.",
            ],
            allowed_uses_in_rps=["background_only"],
            evidence_posture="metadata_only_not_activatable",
            source_material_basis="Metadata-only package; not activatable without stronger source text.",
        ),
    )
    result = evaluate_curation_quality(entry=entry, curation=payload)
    assert result.ok is False
    assert any("treats title/tag metadata as findings" in reason for reason in result.reasons)
    assert any("unsupported RPS transfer concepts" in reason for reason in result.reasons)


def test_abstract_only_quality_gate_rejects_background_only_mix_and_imperative_language() -> None:
    entry = load_core_studies()[0]
    payload = EvidenceCurationModel(
        question_or_focus="Scientific bases for precompetition tapering strategies.",
        population_or_scope="Athletes preparing for competition.",
        study_type="narrative_review",
        what_was_examined=[
            "Taper definition and reduction of training load.",
            "Training intensity, volume, and frequency adjustments during tapering.",
        ],
        core_concepts=[
            "taper",
            "training load",
            "training volume",
        ],
        key_takeaways=[
            "The abstract describes tapering as a reduction of training load.",
            "The abstract reports preserving intensity while reducing load.",
            "The abstract suggests performance tends to improve during tapering.",
        ],
        important_findings=[
            "The abstract reports that taper structure matters for performance.",
            "The abstract describes maintained intensity with reduced volume.",
            "The review abstract suggests taper duration influences outcomes.",
        ],
        practical_implications=[
            "Use a structured taper rather than simply reducing training indiscriminately.",
            "Keep intensity during the taper while lowering volume substantially.",
            "Favor progressive nonlinear taper structures when preparing for competition.",
        ],
        what_this_does_not_justify=[
            "It does not justify a one-size-fits-all taper prescription.",
            "It does not justify athlete-specific protocol claims beyond the abstract.",
        ],
        important_limits=[
            "Abstract-only material; no full-text protocol detail is available.",
            "The source is a review abstract rather than a single dataset.",
        ],
        allowed_uses=[
            "taper_support",
            "planning_justification",
            "background_only",
        ],
        evidence_posture="abstract_curated",
        relevance_assessment=EvidenceRelevanceAssessmentModel(
            overall_relevance="high",
            relevance_rationale="High taper relevance for RPS.",
            rps_domains_supported=["taper"],
            target_audiences_supported=["phase_planning", "coach_chat"],
            best_use_mode="core_scientific_support",
            activation_recommendation="activate",
        ),
        summary_card=EvidenceSummaryCardModel(
            focus="Precompetition tapering strategy.",
            main_takeaway="The abstract supports tapering with maintained intensity and reduced load.",
            main_limit="Abstract-only review evidence.",
        ),
        brief_sections=EvidenceBriefSectionsModel(
            why_this_source_matters_for_rps="The abstract directly informs taper planning in late-phase endurance contexts.",
            research_question_or_purpose="Summarize the scientific bases for tapering strategies.",
            study_type="review",
            population_or_context="Athletes in precompetition settings.",
            what_was_actually_examined="The abstract discusses taper structure and associated performance changes.",
            core_concepts=["taper", "training load", "training volume"],
            key_takeaways=[
                "The abstract describes tapering as a reduction of load.",
                "The abstract reports maintained intensity during tapering.",
                "The abstract suggests performance usually improves.",
            ],
            important_findings=[
                "The abstract reports that taper structure matters.",
                "The abstract describes reduced volume with maintained intensity.",
                "The abstract suggests duration influences outcomes.",
            ],
            practical_implications_for_rps=[
                "Use a structured taper rather than unstructured load reduction.",
                "Keep intensity present while lowering volume.",
                "Favor progressive nonlinear taper structures.",
            ],
            what_this_source_does_not_justify=[
                "No one-size-fits-all taper prescription.",
                "No athlete-specific protocol claims beyond the abstract.",
            ],
            limits_and_transfer_boundaries=[
                "Abstract-only material.",
                "No discipline-specific subgroup detail is available.",
            ],
            allowed_uses_in_rps=["taper_support", "planning_justification", "background_only"],
            evidence_posture="abstract_curated",
            source_material_basis="Curated from abstract-level material.",
        ),
    )
    result = evaluate_curation_quality(entry=entry, curation=payload)
    assert result.ok is False
    assert any("cannot mix background_only with stronger allowed uses" in reason for reason in result.reasons)
    assert any("direct imperative coaching language" in reason for reason in result.reasons)


def test_refresh_evidence_library_skips_already_curated_verified_entries(monkeypatch) -> None:
    original_entries = load_core_studies()
    original_applied = load_applied_sources()
    try:
        curated_verified = replace(
            original_entries[0],
            activation_status="verified",
            curated_at="2026-05-20T10:00:00Z",
            brief_status="generated",
            curation_schema_version="1",
            legacy_active=False,
        )
        save_core_studies([curated_verified])
        save_applied_sources([])
        monkeypatch.setattr("rps.evidence.refresh._search_pubmed", lambda *args, **kwargs: [])
        monkeypatch.setattr("rps.evidence.refresh._summaries_pubmed", lambda ids: [])
        monkeypatch.setattr(
            "rps.evidence.refresh.run_entry_pipeline",
            lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("run_entry_pipeline should not be called")),
        )
        result = refresh_evidence_library(
            now=datetime(2026, 5, 27, 12, 0, tzinfo=UTC),
            refresh_interval_days=0,
            athlete_id="system",
            workspace_root=ROOT / "runtime" / "athletes",
            run_id="",
        )
        assert result["status"] == "done"
        assert result["stats"]["processed_entries"] == 0
        assert result["stats"]["skipped_unchanged"] == 1
        assert result["library_changed"] is False
    finally:
        save_core_studies(original_entries)
        save_applied_sources(original_applied)
        sync_reference_library_outputs()


def test_refresh_evidence_library_processes_pending_legacy_verified_seeds(monkeypatch) -> None:
    original_entries = load_core_studies()
    original_applied = load_applied_sources()
    try:
        pending_seed = replace(
            original_entries[0],
            activation_status="legacy_active",
            legacy_active=True,
            verification_status="verified",
            curated_at="",
            brief_status="pending_curation",
            reference_locator="https://pubmed.ncbi.nlm.nih.gov/12840640/",
        )
        save_core_studies([pending_seed])
        save_applied_sources([])
        monkeypatch.setattr("rps.evidence.refresh._search_pubmed", lambda *args, **kwargs: [])
        monkeypatch.setattr("rps.evidence.refresh._summaries_pubmed", lambda ids: [])
        monkeypatch.setattr(
            "rps.evidence.refresh._fetch_pubmed_abstract_with_backoff",
            lambda pmid: ("Abstract text for one pending manual seed.", False),
        )
        monkeypatch.setattr(
            "rps.evidence.refresh.run_entry_pipeline",
            lambda entry, athlete_id, run_id, workspace_root, abstract_text="", oa_excerpt_text="", oa_fulltext_text="": (
                replace(entry, activation_status="active", legacy_active=False, curated_at="2026-05-27T12:00:00Z"),
                {"status": "active"},
            ),
        )
        result = refresh_evidence_library(
            now=datetime(2026, 5, 27, 12, 0, tzinfo=UTC),
            refresh_interval_days=0,
            athlete_id="system",
            workspace_root=ROOT / "runtime" / "athletes",
            run_id="",
        )
        refreshed = load_core_studies()
        assert result["status"] == "done"
        assert result["stats"]["processed_entries"] == 1
        assert refreshed[0].activation_status == "active"
        assert refreshed[0].legacy_active is False
    finally:
        save_core_studies(original_entries)
        save_applied_sources(original_applied)
        sync_reference_library_outputs()


def test_refresh_evidence_library_resolves_doi_only_pending_seed_to_pubmed(monkeypatch) -> None:
    original_entries = load_core_studies()
    original_applied = load_applied_sources()
    try:
        pending_seed = replace(
            original_entries[0],
            activation_status="legacy_active",
            legacy_active=True,
            verification_status="verified",
            curated_at="",
            brief_status="pending_curation",
            reference_locator="https://doi.org/10.1111/sms.12016",
        )
        save_core_studies([pending_seed])
        save_applied_sources([])
        monkeypatch.setattr("rps.evidence.refresh._search_pubmed", lambda query, **kwargs: ["23134196"] if "10.1111/sms.12016" in query else [])
        monkeypatch.setattr("rps.evidence.refresh._summaries_pubmed", lambda ids: [])
        monkeypatch.setattr(
            "rps.evidence.refresh._fetch_pubmed_abstract_with_backoff",
            lambda pmid: ("Resolved abstract text.", False),
        )
        captured: dict[str, str] = {}

        def _pipeline(entry, athlete_id, run_id, workspace_root, abstract_text="", oa_excerpt_text="", oa_fulltext_text=""):
            captured["abstract_text"] = abstract_text
            return replace(entry, activation_status="active", legacy_active=False, curated_at="2026-05-27T12:00:00Z"), {"status": "active"}

        monkeypatch.setattr("rps.evidence.refresh.run_entry_pipeline", _pipeline)
        result = refresh_evidence_library(
            now=datetime(2026, 5, 27, 12, 0, tzinfo=UTC),
            refresh_interval_days=0,
            athlete_id="system",
            workspace_root=ROOT / "runtime" / "athletes",
            run_id="",
        )
        assert result["stats"]["processed_entries"] == 1
        assert captured["abstract_text"] == "Resolved abstract text."
    finally:
        save_core_studies(original_entries)
        save_applied_sources(original_applied)
        sync_reference_library_outputs()


def test_refresh_evidence_library_skips_processing_when_abstract_fetch_is_rate_limited(monkeypatch) -> None:
    original_entries = load_core_studies()
    original_applied = load_applied_sources()
    try:
        needs_abstract = replace(
            original_entries[0],
            activation_status="verified",
            curated_at="",
            brief_status="pending_curation",
            reference_locator="https://pubmed.ncbi.nlm.nih.gov/12840640/",
            legacy_active=False,
        )
        save_core_studies([needs_abstract])
        save_applied_sources([])
        monkeypatch.setattr("rps.evidence.refresh._search_pubmed", lambda *args, **kwargs: [])
        monkeypatch.setattr("rps.evidence.refresh._summaries_pubmed", lambda ids: [])
        monkeypatch.setattr(
            "rps.evidence.refresh._fetch_pubmed_abstract_with_backoff",
            lambda pmid: ("", True),
        )
        monkeypatch.setattr(
            "rps.evidence.refresh.run_entry_pipeline",
            lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("run_entry_pipeline should not be called")),
        )
        result = refresh_evidence_library(
            now=datetime(2026, 5, 27, 12, 0, tzinfo=UTC),
            refresh_interval_days=0,
            athlete_id="system",
            workspace_root=ROOT / "runtime" / "athletes",
            run_id="",
        )
        refreshed = load_core_studies()
        assert result["stats"]["processed_entries"] == 0
        assert result["stats"]["rate_limited_skipped"] == 1
        assert refreshed[0].activation_status == "verified"
        assert refreshed[0].curated_at == ""
        assert result["library_changed"] is False
    finally:
        save_core_studies(original_entries)
        save_applied_sources(original_applied)
        sync_reference_library_outputs()


def test_refresh_evidence_library_caps_processed_entries_per_run(monkeypatch) -> None:
    original_entries = load_core_studies()
    original_applied = load_applied_sources()
    try:
        first = replace(
            original_entries[0],
            id="cap_one",
            activation_status="verified",
            curated_at="",
            brief_status="pending_curation",
            reference_locator="https://pubmed.ncbi.nlm.nih.gov/12840640/",
            legacy_active=False,
        )
        second = replace(
            original_entries[1],
            id="cap_two",
            activation_status="verified",
            curated_at="",
            brief_status="pending_curation",
            reference_locator="https://pubmed.ncbi.nlm.nih.gov/33886100/",
            legacy_active=False,
        )
        save_core_studies([first, second])
        save_applied_sources([])
        monkeypatch.setattr("rps.evidence.refresh._search_pubmed", lambda *args, **kwargs: [])
        monkeypatch.setattr("rps.evidence.refresh._summaries_pubmed", lambda ids: [])
        monkeypatch.setattr(
            "rps.evidence.refresh._fetch_pubmed_abstract_with_backoff",
            lambda pmid: ("Abstract text for testing.", False),
        )
        monkeypatch.setattr(
            "rps.evidence.refresh.run_entry_pipeline",
            lambda entry, athlete_id, run_id, workspace_root, abstract_text="", oa_excerpt_text="", oa_fulltext_text="": (
                replace(entry, activation_status="active", curated_at="2026-05-27T12:00:00Z"),
                {"status": "active"},
            ),
        )
        result = refresh_evidence_library(
            now=datetime(2026, 5, 27, 12, 0, tzinfo=UTC),
            refresh_interval_days=0,
            athlete_id="system",
            workspace_root=ROOT / "runtime" / "athletes",
            run_id="",
            max_entries_per_refresh=1,
        )
        refreshed = load_core_studies()
        by_id = {entry.id: entry for entry in refreshed}
        assert result["stats"]["processed_entries"] == 1
        assert result["stats"]["skipped_due_to_cap"] == 1
        assert by_id["cap_one"].activation_status == "active"
        assert by_id["cap_two"].activation_status == "verified"
    finally:
        save_core_studies(original_entries)
        save_applied_sources(original_applied)
        sync_reference_library_outputs()
