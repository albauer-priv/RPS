import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from rps.orchestrator.workout_export import run_workout_export
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType
from tests.planning_context_helpers import (
    write_minimal_availability as _write_minimal_availability,
)
from tests.planning_context_helpers import (
    write_minimal_scenario_chain as _write_minimal_scenario_chain,
)

MIN_PHASE_SELECTBOX_COUNT = 2


@pytest.fixture(autouse=True)
def _env_setup(monkeypatch, tmp_path):
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-key")
    monkeypatch.setenv("ATHLETE_ID", "test_athlete")
    monkeypatch.setenv("ATHLETE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("RPS_DISABLE_INTERVALS_REFRESH", "1")


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

    object.__setattr__(plan_hub.SETTINGS, "workspace_root", tmp_path)
    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace("test_athlete")
    store.latest_path("test_athlete", ArtifactType.ATHLETE_PROFILE).write_text("{}", encoding="utf-8")
    store.latest_path("test_athlete", ArtifactType.PLANNING_EVENTS).write_text(json.dumps({"data": {"events": []}}), encoding="utf-8")
    store.latest_path("test_athlete", ArtifactType.LOGISTICS).write_text(json.dumps({"data": {"events": []}}), encoding="utf-8")
    _write_minimal_availability(store, "test_athlete")
    store.save_document(
        "test_athlete",
        ArtifactType.KPI_PROFILE,
        "2026-05",
        {"data": {}},
        producer_agent="test",
        run_id="store_kpi",
        update_latest=True,
    )
    store.save_document(
        "test_athlete",
        ArtifactType.WELLNESS,
        "2026-05",
        {"data": {}},
        producer_agent="test",
        run_id="store_wellness",
        update_latest=True,
    )
    _write_minimal_scenario_chain(store, "test_athlete", version_key="2026-05", selected_scenario_id="A")

    readiness = plan_hub._compute_readiness("test_athlete", 2026, 5)
    readiness_map = {step.key: step for step in readiness}
    assert readiness_map["scenario_selection"].status == "ready"
    assert readiness_map["season_plan"].status in {"missing", "blocked"}



def test_plan_hub_marks_selection_stale_after_new_scenarios(tmp_path):
    from rps.ui.pages.plan import hub as plan_hub

    object.__setattr__(plan_hub.SETTINGS, "workspace_root", tmp_path)
    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace("test_athlete")
    store.latest_path("test_athlete", ArtifactType.ATHLETE_PROFILE).write_text("{}", encoding="utf-8")
    store.latest_path("test_athlete", ArtifactType.PLANNING_EVENTS).write_text(json.dumps({"data": {"events": []}}), encoding="utf-8")
    store.latest_path("test_athlete", ArtifactType.LOGISTICS).write_text(json.dumps({"data": {"events": []}}), encoding="utf-8")
    _write_minimal_availability(store, "test_athlete")
    store.save_document(
        "test_athlete",
        ArtifactType.KPI_PROFILE,
        "2026-05",
        {"data": {}},
        producer_agent="test",
        run_id="store_kpi",
        update_latest=True,
    )
    store.save_document(
        "test_athlete",
        ArtifactType.WELLNESS,
        "2026-05",
        {"data": {}},
        producer_agent="test",
        run_id="store_wellness",
        update_latest=True,
    )
    _write_minimal_scenario_chain(store, "test_athlete", version_key="2026-05", selected_scenario_id="A")
    store.save_document(
        "test_athlete",
        ArtifactType.SEASON_SCENARIOS,
        "2026-06",
        {
            "meta": {"artifact_type": "SEASON_SCENARIOS", "version_key": "2026-06", "run_id": "store_scenarios_2026-06"},
            "data": {
                "planning_horizon_weeks": 3,
                "scenarios": [
                    {
                        "scenario_id": "A",
                        "name": "Fresh scenarios",
                        "load_philosophy": "balanced_progressive",
                        "risk_profile": "medium",
                        "best_suited_if": "Stable recovery",
                        "key_differences": "New scenario set",
                        "main_payoff": "Updated options",
                        "main_cost": "Requires reselection",
                        "scenario_guidance": {
                            "deload_cadence": "2:1",
                            "phase_length_weeks": 3,
                            "phase_count_expected": 1,
                            "max_shortened_phases": 0,
                            "shortening_budget_weeks": 0,
                            "phase_plan_summary": {"full_phases": 1, "shortened_phases": []},
                            "recovery_margin": "medium",
                            "fatigue_exposure": "moderate",
                            "specificity_density": "controlled",
                            "constraint_summary": ["Updated scenario set."],
                            "event_alignment_notes": ["Needs fresh confirmation."],
                            "risk_flags": [],
                            "kpi_guardrail_notes": ["Stay repeatable."],
                            "decision_notes": ["New scenarios invalidated the old selection."],
                        },
                    }
                ],
            },
        },
        producer_agent="test",
        run_id="store_scenarios_2026-06",
        update_latest=True,
    )

    readiness = plan_hub._compute_readiness("test_athlete", 2026, 6)
    readiness_map = {step.key: step for step in readiness}

    assert readiness_map["scenario_selection"].status == "stale"
    assert readiness_map["scenario_selection"].summary == "Selection stale; reselect required"
    assert readiness_map["season_plan"].status == "blocked"



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
        plan_hub.ReadinessStep("workout_export", "Build Workouts", "ready", "", "", optional=True),
    ]

    steps = plan_hub._build_execution_steps(readiness, "Scoped", "Week Plan")
    status_by_id = {step["step_id"]: step["Status"] for step in steps}

    assert status_by_id["WEEK_PLAN"] == "QUEUED"
    assert "WORKOUT_EXPORT" not in status_by_id



