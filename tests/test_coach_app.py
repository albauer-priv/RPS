import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType


@pytest.fixture(autouse=True)
def _env_setup(monkeypatch):
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-key")


def test_coach_summary_above_input():
    at = AppTest.from_file("src/rps/ui/pages/coach.py")
    at.run(timeout=10)

    assert len(at.error) == 0
    assert len(at.chat_input) == 1
    assert len(at.info) >= 1

    summary_info = None
    for info in at.info:
        if info.value.startswith("Summary:"):
            summary_info = info
            break
    assert summary_info is not None

    info_index = next(idx for idx, node in enumerate(list(at)) if node is summary_info)
    chat_index = next(idx for idx, node in enumerate(list(at)) if node.type == "chat_input")
    assert info_index < chat_index


def test_coach_source_exposes_active_operation_tools():
    source = Path("src/rps/ui/pages/coach.py").read_text(encoding="utf-8")
    assert "preview_scoped_week_replan" in source
    assert "apply_pending_coach_operation" in source
    assert "preview_run_performance_report" in source
    assert "preview_run_feed_forward" in source


def test_coach_source_no_longer_depends_on_rps_chatbot():
    source = Path("src/rps/ui/pages/coach.py").read_text(encoding="utf-8")
    assert "rps_chatbot" not in source
    assert "run_coach_flow(" in source


def test_workouts_editor_source_no_longer_depends_on_rps_chatbot():
    source = Path("src/rps/ui/pages/plan/workouts.py").read_text(encoding="utf-8")
    assert "rps_chatbot" not in source


def test_coach_shows_one_startup_context_summary(monkeypatch, tmp_path):
    monkeypatch.setenv("ATHLETE_WORKSPACE_ROOT", str(tmp_path))
    sys.modules.pop("rps.ui.shared", None)
    sys.modules.pop("src.rps.ui.shared", None)
    athlete_id = "i150546"
    store = LocalArtifactStore(root=tmp_path)
    store.save_document(
        athlete_id,
        ArtifactType.ATHLETE_STATE_SNAPSHOT,
        "2026-20",
        {
            "meta": {
                "artifact_type": "ATHLETE_STATE_SNAPSHOT",
                "schema_id": "AthleteStateSnapshotInterface",
                "schema_version": "1.0",
                "version": "1.0",
                "authority": "Derived",
                "owner_agent": "Policy-Owner",
                "run_id": "pending",
                "created_at": "1970-01-01T00:00:00Z",
                "scope": "Context",
                "iso_week": "2026-20",
                "iso_week_range": "2026-20--2026-20",
                "temporal_scope": {"from": "2026-05-11", "to": "2026-05-17"},
                "trace_upstream": [],
                "trace_data": [],
                "trace_events": [],
                "data_confidence": "HIGH",
                "notes": "test",
            },
            "data": {"target_iso_week": "2026-20", "source_versions": {}, "prompt_blocks": {"athlete": "ok"}},
        },
        producer_agent="test",
        run_id="test",
        update_latest=True,
    )
    store.save_document(
        athlete_id,
        ArtifactType.PLANNING_CONTEXT_SNAPSHOT,
        "2026-20",
        {
            "meta": {
                "artifact_type": "PLANNING_CONTEXT_SNAPSHOT",
                "schema_id": "PlanningContextSnapshotInterface",
                "schema_version": "1.0",
                "version": "1.0",
                "authority": "Derived",
                "owner_agent": "Policy-Owner",
                "run_id": "pending",
                "created_at": "1970-01-01T00:00:00Z",
                "scope": "Context",
                "iso_week": "2026-20",
                "iso_week_range": "2026-20--2026-20",
                "temporal_scope": {"from": "2026-05-11", "to": "2026-05-17"},
                "trace_upstream": [],
                "trace_data": [],
                "trace_events": [],
                "data_confidence": "HIGH",
                "notes": "test",
            },
            "data": {
                "target_iso_week": "2026-20",
                "phase_iso_week_range": "2026-19--2026-22",
                "source_versions": {},
                "prompt_blocks": {
                    "phase": (
                        "**Resolved Phase Context**\n"
                        "phase_name: Rebuild and Aerobic Re-Entry\n"
                        "phase_type: Base\n"
                        "phase_week_index: 2\n"
                        "phase_iso_week_range: 2026-19--2026-22\n"
                    ),
                    "load_governance": (
                        "**Resolved Load Governance Context**\n"
                        "phase_guardrails.active_weekly_kj_band (2026-20): min 6200, max 7600\n"
                    ),
                },
            },
        },
        producer_agent="test",
        run_id="test",
    )
    store.save_document(
        athlete_id,
        ArtifactType.ADVISORY_MEMORY,
        "2026-20",
        {
            "meta": {
                "artifact_type": "ADVISORY_MEMORY",
                "schema_id": "AdvisoryMemoryInterface",
                "schema_version": "1.0",
                "version": "1.0",
                "authority": "Advisory",
                "owner_agent": "Policy-Owner",
                "run_id": "pending",
                "created_at": "1970-01-01T00:00:00Z",
                "scope": "Context",
                "iso_week": "2026-20",
                "iso_week_range": "2026-20--2026-20",
                "temporal_scope": {"from": "2026-05-11", "to": "2026-05-17"},
                "trace_upstream": [],
                "trace_data": [],
                "trace_events": [],
                "data_confidence": "MEDIUM",
                "notes": "test",
            },
            "data": {
                "target_iso_week": "2026-20",
                "source_versions": {},
                "prompt_blocks": {
                    "week": (
                        "**Week Advisory Summary**\n"
                        "week_objective: Stabilize aerobic re-entry.\n"
                        "planned_weekly_load_kj: 6700\n"
                    ),
                    "current_week_plan": (
                        "**Current Week Plan Snapshot**\n"
                        "Use this derived current-week plan summary directly before asking tools to rediscover the same workout list.\n"
                        "- Tue 2026-05-12 | QUALITY | Tempo Stabilization | 01:33 | 1017 kJ | start 18:00\n"
                    ),
                },
            },
        },
        producer_agent="test",
        run_id="test",
    )

    at = AppTest.from_file("src/rps/ui/pages/coach.py")
    at.run(timeout=10)
    at.run(timeout=10)

    assert len(at.error) == 0
    intro_count = sum(
        1 for markdown in at.markdown if "Context loaded for 2026-20." in str(markdown.value)
    )
    assert intro_count == 1
