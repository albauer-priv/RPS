from types import SimpleNamespace

from rps.orchestrator.advisory_actions import run_feed_forward_chain
from rps.workspace.iso_helpers import IsoWeek
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType

ATHLETE_ID = "test_athlete"
TARGET_WEEK = IsoWeek(year=2026, week=14)
SELECTED_WEEK_KEY = "2026-14"


def _generic_document(artifact_type: str) -> dict:
    return {
        "meta": {
            "artifact_type": artifact_type,
            "schema_id": "TestInterface",
            "schema_version": "1.0",
            "version": "1.0",
            "authority": "Binding",
            "owner_agent": "test",
            "run_id": f"seed_{artifact_type.lower()}",
            "created_at": "2026-04-01T00:00:00Z",
            "scope": "Shared",
            "iso_week": SELECTED_WEEK_KEY,
            "iso_week_range": SELECTED_WEEK_KEY,
            "temporal_scope": {"from": "2026-03-30", "to": "2026-04-05"},
            "trace_upstream": [],
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "UNKNOWN",
            "notes": "",
        },
        "data": {},
    }


def _seed(store: LocalArtifactStore, artifact_type: ArtifactType) -> None:
    store.save_document(
        ATHLETE_ID,
        artifact_type,
        SELECTED_WEEK_KEY,
        _generic_document(artifact_type.value),
        producer_agent="test",
        run_id=f"seed_{artifact_type.value.lower()}",
        update_latest=True,
    )


def _stub_noop_snapshot_helpers(monkeypatch) -> None:
    """Stub the snapshot/context-block collaborators so the chain's own control
    flow is exercised without needing fully realistic snapshot payloads."""
    monkeypatch.setattr(
        "rps.orchestrator.advisory_actions.save_athlete_state_snapshot", lambda *a, **k: {}
    )
    monkeypatch.setattr(
        "rps.orchestrator.advisory_actions.build_athlete_state_snapshot_prompt_block", lambda *a, **k: ""
    )
    monkeypatch.setattr(
        "rps.orchestrator.advisory_actions.save_planning_context_snapshot", lambda *a, **k: {}
    )
    monkeypatch.setattr(
        "rps.orchestrator.advisory_actions.build_planning_context_snapshot_prompt_block", lambda *a, **k: ""
    )
    monkeypatch.setattr("rps.orchestrator.advisory_actions.save_advisory_memory", lambda *a, **k: None)
    monkeypatch.setattr(
        "rps.orchestrator.advisory_actions.build_resolved_des_evaluation_context", lambda *a, **k: ""
    )


def _stub_phase_info(monkeypatch) -> None:
    fake_phase_info = SimpleNamespace(
        phase_id="phase_1",
        phase_range=SimpleNamespace(key=SELECTED_WEEK_KEY),
    )
    monkeypatch.setattr(
        "rps.orchestrator.advisory_actions.resolve_season_plan_phase_info",
        lambda *a, **k: fake_phase_info,
    )


def test_run_feed_forward_chain_report_failure_short_circuits(monkeypatch, tmp_path):
    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace(ATHLETE_ID)
    monkeypatch.setattr(
        "rps.orchestrator.advisory_actions.create_performance_report",
        lambda *a, **k: {"ok": False, "message": "missing activities"},
    )

    result = run_feed_forward_chain(
        lambda _agent_name: SimpleNamespace(workspace_root=tmp_path),
        workspace_root=tmp_path,
        athlete_id=ATHLETE_ID,
        target_week=TARGET_WEEK,
        run_id_prefix="ff_test",
    )

    assert result.ok is False
    assert result.report_ok is False
    assert result.season_phase_ok is False
    assert result.phase_ok is False
    assert result.error == "missing activities"


def test_run_feed_forward_chain_missing_season_plan_short_circuits(monkeypatch, tmp_path):
    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace(ATHLETE_ID)
    monkeypatch.setattr(
        "rps.orchestrator.advisory_actions.create_performance_report",
        lambda *a, **k: {"ok": True},
    )

    result = run_feed_forward_chain(
        lambda _agent_name: SimpleNamespace(workspace_root=tmp_path),
        workspace_root=tmp_path,
        athlete_id=ATHLETE_ID,
        target_week=TARGET_WEEK,
        run_id_prefix="ff_test",
    )

    assert result.ok is False
    assert result.report_ok is True
    assert result.season_phase_ok is False
    assert result.phase_ok is False
    assert result.error == "Season plan or covering phase context missing for feed forward."


