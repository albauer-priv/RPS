import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from streamlit.testing.v1 import AppTest

from rps.agents.tasks import AgentTask
from rps.orchestrator import season_flow
from rps.orchestrator.plan_week import create_performance_report, plan_week
from rps.orchestrator.workout_export import create_intervals_workouts_export
from rps.ui.shared import SETTINGS
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType

MIN_PHASE_SELECTBOX_COUNT = 2
EXPECTED_SCOPED_ACTION_CALLS = 2
MIN_PLAN_HUB_NUMBER_INPUTS = 2


@pytest.fixture(autouse=True)
def _env_setup(monkeypatch, tmp_path):
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-key")
    monkeypatch.setenv("ATHLETE_ID", "test_athlete")
    monkeypatch.setenv("ATHLETE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("RPS_DISABLE_INTERVALS_REFRESH", "1")


def test_season_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/plan/season.py")
    at.run()
    assert len(at.error) == 0
    assert len(at.text_input) >= 1
    assert all(button.label != "Create Scenarios" for button in at.button)


def test_season_page_handles_selection_error_state():
    at = AppTest.from_file("src/rps/ui/pages/plan/season.py")
    at.session_state["rps_state"] = {"season_selection_error_output": "error output"}
    at.run()
    assert len(at.error) == 0


def test_plan_hub_season_actions_expander(tmp_path):
    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace("test_athlete")
    plan_path = store.latest_path("test_athlete", ArtifactType.SEASON_PLAN)
    plan_path.write_text(json.dumps({"meta": {"version_key": "test"}, "data": {"phases": []}}), encoding="utf-8")

    at = AppTest.from_file("src/rps/ui/pages/plan/hub.py")
    at.run(timeout=10)
    assert len(at.error) == 0
    labels = [expander.label for expander in at.expander]
    assert "Season Plan: Delete or Reset" in labels
    assert any("Build Workouts" in label for label in labels)
    assert all("Was wird alles erstellt:" not in info.value for info in at.info)
    # Run planning UI is hidden when readiness has blockers.
    info_text = "\n".join(info.value for info in at.info)
    assert "Resolve missing inputs/artifacts above" in info_text
    assert "Inputs missing" in info_text


def test_plan_hub_uses_quick_actions_with_advanced_manual_run(tmp_path):
    at = AppTest.from_file("src/rps/ui/pages/plan/hub.py")
    at.run(timeout=10)

    assert len(at.error) == 0
    subheaders = [subheader.value for subheader in at.subheader]
    assert "Scope" not in subheaders
    assert "Run Planning" not in subheaders
    source = Path("src/rps/ui/pages/plan/hub.py").read_text(encoding="utf-8")
    assert 'st.subheader("Quick Actions")' in source
    assert 'st.expander("Context"' in source
    assert 'st.expander("Advanced manual run"' in source


def test_plan_hub_reset_delete_latest(tmp_path):
    from rps.ui.pages.plan import hub as plan_hub

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace("test_athlete")
    for artifact_type in plan_hub.DELETE_LATEST_TYPES:
        path = store.latest_path("test_athlete", artifact_type)
        path.write_text("{}", encoding="utf-8")

    removed_delete = plan_hub._clear_latest_artifacts(store, "test_athlete", plan_hub.DELETE_LATEST_TYPES)
    assert removed_delete
    for artifact_type in plan_hub.DELETE_LATEST_TYPES:
        assert not store.latest_path("test_athlete", artifact_type).exists()

    for artifact_type in plan_hub.DELETE_LATEST_TYPES:
        path = store.latest_path("test_athlete", artifact_type)
        path.write_text("{}", encoding="utf-8")

    removed_reset = plan_hub._clear_latest_artifacts(store, "test_athlete", plan_hub.RESET_LATEST_TYPES)
    assert removed_reset
    for artifact_type in plan_hub.RESET_LATEST_TYPES:
        assert not store.latest_path("test_athlete", artifact_type).exists()
    assert store.latest_path("test_athlete", ArtifactType.SEASON_SCENARIOS).exists()
    assert store.latest_path("test_athlete", ArtifactType.SEASON_SCENARIO_SELECTION).exists()


def test_plan_hub_readiness_requires_latest_files(tmp_path):
    from rps.ui.pages.plan import hub as plan_hub
    from rps.workspace.index_manager import WorkspaceIndexManager

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace("test_athlete")

    inputs_dir = tmp_path / "test_athlete" / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    (inputs_dir / "season_brief_2026.md").write_text("test", encoding="utf-8")
    (inputs_dir / "events_2026.md").write_text("test", encoding="utf-8")

    for artifact_type in (
        ArtifactType.KPI_PROFILE,
        ArtifactType.AVAILABILITY,
        ArtifactType.ZONE_MODEL,
        ArtifactType.WELLNESS,
        ArtifactType.SEASON_SCENARIOS,
        ArtifactType.SEASON_SCENARIO_SELECTION,
    ):
        path = store.latest_path("test_athlete", artifact_type)
        path.write_text("{}", encoding="utf-8")

    scenarios_key = "2026-05"
    scenarios_path = store.versioned_path("test_athlete", ArtifactType.SEASON_SCENARIOS, scenarios_key)
    scenarios_path.write_text("{}", encoding="utf-8")
    selection_key = "2026-05"
    selection_path = store.versioned_path("test_athlete", ArtifactType.SEASON_SCENARIO_SELECTION, selection_key)
    selection_path.write_text("{}", encoding="utf-8")

    version_key = "2026-05"
    version_path = store.versioned_path("test_athlete", ArtifactType.SEASON_PLAN, version_key)
    version_path.write_text("{}", encoding="utf-8")

    manager = WorkspaceIndexManager(root=tmp_path, athlete_id="test_athlete")
    index = {
        "athlete_id": "test_athlete",
        "updated_at": "2026-02-01T00:00:00Z",
        "artefacts": {
            ArtifactType.SEASON_SCENARIOS.value: {
                "latest": {
                    "version_key": scenarios_key,
                    "path": str(scenarios_path.relative_to(tmp_path / "test_athlete")),
                    "created_at": "2026-02-01T00:00:00Z",
                },
                "versions": {
                    scenarios_key: {
                        "version_key": scenarios_key,
                        "path": str(scenarios_path.relative_to(tmp_path / "test_athlete")),
                        "created_at": "2026-02-01T00:00:00Z",
                    }
                },
            },
            ArtifactType.SEASON_SCENARIO_SELECTION.value: {
                "latest": {
                    "version_key": selection_key,
                    "path": str(selection_path.relative_to(tmp_path / "test_athlete")),
                    "created_at": "2026-02-01T00:00:00Z",
                },
                "versions": {
                    selection_key: {
                        "version_key": selection_key,
                        "path": str(selection_path.relative_to(tmp_path / "test_athlete")),
                        "created_at": "2026-02-01T00:00:00Z",
                    }
                },
            },
            ArtifactType.SEASON_PLAN.value: {
                "latest": {
                    "version_key": version_key,
                    "path": str(version_path.relative_to(tmp_path / "test_athlete")),
                    "created_at": "2026-02-01T00:00:00Z",
                },
                "versions": {
                    version_key: {
                        "version_key": version_key,
                        "path": str(version_path.relative_to(tmp_path / "test_athlete")),
                        "created_at": "2026-02-01T00:00:00Z",
                    }
                },
            }
        },
    }
    manager.save(index)

    readiness = plan_hub._compute_readiness("test_athlete", 2026, 5)
    readiness_map = {step.key: step for step in readiness}
    assert readiness_map["season_plan"].status in {"missing", "blocked"}


def test_plan_hub_scoped_week_run_forces_rerun_when_ready():
    from rps.ui.pages.plan import hub as plan_hub

    readiness = [
        plan_hub.ReadinessStep("inputs", "Inputs", "ready", "", ""),
        plan_hub.ReadinessStep("season_scenarios", "Season Scenarios", "ready", "", ""),
        plan_hub.ReadinessStep("scenario_selection", "Selected Scenario", "ready", "", ""),
        plan_hub.ReadinessStep("season_plan", "Season Plan", "ready", "", ""),
        plan_hub.ReadinessStep("phase", "Phase", "ready", "", ""),
        plan_hub.ReadinessStep("phase_guardrails", "Phase Guardrails", "ready", "", ""),
        plan_hub.ReadinessStep("phase_structure", "Phase Structure", "ready", "", ""),
        plan_hub.ReadinessStep("phase_preview", "Phase Preview", "ready", "", "", optional=True),
        plan_hub.ReadinessStep("week_plan", "Week Plan", "ready", "", ""),
        plan_hub.ReadinessStep("intervals_workouts", "Build Workouts", "ready", "", "", optional=True),
    ]

    steps = plan_hub._build_execution_steps(readiness, "Scoped", "Week Plan")
    status_by_id = {step["step_id"]: step["Status"] for step in steps}

    assert status_by_id["WEEK_PLAN"] == "QUEUED"
    assert status_by_id["EXPORT_WORKOUTS"] == "QUEUED"


def test_plan_hub_scoped_build_workouts_forces_rerun_when_ready():
    from rps.ui.pages.plan import hub as plan_hub

    readiness = [
        plan_hub.ReadinessStep("week_plan", "Week Plan", "ready", "", ""),
        plan_hub.ReadinessStep("intervals_workouts", "Build Workouts", "ready", "", "", optional=True),
    ]

    steps = plan_hub._build_execution_steps(readiness, "Scoped", "Build Workouts")
    status_by_id = {step["step_id"]: step["Status"] for step in steps}

    assert status_by_id["EXPORT_WORKOUTS"] == "QUEUED"


def test_plan_hub_phase_scope_queues_all_phase_artefacts():
    from rps.ui.pages.plan import hub as plan_hub

    readiness = [
        plan_hub.ReadinessStep("season_plan", "Season Plan", "ready", "", ""),
        plan_hub.ReadinessStep("phase", "Phase", "ready", "", ""),
        plan_hub.ReadinessStep("phase_guardrails", "Phase Guardrails", "ready", "", ""),
        plan_hub.ReadinessStep("phase_structure", "Phase Structure", "ready", "", ""),
        plan_hub.ReadinessStep("phase_preview", "Phase Preview", "ready", "", "", optional=True),
        plan_hub.ReadinessStep("week_plan", "Week Plan", "ready", "", ""),
        plan_hub.ReadinessStep("intervals_workouts", "Build Workouts", "ready", "", "", optional=True),
    ]

    steps = plan_hub._build_execution_steps(readiness, "Scoped", "Phase")

    assert [step["step_id"] for step in steps] == ["PHASE_GUARDRAILS", "PHASE_STRUCTURE", "PHASE_PREVIEW"]
    assert all(step["Status"] == "QUEUED" for step in steps)


def test_plan_hub_build_workouts_adds_missing_week_dependencies():
    from rps.ui.pages.plan import hub as plan_hub

    readiness = [
        plan_hub.ReadinessStep("phase_guardrails", "Phase Guardrails", "ready", "", ""),
        plan_hub.ReadinessStep("phase_structure", "Phase Structure", "ready", "", ""),
        plan_hub.ReadinessStep("phase_preview", "Phase Preview", "ready", "", "", optional=True),
        plan_hub.ReadinessStep("week_plan", "Week Plan", "missing", "", ""),
        plan_hub.ReadinessStep("intervals_workouts", "Build Workouts", "missing", "", "", optional=True),
    ]

    steps = plan_hub._build_execution_steps(readiness, "Scoped", "Build Workouts")
    status_by_id = {step["step_id"]: step["Status"] for step in steps}

    assert status_by_id["WEEK_PLAN"] == "QUEUED"
    assert status_by_id["EXPORT_WORKOUTS"] == "QUEUED"


def test_plan_hub_phase_week_selector_helpers_follow_current_week(tmp_path):
    from rps.ui.pages.plan import hub as plan_hub

    store = LocalArtifactStore(root=tmp_path)
    athlete_id = "test_athlete"
    store.ensure_workspace(athlete_id)
    current_week = plan_hub._current_iso_week()
    next_week = plan_hub.next_iso_week(current_week)
    store.latest_path(athlete_id, ArtifactType.SEASON_PLAN).write_text(
        json.dumps(
            {
                "data": {
                    "phases": [
                        {
                            "phase_id": "P01",
                            "name": "Base 1",
                            "iso_week_range": (
                                f"{current_week.year:04d}-{current_week.week:02d}"
                                f"--{current_week.year:04d}-{current_week.week:02d}"
                            ),
                        },
                        {
                            "phase_id": "P02",
                            "name": "Build 1",
                            "iso_week_range": (
                                f"{next_week.year:04d}-{next_week.week:02d}"
                                f"--{next_week.year:04d}-{next_week.week:02d}"
                            ),
                        },
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    original_root = plan_hub.SETTINGS.workspace_root
    object.__setattr__(plan_hub.SETTINGS, "workspace_root", tmp_path)
    try:
        selected_phase = plan_hub._default_phase_label(athlete_id, current_week)
        phase_weeks = plan_hub._weeks_for_phase_label(athlete_id, selected_phase)
    finally:
        object.__setattr__(plan_hub.SETTINGS, "workspace_root", original_root)

    assert selected_phase is not None
    assert selected_phase.startswith("P01")
    assert phase_weeks == [current_week]


def test_plan_hub_direct_action_buttons_render(tmp_path):
    from rps.ui.pages.plan import hub as plan_hub

    store = LocalArtifactStore(root=tmp_path)
    athlete_id = "test_athlete"
    store.ensure_workspace(athlete_id)
    current_week = plan_hub._current_iso_week()
    next_week = plan_hub.next_iso_week(current_week)
    store.latest_path(athlete_id, ArtifactType.SEASON_PLAN).write_text(
        json.dumps(
            {
                "data": {
                    "phases": [
                        {
                            "phase_id": "P01",
                            "name": "Base 1",
                            "iso_week_range": (
                                f"{current_week.year:04d}-{current_week.week:02d}"
                                f"--{current_week.year:04d}-{current_week.week:02d}"
                            ),
                        },
                        {
                            "phase_id": "P02",
                            "name": "Build 1",
                            "iso_week_range": (
                                f"{next_week.year:04d}-{next_week.week:02d}"
                                f"--{next_week.year:04d}-{next_week.week:02d}"
                            ),
                        },
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    original_root = plan_hub.SETTINGS.workspace_root
    object.__setattr__(plan_hub.SETTINGS, "workspace_root", tmp_path)
    try:
        at = AppTest.from_file("src/rps/ui/pages/plan/hub.py")
        at.session_state["hub_scope"] = {
            "athlete_id": athlete_id,
            "iso_year": current_week.year,
            "iso_week": current_week.week,
            "phase_label": None,
        }
        at.run(timeout=10)
    finally:
        object.__setattr__(plan_hub.SETTINGS, "workspace_root", original_root)

    assert len(at.error) == 0
    labels = [button.label for button in at.button]
    assert labels.count("Run Phase") >= 1
    assert labels.count("Run Week") >= 1
    assert labels.count("Run Workouts") >= 1
    select_labels = [select.label for select in at.selectbox]
    assert select_labels.count("Phase") >= MIN_PHASE_SELECTBOX_COUNT
    assert "Week" in select_labels
    expander_labels = [expander.label for expander in at.expander]
    assert any("Phase" in label for label in expander_labels)
    assert all("Phase Guardrails" not in label for label in expander_labels)
    assert all("Phase Structure" not in label for label in expander_labels)
    assert all("Phase Preview" not in label for label in expander_labels)


def test_plan_hub_shows_knowledge_store_status(tmp_path):
    store = LocalArtifactStore(root=tmp_path)
    athlete_id = "test_athlete"
    store.ensure_workspace(athlete_id)
    store.latest_path(athlete_id, ArtifactType.SEASON_PLAN).write_text(
        json.dumps({"meta": {"version_key": "test"}, "data": {"phases": []}}),
        encoding="utf-8",
    )

    at = AppTest.from_file("src/rps/ui/pages/plan/hub.py")
    at.run(timeout=10)

    assert len(at.error) == 0
    success_text = "\n".join(success.value for success in at.success)
    assert "Ready: `vs_rps_all_agents`" in success_text


def test_workout_export_force_export_runs_even_when_current(tmp_path, monkeypatch):
    class _Runtime:
        def __init__(self, workspace_root):
            self.workspace_root = workspace_root

    store = LocalArtifactStore(root=tmp_path)
    athlete_id = "test_athlete"
    store.ensure_workspace(athlete_id)
    week_key = "2026-12"
    store.versioned_path(athlete_id, ArtifactType.WEEK_PLAN, week_key).write_text("{}", encoding="utf-8")
    store.versioned_path(athlete_id, ArtifactType.INTERVALS_WORKOUTS, week_key).write_text("{}", encoding="utf-8")

    calls = []

    def _runtime_for(_agent_name):
        return _Runtime(tmp_path)

    def _fake_run_agent_multi_output(*args, **kwargs):
        calls.append(kwargs)
        return {"ok": True, "produced": True}

    monkeypatch.setattr("rps.orchestrator.workout_export.run_agent_multi_output", _fake_run_agent_multi_output)

    result = create_intervals_workouts_export(
        _runtime_for,
        store=store,
        athlete_id=athlete_id,
        year=2026,
        week=12,
        run_id="test_run",
        injected_block="",
        plan_mtime=None,
        needs_week_plan=False,
        force_export=True,
        override_text="rebuild export",
    )

    assert result["ran"] is True
    assert calls


def test_season_flow_scoped_actions_do_not_short_circuit(monkeypatch, tmp_path):
    calls = []

    def _fake_runtime_for(_agent_name):
        return SimpleNamespace(workspace_root=tmp_path)

    def _fake_run_agent_multi_output(*args, **kwargs):
        calls.append(kwargs)
        return {"ok": True, "produced": True}

    monkeypatch.setattr("rps.orchestrator.season_flow.run_agent_multi_output", _fake_run_agent_multi_output)
    monkeypatch.setattr("rps.orchestrator.season_flow.build_injection_block", lambda *_args, **_kwargs: "")

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace("test_athlete")
    store.latest_path("test_athlete", ArtifactType.ATHLETE_PROFILE).write_text("{}", encoding="utf-8")
    store.latest_path("test_athlete", ArtifactType.SEASON_SCENARIO_SELECTION).write_text(
        json.dumps({"data": {"kpi_moving_time_rate_guidance_selection": None}}),
        encoding="utf-8",
    )

    season_flow.create_season_scenarios(
        _fake_runtime_for,
        athlete_id="test_athlete",
        year=2026,
        week=12,
        run_id="run_scenarios",
        override_text="rerun scenarios",
    )
    season_flow.create_season_plan(
        _fake_runtime_for,
        athlete_id="test_athlete",
        year=2026,
        week=12,
        run_id="run_plan",
        selected=None,
        override_text="rerun season",
    )

    assert len(calls) == EXPECTED_SCOPED_ACTION_CALLS


def test_create_season_plan_includes_selected_kpi_guidance(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured_inputs: list[str] = []

    def _fake_runtime_for(_agent_name):
        return SimpleNamespace(workspace_root=tmp_path)

    def _fake_run_agent_multi_output(*args, **kwargs):
        captured_inputs.append(kwargs["user_input"])
        return {"ok": True, "produced": True}

    monkeypatch.setattr("rps.orchestrator.season_flow.run_agent_multi_output", _fake_run_agent_multi_output)
    monkeypatch.setattr("rps.orchestrator.season_flow.build_injection_block", lambda *_args, **_kwargs: "")

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace("test_athlete")
    store.latest_path("test_athlete", ArtifactType.ATHLETE_PROFILE).write_text("{}", encoding="utf-8")
    store.save_document(
        "test_athlete",
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
        run_id="test_selection",
        update_latest=True,
    )

    season_flow.create_season_plan(
        _fake_runtime_for,
        athlete_id="test_athlete",
        year=2026,
        week=12,
        run_id="run_plan",
        selected=None,
        override_text="rerun season",
    )

    assert captured_inputs
    assert "Selected KPI guidance:" in captured_inputs[0]
    assert "kpi_rate_band_selector fast_competitive" in captured_inputs[0]


def test_plan_week_force_phase_structure_rerun(monkeypatch, tmp_path):
    athlete_id = "test_athlete"
    year = 2026
    week = 12
    run_ids = []

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace(athlete_id)
    store.latest_path(athlete_id, ArtifactType.SEASON_PLAN).write_text(
        json.dumps(
            {
                "meta": {"iso_week_range": "2026-11--2026-13"},
                "data": {
                    "phases": [
                        {
                            "id": "P01",
                            "name": "Base 1",
                            "cycle": "Base",
                            "iso_week_range": "2026-11--2026-13",
                        }
                    ]
                },
            }
        ),
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

    monkeypatch.setattr("rps.orchestrator.plan_week._build_user_data_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr("rps.orchestrator.plan_week._build_kpi_selection_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr("rps.orchestrator.plan_week.build_injection_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(
        "rps.orchestrator.plan_week.run_agent_multi_output",
        lambda *_args, **kwargs: run_ids.append(kwargs["run_id"]) or {"ok": True, "produced": True},
    )
    monkeypatch.setattr(
        "rps.orchestrator.plan_week.create_intervals_workouts_export",
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
    assert any(run_id.endswith("_phase_create_phase_structure") for run_id in run_ids)
    assert any(run_id.endswith("_phase_create_phase_preview") for run_id in run_ids)


def test_plan_week_force_phase_guardrails_runs_in_isolation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    athlete_id = "test_athlete"
    year = 2026
    week = 12
    written_types: list[ArtifactType] = []

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace(athlete_id)
    store.latest_path(athlete_id, ArtifactType.SEASON_PLAN).write_text(
        json.dumps(
            {
                "meta": {"iso_week_range": "2026-11--2026-13"},
                "data": {
                    "phases": [
                        {
                            "id": "P01",
                            "name": "Base 1",
                            "cycle": "Base",
                            "iso_week_range": "2026-11--2026-13",
                        }
                    ]
                },
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
    monkeypatch.setattr("rps.orchestrator.plan_week._build_kpi_selection_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr("rps.orchestrator.plan_week.build_injection_block", lambda *_args, **_kwargs: "")

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
        "rps.orchestrator.plan_week.create_intervals_workouts_export",
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


def test_plan_week_phase_architect_omits_direct_kpi_guidance(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    athlete_id = "test_athlete"
    captured_inputs: list[str] = []

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace(athlete_id)
    store.latest_path(athlete_id, ArtifactType.SEASON_PLAN).write_text(
        json.dumps(
            {
                "meta": {"iso_week_range": "2026-11--2026-13"},
                "data": {
                    "phases": [
                        {
                            "id": "P01",
                            "name": "Base 1",
                            "cycle": "Base",
                            "iso_week_range": "2026-11--2026-13",
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
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
        run_id="test_selection",
        update_latest=True,
    )

    runtime = SimpleNamespace(
        workspace_root=tmp_path,
        reasoning_effort=None,
        reasoning_summary=None,
    )

    monkeypatch.setattr("rps.orchestrator.plan_week._build_user_data_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr("rps.orchestrator.plan_week.build_injection_block", lambda *_args, **_kwargs: "")

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
        "rps.orchestrator.plan_week.create_intervals_workouts_export",
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


def test_system_pages_render():
    status = AppTest.from_file("src/rps/ui/pages/system/status.py")
    status.run()
    assert len(status.error) == 0

    history = AppTest.from_file("src/rps/ui/pages/system/history.py")
    history.run()
    assert len(history.error) == 0

    log_page = AppTest.from_file("src/rps/ui/pages/system/log.py")
    log_page.run()
    assert len(log_page.error) == 0


def test_kpi_profile_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/athlete_profile/kpi_profile.py")
    at.run()
    assert len(at.error) == 0


def test_kpi_profile_page_defaults_to_saved_profile():
    store = LocalArtifactStore(root=SETTINGS.workspace_root)
    athlete_id = "test_athlete"
    store.ensure_workspace(athlete_id)
    profile_key = "des_brevet_600_km_masters"

    selected_payload = json.loads(
        (Path("specs/kpi_profiles") / f"kpi_profile_{profile_key}.json").read_text(encoding="utf-8")
    )
    store.save_document(
        athlete_id,
        ArtifactType.KPI_PROFILE,
        profile_key,
        selected_payload,
        producer_agent="user",
        run_id="test_kpi_profile_select",
        update_latest=True,
    )

    at = AppTest.from_file("src/rps/ui/pages/athlete_profile/kpi_profile.py")
    at.run()

    assert len(at.error) == 0
    assert at.selectbox[0].value == f"kpi_profile_{profile_key}"
    assert any(f"Active KPI Profile: kpi_profile_{profile_key}" in info.value for info in at.info)


def test_kpi_profile_page_saves_canonical_meta():
    store = LocalArtifactStore(root=SETTINGS.workspace_root)
    athlete_id = "test_athlete"
    store.ensure_workspace(athlete_id)
    latest_path = store.latest_path(athlete_id, ArtifactType.KPI_PROFILE)
    if latest_path.exists():
        latest_path.unlink()

    at = AppTest.from_file("src/rps/ui/pages/athlete_profile/kpi_profile.py")
    at.run()
    assert len(at.error) == 0

    at.button[0].click()
    at.run()

    saved = store.load_latest(athlete_id, ArtifactType.KPI_PROFILE)
    assert isinstance(saved, dict)
    meta = saved["meta"]
    assert meta["artifact_type"] == "KPI_PROFILE"
    assert meta["schema_id"] == "KPIProfileInterface"
    assert meta["authority"] == "Binding"
    assert meta["owner_agent"] == "Policy-Owner"
    assert meta["scope"] == "Shared"
    assert meta["data_confidence"] == "UNKNOWN"
    assert meta["iso_week"]
    assert meta["iso_week_range"] == f"{meta['iso_week']}--{meta['iso_week']}"
    assert isinstance(meta["temporal_scope"], dict)
    assert meta["temporal_scope"]["from"]
    assert meta["temporal_scope"]["to"]
    assert isinstance(meta["trace_upstream"], list)
    assert meta["trace_upstream"]
    assert "run_id" in meta["trace_upstream"][0]
    assert meta["trace_data"] == []
    assert meta["trace_events"] == []


def test_create_performance_report_does_not_require_phase_artefacts(monkeypatch, tmp_path):
    store = LocalArtifactStore(root=tmp_path)
    athlete_id = "test_athlete"
    store.ensure_workspace(athlete_id)

    season_plan = {
        "meta": {
            "artifact_type": "SEASON_PLAN",
            "schema_id": "SeasonPlanInterface",
            "schema_version": "1.0",
            "version": "1.0",
            "authority": "Binding",
            "owner_agent": "Season-Planner",
            "run_id": "season_plan_test",
            "created_at": "2026-04-01T00:00:00Z",
            "scope": "Season",
            "iso_week": "2026-14",
            "iso_week_range": "2026-14--2026-20",
            "temporal_scope": {"from": "2026-03-30", "to": "2026-05-17"},
            "trace_upstream": [],
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "UNKNOWN",
            "notes": "",
        },
        "data": {
            "phases": [
                {
                    "phase_id": "P02",
                    "phase_name": "Build 1",
                    "phase_type": "Build",
                    "iso_week_range": "2026-14--2026-16",
                }
            ]
        },
    }
    generic_input = {
        "meta": {
            "artifact_type": "TEST",
            "schema_id": "TestInterface",
            "schema_version": "1.0",
            "version": "1.0",
            "authority": "Binding",
            "owner_agent": "User",
            "run_id": "input_test",
            "created_at": "2026-04-10T00:00:00Z",
            "scope": "Shared",
            "iso_week": "2026-15",
            "iso_week_range": "2026-15--2026-15",
            "temporal_scope": {"from": "2026-04-06", "to": "2026-04-12"},
            "trace_upstream": [],
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "UNKNOWN",
            "notes": "",
        },
        "data": {},
    }

    for artifact_type, version_key, document in (
        (ArtifactType.SEASON_PLAN, "2026-14--2026-20", season_plan),
        (ArtifactType.ACTIVITIES_ACTUAL, "2026-15", generic_input),
        (ArtifactType.ACTIVITIES_TREND, "2026-15", generic_input),
        (ArtifactType.KPI_PROFILE, "sample_profile", generic_input),
        (ArtifactType.PLANNING_EVENTS, "2026-15", generic_input),
        (ArtifactType.LOGISTICS, "2026-15", generic_input),
    ):
        store.save_document(
            athlete_id,
            artifact_type,
            version_key,
            document,
            producer_agent="test",
            run_id=f"store_{artifact_type.value.lower()}",
            update_latest=True,
        )

    captured: dict[str, object] = {}

    def _fake_run_agent_multi_output(runtime, **kwargs):
        captured["runtime"] = runtime
        captured["kwargs"] = kwargs
        return {"ok": True, "produced": {"store_des_analysis_report": {"path": "dummy"}}}

    monkeypatch.setattr("rps.orchestrator.plan_week.run_agent_multi_output", _fake_run_agent_multi_output)

    runtime = SimpleNamespace(workspace_root=tmp_path)
    result = create_performance_report(
        lambda _agent_name: runtime,
        athlete_id=athlete_id,
        report_week=SimpleNamespace(year=2026, week=15),
        run_id_prefix="report_ui",
    )

    assert result["ok"] is True
    assert captured["kwargs"]["tasks"] == [AgentTask.CREATE_DES_ANALYSIS_REPORT]


def test_create_performance_report_skips_when_context_inputs_missing(tmp_path):
    store = LocalArtifactStore(root=tmp_path)
    athlete_id = "test_athlete"
    store.ensure_workspace(athlete_id)

    season_plan = {
        "meta": {
            "artifact_type": "SEASON_PLAN",
            "schema_id": "SeasonPlanInterface",
            "schema_version": "1.0",
            "version": "1.0",
            "authority": "Binding",
            "owner_agent": "Season-Planner",
            "run_id": "season_plan_test",
            "created_at": "2026-04-01T00:00:00Z",
            "scope": "Season",
            "iso_week": "2026-14",
            "iso_week_range": "2026-14--2026-20",
            "temporal_scope": {"from": "2026-03-30", "to": "2026-05-17"},
            "trace_upstream": [],
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "UNKNOWN",
            "notes": "",
        },
        "data": {"phases": []},
    }
    generic_input = {
        "meta": {
            "artifact_type": "TEST",
            "schema_id": "TestInterface",
            "schema_version": "1.0",
            "version": "1.0",
            "authority": "Binding",
            "owner_agent": "User",
            "run_id": "input_test",
            "created_at": "2026-04-10T00:00:00Z",
            "scope": "Shared",
            "iso_week": "2026-15",
            "iso_week_range": "2026-15--2026-15",
            "temporal_scope": {"from": "2026-04-06", "to": "2026-04-12"},
            "trace_upstream": [],
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "UNKNOWN",
            "notes": "",
        },
        "data": {},
    }

    for artifact_type, version_key, document in (
        (ArtifactType.SEASON_PLAN, "2026-14--2026-20", season_plan),
        (ArtifactType.ACTIVITIES_ACTUAL, "2026-15", generic_input),
        (ArtifactType.ACTIVITIES_TREND, "2026-15", generic_input),
        (ArtifactType.KPI_PROFILE, "sample_profile", generic_input),
    ):
        store.save_document(
            athlete_id,
            artifact_type,
            version_key,
            document,
            producer_agent="test",
            run_id=f"store_{artifact_type.value.lower()}",
            update_latest=True,
        )

    runtime = SimpleNamespace(workspace_root=tmp_path)
    result = create_performance_report(
        lambda _agent_name: runtime,
        athlete_id=athlete_id,
        report_week=SimpleNamespace(year=2026, week=15),
        run_id_prefix="report_ui",
    )

    assert result["ok"] is False
    assert "planning_events" in result["message"]
    assert "logistics" in result["message"]


def test_data_operations_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/athlete_profile/data_operations.py")
    at.run()
    assert len(at.error) == 0
    labels = [button.label for button in at.button]
    assert "Create Backup" in labels


def test_feed_forward_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/performance/feed_forward.py")
    at.run()
    assert len(at.error) == 0


def test_performance_report_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/performance/report.py")
    at.run()
    assert len(at.error) == 0


def test_data_metrics_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/performance/data_metrics.py")
    at.run(timeout=10)
    assert len(at.error) == 0
    labels = [button.label for button in at.button]
    assert "Refresh Intervals Data" in labels
    slider_labels = [slider.label for slider in at.slider]
    assert "Show last N weeks (including current)" in slider_labels


def test_availability_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/athlete_profile/availability.py")
    at.run()
    assert len(at.error) == 0
