from rps.orchestrator.resolved_context import build_resolved_report_evidence_block
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType


def test_build_resolved_report_evidence_block_returns_empty_without_version(tmp_path) -> None:
    store = LocalArtifactStore(root=tmp_path)
    athlete_id = "test_athlete"
    store.ensure_workspace(athlete_id)

    block = build_resolved_report_evidence_block(store, athlete_id, des_analysis_report_version=None)

    assert block == ""


def test_build_resolved_report_evidence_block_returns_empty_when_version_missing(tmp_path) -> None:
    store = LocalArtifactStore(root=tmp_path)
    athlete_id = "test_athlete"
    store.ensure_workspace(athlete_id)

    block = build_resolved_report_evidence_block(store, athlete_id, des_analysis_report_version="2026-11")

    assert block == ""


def test_build_resolved_report_evidence_block_renders_kpi_trend_and_recommendation(tmp_path) -> None:
    store = LocalArtifactStore(root=tmp_path)
    athlete_id = "test_athlete"
    store.ensure_workspace(athlete_id)
    store.save_document(
        athlete_id,
        ArtifactType.DES_ANALYSIS_REPORT,
        "2026-11",
        {
            "data": {
                "kpi_summary": {
                    "durability": {"status": "ON_TRACK", "confidence": "high"},
                    "fatigue_resistance": {"status": "AT_RISK", "confidence": "medium"},
                    "fueling_stability": {"status": "ON_TRACK", "confidence": "high"},
                },
                "weekly_analysis": {
                    "interpretation": {"summary": "Solid endurance week with controlled fatigue accumulation."}
                },
                "trend_analysis": {
                    "observations": [
                        {"metric": "durability_index", "trend": "improving"},
                        {"metric": "decoupling_percent", "trend": "stable"},
                    ]
                },
                "recommendation": {
                    "urgency": "moderate",
                    "rationale": ["Maintain current cadence.", "Watch fatigue resistance next week."],
                },
            }
        },
        producer_agent="test",
        run_id="report_2026_11",
        update_latest=True,
    )

    block = build_resolved_report_evidence_block(store, athlete_id, des_analysis_report_version="2026-11")

    assert "**Resolved Report Evidence**" in block
    assert "des_analysis_report_version: 2026-11" in block
    assert "kpi_summary.durability: status=ON_TRACK confidence=high" in block
    assert "kpi_summary.fatigue_resistance: status=AT_RISK confidence=medium" in block
    assert "kpi_summary.fueling_stability: status=ON_TRACK confidence=high" in block
    assert "weekly_analysis.interpretation.summary: Solid endurance week with controlled fatigue accumulation." in block
    assert "trend_analysis.observation: durability_index is improving" in block
    assert "trend_analysis.observation: decoupling_percent is stable" in block
    assert "recommendation.urgency: moderate" in block
    assert "recommendation.rationale: Maintain current cadence.; Watch fatigue resistance next week." in block


def test_build_resolved_report_evidence_block_omits_missing_sections(tmp_path) -> None:
    store = LocalArtifactStore(root=tmp_path)
    athlete_id = "test_athlete"
    store.ensure_workspace(athlete_id)
    store.save_document(
        athlete_id,
        ArtifactType.DES_ANALYSIS_REPORT,
        "2026-11",
        {"data": {}},
        producer_agent="test",
        run_id="report_2026_11_empty",
        update_latest=True,
    )

    block = build_resolved_report_evidence_block(store, athlete_id, des_analysis_report_version="2026-11")

    assert "**Resolved Report Evidence**" in block
    assert "des_analysis_report_version: 2026-11" in block
    assert "kpi_summary." not in block
    assert "weekly_analysis." not in block
    assert "trend_analysis." not in block
    assert "recommendation." not in block