def test_run_feed_forward_chain_season_phase_failure(monkeypatch, tmp_path):
    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace(ATHLETE_ID)
    _seed(store, ArtifactType.SEASON_PLAN)
    monkeypatch.setattr(
        "rps.orchestrator.advisory_actions.create_performance_report",
        lambda *a, **k: {"ok": True},
    )
    _stub_phase_info(monkeypatch)
    _stub_noop_snapshot_helpers(monkeypatch)
    monkeypatch.setattr(
        "rps.orchestrator.advisory_actions.run_feed_forward_flow",
        lambda **k: {"season_phase_result": {"ok": False}, "phase_result": {"ok": False}},
    )

    result = run_feed_forward_chain(
        lambda _agent_name: SimpleNamespace(workspace_root=tmp_path),
        workspace_root=tmp_path,
        athlete_id=ATHLETE_ID,
        target_week=TARGET_WEEK,
        run_id_prefix="ff_test",
    )

    assert result.ok is False
    assert result.report_ok is True
    assert result.season_phase_ok is False
    assert result.phase_ok is False
    assert result.error == "Season → Phase feed forward failed."


def test_run_feed_forward_chain_phase_failure(monkeypatch, tmp_path):
    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace(ATHLETE_ID)
    _seed(store, ArtifactType.SEASON_PLAN)
    _seed(store, ArtifactType.SEASON_PHASE_FEED_FORWARD)
    monkeypatch.setattr(
        "rps.orchestrator.advisory_actions.create_performance_report",
        lambda *a, **k: {"ok": True},
    )
    _stub_phase_info(monkeypatch)
    _stub_noop_snapshot_helpers(monkeypatch)
    monkeypatch.setattr(
        "rps.orchestrator.advisory_actions.run_feed_forward_flow",
        lambda **k: {"season_phase_result": {"ok": True}, "phase_result": {"ok": False}},
    )

    result = run_feed_forward_chain(
        lambda _agent_name: SimpleNamespace(workspace_root=tmp_path),
        workspace_root=tmp_path,
        athlete_id=ATHLETE_ID,
        target_week=TARGET_WEEK,
        run_id_prefix="ff_test",
    )

    assert result.ok is False
    assert result.report_ok is True
    assert result.season_phase_ok is True
    assert result.phase_ok is False
    assert result.season_phase_version_key == SELECTED_WEEK_KEY
    assert result.error == "Phase → Week feed forward failed."


def test_run_feed_forward_chain_success(monkeypatch, tmp_path):
    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace(ATHLETE_ID)
    _seed(store, ArtifactType.SEASON_PLAN)
    _seed(store, ArtifactType.DES_ANALYSIS_REPORT)
    _seed(store, ArtifactType.SEASON_PHASE_FEED_FORWARD)
    _seed(store, ArtifactType.PHASE_FEED_FORWARD)
    monkeypatch.setattr(
        "rps.orchestrator.advisory_actions.create_performance_report",
        lambda *a, **k: {"ok": True},
    )
    _stub_phase_info(monkeypatch)
    _stub_noop_snapshot_helpers(monkeypatch)
    monkeypatch.setattr(
        "rps.orchestrator.advisory_actions.build_resolved_season_phase_feed_forward_context",
        lambda *a, **k: "",
    )
    monkeypatch.setattr(
        "rps.orchestrator.advisory_actions.run_feed_forward_flow",
        lambda **k: {"season_phase_result": {"ok": True}, "phase_result": {"ok": True}},
    )

    result = run_feed_forward_chain(
        lambda _agent_name: SimpleNamespace(workspace_root=tmp_path),
        workspace_root=tmp_path,
        athlete_id=ATHLETE_ID,
        target_week=TARGET_WEEK,
        run_id_prefix="ff_test",
    )

    assert result.ok is True
    assert result.report_ok is True
    assert result.season_phase_ok is True
    assert result.phase_ok is True
    # DES_ANALYSIS_REPORT is week-scoped, so the store appends a generated
    # timestamp suffix to the bare week key used when seeding it.
    assert result.report_version_key is not None
    assert result.report_version_key.startswith(SELECTED_WEEK_KEY)
    assert result.season_phase_version_key == SELECTED_WEEK_KEY
    assert result.phase_version_key == SELECTED_WEEK_KEY
    assert result.error is None
