from __future__ import annotations

from rps.orchestrator.planning_evidence import (
    build_evidence_alignment_payload,
    report_matches_resolved_evidence,
    resolve_planning_evidence_week,
    resolve_previous_week_activity_versions,
)
from rps.workspace.iso_helpers import IsoWeek
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType


def test_resolve_planning_evidence_week_uses_exact_previous_week_across_year_boundary() -> None:
    assert resolve_planning_evidence_week(IsoWeek(2026, 1)) == IsoWeek(2025, 52)


def test_resolve_previous_week_activity_versions_uses_exact_previous_week_not_latest_older(tmp_path) -> None:
    store = LocalArtifactStore(root=tmp_path)
    athlete_id = "athlete"
    store.ensure_workspace(athlete_id)
    for artifact_type, version_key in (
        (ArtifactType.ACTIVITIES_ACTUAL, "2026-24"),
        (ArtifactType.ACTIVITIES_TREND, "2026-24"),
        (ArtifactType.ACTIVITIES_ACTUAL, "2026-25"),
        (ArtifactType.ACTIVITIES_TREND, "2026-25"),
    ):
        store.save_document(
            athlete_id,
            artifact_type,
            version_key,
            {"meta": {"artifact_type": artifact_type.value, "version_key": version_key, "run_id": "test"}, "data": {}},
            producer_agent="test",
            run_id="test",
            update_latest=True,
        )
    resolution = resolve_previous_week_activity_versions(store, athlete_id, IsoWeek(2026, 26))
    assert resolution.evidence_week == IsoWeek(2026, 25)
    assert resolution.activities_actual_version == "2026-25"
    assert resolution.activities_trend_version == "2026-25"


def test_report_matches_resolved_evidence_checks_week_and_source_versions() -> None:
    payload = {
        "meta": {
            "artifact_type": "DES_ANALYSIS_REPORT",
            "iso_week": "2026-25",
            "trace_upstream": [
                {"artifact": "ACTIVITIES_ACTUAL", "version": "2026-25", "version_key": "2026-25", "run_id": "aa", "schema_version": "1.0"},
                {"artifact": "ACTIVITIES_TREND", "version": "2026-25", "version_key": "2026-25", "run_id": "at", "schema_version": "1.0"},
            ],
        },
        "data": {"summary_meta": {"year": 2026, "iso_week": 25, "run_id": "des"}},
    }
    assert report_matches_resolved_evidence(
        payload,
        evidence_week=IsoWeek(2026, 25),
        activities_actual_version="2026-25",
        activities_trend_version="2026-25",
    )
    assert not report_matches_resolved_evidence(
        payload,
        evidence_week=IsoWeek(2026, 25),
        activities_actual_version="2026-24",
        activities_trend_version="2026-25",
    )


def test_build_evidence_alignment_payload_marks_conservative_week_when_report_is_yellow() -> None:
    payload = build_evidence_alignment_payload(
        scope="week",
        target_week=IsoWeek(2026, 26),
        evidence_week=IsoWeek(2026, 25),
        des_analysis_payload={
            "data": {
                "kpi_summary": {
                    "durability": {"status": "yellow"},
                    "fatigue_resistance": {"status": "green"},
                },
                "recommendation": {"urgency": "medium"},
            }
        },
        activities_trend_payload={
            "data": {
                "weekly_trends": [
                    {
                        "weekly_aggregates": {"activity_count": 3, "work_kj": 4500},
                    }
                ]
            }
        },
    )
    assert payload["scope"] == "week"
    assert payload["reduce_quality_density"] is True
    assert payload["conservative_load_fraction_cap"] <= 0.4
    assert payload["planning_implications"]