def test_plan_hub_scoped_build_workouts_forces_rerun_when_ready():
    from rps.ui.pages.plan import hub as plan_hub

    readiness = [
        plan_hub.ReadinessStep("week_plan", "Week Plan", "ready", "", ""),
        plan_hub.ReadinessStep("workout_export", "Build Workouts", "ready", "", "", optional=True),
    ]

    steps = plan_hub._build_execution_steps(readiness, "Scoped", "Build Workouts")
    status_by_id = {step["step_id"]: step["Status"] for step in steps}

    assert status_by_id["WORKOUT_EXPORT"] == "QUEUED"



def test_plan_hub_season_plan_scope_drops_redundant_workout_export_when_week_plan_is_selected():
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
        plan_hub.ReadinessStep("workout_export", "Build Workouts", "ready", "", "", optional=True),
    ]

    steps = plan_hub._build_execution_steps(readiness, "Scoped", "Season Plan")
    step_ids = [step["step_id"] for step in steps]

    assert "WEEK_PLAN" in step_ids
    assert "WORKOUT_EXPORT" not in step_ids



def test_plan_hub_phase_scope_queues_all_phase_artefacts():
    from rps.ui.pages.plan import hub as plan_hub

    readiness = [
        plan_hub.ReadinessStep("season_plan", "Season Plan", "ready", "", ""),
        plan_hub.ReadinessStep("phase", "Phase", "ready", "", ""),
        plan_hub.ReadinessStep("phase_guardrails", "Phase Guardrails", "ready", "", ""),
        plan_hub.ReadinessStep("phase_structure", "Phase Structure", "ready", "", ""),
        plan_hub.ReadinessStep("phase_preview", "Phase Preview", "ready", "", "", optional=True),
        plan_hub.ReadinessStep("week_plan", "Week Plan", "ready", "", ""),
        plan_hub.ReadinessStep("workout_export", "Build Workouts", "ready", "", "", optional=True),
    ]

    steps = plan_hub._build_execution_steps(readiness, "Scoped", "Phase")

    assert [step["step_id"] for step in steps] == ["PHASE_GUARDRAILS", "PHASE_STRUCTURE", "PHASE_PREVIEW"]
    assert all(step["Status"] == "QUEUED" for step in steps)



