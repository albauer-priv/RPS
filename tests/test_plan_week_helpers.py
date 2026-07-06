from types import SimpleNamespace

import pytest

from rps.orchestrator.plan_week import (
    SnapshotPromptBlocks,
    _build_historical_context_line,
    _load_common_latest_payloads,
    _load_exact_range_payload,
    _load_week_version_payload,
    _prepare_snapshot_preflight,
    _resolve_previous_week_report_gate,
    _snapshot_freshness_error,
)
from rps.orchestrator.planning_evidence import PlanningEvidenceResolution
from rps.planning.contracts import PlanningContractIssue
from rps.workspace.iso_helpers import IsoWeek, IsoWeekRange
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType


def test_build_historical_context_line_renders_expected_versions() -> None:
    resolution = PlanningEvidenceResolution(
        target_week=IsoWeek(2026, 12),
        evidence_week=IsoWeek(2026, 11),
        activities_actual_version="2026-11",
        activities_trend_version="2026-11",
        des_analysis_report_version="2026-11",
    )

    line = _build_historical_context_line(resolution)

    assert "DES_ANALYSIS_REPORT version_key 2026-11" in line
    assert "ACTIVITIES_ACTUAL version_key 2026-11" in line
    assert "ACTIVITIES_TREND version_key 2026-11" in line
    assert "never use workspace_get_latest" in line


def test_build_historical_context_line_returns_empty_when_incomplete() -> None:
    resolution = PlanningEvidenceResolution(
        target_week=IsoWeek(2026, 12),
        evidence_week=IsoWeek(2026, 11),
        activities_actual_version="2026-11",
        activities_trend_version="2026-11",
        des_analysis_report_version=None,
    )

    assert _build_historical_context_line(resolution) == ""


def test_snapshot_freshness_error_returns_none_when_no_blockers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("rps.orchestrator.plan_week.validate_snapshot_freshness", lambda **_kwargs: [])

    error = _snapshot_freshness_error(
        snapshot_payload={"meta": {}},
        expected_source_versions={},
        snapshot_label="ATHLETE_STATE_SNAPSHOT",
        failure_prefix="Snapshot failed",
    )

    assert error is None


def test_snapshot_freshness_error_formats_blocker_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "rps.orchestrator.plan_week.validate_snapshot_freshness",
        lambda **_kwargs: [PlanningContractIssue("stale", "snapshot is stale", path="meta.trace")],
    )

    error = _snapshot_freshness_error(
        snapshot_payload={"meta": {}},
        expected_source_versions={},
        snapshot_label="ATHLETE_STATE_SNAPSHOT",
        failure_prefix="Snapshot failed",
    )

    assert error is not None
    assert error.startswith("Snapshot failed:")
    assert "BLOCKER stale" in error
    assert "meta.trace" in error


def test_prepare_snapshot_preflight_returns_prompt_blocks_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def _fake_snapshot_error(**kwargs):
        calls.append(kwargs["snapshot_label"])
        return None

    monkeypatch.setattr("rps.orchestrator.plan_week._snapshot_freshness_error", _fake_snapshot_error)
    monkeypatch.setattr(
        "rps.orchestrator.plan_week._build_snapshot_prompt_blocks",
        lambda *_args, **_kwargs: SnapshotPromptBlocks("athlete-block", "planning-block"),
    )

    outcome = _prepare_snapshot_preflight(
        athlete_state_snapshot={"meta": {}},
        planning_context_snapshot={"meta": {}},
        athlete_expected_source_versions={"a": "1"},
        planning_expected_source_versions={"b": "2"},
        athlete_failure_prefix="Athlete snapshot failed",
        planning_failure_prefix="Planning snapshot failed",
    )

    assert outcome.error is None
    assert outcome.prompt_blocks == SnapshotPromptBlocks("athlete-block", "planning-block")
    assert calls == ["ATHLETE_STATE_SNAPSHOT", "PLANNING_CONTEXT_SNAPSHOT"]


def test_prepare_snapshot_preflight_stops_on_first_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "rps.orchestrator.plan_week._snapshot_freshness_error",
        lambda **kwargs: "boom" if kwargs["snapshot_label"] == "ATHLETE_STATE_SNAPSHOT" else None,
    )

    outcome = _prepare_snapshot_preflight(
        athlete_state_snapshot={"meta": {}},
        planning_context_snapshot={"meta": {}},
        athlete_expected_source_versions={"a": "1"},
        planning_expected_source_versions={"b": "2"},
        athlete_failure_prefix="Athlete snapshot failed",
        planning_failure_prefix="Planning snapshot failed",
    )

    assert outcome.error == "boom"
    assert outcome.prompt_blocks is None


