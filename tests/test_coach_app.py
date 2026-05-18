import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType


@pytest.fixture(autouse=True)
def _env_setup(monkeypatch, tmp_path):
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-key")
    monkeypatch.setenv("ATHLETE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setattr(
        "rps.orchestrator.context_snapshots.fetch_current_week_activities_actual_payload",
        lambda **_: None,
    )


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
    assert "run_conversational_turn(" in source


def test_coach_preview_toolset_is_scoped_replan_only() -> None:
    source = Path("src/rps/ui/pages/coach.py").read_text(encoding="utf-8")
    assert 'preview_names = [\n        "preview_scoped_week_replan",' in source


def test_coach_source_no_longer_depends_on_rps_chatbot():
    source = Path("src/rps/ui/pages/coach.py").read_text(encoding="utf-8")
    assert "rps_chatbot" not in source
    assert "run_coach_flow(" in source
    assert "coach_turn_helpers" not in source


def test_workouts_editor_source_no_longer_depends_on_rps_chatbot():
    source = Path("src/rps/ui/pages/plan/workouts.py").read_text(encoding="utf-8")
    assert "rps_chatbot" not in source
    assert "run_conversational_turn(" in source


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
                "created_at": "2026-05-13T06:00:00Z",
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
                        "planned_workouts_table:\n"
                        "- Tue | 2026-05-12 | QUALITY | Tempo Stabilization | 01:33 | 1017 kJ\n"
                    ),
                },
            },
        },
        producer_agent="test",
        run_id="test",
    )
    store.save_document(
        athlete_id,
        ArtifactType.WEEK_PLAN,
        "2026-20",
        {
            "meta": {
                "artifact_type": "WEEK_PLAN",
                "schema_id": "WeekPlanInterface",
                "schema_version": "1.0",
                "version": "1.0",
                "authority": "Binding",
                "owner_agent": "Policy-Owner",
                "run_id": "week_run",
                "created_at": "2026-05-13T06:00:00Z",
                "scope": "Shared",
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
                "week_summary": {"week_objective": "Stabilize aerobic re-entry.", "planned_weekly_load_kj": 6700},
                "agenda": [
                    {
                        "day": "Tue",
                        "date": "2026-05-12",
                        "day_role": "QUALITY",
                        "planned_duration": "01:33",
                        "planned_kj": 1017,
                        "workout_id": "w1",
                    }
                ],
                "workouts": [
                    {"workout_id": "w1", "title": "Tempo Stabilization", "start": "18:00", "duration": "01:33"}
                ],
            },
        },
        producer_agent="test",
        run_id="test",
    )
    week_plan_version = store.resolve_week_version_key(athlete_id, ArtifactType.WEEK_PLAN, "2026-20")
    assert week_plan_version is not None
    monkeypatch.setattr(
        "rps.orchestrator.context_snapshots.fetch_current_week_activities_actual_payload",
        lambda **_: (_ for _ in ()).throw(AssertionError("unexpected live current-week fetch")),
    )
    store.save_document(
        athlete_id,
        ArtifactType.CURRENT_WEEK_STATUS_SNAPSHOT,
        "2026-20",
        {
            "meta": {
                "artifact_type": "CURRENT_WEEK_STATUS_SNAPSHOT",
                "schema_id": "CurrentWeekStatusSnapshotInterface",
                "schema_version": "1.0",
                "version": "1.0",
                "authority": "Derived",
                "owner_agent": "Policy-Owner",
                "run_id": "pending",
                "created_at": "2026-05-13T06:00:00Z",
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
                "source_versions": {"week_plan": week_plan_version, "current_week_activities_actual": "2026-20"},
                "prompt_blocks": {
                    "current_week_actuals": (
                        "**Current Week Actuals Snapshot**\n"
                        "target_iso_week: 2026-20\n"
                        "completed_sessions_count: 1\n"
                        "completed_moving_time: 01:33:00\n"
                        "completed_work_kj: 1017\n"
                        "completed_sessions_table:\n"
                        "- Tue | 2026-05-12 | Ride | Evening Ride | 01:33:00 | 1017 kJ | 0.78 | 96\n"
                    ),
                    "plan_vs_actual": (
                        "**Plan vs Actual Snapshot**\n"
                        "matched_planned_days_count: 1\n"
                        "open_planned_days_count: 1\n"
                        "unplanned_completed_days_count: 0\n"
                        "completed_work_kj_so_far: 1017\n"
                        "open_planned_days_table:\n"
                        "- Thu | 2026-05-14 | RECOVERY | Recovery Spin | 00:45 | 250 kJ\n"
                    ),
                },
            },
        },
        producer_agent="test",
        run_id="test",
    )

    at = AppTest.from_file("src/rps/ui/pages/coach.py")
    at.session_state["rps_state"] = {"athlete_id": athlete_id, "iso_year": 2026, "iso_week": 20}
    at.run(timeout=10)
    at.run(timeout=10)

    assert len(at.error) == 0
    intro_count = sum(
        1 for markdown in at.markdown if "Context loaded for 2026-20." in str(markdown.value)
    )
    assert intro_count == 1
    intro_text = "\n".join(str(markdown.value) for markdown in at.markdown)
    assert "**Current Week Actuals**" in intro_text
    assert "Completed sessions so far: 1" in intro_text
    assert "**Plan vs Actual**" in intro_text
    assert "Planned workouts:\n\n| Day | Date | Day-Role | Title | Planned Duration | Planned Load (kJ) |" in intro_text
    assert "Completed sessions:\n\n| Day | Date | Type | Title | Actual Duration | Actual Load (kJ) | IF | TSS |" in intro_text
    assert "Open planned day details:\n\n| Day | Date | Day-Role | Title | Planned Duration | Planned Load (kJ) |" in intro_text
    assert "| Day | Date | Day-Role | Title | Planned Duration | Planned Load (kJ) |" in intro_text
    assert "| Day | Date | Type | Title | Actual Duration | Actual Load (kJ) | IF | TSS |" in intro_text
    assert "| Tue | 2026-05-12 | QUALITY | Tempo Stabilization | 01:33 | 1017 kJ |" in intro_text
    assert "| Tue | 2026-05-12 | Ride | Evening Ride | 01:33:00 | 1017 kJ | 0.78 | 96 |" in intro_text
    assert "| Thu | 2026-05-14 | RECOVERY | Recovery Spin | 00:45 | 250 kJ |" in intro_text
    assert "**Pending Status**" not in intro_text
    assert "No pending coach operation." not in intro_text