def test_plan_hub_phase_display_stays_ready_when_only_optional_preview_missing():
    from rps.ui.pages.plan import hub as plan_hub

    readiness = [
        plan_hub.ReadinessStep("inputs", "Inputs", "ready", "", ""),
        plan_hub.ReadinessStep("season_scenarios", "Season Scenarios", "ready", "", ""),
        plan_hub.ReadinessStep("scenario_selection", "Selected Scenario", "ready", "", ""),
        plan_hub.ReadinessStep("season_plan", "Season Plan", "ready", "", ""),
        plan_hub.ReadinessStep("phase_guardrails", "Phase Guardrails", "ready", "", "", latest="g1"),
        plan_hub.ReadinessStep("phase_structure", "Phase Structure", "ready", "", "", latest="s1"),
        plan_hub.ReadinessStep("phase_preview", "Phase Preview (optional)", "missing", "Missing (optional)", "Optional step; no artifact present.", optional=True),
        plan_hub.ReadinessStep("week_plan", "Week Plan", "missing", "", ""),
    ]

    display_steps = plan_hub._display_readiness_steps(readiness)
    phase_step = next(step for step in display_steps if step.key == "phase")

    assert phase_step.status == "ready"
    assert phase_step.summary == "Ready"
    assert phase_step.reason == "Optional attention: Phase Preview"



def test_plan_hub_build_workouts_adds_missing_week_dependencies():
    from rps.ui.pages.plan import hub as plan_hub

    readiness = [
        plan_hub.ReadinessStep("phase_guardrails", "Phase Guardrails", "ready", "", ""),
        plan_hub.ReadinessStep("phase_structure", "Phase Structure", "ready", "", ""),
        plan_hub.ReadinessStep("phase_preview", "Phase Preview", "ready", "", "", optional=True),
        plan_hub.ReadinessStep("week_plan", "Week Plan", "missing", "", ""),
        plan_hub.ReadinessStep("workout_export", "Build Workouts", "missing", "", "", optional=True),
    ]

    steps = plan_hub._build_execution_steps(readiness, "Scoped", "Build Workouts")
    status_by_id = {step["step_id"]: step["Status"] for step in steps}

    assert status_by_id["WEEK_PLAN"] == "QUEUED"
    assert "WORKOUT_EXPORT" not in status_by_id



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



