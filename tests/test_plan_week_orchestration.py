import json
import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from streamlit.testing.v1 import AppTest

from rps.orchestrator.plan_week import plan_week
from rps.workspace.index_manager import WorkspaceIndexManager
from rps.workspace.iso_helpers import IsoWeek
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType
from tests.planning_context_helpers import (
    mock_previous_week_report_gate as _mock_previous_week_report_gate,
)
from tests.planning_context_helpers import (
    patch_plan_week_exact_query as _patch_plan_week_exact_query,
)
from tests.planning_context_helpers import (
    season_plan_stub_payload as _season_plan_stub_payload,
)
from tests.planning_context_helpers import (
    seed_minimal_phase_test_context as _seed_minimal_phase_test_context,
)
from tests.planning_context_helpers import (
    seed_previous_week_planning_evidence as _seed_previous_week_planning_evidence,
)
from tests.planning_context_helpers import (
    write_contract_phase_docs as _write_contract_phase_docs,
)
from tests.planning_context_helpers import (
    write_minimal_scenario_chain as _write_minimal_scenario_chain,
)

MIN_PLAN_HUB_NUMBER_INPUTS = 2
JsonMap = dict[str, Any]


@pytest.fixture(autouse=True)
def _env_setup(monkeypatch, tmp_path):
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-key")
    monkeypatch.setenv("ATHLETE_ID", "test_athlete")
    monkeypatch.setenv("ATHLETE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("RPS_DISABLE_INTERVALS_REFRESH", "1")


def test_plan_week_force_phase_structure_rerun(monkeypatch, tmp_path):
    athlete_id = "test_athlete"
    year = 2026
    week = 12
    run_ids = []

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace(athlete_id)
    store.save_document(
        athlete_id,
        ArtifactType.SEASON_PLAN,
        "2026-11--2026-13",
        {
            **_season_plan_stub_payload(),
            "data": {
                "phases": [
                    {
                        **cast(dict[str, object], _season_plan_stub_payload()["data"])["phases"][0],
                        "scenario_cadence": "2:1",
                        "cadence_week_roles": ["LOAD_1", "LOAD_2", "DELOAD"],
                    }
                ]
            },
        },
        producer_agent="test",
        run_id="season_plan_test",
        update_latest=True,
    )
    _write_minimal_scenario_chain(store, athlete_id)
    _seed_previous_week_planning_evidence(store, athlete_id, target_year=year, target_week=week)
    store.save_document(
        athlete_id,
        ArtifactType.KPI_PROFILE,
        "sample_profile",
        {"data": {}},
        producer_agent="test",
        run_id="store_kpi_profile",
        update_latest=True,
    )
    store.latest_path(athlete_id, ArtifactType.PLANNING_EVENTS).write_text(
        json.dumps({"data": {"events": []}}),
        encoding="utf-8",
    )
    store.latest_path(athlete_id, ArtifactType.LOGISTICS).write_text(
        json.dumps({"data": {"events": []}}),
        encoding="utf-8",
    )
    for artifact_type in (
        ArtifactType.PHASE_GUARDRAILS,
        ArtifactType.PHASE_STRUCTURE,
        ArtifactType.PHASE_PREVIEW,
        ArtifactType.WEEK_PLAN,
        ArtifactType.INTERVALS_WORKOUTS,
    ):
        key = "2026-11--2026-13" if artifact_type in {
            ArtifactType.PHASE_GUARDRAILS,
            ArtifactType.PHASE_STRUCTURE,
            ArtifactType.PHASE_PREVIEW,
        } else "2026-12"
        store.versioned_path(athlete_id, artifact_type, key).write_text("{}", encoding="utf-8")

    runtime = SimpleNamespace(
        workspace_root=tmp_path,
        reasoning_effort=None,
        reasoning_summary=None,
    )
    _patch_plan_week_exact_query(monkeypatch, root=tmp_path, athlete_id=athlete_id)

    def _record_run_id(*_args, **kwargs):
        run_ids.append(kwargs["run_id"])
        return {"ok": True, "produced": True}

    monkeypatch.setattr("rps.orchestrator.plan_week._build_user_data_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr("rps.orchestrator.plan_week._build_kpi_selection_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(
        "rps.orchestrator.plan_week._ensure_previous_week_report",
        lambda *_args, **_kwargs: (
            SimpleNamespace(
                evidence_week=IsoWeek(2026, 11),
                activities_actual_version="2026-11",
                activities_trend_version="2026-11",
                des_analysis_report_version="2026-11",
            ),
            {},
            None,
            None,
        ),
    )
    monkeypatch.setattr(
        "rps.orchestrator.plan_week.run_agent_multi_output",
        _record_run_id,
    )
    monkeypatch.setattr(
        "rps.orchestrator.plan_week.run_workout_export",
        lambda *_args, **_kwargs: {"ran": False, "ok": True, "produced": False, "result": None},
    )

    result = plan_week(
        runtime,
        athlete_id=athlete_id,
        year=year,
        week=week,
        run_id="test_run",
        force_steps=["PHASE_STRUCTURE"],
    )

    assert any(step["agent"] == "phase_architect" for step in result.steps)
    assert run_ids == ["test_run_phase_bundle"]
    assert not result.ok



def test_plan_week_force_phase_guardrails_and_structure_reruns_preview(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    athlete_id = "test_athlete"
    year = 2026
    week = 12
    run_ids: list[str] = []

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace(athlete_id)
    season_plan_payload = _season_plan_stub_payload(weeks=("2026-11", "2026-12", "2026-13"))
    season_plan_data = cast(dict[str, object], season_plan_payload["data"])
    phase = cast(dict[str, object], cast(list[object], season_plan_data["phases"])[0])
    store.save_document(
        athlete_id,
        ArtifactType.SEASON_PLAN,
        "2026-11--2026-13",
        {
            **season_plan_payload,
            "data": {
                "phases": [
                    {
                        **phase,
                        "scenario_cadence": "2:1",
                        "cadence_week_roles": ["LOAD_1", "LOAD_2", "DELOAD"],
                    }
                ]
            },
        },
        producer_agent="test",
        run_id="season_plan_test",
        update_latest=True,
    )
    _write_minimal_scenario_chain(store, athlete_id)
    _seed_previous_week_planning_evidence(store, athlete_id, target_year=year, target_week=week)
    store.save_document(
        athlete_id,
        ArtifactType.KPI_PROFILE,
        "sample_profile",
        {"data": {}},
        producer_agent="test",
        run_id="store_kpi_profile",
        update_latest=True,
    )
    store.latest_path(athlete_id, ArtifactType.PLANNING_EVENTS).write_text(
        json.dumps({"data": {"events": []}}),
        encoding="utf-8",
    )
    store.latest_path(athlete_id, ArtifactType.LOGISTICS).write_text(
        json.dumps({"data": {"events": []}}),
        encoding="utf-8",
    )
    for artifact_type in (
        ArtifactType.PHASE_GUARDRAILS,
        ArtifactType.PHASE_STRUCTURE,
        ArtifactType.PHASE_PREVIEW,
    ):
        store.save_document(
            athlete_id,
            artifact_type,
            "2026-11--2026-13",
            {
                "meta": {
                    "artifact_type": artifact_type.value,
                    "iso_week": "2026-12",
                    "iso_week_range": "2026-11--2026-13",
                },
                "data": {},
            },
            producer_agent="test",
            run_id=f"{artifact_type.value.lower()}_test",
            update_latest=True,
        )

    runtime = SimpleNamespace(
        workspace_root=tmp_path,
        reasoning_effort=None,
        reasoning_summary=None,
    )
    _patch_plan_week_exact_query(monkeypatch, root=tmp_path, athlete_id=athlete_id)

    monkeypatch.setattr("rps.orchestrator.plan_week._build_user_data_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr("rps.orchestrator.plan_week._build_kpi_selection_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(
        "rps.orchestrator.plan_week._ensure_previous_week_report",
        lambda *_args, **_kwargs: (
            SimpleNamespace(
                evidence_week=IsoWeek(2026, 11),
                activities_actual_version="2026-11",
                activities_trend_version="2026-11",
                des_analysis_report_version="2026-11",
            ),
            {},
            None,
            None,
        ),
    )
    def _record_run_id(*_args, **kwargs):
        run_ids.append(kwargs["run_id"])
        for task in kwargs["tasks"]:
            artifact_type = ArtifactType[task.value.removeprefix("CREATE_")]
            store.save_document(
                athlete_id,
                artifact_type,
                "2026-11--2026-13",
                {
                    "meta": {
                        "artifact_type": artifact_type.value,
                        "iso_week": "2026-12",
                        "iso_week_range": "2026-11--2026-13",
                    },
                    "data": {},
                },
                producer_agent="test",
                run_id=kwargs["run_id"],
                update_latest=True,
            )
        return {"ok": True, "produced": True}

    monkeypatch.setattr("rps.orchestrator.plan_week.run_agent_multi_output", _record_run_id)
    monkeypatch.setattr(
        "rps.orchestrator.plan_week.run_workout_export",
        lambda *_args, **_kwargs: {"ran": False, "ok": True, "produced": False, "result": None},
    )

    result = plan_week(
        runtime,
        athlete_id=athlete_id,
        year=year,
        week=week,
        run_id="test_run",
        force_steps=["PHASE_GUARDRAILS", "PHASE_STRUCTURE"],
    )

    assert run_ids == ["test_run_phase_bundle"]
    assert result.ok



def test_plan_week_force_phase_guardrails_runs_in_isolation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    athlete_id = "test_athlete"
    year = 2026
    week = 12
    written_types: list[ArtifactType] = []

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace(athlete_id)
    season_plan_payload = _season_plan_stub_payload(weeks=("2026-11", "2026-12", "2026-13"))
    season_plan_data = cast(dict[str, object], season_plan_payload["data"])
    phase = cast(dict[str, object], cast(list[object], season_plan_data["phases"])[0])
    store.save_document(
        athlete_id,
        ArtifactType.SEASON_PLAN,
        "2026-11--2026-13",
        {
            **season_plan_payload,
            "data": {
                "phases": [
                    {
                        **phase,
                        "scenario_cadence": "2:1",
                        "cadence_week_roles": ["LOAD_1", "LOAD_2", "DELOAD"],
                    }
                ]
            },
        },
        producer_agent="test",
        run_id="season_plan_test",
        update_latest=True,
    )
    _write_minimal_scenario_chain(store, athlete_id)
    _seed_previous_week_planning_evidence(store, athlete_id, target_year=year, target_week=week)
    store.save_document(
        athlete_id,
        ArtifactType.KPI_PROFILE,
        "sample_profile",
        {"data": {}},
        producer_agent="test",
        run_id="store_kpi_profile",
        update_latest=True,
    )
    store.latest_path(athlete_id, ArtifactType.PLANNING_EVENTS).write_text(
        json.dumps({"data": {"events": []}}),
        encoding="utf-8",
    )
    store.latest_path(athlete_id, ArtifactType.LOGISTICS).write_text(
        json.dumps({"data": {"events": []}}),
        encoding="utf-8",
    )

    runtime = SimpleNamespace(
        workspace_root=tmp_path,
        reasoning_effort=None,
        reasoning_summary=None,
    )
    _patch_plan_week_exact_query(monkeypatch, root=tmp_path, athlete_id=athlete_id)

    monkeypatch.setattr("rps.orchestrator.plan_week._build_user_data_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr("rps.orchestrator.plan_week._build_kpi_selection_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(
        "rps.orchestrator.plan_week._ensure_previous_week_report",
        lambda *_args, **_kwargs: (
            SimpleNamespace(
                evidence_week=IsoWeek(2026, 11),
                activities_actual_version="2026-11",
                activities_trend_version="2026-11",
                des_analysis_report_version="2026-11",
            ),
            {},
            None,
            None,
        ),
    )

    def _fake_run_agent_multi_output(*_args, **kwargs):
        task_value = kwargs["tasks"][0].value
        if task_value == "CREATE_PHASE_GUARDRAILS":
            payload = {
                "meta": {
                    "artifact_type": "PHASE_GUARDRAILS",
                    "version_key": "2026-11--2026-13",
                    "iso_week_range": "2026-11--2026-13",
                    "created_at": "2026-04-13T00:00:00Z",
                },
                "data": {},
            }
            store.save_document(
                athlete_id,
                ArtifactType.PHASE_GUARDRAILS,
                "2026-11--2026-13",
                payload,
                producer_agent="phase_architect",
                run_id=kwargs["run_id"],
                update_latest=True,
            )
            written_types.append(ArtifactType.PHASE_GUARDRAILS)
        elif task_value == "CREATE_PHASE_STRUCTURE":
            pytest.fail("Isolated PHASE_GUARDRAILS run must not trigger PHASE_STRUCTURE.")
        elif task_value == "CREATE_PHASE_PREVIEW":
            pytest.fail("Isolated PHASE_GUARDRAILS run must not trigger PHASE_PREVIEW.")
        return {"ok": True, "produced": True}

    monkeypatch.setattr("rps.orchestrator.plan_week.run_agent_multi_output", _fake_run_agent_multi_output)
    monkeypatch.setattr(
        "rps.orchestrator.plan_week.run_workout_export",
        lambda *_args, **_kwargs: pytest.fail("Isolated PHASE_GUARDRAILS run must not reach workout export."),
    )

    result = plan_week(
        runtime,
        athlete_id=athlete_id,
        year=year,
        week=week,
        run_id="test_run",
        force_steps=["PHASE_GUARDRAILS"],
    )

    assert result.ok is True
    assert written_types == [ArtifactType.PHASE_GUARDRAILS]
    index = WorkspaceIndexManager(root=tmp_path, athlete_id=athlete_id).load()
    versions = index["artefacts"][ArtifactType.PHASE_GUARDRAILS.value]["versions"]
    record = next(iter(versions.values()))
    assert record["iso_week_range"] == "2026-11--2026-13"



def test_plan_week_logs_effective_phase_steps_when_preview_is_bundled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    athlete_id = "test_athlete"
    year = 2026
    week = 12
    season_plan_payload = _season_plan_stub_payload()
    season_plan_meta = cast(JsonMap, season_plan_payload["meta"])
    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace(athlete_id)
    store.save_document(
        athlete_id,
        ArtifactType.SEASON_PLAN,
        "2026-11",
        {
            **season_plan_payload,
            "meta": {
                **season_plan_meta,
                "artifact_type": "SEASON_PLAN",
                "version_key": "2026-11",
                "iso_week": "2026-11",
                "created_at": "2026-04-02T00:00:00Z",
            },
        },
        producer_agent="season_planner",
        run_id="seed",
        update_latest=True,
    )
    _write_minimal_scenario_chain(store, athlete_id)
    _seed_minimal_phase_test_context(store, athlete_id, target_year=year, target_week=week)
    store.save_document(
        athlete_id,
        ArtifactType.PHASE_GUARDRAILS,
        "2026-11--2026-13__old",
        {
            "meta": {
                "artifact_type": "PHASE_GUARDRAILS",
                "version_key": "2026-11--2026-13__old",
                "iso_week_range": "2026-11--2026-13",
                "created_at": "2026-04-01T00:00:00Z",
            },
            "data": {},
        },
        producer_agent="phase_architect",
        run_id="seed",
        update_latest=True,
    )
    store.save_document(
        athlete_id,
        ArtifactType.PHASE_STRUCTURE,
        "2026-11--2026-13__old",
        {
            "meta": {
                "artifact_type": "PHASE_STRUCTURE",
                "version_key": "2026-11--2026-13__old",
                "iso_week_range": "2026-11--2026-13",
                "created_at": "2026-04-01T00:00:00Z",
            },
            "data": {},
        },
        producer_agent="phase_architect",
        run_id="seed",
        update_latest=True,
    )
    store.save_document(
        athlete_id,
        ArtifactType.PHASE_PREVIEW,
        "2026-11--2026-13__old",
        {
            "meta": {
                "artifact_type": "PHASE_PREVIEW",
                "version_key": "2026-11--2026-13__old",
                "iso_week_range": "2026-11--2026-13",
                "created_at": "2026-04-01T00:00:00Z",
            },
            "data": {},
        },
        producer_agent="phase_architect",
        run_id="seed",
        update_latest=True,
    )

    runtime = SimpleNamespace(
        workspace_root=tmp_path,
        reasoning_effort=None,
        reasoning_summary=None,
    )
    _patch_plan_week_exact_query(monkeypatch, root=tmp_path, athlete_id=athlete_id)

    monkeypatch.setattr("rps.orchestrator.plan_week._build_user_data_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr("rps.orchestrator.plan_week._build_kpi_selection_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr("rps.orchestrator.plan_week._resolve_latest_historical_week_versions", lambda *_args, **_kwargs: {})
    monkeypatch.setattr("rps.orchestrator.plan_week.build_athlete_state_snapshot_prompt_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr("rps.orchestrator.plan_week.build_planning_context_snapshot_prompt_block", lambda *_args, **_kwargs: "")
    _mock_previous_week_report_gate(monkeypatch)

    def _fake_run_agent_multi_output(*_args, **kwargs):
        for idx, task in enumerate(kwargs["tasks"]):
            artifact_type = ArtifactType[task.value.removeprefix("CREATE_")]
            store.save_document(
                athlete_id,
                artifact_type,
                "2026-11--2026-13__new",
                {
                    "meta": {
                        "artifact_type": artifact_type.value,
                        "version_key": "2026-11--2026-13__new",
                        "iso_week_range": "2026-11--2026-13",
                        "created_at": f"2026-04-03T00:00:0{idx}Z",
                    },
                    "data": {},
                },
                producer_agent="phase_architect",
                run_id=kwargs["run_id"],
                update_latest=True,
            )
        return {"ok": True, "produced": True}

    monkeypatch.setattr("rps.orchestrator.plan_week.run_agent_multi_output", _fake_run_agent_multi_output)
    monkeypatch.setattr(
        "rps.orchestrator.plan_week.run_workout_export",
        lambda *_args, **_kwargs: pytest.fail("Scoped phase run must not reach workout export."),
    )

    with caplog.at_level(logging.INFO, logger="rps.orchestrator.plan_week"):
        result = plan_week(
            runtime,
            athlete_id=athlete_id,
            year=year,
            week=week,
            run_id="test_run",
            force_steps=["PHASE_STRUCTURE"],
        )

    assert result.ok is True
    assert "forced_steps=['PHASE_STRUCTURE', 'PHASE_PREVIEW']" in caplog.text



def test_plan_week_scoped_phase_failure_does_not_log_completion(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    athlete_id = "test_athlete"
    year, week = 2026, 12

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace(athlete_id)
    season_plan_payload = _season_plan_stub_payload(weeks=("2026-11", "2026-12", "2026-13"))
    season_plan_data = cast(dict[str, object], season_plan_payload["data"])
    phase = cast(dict[str, object], cast(list[object], season_plan_data["phases"])[0])
    store.save_document(
        athlete_id,
        ArtifactType.SEASON_PLAN,
        "2026-11--2026-13",
        {
            **season_plan_payload,
            "data": {
                "phases": [
                    {
                        **phase,
                        "scenario_cadence": "2:1",
                        "cadence_week_roles": ["LOAD_1", "LOAD_2", "DELOAD"],
                    }
                ]
            },
        },
        producer_agent="test",
        run_id="season_plan_test",
        update_latest=True,
    )
    _write_minimal_scenario_chain(store, athlete_id)
    _seed_minimal_phase_test_context(store, athlete_id, target_year=year, target_week=week)
    for artifact_type in (ArtifactType.PHASE_GUARDRAILS, ArtifactType.PHASE_STRUCTURE, ArtifactType.PHASE_PREVIEW):
        store.save_document(
            athlete_id,
            artifact_type,
            "2026-11--2026-13__old",
            {
                "meta": {
                    "artifact_type": artifact_type.value,
                    "version_key": "2026-11--2026-13__old",
                    "iso_week_range": "2026-11--2026-13",
                    "created_at": "2026-04-01T00:00:00Z",
                },
                "data": {},
            },
            producer_agent="phase_architect",
            run_id="seed",
            update_latest=True,
        )

    runtime = SimpleNamespace(
        workspace_root=tmp_path,
        reasoning_effort=None,
        reasoning_summary=None,
    )
    _patch_plan_week_exact_query(monkeypatch, root=tmp_path, athlete_id=athlete_id)

    monkeypatch.setattr("rps.orchestrator.plan_week._build_user_data_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr("rps.orchestrator.plan_week._build_kpi_selection_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr("rps.orchestrator.plan_week._resolve_latest_historical_week_versions", lambda *_args, **_kwargs: {})
    monkeypatch.setattr("rps.orchestrator.plan_week.build_athlete_state_snapshot_prompt_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr("rps.orchestrator.plan_week.build_planning_context_snapshot_prompt_block", lambda *_args, **_kwargs: "")
    _mock_previous_week_report_gate(monkeypatch)
    monkeypatch.setattr(
        "rps.orchestrator.plan_week.run_agent_multi_output",
        lambda *_args, **_kwargs: {"ok": False, "error": "guardrail failed"},
    )

    with caplog.at_level(logging.INFO, logger="rps.orchestrator.plan_week"):
        result = plan_week(
            runtime,
            athlete_id=athlete_id,
            year=year,
            week=week,
            run_id="test_run",
            force_steps=["PHASE_GUARDRAILS"],
        )

    assert result.ok is False
    assert "Scoped phase run failed for range 2026-11--2026-13." in caplog.text
    assert "Scoped phase run completed for range 2026-11--2026-13" not in caplog.text



def test_plan_week_phase_architect_omits_direct_kpi_guidance(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    athlete_id = "test_athlete"
    captured_inputs: list[str] = []

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace(athlete_id)
    season_plan_payload = _season_plan_stub_payload(weeks=("2026-11", "2026-12", "2026-13"))
    season_plan_data = cast(dict[str, object], season_plan_payload["data"])
    phase = cast(dict[str, object], cast(list[object], season_plan_data["phases"])[0])
    store.save_document(
        athlete_id,
        ArtifactType.SEASON_PLAN,
        "2026-11--2026-13",
        {
            **season_plan_payload,
            "data": {
                "phases": [
                    {
                        **phase,
                        "scenario_cadence": "2:1",
                        "cadence_week_roles": ["LOAD_1", "LOAD_2", "DELOAD"],
                    }
                ]
            },
        },
        producer_agent="test",
        run_id="season_plan_test",
        update_latest=True,
    )
    _write_minimal_scenario_chain(store, athlete_id)
    selection_doc = store.load_latest(athlete_id, ArtifactType.SEASON_SCENARIO_SELECTION)
    selection_data = dict(cast(dict[str, object], selection_doc.get("data", {}))) if isinstance(selection_doc, dict) else {}
    selection_data["kpi_moving_time_rate_guidance_selection"] = {
        "segment": "fast_competitive",
        "w_per_kg": {"min": 2.5, "max": 3.0},
        "kj_per_kg_per_hour": {"min": 20, "max": 24},
    }
    store.save_document(
        athlete_id,
        ArtifactType.SEASON_SCENARIO_SELECTION,
        "2026-12",
        {"data": selection_data},
        producer_agent="user",
        run_id="test_selection",
        update_latest=True,
    )
    _seed_minimal_phase_test_context(store, athlete_id, target_year=2026, target_week=12)
    generic_input = {"meta": {"artifact_type": "GENERIC"}, "data": {}}
    store.save_document(
        athlete_id,
        ArtifactType.ACTIVITIES_ACTUAL,
        "2026-11",
        generic_input,
        producer_agent="test",
        run_id="store_activities_actual_202611",
        update_latest=False,
    )
    store.save_document(
        athlete_id,
        ArtifactType.ACTIVITIES_TREND,
        "2026-11",
        generic_input,
        producer_agent="test",
        run_id="store_activities_trend_202611",
        update_latest=False,
    )
    store.latest_path(athlete_id, ArtifactType.AVAILABILITY).write_text(
        json.dumps(
            {
                "data": {
                    "weekly_hours": {"min": 10.5, "typical": 14.0, "max": 17.5},
                    "fixed_rest_days": ["Mon", "Fri"],
                    "availability_table": [
                        {
                            "weekday": "Tue",
                            "hours_min": 1.5,
                            "hours_typical": 2.0,
                            "hours_max": 2.5,
                            "indoor_possible": True,
                            "travel_risk": "LOW",
                            "locked": False,
                        }
                    ],
                    "source_type": "manual",
                    "source_ref": "ui",
                    "notes": "",
                }
            }
        ),
        encoding="utf-8",
    )
    store.latest_path(athlete_id, ArtifactType.PLANNING_EVENTS).write_text(
        json.dumps(
            {
                "data": {
                    "events": [
                        {
                            "type": "B",
                            "priority_rank": 2,
                            "event_name": "Spring 200",
                            "date": "2026-03-18",
                            "event_type": "Brevet",
                            "goal": "rehearsal",
                            "distance_km": 200,
                            "elevation_m": 1800,
                            "expected_duration": "08:00",
                            "time_limit": "13:30",
                        },
                        {
                            "type": "A",
                            "priority_rank": 1,
                            "event_name": "Main 400",
                            "date": "2026-05-10",
                            "event_type": "Brevet",
                            "goal": "finish strong",
                            "distance_km": 400,
                            "elevation_m": 3600,
                            "expected_duration": "18:00",
                            "time_limit": "27:00",
                        },
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    runtime = SimpleNamespace(
        workspace_root=tmp_path,
        reasoning_effort=None,
        reasoning_summary=None,
    )

    monkeypatch.setattr("rps.orchestrator.plan_week._build_user_data_block", lambda *_args, **_kwargs: "")
    _mock_previous_week_report_gate(monkeypatch)

    def _fake_run_agent_multi_output(*_args, **kwargs):
        captured_inputs.append(kwargs["user_input"])
        payload = {
            "meta": {
                "artifact_type": "PHASE_GUARDRAILS",
                "version_key": "2026-11--2026-13",
                "iso_week_range": "2026-11--2026-13",
                "created_at": "2026-04-13T00:00:00Z",
            },
            "data": {},
        }
        store.save_document(
            athlete_id,
            ArtifactType.PHASE_GUARDRAILS,
            "2026-11--2026-13",
            payload,
            producer_agent="phase_architect",
            run_id=kwargs["run_id"],
            update_latest=True,
        )
        return {"ok": True, "produced": True}

    monkeypatch.setattr("rps.orchestrator.plan_week.run_agent_multi_output", _fake_run_agent_multi_output)
    monkeypatch.setattr(
        "rps.orchestrator.plan_week.run_workout_export",
        lambda *_args, **_kwargs: pytest.fail("Isolated PHASE_GUARDRAILS run must not reach workout export."),
    )

    result = plan_week(
        runtime,
        athlete_id=athlete_id,
        year=2026,
        week=12,
        run_id="test_run",
        force_steps=["PHASE_GUARDRAILS"],
    )

    assert result.ok is True
    assert captured_inputs
    assert all("Selected KPI guidance:" not in user_input for user_input in captured_inputs)
    assert all("ACTIVITIES_ACTUAL version_key 2026-11" in user_input for user_input in captured_inputs)
    assert all("ACTIVITIES_TREND version_key 2026-11" in user_input for user_input in captured_inputs)
    assert all("**Resolved Phase Context**" in user_input for user_input in captured_inputs)
    assert all("phase_iso_week_range: 2026-11--2026-13" in user_input for user_input in captured_inputs)
    assert all("**Resolved Availability Context**" in user_input for user_input in captured_inputs)
    assert all("fixed_rest_days: Mon, Fri" in user_input for user_input in captured_inputs)
    assert all("**Resolved Planning Event Context**" in user_input for user_input in captured_inputs)
    assert all("Spring 200" in user_input for user_input in captured_inputs)
    assert all("**Deterministic Phase Execution Context**" in user_input for user_input in captured_inputs)
    assert all("required_phase_weeks: 2026-11, 2026-12, 2026-13" in user_input for user_input in captured_inputs)



def test_plan_week_week_planner_uses_historical_activity_versions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    athlete_id = "test_athlete"
    captured_inputs: list[str] = []

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace(athlete_id)
    store.save_document(
        athlete_id,
        ArtifactType.SEASON_PLAN,
        "2026-11--2026-13",
        _season_plan_stub_payload(),
        producer_agent="test",
        run_id="season_plan_test",
        update_latest=True,
    )
    _write_minimal_scenario_chain(store, athlete_id)
    for artifact_type in (
        ArtifactType.PHASE_GUARDRAILS,
        ArtifactType.PHASE_STRUCTURE,
        ArtifactType.PHASE_PREVIEW,
    ):
        store.save_document(
            athlete_id,
            artifact_type,
            "2026-11--2026-13",
            {"meta": {"artifact_type": artifact_type.value, "iso_week_range": "2026-11--2026-13"}, "data": {}},
            producer_agent="phase_architect",
            run_id=f"store_{artifact_type.value.lower()}",
            update_latest=True,
        )
    _write_contract_phase_docs(store, athlete_id)
    store.save_document(
        athlete_id,
        ArtifactType.ACTIVITIES_ACTUAL,
        "2026-11",
        {"meta": {"artifact_type": "ACTIVITIES_ACTUAL", "iso_week": "2026-11"}, "data": {}},
        producer_agent="pipeline",
        run_id="store_activities_actual_202611",
        update_latest=True,
    )
    store.save_document(
        athlete_id,
        ArtifactType.ACTIVITIES_TREND,
        "2026-11",
        {"meta": {"artifact_type": "ACTIVITIES_TREND", "iso_week": "2026-11"}, "data": {}},
        producer_agent="pipeline",
        run_id="store_activities_trend_202611",
        update_latest=True,
    )
    _seed_minimal_phase_test_context(store, athlete_id, target_year=2026, target_week=12)

    runtime = SimpleNamespace(
        workspace_root=tmp_path,
        reasoning_effort=None,
        reasoning_summary=None,
    )

    monkeypatch.setattr("rps.orchestrator.plan_week._build_user_data_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr("rps.orchestrator.plan_week._build_kpi_selection_block", lambda *_args, **_kwargs: "")
    _mock_previous_week_report_gate(monkeypatch)

    def _fake_run_agent_multi_output(*_args, **kwargs):
        captured_inputs.append(kwargs["user_input"])
        return {"ok": True, "produced": True}

    monkeypatch.setattr("rps.orchestrator.plan_week.run_agent_multi_output", _fake_run_agent_multi_output)
    monkeypatch.setattr(
        "rps.orchestrator.plan_week.run_workout_export",
        lambda *_args, **_kwargs: {"ran": False, "ok": True, "produced": False, "result": None},
    )

    result = plan_week(
        runtime,
        athlete_id=athlete_id,
        year=2026,
        week=12,
        run_id="test_run",
    )

    assert result.ok is True
    assert captured_inputs
    assert any("ACTIVITIES_ACTUAL version_key 2026-11" in user_input for user_input in captured_inputs)
    assert any("ACTIVITIES_TREND version_key 2026-11" in user_input for user_input in captured_inputs)
    assert any(
        "use workspace_get_version with version_key 2026-11--2026-13 for both PHASE_GUARDRAILS and PHASE_STRUCTURE"
        in user_input
        for user_input in captured_inputs
    )



def test_plan_week_week_planner_injects_wellness_body_mass_for_kpi_gating(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    athlete_id = "test_athlete"
    captured_inputs: list[str] = []

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace(athlete_id)
    store.save_document(
        athlete_id,
        ArtifactType.SEASON_PLAN,
        "2026-11--2026-13",
        _season_plan_stub_payload(),
        producer_agent="test",
        run_id="season_plan_test",
        update_latest=True,
    )
    _write_minimal_scenario_chain(store, athlete_id)
    for artifact_type in (
        ArtifactType.PHASE_GUARDRAILS,
        ArtifactType.PHASE_STRUCTURE,
        ArtifactType.PHASE_PREVIEW,
    ):
        store.save_document(
            athlete_id,
            artifact_type,
            "2026-11--2026-13",
            {"meta": {"artifact_type": artifact_type.value, "iso_week_range": "2026-11--2026-13"}, "data": {}},
            producer_agent="phase_architect",
            run_id=f"store_{artifact_type.value.lower()}",
            update_latest=True,
        )
    _write_contract_phase_docs(store, athlete_id)
    store.save_document(
        athlete_id,
        ArtifactType.WELLNESS,
        "2026-11",
        {
            "meta": {"artifact_type": "WELLNESS", "iso_week": "2026-11"},
            "data": {"body_mass_kg": 82.4},
        },
        producer_agent="pipeline",
        run_id="store_wellness_202611",
        update_latest=True,
    )
    store.save_document(
        athlete_id,
        ArtifactType.ACTIVITIES_ACTUAL,
        "2026-11",
        {"meta": {"artifact_type": "ACTIVITIES_ACTUAL", "iso_week": "2026-11"}, "data": {}},
        producer_agent="pipeline",
        run_id="store_activities_actual_202611",
        update_latest=True,
    )
    store.save_document(
        athlete_id,
        ArtifactType.ACTIVITIES_TREND,
        "2026-11",
        {"meta": {"artifact_type": "ACTIVITIES_TREND", "iso_week": "2026-11"}, "data": {}},
        producer_agent="pipeline",
        run_id="store_activities_trend_202611",
        update_latest=True,
    )
    store.save_document(
        athlete_id,
        ArtifactType.SEASON_SCENARIO_SELECTION,
        "2026-12",
        {
            "data": {
                "kpi_moving_time_rate_guidance_selection": {
                    "segment": "fast_competitive",
                    "w_per_kg": {"min": 2.5, "max": 3.0},
                    "kj_per_kg_per_hour": {"min": 20, "max": 24},
                }
            }
        },
        producer_agent="user",
        run_id="store_selection_202612",
        update_latest=True,
    )
    _write_minimal_scenario_chain(store, athlete_id)
    store.latest_path(athlete_id, ArtifactType.AVAILABILITY).write_text(
        json.dumps(
            {
                "data": {
                    "weekly_hours": {"min": 10.5, "typical": 14.0, "max": 17.5},
                    "fixed_rest_days": ["Mon", "Fri"],
                    "availability_table": [
                        {
                            "weekday": "Tue",
                            "hours_min": 1.5,
                            "hours_typical": 2.0,
                            "hours_max": 2.5,
                            "indoor_possible": True,
                            "travel_risk": "LOW",
                            "locked": False,
                        }
                    ],
                    "source_type": "manual",
                    "source_ref": "ui",
                    "notes": "",
                }
            }
        ),
        encoding="utf-8",
    )
    store.latest_path(athlete_id, ArtifactType.PLANNING_EVENTS).write_text(
        json.dumps(
            {
                "data": {
                    "events": [
                        {
                            "type": "B",
                            "priority_rank": 2,
                            "event_name": "Spring 200",
                            "date": "2026-03-18",
                            "event_type": "Brevet",
                            "goal": "rehearsal",
                            "distance_km": 200,
                            "elevation_m": 1800,
                            "expected_duration": "08:00",
                            "time_limit": "13:30",
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    store.latest_path(athlete_id, ArtifactType.LOGISTICS).write_text(
        json.dumps({"data": {"events": []}}),
        encoding="utf-8",
    )
    store.save_document(
        athlete_id,
        ArtifactType.KPI_PROFILE,
        "sample_profile",
        {
            "data": {
                "durability": {
                    "moving_time_rate_guidance": {
                        "derived_from": "kpi_profile_v1",
                        "notes": "Use selected segment directly.",
                        "bands": [
                            {
                                "segment": "fast_competitive",
                                "w_per_kg": {"min": 2.5, "max": 3.0},
                                "kj_per_kg_per_hour": {"min": 20, "max": 24},
                                "basis": "validated",
                            }
                        ],
                    }
                }
            }
        },
        producer_agent="user",
        run_id="store_kpi_profile_202612",
        update_latest=True,
    )

    runtime = SimpleNamespace(
        workspace_root=tmp_path,
        reasoning_effort=None,
        reasoning_summary=None,
    )

    monkeypatch.setattr("rps.orchestrator.plan_week._build_user_data_block", lambda *_args, **_kwargs: "")
    _mock_previous_week_report_gate(monkeypatch)

    def _fake_run_agent_multi_output(*_args, **kwargs):
        captured_inputs.append(kwargs["user_input"])
        return {"ok": True, "produced": True}

    monkeypatch.setattr("rps.orchestrator.plan_week.run_agent_multi_output", _fake_run_agent_multi_output)
    monkeypatch.setattr(
        "rps.orchestrator.plan_week.run_workout_export",
        lambda *_args, **_kwargs: {"ran": False, "ok": True, "produced": False, "result": None},
    )

    result = plan_week(
        runtime,
        athlete_id=athlete_id,
        year=2026,
        week=12,
        run_id="test_run",
    )

    assert result.ok is True
    assert captured_inputs
    assert any("WELLNESS.data.body_mass_kg is present and authoritative for KPI gating: 82.4 kg." in user_input for user_input in captured_inputs)
    assert any("Use WELLNESS.data.body_mass_kg for any kJ/kg/h or W/kg gating" in user_input for user_input in captured_inputs)
    assert any("**Resolved KPI Context**" in user_input for user_input in captured_inputs)
    assert any("**Deterministic Workout Load Estimation Context**" in user_input for user_input in captured_inputs)
    assert any("selected_kpi_rate_band_selector: fast_competitive" in user_input for user_input in captured_inputs)
    assert any("kpi_profile_moving_time_rate_guidance.available_bands:" in user_input for user_input in captured_inputs)



def test_plan_week_injects_resolved_activity_context(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured_inputs: list[str] = []

    def _fake_run_agent_multi_output(*_args, **kwargs):
        captured_inputs.append(kwargs["user_input"])
        task_values = [task.value for task in kwargs["tasks"]]
        return {"ok": True, "produced": True, "tasks": task_values}

    monkeypatch.setattr("rps.orchestrator.plan_week.run_agent_multi_output", _fake_run_agent_multi_output)
    monkeypatch.setattr(
        "rps.orchestrator.plan_week.run_workout_export",
        lambda **_kwargs: {"ran": False, "result": {"ok": True, "produced": False}},
    )

    store = LocalArtifactStore(root=tmp_path)
    athlete_id = "athlete1"
    store.ensure_workspace(athlete_id)
    _write_minimal_scenario_chain(store, athlete_id, version_key="2026-17", horizon_weeks=3, cadence="2:1")

    store.save_document(
        athlete_id,
        ArtifactType.SEASON_PLAN,
        "2026-17",
        {
            "meta": {
                "scope": "Season",
                "iso_week": "2026-17",
                "iso_week_range": "2026-17--2026-20",
            },
            "data": {
                "global_constraints": {
                    "planned_event_windows": [
                        "2026-04-25 B event rehearsal window",
                        "2026-05-16 A event peak window",
                    ],
                    "recovery_protection": {
                        "fixed_rest_days": ["Mon", "Fri"],
                        "notes": [
                            "Fixed rest days from AVAILABILITY are non-negotiable and must be preserved downstream.",
                            "When travel compresses the week, reduce ambition before reducing recovery protection.",
                        ],
                    },
                },
                "phases": [
                    {
                        "phase_id": "P01",
                        "name": "Build",
                        "cycle": "Build",
                        "phase_type": "BUILD",
                        "phase_intent": "durability_build",
                        "build_subtype": "durability_build",
                        "scenario_cadence": "2:1",
                        "cadence_week_roles": ["LOAD_1", "LOAD_2", "DELOAD"],
                        "iso_week_range": "2026-17--2026-19",
                        "role_week_load_bands": [
                            {"week": "2026-17", "role": "LOAD_1", "band": {"min": 7200, "max": 7800}},
                            {"week": "2026-18", "role": "LOAD_2", "band": {"min": 7600, "max": 8600}},
                            {"week": "2026-19", "role": "DELOAD", "band": {"min": 6800, "max": 7400}},
                        ],
                        "weekly_load_corridor": {
                            "weekly_kj": {
                                "min": 7200,
                                "max": 8600,
                                "notes": "Season corridor",
                            }
                        },
                        "allowed_forbidden_semantics": {
                            "allowed_intensity_domains": ["ENDURANCE", "TEMPO"],
                            "forbidden_intensity_domains": ["VO2MAX"],
                            "allowed_load_modalities": ["NONE", "K3"],
                        },
                        "overview": {"phase_goals": {"primary": "Build durable repeatable load."}},
                    }
                ]
            },
        },
        producer_agent="test",
        run_id="season_plan",
        update_latest=True,
    )
    for artifact_type in (ArtifactType.PHASE_GUARDRAILS, ArtifactType.PHASE_STRUCTURE, ArtifactType.PHASE_PREVIEW):
        store.save_document(
            athlete_id,
            artifact_type,
            "2026-17--2026-19",
            {
                "meta": {
                    "scope": "Phase",
                    "iso_week": "2026-17",
                    "iso_week_range": "2026-17--2026-19",
                },
                "data": (
                    {
                        "load_guardrails": {
                            "weekly_kj_bands": [
                                {
                                    "week": "2026-17",
                                    "band": {"min": 7200, "max": 8600, "notes": "Phase corridor"},
                                }
                            ]
                        },
                        "allowed_forbidden_semantics": {
                            "allowed_intensity_domains": ["ENDURANCE", "TEMPO"],
                            "allowed_load_modalities": ["NONE", "K3"],
                            "quality_density": {
                                "max_quality_days_per_week": 2,
                                "quality_intent": "Build",
                                "forbidden_patterns": ["Back-to-back quality days"],
                            },
                        },
                        "execution_non_negotiables": {
                            "minimum_recovery_opportunities": "Preserve at least two fixed recovery opportunities.",
                            "no_catch_up_rule": "Missed load is never made up later in the week.",
                        },
                        "events_constraints": {
                            "events": [
                                {
                                    "date": "2026-04-25",
                                    "week": "2026-17",
                                    "type": "B",
                                    "constraint": "Use as rehearsal only.",
                                }
                            ]
                        },
                    }
                    if artifact_type == ArtifactType.PHASE_GUARDRAILS
                    else (
                        {
                            "execution_principles": {
                                "recovery_protection": {
                                    "fixed_non_training_days": ["Mon", "Fri"],
                                    "mandatory_recovery_spacing_rules": [
                                        "Keep Monday and Friday protected.",
                                    ],
                                    "forbidden_sequences": ["Back-to-back quality days"],
                                },
                                "load_intensity_handling": {
                                    "max_quality_days_per_week": 2,
                                    "quality_intent": "Build",
                                },
                            }
                        }
                        if artifact_type == ArtifactType.PHASE_STRUCTURE
                        else {}
                    )
                ),
            },
            producer_agent="test",
            run_id=f"{artifact_type.value}_run",
            update_latest=True,
        )
    store.save_document(
        athlete_id,
        ArtifactType.AVAILABILITY,
        "2026-10",
        {
            "data": {
                "weekly_hours": {"min": 10, "typical": 12, "max": 14},
                "fixed_rest_days": ["Mon", "Fri"],
                "availability_table": [],
            }
        },
        producer_agent="test",
        run_id="availability",
        update_latest=True,
    )
    store.save_document(
        athlete_id,
        ArtifactType.WELLNESS,
        "2026-16",
        {"data": {"body_mass_kg": 82.4}},
        producer_agent="test",
        run_id="wellness",
        update_latest=True,
    )
    store.save_document(
        athlete_id,
        ArtifactType.ZONE_MODEL,
        "zone_model",
        {"data": {"model_metadata": {"ftp_watts": 300}, "zones": []}},
        producer_agent="test",
        run_id="zone_model",
        update_latest=True,
    )
    store.save_document(
        athlete_id,
        ArtifactType.KPI_PROFILE,
        "sample_profile",
        {"data": {}},
        producer_agent="test",
        run_id="kpi_profile",
        update_latest=True,
    )
    (tmp_path / athlete_id / "inputs").mkdir(parents=True, exist_ok=True)
    (tmp_path / athlete_id / "inputs" / "planning_events.json").write_text(
        json.dumps(
            {
                "data": {
                    "events": [
                        {
                            "date": "2026-04-25",
                            "type": "B",
                            "event_name": "Spring 200",
                        },
                        {
                            "date": "2026-05-16",
                            "type": "A",
                            "event_name": "Main 400",
                        },
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / athlete_id / "inputs" / "logistics.json").write_text(json.dumps({"data": {"events": []}}), encoding="utf-8")

    store.save_document(
        athlete_id,
        ArtifactType.ACTIVITIES_ACTUAL,
        "2026-16",
        {
            "data": {
                "activities": [
                    {
                        "day": "2026-04-18",
                        "type": "Ride",
                        "moving_time": "04:54:00",
                        "work_kj": 3200,
                        "load_tss": 180,
                        "intensity_factor": 0.72,
                        "flags": {
                            "flag_long_ride_180min_bool": True,
                            "flag_long_ride_240min_bool": True,
                            "flag_des_long_build_candidate_bool": True,
                            "flag_des_long_base_candidate_bool": False,
                            "flag_brevet_long_candidate_bool": False,
                        },
                    }
                ]
            }
        },
        producer_agent="test",
        run_id="activities_actual",
        update_latest=True,
    )
    store.save_document(
        athlete_id,
        ArtifactType.ACTIVITIES_TREND,
        "2026-16",
        {
            "data": {
                "weekly_trends": [
                    {
                        "year": 2026,
                        "iso_week": 16,
                        "weekly_aggregates": {
                            "activity_count": 5,
                            "moving_time": "13:48",
                            "distance_km": 302.4,
                            "work_kj": 7760,
                            "load_tss": 525,
                        },
                        "intensity_load_metrics": {
                            "intensity_factor": 0.71,
                            "decoupling_percent": 6.1,
                            "durability_index": 0.94,
                            "efficiency_factor": 1.23,
                            "ftp_estimated_w": 295,
                        },
                        "distribution_metrics": {
                            "z1_z2_time_percent": 84.0,
                            "z5_time_percent": 2.0,
                            "z2_share_power_percent": 68.0,
                            "back_to_back_z2_days_count": 1,
                        },
                        "flag_any": {
                            "flag_long_ride_180min_bool": True,
                            "flag_long_ride_240min_bool": True,
                            "flag_des_long_base_candidate_bool": False,
                            "flag_des_long_build_candidate_bool": True,
                            "flag_brevet_long_candidate_bool": False,
                        },
                        "metrics": {
                            "weekly_moving_time_total_min": 828,
                            "weekly_z2_time_total_min": 460,
                            "weekly_moving_time_max_min": 294,
                            "weekly_z2_time_max_min": 210,
                            "weekly_moving_time_180min_sum_min": 294,
                            "weekly_moving_time_240min_sum_min": 294,
                            "weekly_z2_time_180min_sum_min": 210,
                            "weekly_z2_time_240min_sum_min": 210,
                            "weekly_moving_time_des_base_sum_min": 0,
                            "weekly_moving_time_des_build_sum_min": 294,
                            "weekly_z2_time_des_base_sum_min": 0,
                            "weekly_z2_time_des_build_sum_min": 210,
                        },
                    }
                ]
            }
        },
        producer_agent="test",
        run_id="activities_trend",
        update_latest=True,
    )

    runtime = SimpleNamespace(workspace_root=tmp_path)
    _patch_plan_week_exact_query(monkeypatch, root=tmp_path, athlete_id=athlete_id)
    _mock_previous_week_report_gate(monkeypatch, evidence_week=IsoWeek(2026, 16))
    result = plan_week(runtime, athlete_id=athlete_id, year=2026, week=17, run_id="week_run")

    assert result.ok
    assert captured_inputs
    assert any("**Resolved Activity Context**" in user_input for user_input in captured_inputs)
    assert any("historical_reference_week: 2026-16" in user_input for user_input in captured_inputs)
    assert any("activities_actual_version: 2026-16" in user_input for user_input in captured_inputs)
    assert any("activities_trend_version: 2026-16" in user_input for user_input in captured_inputs)
    assert any("intensity_load_metrics.durability_index: 0.94" in user_input for user_input in captured_inputs)
    assert any("key_actual_sessions:" in user_input for user_input in captured_inputs)
    assert any("**Resolved Recovery Context**" in user_input for user_input in captured_inputs)
    assert any("**Resolved Event Priority Context**" in user_input for user_input in captured_inputs)
    assert any("**Resolved Load Governance Context**" in user_input for user_input in captured_inputs)
    assert any("**Resolved Feed-Forward Applicability Context**" in user_input for user_input in captured_inputs)



def test_plan_week_injects_resolved_logistics_and_zone_context(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    athlete_id = "test_athlete"
    captured_inputs: list[str] = []

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace(athlete_id)
    store.save_document(
        athlete_id,
        ArtifactType.SEASON_PLAN,
        "2026-11--2026-13",
        _season_plan_stub_payload(),
        producer_agent="test",
        run_id="season_plan_test",
        update_latest=True,
    )
    _write_minimal_scenario_chain(store, athlete_id)
    for artifact_type in (
        ArtifactType.PHASE_GUARDRAILS,
        ArtifactType.PHASE_STRUCTURE,
        ArtifactType.PHASE_PREVIEW,
    ):
        store.save_document(
            athlete_id,
            artifact_type,
            "2026-11--2026-13",
            {"meta": {"artifact_type": artifact_type.value, "iso_week_range": "2026-11--2026-13"}, "data": {}},
            producer_agent="phase_architect",
            run_id=f"store_{artifact_type.value.lower()}",
            update_latest=True,
        )
    _write_contract_phase_docs(store, athlete_id)
    store.save_document(
        athlete_id,
        ArtifactType.ACTIVITIES_ACTUAL,
        "2026-11",
        {"meta": {"artifact_type": "ACTIVITIES_ACTUAL", "iso_week": "2026-11"}, "data": {}},
        producer_agent="pipeline",
        run_id="store_activities_actual_202611",
        update_latest=True,
    )
    store.save_document(
        athlete_id,
        ArtifactType.ACTIVITIES_TREND,
        "2026-11",
        {"meta": {"artifact_type": "ACTIVITIES_TREND", "iso_week": "2026-11"}, "data": {}},
        producer_agent="pipeline",
        run_id="store_activities_trend_202611",
        update_latest=True,
    )
    store.latest_path(athlete_id, ArtifactType.LOGISTICS).write_text(
        json.dumps(
            {
                "data": {
                    "events": [
                        {
                            "date": "2026-03-19",
                            "event_id": "LOG-1",
                            "event_type": "TRAVEL",
                            "status": "PLANNED",
                            "impact": "AVAILABILITY",
                            "description": "Business trip",
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    store.latest_path(athlete_id, ArtifactType.PLANNING_EVENTS).write_text(
        json.dumps(
            {
                "data": {
                    "events": [
                        {
                            "type": "B",
                            "priority_rank": 2,
                            "event_name": "Spring 200",
                            "date": "2026-03-18",
                            "event_type": "Brevet",
                            "goal": "rehearsal",
                            "distance_km": 200,
                            "elevation_m": 1800,
                            "expected_duration": "08:00",
                            "time_limit": "13:30",
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    store.latest_path(athlete_id, ArtifactType.AVAILABILITY).write_text(
        json.dumps(
            {
                "data": {
                    "weekly_hours": {"min": 10.5, "typical": 14.0, "max": 17.5},
                    "fixed_rest_days": ["Mon", "Fri"],
                    "availability_table": [],
                    "source_type": "manual",
                    "source_ref": "ui",
                    "notes": "",
                }
            }
        ),
        encoding="utf-8",
    )
    store.latest_path(athlete_id, ArtifactType.ZONE_MODEL).write_text(
        json.dumps(
            {
                "data": {
                    "model_metadata": {
                        "valid_from": "2026-01-01",
                        "ftp_watts": 300,
                        "purpose": "planning",
                        "filename": "zone_model_power_300W.json",
                    },
                    "zones": [
                        {
                            "zone_id": "Z2",
                            "name": "Endurance",
                            "ftp_percent_range": {"min": 56, "max": 75},
                            "watt_range": {"min": 168, "max": 225},
                            "training_intent": "endurance",
                            "typical_if": 0.68,
                        }
                    ],
                    "examples": [],
                    "versioning_usage": [],
                }
            }
        ),
        encoding="utf-8",
    )
    store.save_document(
        athlete_id,
        ArtifactType.KPI_PROFILE,
        "sample_profile",
        {"data": {}},
        producer_agent="test",
        run_id="store_kpi_profile",
        update_latest=True,
    )

    runtime = SimpleNamespace(
        workspace_root=tmp_path,
        reasoning_effort=None,
        reasoning_summary=None,
    )
    _patch_plan_week_exact_query(monkeypatch, root=tmp_path, athlete_id=athlete_id)
    _mock_previous_week_report_gate(monkeypatch)

    monkeypatch.setattr("rps.orchestrator.plan_week._build_user_data_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr("rps.orchestrator.plan_week._build_kpi_selection_block", lambda *_args, **_kwargs: "")

    def _fake_run_agent_multi_output(*_args, **kwargs):
        captured_inputs.append(kwargs["user_input"])
        return {"ok": True, "produced": True}

    monkeypatch.setattr("rps.orchestrator.plan_week.run_agent_multi_output", _fake_run_agent_multi_output)
    monkeypatch.setattr(
        "rps.orchestrator.plan_week.run_workout_export",
        lambda *_args, **_kwargs: {"ran": False, "ok": True, "produced": False, "result": None},
    )

    result = plan_week(
        runtime,
        athlete_id=athlete_id,
        year=2026,
        week=12,
        run_id="test_run",
    )

    assert result.ok is True
    assert captured_inputs
    assert store.latest_exists(athlete_id, ArtifactType.ATHLETE_STATE_SNAPSHOT)
    assert store.latest_exists(athlete_id, ArtifactType.PLANNING_CONTEXT_SNAPSHOT)
    assert any("**Athlete State Snapshot**" in user_input for user_input in captured_inputs)
    assert any("**Planning Context Snapshot**" in user_input for user_input in captured_inputs)
    assert any("**Resolved Logistics Context**" in user_input for user_input in captured_inputs)
    assert any("Business trip" in user_input for user_input in captured_inputs)
    assert any("**Resolved Zone Model Context**" in user_input for user_input in captured_inputs)
    assert any("ftp_watts: 300" in user_input for user_input in captured_inputs)
    assert any("**Resolved Phase Context**" in user_input for user_input in captured_inputs)
    assert any("phase_iso_week_range: 2026-11--2026-13" in user_input for user_input in captured_inputs)
    assert any("**Resolved Availability Context**" in user_input for user_input in captured_inputs)
    assert any("fixed_rest_days: Mon, Fri" in user_input for user_input in captured_inputs)
    assert any("**Resolved Planning Event Context**" in user_input for user_input in captured_inputs)
    assert any("Spring 200" in user_input for user_input in captured_inputs)
    assert any("**Deterministic Week Calendar and Availability Context**" in user_input for user_input in captured_inputs)
    assert any("day_matrix:" in user_input for user_input in captured_inputs)



def test_plan_week_skips_export_when_week_plan_creation_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    athlete_id = "test_athlete"

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace(athlete_id)
    store.save_document(
        athlete_id,
        ArtifactType.SEASON_PLAN,
        "2026-11--2026-13",
        _season_plan_stub_payload(),
        producer_agent="test",
        run_id="season_plan_test",
        update_latest=True,
    )
    _write_minimal_scenario_chain(store, athlete_id)
    for artifact_type in (
        ArtifactType.PHASE_GUARDRAILS,
        ArtifactType.PHASE_STRUCTURE,
        ArtifactType.PHASE_PREVIEW,
    ):
        store.save_document(
            athlete_id,
            artifact_type,
            "2026-11--2026-13",
            {"meta": {"artifact_type": artifact_type.value, "iso_week_range": "2026-11--2026-13"}, "data": {}},
            producer_agent="phase_architect",
            run_id=f"store_{artifact_type.value.lower()}",
            update_latest=True,
        )
    _write_contract_phase_docs(store, athlete_id)

    runtime = SimpleNamespace(
        workspace_root=tmp_path,
        reasoning_effort=None,
        reasoning_summary=None,
    )
    _patch_plan_week_exact_query(monkeypatch, root=tmp_path, athlete_id=athlete_id)

    monkeypatch.setattr("rps.orchestrator.plan_week._build_user_data_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr("rps.orchestrator.plan_week._build_kpi_selection_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(
        "rps.orchestrator.plan_week.run_agent_multi_output",
        lambda *_args, **_kwargs: {"ok": False, "produced": False},
    )
    monkeypatch.setattr(
        "rps.orchestrator.plan_week.run_workout_export",
        lambda *_args, **_kwargs: pytest.fail("Workout export must not run after failed WEEK_PLAN creation."),
    )

    result = plan_week(
        runtime,
        athlete_id=athlete_id,
        year=2026,
        week=12,
        run_id="test_run",
    )

    assert result.ok is False
    assert len(result.steps) == 1
    assert result.steps[0]["agent"] == "week_planner"



def test_week_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/plan/week.py")
    at.run()
    assert len(at.error) == 0
    assert len(at.number_input) >= MIN_PLAN_HUB_NUMBER_INPUTS



def test_workouts_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/plan/workouts.py")
    at.run()
    assert len(at.error) == 0
    assert len(at.info) >= 1
    subheaders = [subheader.value for subheader in at.subheader]
    assert "Workout Editor" in subheaders