def test_load_common_latest_payloads_returns_saved_payloads_and_missing_none(tmp_path) -> None:
    store = LocalArtifactStore(root=tmp_path)
    athlete_id = "test_athlete"
    store.ensure_workspace(athlete_id)
    store.save_document(
        athlete_id,
        ArtifactType.AVAILABILITY,
        "2026-12",
        {"data": {"weekly_hours": {"typical": 12}}},
        producer_agent="test",
        run_id="availability",
        update_latest=True,
    )
    store.save_document(
        athlete_id,
        ArtifactType.LOGISTICS,
        "2026-12",
        {"data": {"events": []}},
        producer_agent="test",
        run_id="logistics",
        update_latest=True,
    )

    payloads = _load_common_latest_payloads(store, athlete_id)

    assert payloads.availability_payload == {"data": {"weekly_hours": {"typical": 12}}}
    assert payloads.logistics_payload == {"data": {"events": []}}
    assert payloads.kpi_profile_payload is None
    assert payloads.selection_payload is None


def test_load_week_version_payload_returns_payload_for_resolved_version(monkeypatch: pytest.MonkeyPatch) -> None:
    store = SimpleNamespace(
        resolve_week_version_key=lambda *_args: "2026-12",
        load_version=lambda *_args: {"data": {"ok": True}},
    )

    payload = _load_week_version_payload(store, "test_athlete", ArtifactType.PHASE_FEED_FORWARD, "2026-12")

    assert payload == {"data": {"ok": True}}


def test_load_week_version_payload_returns_none_when_version_missing() -> None:
    store = SimpleNamespace(
        resolve_week_version_key=lambda *_args: None,
        load_version=lambda *_args: {"data": {"ok": True}},
    )

    payload = _load_week_version_payload(store, "test_athlete", ArtifactType.PHASE_FEED_FORWARD, "2026-12")

    assert payload is None


def test_load_exact_range_payload_returns_payload_for_best_range_version() -> None:
    store = SimpleNamespace(load_version=lambda *_args: {"data": {"range": True}})
    index_query = SimpleNamespace(best_exact_range_version=lambda *_args: "2026-10--2026-13")

    payload = _load_exact_range_payload(
        store,
        index_query,
        "test_athlete",
        ArtifactType.PHASE_STRUCTURE,
        IsoWeekRange(start=IsoWeek(2026, 10), end=IsoWeek(2026, 13)),
    )

    assert payload == {"data": {"range": True}}


def test_load_exact_range_payload_returns_none_when_no_matching_version() -> None:
    store = SimpleNamespace(load_version=lambda *_args: {"data": {"range": True}})
    index_query = SimpleNamespace(best_exact_range_version=lambda *_args: None)

    payload = _load_exact_range_payload(
        store,
        index_query,
        "test_athlete",
        ArtifactType.PHASE_GUARDRAILS,
        IsoWeekRange(start=IsoWeek(2026, 10), end=IsoWeek(2026, 13)),
    )

    assert payload is None


def test_resolve_previous_week_report_gate_wraps_tuple_result(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    resolution = PlanningEvidenceResolution(
        target_week=IsoWeek(2026, 12),
        evidence_week=IsoWeek(2026, 11),
        activities_actual_version="2026-11",
        activities_trend_version="2026-11",
        des_analysis_report_version="2026-11",
    )
    monkeypatch.setattr(
        "rps.orchestrator.plan_week._ensure_previous_week_report",
        lambda *_args, **_kwargs: (resolution, {"data": {}}, {"ok": True}, None),
    )

    runtime_for = lambda _agent_name: SimpleNamespace(workspace_root=tmp_path, reasoning_effort=None, reasoning_summary=None)

    outcome = _resolve_previous_week_report_gate(
        runtime_for,
        athlete_id="test_athlete",
        target_week=IsoWeek(2026, 12),
        run_id="run_1",
    )

    assert outcome.evidence_resolution == resolution
    assert outcome.des_analysis_payload == {"data": {}}
    assert outcome.report_result == {"ok": True}
    assert outcome.error is None