def test_workout_export_force_export_runs_even_when_current(tmp_path):
    store = LocalArtifactStore(root=tmp_path)
    athlete_id = "test_athlete"
    store.ensure_workspace(athlete_id)
    week_key = "2026-12"
    week_plan = {
        "meta": {
            "artifact_type": "WEEK_PLAN",
            "schema_id": "WeekPlanInterface",
            "schema_version": "1.2",
            "version": "1.0",
            "version_key": f"{week_key}__20260315_120000",
            "authority": "Binding",
            "owner_agent": "Week-Artifact-Writer",
            "run_id": "week_plan_test",
            "created_at": "2026-04-21T14:53:19Z",
            "scope": "Week",
            "iso_week": "2026-12",
            "iso_week_range": "2026-12--2026-12",
            "temporal_scope": {"from": "2026-03-16", "to": "2026-03-22"},
            "trace_upstream": [],
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "HIGH",
            "notes": "",
        },
        "data": {
            "inherited_planning_posture": {
                "selected_scenario_id": "B",
                "load_posture": "balanced_progressive",
                "recovery_margin": "medium",
                "fatigue_exposure": "moderate",
                "specificity_density": "moderate",
                "season_archetype": "endurance_build",
                "phase_intent": "durability_build",
                "phase_week_role": "LOAD_1",
                "allowed_intensity_domains": ["ENDURANCE", "TEMPO"],
                "forbidden_intensity_domains": ["VO2MAX"],
                "risk_flags": [],
            },
            "effective_week_constraints": {
                "phase_intent": "durability_build",
                "phase_week_role": "LOAD_1",
                "allowed_intensity_domains": ["ENDURANCE", "TEMPO"],
                "forbidden_intensity_domains": ["VO2MAX"],
                "allowed_load_modalities": ["NONE"],
                "weekly_kj_band": {"min": 1, "max": 1000, "notes": "test band"},
            },
            "week_summary": {
                "week_objective": "Test objective",
                "weekly_load_corridor_kj": {"min": 1, "max": 1000, "notes": "test band"},
                "planned_weekly_load_kj": 500,
                "notes": "",
            },
            "agenda": [
                {
                    "day": "Mon",
                    "date": "2026-03-16",
                    "day_role": "ENDURANCE",
                    "planned_duration": "01:00",
                    "planned_kj": 500,
                    "workout_id": "W-2026-12-MON",
                },
                {
                    "day": "Tue",
                    "date": "2026-03-17",
                    "day_role": "REST",
                    "planned_duration": "00:00",
                    "planned_kj": 0,
                    "workout_id": None,
                },
                {
                    "day": "Wed",
                    "date": "2026-03-18",
                    "day_role": "REST",
                    "planned_duration": "00:00",
                    "planned_kj": 0,
                    "workout_id": None,
                },
                {
                    "day": "Thu",
                    "date": "2026-03-19",
                    "day_role": "REST",
                    "planned_duration": "00:00",
                    "planned_kj": 0,
                    "workout_id": None,
                },
                {
                    "day": "Fri",
                    "date": "2026-03-20",
                    "day_role": "REST",
                    "planned_duration": "00:00",
                    "planned_kj": 0,
                    "workout_id": None,
                },
                {
                    "day": "Sat",
                    "date": "2026-03-21",
                    "day_role": "REST",
                    "planned_duration": "00:00",
                    "planned_kj": 0,
                    "workout_id": None,
                },
                {
                    "day": "Sun",
                    "date": "2026-03-22",
                    "day_role": "REST",
                    "planned_duration": "00:00",
                    "planned_kj": 0,
                    "workout_id": None,
                },
            ],
            "workouts": [
                {
                    "workout_id": "W-2026-12-MON",
                    "title": "Endurance Ride",
                    "date": "2026-03-16",
                    "start": "07:00",
                    "duration": "01:00:00",
                    "workout_text": "Warmup\n- 8m ramp 50%-70% 85-90rpm\n\nMain Set\n- 44m 68% 85-92rpm\n\nCooldown\n- 8m ramp 60%-45% 80-85rpm",
                    "notes": "",
                }
            ],
        },
    }
    store.save_document(
        athlete_id,
        ArtifactType.PHASE_STRUCTURE,
        "2026-12--2026-12__20260315_120000",
        {"meta": {"artifact_type": "PHASE_STRUCTURE"}, "data": {}},
        producer_agent="phase_architect",
        run_id="phase_structure_test",
        update_latest=True,
    )
    store.save_document(
        athlete_id,
        ArtifactType.WEEK_PLAN,
        f"{week_key}__20260315_120000",
        week_plan,
        producer_agent="week_planner",
        run_id="week_plan_test",
        update_latest=True,
    )
    store.save_document(
        athlete_id,
        ArtifactType.INTERVALS_WORKOUTS,
        f"{week_key}__20260315_120000",
        [],
        producer_agent="workout_export",
        run_id="intervals_test",
        update_latest=True,
    )

    result = run_workout_export(
        store=store,
        athlete_id=athlete_id,
        year=2026,
        week=12,
        run_id="test_run",
        plan_mtime=None,
        needs_week_plan=False,
        force_export=True,
    )

    assert result["ran"] is True
    assert result["ok"] is True
    payload = store.load_version(athlete_id, ArtifactType.INTERVALS_WORKOUTS, week_key)
    assert isinstance(payload, list)
    assert payload


