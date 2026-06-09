import json
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest
from streamlit.testing.v1 import AppTest

from rps.agents.tasks import AgentTask
from rps.orchestrator import season_flow
from rps.orchestrator.plan_week import create_performance_report, plan_week
from rps.orchestrator.workout_export import run_workout_export
from rps.ui.shared import SETTINGS
from rps.workspace.index_manager import WorkspaceIndexManager
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType

MIN_PHASE_SELECTBOX_COUNT = 2
EXPECTED_SCOPED_ACTION_CALLS = 2
MIN_PLAN_HUB_NUMBER_INPUTS = 2


def _write_minimal_scenario_chain(
    store: LocalArtifactStore,
    athlete_id: str,
    *,
    version_key: str = "2026-12",
    horizon_weeks: int = 3,
    cadence: str = "2:1",
    selected_scenario_id: str = "A",
) -> None:
    phase_length = {"2:1": 3, "3:1": 4, "2:1:1": 4}[cadence]
    phase_count = (horizon_weeks + phase_length - 1) // phase_length
    shortened_len = horizon_weeks - ((phase_count - 1) * phase_length)
    shortened = [{"len": shortened_len, "count": 1}] if shortened_len < phase_length else []
    full_phases = phase_count - len(shortened)
    store.save_document(
        athlete_id,
        ArtifactType.SEASON_SCENARIOS,
        version_key,
        {
            "meta": {
                "artifact_type": "SEASON_SCENARIOS",
                "version_key": version_key,
                "run_id": f"store_scenarios_{version_key}",
            },
            "data": {
                "planning_horizon_weeks": horizon_weeks,
                "scenarios": [
                    {
                        "scenario_id": selected_scenario_id,
                        "name": "Minimal contract scenario",
                        "load_philosophy": "balanced_progressive",
                        "risk_profile": "medium",
                        "best_suited_if": "stable recovery",
                        "key_differences": "Balances continuity and progression.",
                        "main_payoff": "Repeatable load progression.",
                        "main_cost": "Less conservative than scenario A.",
                        "scenario_guidance": {
                            "deload_cadence": cadence,
                            "phase_length_weeks": phase_length,
                            "phase_count_expected": phase_count,
                            "max_shortened_phases": len(shortened),
                            "shortening_budget_weeks": 0 if not shortened else phase_length - shortened_len,
                            "phase_plan_summary": {
                                "full_phases": full_phases,
                                "shortened_phases": shortened,
                            },
                            "recovery_margin": "medium",
                            "fatigue_exposure": "moderate",
                            "specificity_density": "controlled",
                            "constraint_summary": ["Preserve continuity and legal intensity domains."],
                            "intensity_guidance": {
                                "allowed_domains": ["ENDURANCE", "TEMPO"],
                                "avoid_domains": ["VO2MAX"],
                            },
                            "event_alignment_notes": ["Test scenario anchor."],
                            "risk_flags": [],
                            "kpi_guardrail_notes": ["Stay repeatable."],
                            "decision_notes": ["Selected for testing."],
                        },
                    }
                ],
            }
        },
        producer_agent="test",
        run_id=f"store_scenarios_{version_key}",
        update_latest=True,
    )
    scenarios_doc = store.load_latest(athlete_id, ArtifactType.SEASON_SCENARIOS)
    scenarios_meta = scenarios_doc.get("meta", {}) if isinstance(scenarios_doc, dict) else {}
    actual_scenarios_version = scenarios_meta.get("version_key", version_key)
    actual_scenarios_run_id = scenarios_meta.get("run_id", f"store_scenarios_{version_key}")
    existing_selection: dict[str, object] = {}
    try:
        loaded = store.load_latest(athlete_id, ArtifactType.SEASON_SCENARIO_SELECTION)
        if isinstance(loaded, dict):
            existing_selection = loaded
    except Exception:
        existing_selection = {}
    selection_data = existing_selection.get("data")
    if not isinstance(selection_data, dict):
        selection_data = {}
    selection_data["selected_scenario_id"] = selected_scenario_id
    selection_data["season_scenarios_ref"] = actual_scenarios_version
    selection_data.setdefault("selection_source", "user")
    selection_data.setdefault("selection_rationale", "Test selection")
    selection_data.setdefault("notes", ["Selected in test helper."])
    selection_data.setdefault("kpi_moving_time_rate_guidance_selection", None)
    store.save_document(
        athlete_id,
        ArtifactType.SEASON_SCENARIO_SELECTION,
        version_key,
        {
            "meta": {
                "artifact_type": "SEASON_SCENARIO_SELECTION",
                "version_key": version_key,
                "run_id": f"store_selection_{version_key}",
                "trace_upstream": [
                    {
                        "artifact": "SEASON_SCENARIOS",
                        "version": actual_scenarios_version,
                        "version_key": actual_scenarios_version,
                        "run_id": actual_scenarios_run_id,
                    }
                ],
            },
            "data": selection_data,
        },
        producer_agent="test",
        run_id=f"store_selection_{version_key}",
        update_latest=True,
    )
    if not store.latest_exists(athlete_id, ArtifactType.ZONE_MODEL):
        store.save_document(
            athlete_id,
            ArtifactType.ZONE_MODEL,
            "zone_model",
            {
                "data": {
                    "model_metadata": {"ftp_watts": 300},
                    "zones": [
                        {
                            "zone_id": "Z2",
                            "name": "Endurance",
                            "ftp_percent_range": {"min": 56, "max": 75},
                            "typical_if": 0.66,
                        }
                    ],
                }
            },
            producer_agent="test",
            run_id="store_zone_model",
            update_latest=True,
        )


def _write_minimal_availability(store: LocalArtifactStore, athlete_id: str) -> None:
    store.latest_path(athlete_id, ArtifactType.AVAILABILITY).write_text(
        json.dumps(
            {
                "data": {
                    "weekly_hours": {"min": 10.5, "typical": 14.0, "max": 17.5},
                    "fixed_rest_days": ["Mon", "Fri"],
                    "availability_table": [],
                    "source_type": "manual",
                    "source_ref": "test",
                    "notes": "",
                }
            }
        ),
        encoding="utf-8",
    )
    if not store.latest_exists(athlete_id, ArtifactType.ZONE_MODEL):
        store.save_document(
            athlete_id,
            ArtifactType.ZONE_MODEL,
            "zone_model",
            {
                "data": {
                    "model_metadata": {"ftp_watts": 300},
                    "zones": [
                        {
                            "zone_id": "Z2",
                            "name": "Endurance",
                            "ftp_percent_range": {"min": 56, "max": 75},
                            "typical_if": 0.66,
                        }
                    ],
                }
            },
            producer_agent="test",
            run_id="store_zone_model",
            update_latest=True,
        )


def _write_contract_phase_docs(
    store: LocalArtifactStore,
    athlete_id: str,
    *,
    phase_range: str = "2026-11--2026-13",
    weeks: tuple[str, ...] = ("2026-11", "2026-12", "2026-13"),
) -> None:
    roles = ["LOAD_1", "LOAD_2", "DELOAD"][: len(weeks)]
    bands = [
        {"week": week, "band": {"min": 1000 + idx * 100, "max": 2000 + idx * 100, "notes": "Contract band"}}
        for idx, week in enumerate(weeks)
    ]
    store.save_document(
        athlete_id,
        ArtifactType.PHASE_GUARDRAILS,
        phase_range,
        {
            "meta": {"artifact_type": "PHASE_GUARDRAILS", "iso_week_range": phase_range},
            "data": {
                "load_guardrails": {"weekly_kj_bands": bands},
                "allowed_forbidden_semantics": {
                    "allowed_day_roles": ["REST", "RECOVERY", "ENDURANCE", "QUALITY"],
                    "forbidden_day_roles": [],
                    "allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO"],
                    "forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
                    "allowed_load_modalities": ["NONE"],
                    "quality_density": {"max_quality_days_per_week": 1},
                },
            },
        },
        producer_agent="phase_architect",
        run_id=f"store_phase_guardrails_{phase_range}",
        update_latest=True,
    )
    store.save_document(
        athlete_id,
        ArtifactType.PHASE_STRUCTURE,
        phase_range,
        {
            "meta": {"artifact_type": "PHASE_STRUCTURE", "iso_week_range": phase_range},
            "data": {
                "execution_principles": {
                    "phase_role": "Base",
                    "recovery_protection": {"fixed_non_training_days": ["Mon", "Fri"]},
                    "load_intensity_handling": {"max_quality_days_per_week": 1},
                },
                "week_skeleton_logic": {
                    "week_roles": {
                        "week_roles": [
                            {"week": week, "role": role}
                            for week, role in zip(weeks, roles, strict=False)
                        ],
                        "allowed_role_set": roles,
                    }
                },
                "load_ranges": {
                    "weekly_kj_bands": bands,
                    "source": "phase_guardrails_latest.json",
                },
            },
        },
        producer_agent="phase_architect",
        run_id=f"store_phase_structure_{phase_range}",
        update_latest=True,
    )
    store.save_document(
        athlete_id,
        ArtifactType.PHASE_PREVIEW,
        phase_range,
        {"meta": {"artifact_type": "PHASE_PREVIEW", "iso_week_range": phase_range}, "data": {}},
        producer_agent="phase_architect",
        run_id=f"store_phase_preview_{phase_range}",
        update_latest=True,
    )


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


def test_season_page_renders_scenario_ux_fields(tmp_path):
    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace("test_athlete")
    store.save_document(
        "test_athlete",
        ArtifactType.SEASON_SCENARIOS,
        "2026-21",
        {
            "meta": {
                "artifact_type": "SEASON_SCENARIOS",
                "schema_id": "SeasonScenariosInterface",
                "schema_version": "1.0",
                "version": "1.0",
                "authority": "Informational",
                "owner_agent": "Season-Scenario-Agent",
                "run_id": "season_scenarios_test",
                "created_at": "2026-05-19T21:00:00Z",
                "scope": "Season",
                "iso_week": "2026-21",
                "iso_week_range": "2026-21--2026-37",
                "temporal_scope": {"from": "2026-05-18", "to": "2026-09-13"},
                "trace_upstream": [],
                "trace_data": [],
                "trace_events": [],
                "data_confidence": "HIGH",
                "notes": "",
            },
            "data": {
                "kpi_profile_ref": "kpi",
                "athlete_profile_ref": "test_athlete",
                "planning_horizon_weeks": 17,
                "notes": [],
                "scenarios": [
                    {
                        "scenario_id": "A",
                        "name": "Scenario A",
                        "core_idea": "Core.",
                        "load_philosophy": "Load.",
                        "risk_profile": "Risk.",
                        "key_differences": "Diff.",
                        "best_suited_if": "Best.",
                        "typical_week_feel": "Calm and repeatable.",
                        "main_payoff": "High executability.",
                        "main_cost": "Less upside.",
                        "what_gets_prioritized": "Consistency.",
                        "what_gets_de_emphasized": "Aggressive sharpening.",
                        "scenario_guidance": {
                            "deload_cadence": "2:1",
                            "phase_length_weeks": 3,
                            "phase_count_expected": 6,
                            "max_shortened_phases": 1,
                            "shortening_budget_weeks": 1,
                            "phase_plan_summary": {"full_phases": 5, "shortened_phases": [{"len": 2, "count": 1}]},
                            "event_alignment_notes": ["Note."],
                            "risk_flags": ["Risk."],
                            "fixed_rest_days": ["Mon", "Fri"],
                            "constraint_summary": ["Constraint."],
                            "kpi_guardrail_notes": ["Guardrail."],
                            "decision_notes": ["Decision."],
                            "intensity_guidance": {"allowed_domains": ["ENDURANCE"], "avoid_domains": ["THRESHOLD"]},
                            "assumptions": ["Assumption."],
                            "unknowns": ["Unknown."],
                        },
                    },
                    {
                        "scenario_id": "B",
                        "name": "Scenario B",
                        "core_idea": "Core.",
                        "load_philosophy": "Load.",
                        "risk_profile": "Risk.",
                        "key_differences": "Diff.",
                        "best_suited_if": "Best.",
                        "typical_week_feel": "Structured and productive.",
                        "main_payoff": "Balanced progress.",
                        "main_cost": "Needs steadier recovery.",
                        "what_gets_prioritized": "Durability under load.",
                        "what_gets_de_emphasized": "Maximal intensity.",
                        "scenario_guidance": {
                            "deload_cadence": "2:1:1",
                            "phase_length_weeks": 4,
                            "phase_count_expected": 5,
                            "max_shortened_phases": 2,
                            "shortening_budget_weeks": 3,
                            "phase_plan_summary": {"full_phases": 3, "shortened_phases": [{"len": 3, "count": 1}]},
                            "event_alignment_notes": ["Note."],
                            "risk_flags": ["Risk."],
                            "fixed_rest_days": ["Mon", "Fri"],
                            "constraint_summary": ["Constraint."],
                            "kpi_guardrail_notes": ["Guardrail."],
                            "decision_notes": ["Decision."],
                            "intensity_guidance": {"allowed_domains": ["ENDURANCE", "TEMPO"], "avoid_domains": ["VO2MAX"]},
                            "assumptions": ["Assumption."],
                            "unknowns": ["Unknown."],
                        },
                    },
                    {
                        "scenario_id": "C",
                        "name": "Scenario C",
                        "core_idea": "Core.",
                        "load_philosophy": "Load.",
                        "risk_profile": "Risk.",
                        "key_differences": "Diff.",
                        "best_suited_if": "Best.",
                        "typical_week_feel": "Dense and demanding.",
                        "main_payoff": "Highest specificity.",
                        "main_cost": "Lower recovery margin.",
                        "what_gets_prioritized": "Fatigue-context specificity.",
                        "what_gets_de_emphasized": "Comfort and slack.",
                        "scenario_guidance": {
                            "deload_cadence": "3:1",
                            "phase_length_weeks": 4,
                            "phase_count_expected": 5,
                            "max_shortened_phases": 2,
                            "shortening_budget_weeks": 3,
                            "phase_plan_summary": {"full_phases": 3, "shortened_phases": [{"len": 3, "count": 1}]},
                            "event_alignment_notes": ["Note."],
                            "risk_flags": ["Risk."],
                            "fixed_rest_days": ["Mon", "Fri"],
                            "constraint_summary": ["Constraint."],
                            "kpi_guardrail_notes": ["Guardrail."],
                            "decision_notes": ["Decision."],
                            "intensity_guidance": {"allowed_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT"], "avoid_domains": []},
                            "assumptions": ["Assumption."],
                            "unknowns": ["Unknown."],
                        },
                    },
                ],
            },
        },
        producer_agent="season_scenario",
        run_id="season_scenarios_test",
        update_latest=True,
    )

    at = AppTest.from_file("src/rps/ui/pages/plan/season.py")
    at.run(timeout=10)

    assert len(at.error) == 0
    source = Path("src/rps/ui/pages/plan/season.py").read_text(encoding="utf-8")
    assert "Typical week feel:" in source
    assert "Main payoff:" in source
    assert "Main cost:" in source
    assert "What gets prioritized:" in source
    assert "What gets de-emphasized:" in source


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
            "authority": "Binding",
            "owner_agent": "Week-Planner",
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
            "week_summary": {
                "week_objective": "Test objective",
                "weekly_load_corridor_kj": {"min": 1, "max": 2, "notes": ""},
                "planned_weekly_load_kj": 1,
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


def test_season_flow_scoped_actions_do_not_short_circuit(monkeypatch, tmp_path):
    calls = []

    def _fake_runtime_for(_agent_name):
        return SimpleNamespace(workspace_root=tmp_path)

    def _fake_run_agent_multi_output(*args, **kwargs):
        calls.append(kwargs)
        return {"ok": True, "produced": True}

    monkeypatch.setattr("rps.orchestrator.season_flow.run_agent_multi_output", _fake_run_agent_multi_output)

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace("test_athlete")
    store.latest_path("test_athlete", ArtifactType.ATHLETE_PROFILE).write_text("{}", encoding="utf-8")
    store.latest_path("test_athlete", ArtifactType.AVAILABILITY).write_text(
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
    store.latest_path("test_athlete", ArtifactType.PLANNING_EVENTS).write_text(
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
    store.latest_path("test_athlete", ArtifactType.SEASON_SCENARIO_SELECTION).write_text(
        json.dumps({"data": {"kpi_moving_time_rate_guidance_selection": None}}),
        encoding="utf-8",
    )
    _write_minimal_scenario_chain(store, "test_athlete", horizon_weeks=8)

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

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace("test_athlete")
    store.latest_path("test_athlete", ArtifactType.ATHLETE_PROFILE).write_text("{}", encoding="utf-8")
    store.latest_path("test_athlete", ArtifactType.AVAILABILITY).write_text(
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
    store.latest_path("test_athlete", ArtifactType.PLANNING_EVENTS).write_text(
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
    store.save_document(
        "test_athlete",
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
                            },
                            {
                                "segment": "steady_endurance",
                                "w_per_kg": {"min": 2.0, "max": 2.4},
                                "kj_per_kg_per_hour": {"min": 16, "max": 19},
                                "basis": "validated",
                            },
                        ],
                    }
                }
            }
        },
        producer_agent="user",
        run_id="test_kpi_profile",
        update_latest=True,
    )
    _write_minimal_scenario_chain(store, "test_athlete", horizon_weeks=8)

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
    assert "**Athlete State Snapshot**" in captured_inputs[0]
    assert "**Resolved KPI Context**" in captured_inputs[0]
    assert "selected_kpi_rate_band_selector: fast_competitive" in captured_inputs[0]
    assert "kj_per_kg_per_hour 20 - 24" in captured_inputs[0]
    assert "kpi_profile_moving_time_rate_guidance.available_bands:" in captured_inputs[0]
    assert "**Resolved Availability Context**" in captured_inputs[0]
    assert "fixed_rest_days: Mon, Fri" in captured_inputs[0]
    assert "**Resolved Planning Event Context**" in captured_inputs[0]
    assert "Spring 200" in captured_inputs[0]
    assert "workspace_get_version for ACTIVITIES_ACTUAL and ACTIVITIES_TREND with version_key 2026-12" not in captured_inputs[0]
    assert store.latest_exists("test_athlete", ArtifactType.ATHLETE_STATE_SNAPSHOT)


def test_create_season_plan_injects_selected_scenario_phase_math(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured_inputs: list[str] = []

    def _fake_runtime_for(_agent_name):
        return SimpleNamespace(workspace_root=tmp_path)

    def _fake_run_agent_multi_output(*_args, **kwargs):
        captured_inputs.append(kwargs["user_input"])
        return {"ok": True, "produced": True}

    monkeypatch.setattr("rps.orchestrator.season_flow.run_agent_multi_output", _fake_run_agent_multi_output)

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace("test_athlete")
    store.latest_path("test_athlete", ArtifactType.ATHLETE_PROFILE).write_text("{}", encoding="utf-8")
    _write_minimal_availability(store, "test_athlete")
    store.save_document(
        "test_athlete",
        ArtifactType.SEASON_SCENARIOS,
        "2026-12",
        {
            "meta": {
                "artifact_type": "SEASON_SCENARIOS",
                "version_key": "2026-12",
                "run_id": "test_scenarios",
            },
            "data": {
                "planning_horizon_weeks": 17,
                "scenarios": [
                    {
                        "scenario_id": "B",
                        "name": "Compact resilient build",
                        "load_philosophy": "balanced_progressive",
                        "risk_profile": "medium",
                        "best_suited_if": "Compressed horizon with stable recovery.",
                        "key_differences": "Uses shorter phases with bounded compression.",
                        "main_payoff": "Preserves continuity in a compressed horizon.",
                        "main_cost": "Less room for recovery drift.",
                        "scenario_guidance": {
                            "deload_cadence": "2:1",
                            "phase_length_weeks": 3,
                            "phase_count_expected": 6,
                            "max_shortened_phases": 2,
                            "shortening_budget_weeks": 1,
                            "phase_plan_summary": {
                                "full_phases": 5,
                                "shortened_phases": [{"len": 2, "count": 1}],
                            },
                            "recovery_margin": "medium",
                            "fatigue_exposure": "moderate",
                            "specificity_density": "controlled",
                            "constraint_summary": ["Keep compression bounded and repeatable."],
                            "intensity_guidance": {
                                "allowed_domains": ["ENDURANCE", "TEMPO"],
                                "avoid_domains": ["VO2MAX"],
                            },
                            "event_alignment_notes": ["A-event backplanned."],
                            "risk_flags": ["Compressed horizon."],
                            "kpi_guardrail_notes": ["Do not over-compress early load."],
                            "decision_notes": ["Chosen for compact progression test."],
                        },
                    }
                ],
            }
        },
        producer_agent="test",
        run_id="test_scenarios",
        update_latest=True,
    )
    scenarios_doc = store.load_latest("test_athlete", ArtifactType.SEASON_SCENARIOS)
    scenarios_meta = scenarios_doc.get("meta", {}) if isinstance(scenarios_doc, dict) else {}
    scenarios_version_key = scenarios_meta.get("version_key", "2026-12")
    store.save_document(
        "test_athlete",
        ArtifactType.SEASON_SCENARIO_SELECTION,
        "2026-12",
        {
            "meta": {
                "artifact_type": "SEASON_SCENARIO_SELECTION",
                "version_key": "2026-12",
                "run_id": "test_selection",
                "trace_upstream": [
                    {
                        "artifact": "SEASON_SCENARIOS",
                        "version": scenarios_version_key,
                        "version_key": scenarios_version_key,
                        "run_id": "test_scenarios",
                    }
                ],
            },
            "data": {
                "selected_scenario_id": "B",
                "season_scenarios_ref": scenarios_version_key,
                "selection_source": "user",
                "selection_rationale": "Compact resilient build.",
                "notes": ["Test selection."],
                "kpi_moving_time_rate_guidance_selection": None,
            },
        },
        producer_agent="test",
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
    )

    assert captured_inputs
    assert "**Deterministic Selected Scenario Structure Context**" in captured_inputs[0]
    assert "planning_horizon_weeks: 17" in captured_inputs[0]
    assert "deload_cadence: 2:1" in captured_inputs[0]
    assert "phase_length_weeks: 3" in captured_inputs[0]
    assert "phase_count_expected: 6" in captured_inputs[0]
    assert "full_phases: 5" in captured_inputs[0]
    assert "- len 2, count 1" in captured_inputs[0]
    assert "consistent_with_horizon: True" in captured_inputs[0]
    assert "**Deterministic Season Phase Slot Context**" in captured_inputs[0]
    assert "P01: 2026-12--2026-13" in captured_inputs[0]
    assert "scenario_cadence 2:1" in captured_inputs[0]
    assert "cadence_week_roles SHORTENED_RE_ENTRY, SHORTENED_CONSOLIDATION" in captured_inputs[0]
    assert "P06: 2026-26--2026-28" in captured_inputs[0]
    assert "**Deterministic Season Phase Load Context**" in captured_inputs[0]
    assert "season_phase_role" in captured_inputs[0]
    assert "role_week_load_bands" in captured_inputs[0]


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
    _write_minimal_scenario_chain(store, athlete_id)
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
    monkeypatch.setattr(
        "rps.orchestrator.plan_week.run_agent_multi_output",
        lambda *_args, **kwargs: run_ids.append(kwargs["run_id"]) or {"ok": True, "produced": True},
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
    store.save_document(
        athlete_id,
        ArtifactType.SEASON_PLAN,
        "2026-11--2026-13",
        {
            "meta": {"iso_week_range": "2026-11--2026-13"},
            "data": {
                "phases": [
                    {
                        "phase_id": "P01",
                        "name": "Base 1",
                        "cycle": "Base",
                        "iso_week_range": "2026-11--2026-13",
                    }
                ]
            },
        },
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

    monkeypatch.setattr("rps.orchestrator.plan_week._build_user_data_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr("rps.orchestrator.plan_week._build_kpi_selection_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(
        "rps.orchestrator.plan_week.run_agent_multi_output",
        lambda *_args, **kwargs: run_ids.append(kwargs["run_id"]) or {"ok": True, "produced": True},
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
    _write_minimal_scenario_chain(store, athlete_id)

    runtime = SimpleNamespace(
        workspace_root=tmp_path,
        reasoning_effort=None,
        reasoning_summary=None,
    )

    monkeypatch.setattr("rps.orchestrator.plan_week._build_user_data_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr("rps.orchestrator.plan_week._build_kpi_selection_block", lambda *_args, **_kwargs: "")

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
    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace(athlete_id)
    store.save_document(
        athlete_id,
        ArtifactType.SEASON_PLAN,
        "2026-11",
        {
            "meta": {
                "artifact_type": "SEASON_PLAN",
                "version_key": "2026-11",
                "iso_week": "2026-11",
                "iso_week_range": "2026-11--2026-13",
                "created_at": "2026-04-02T00:00:00Z",
            },
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
        },
        producer_agent="season_planner",
        run_id="seed",
        update_latest=True,
    )
    _write_minimal_scenario_chain(store, athlete_id)
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

    monkeypatch.setattr("rps.orchestrator.plan_week._build_user_data_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr("rps.orchestrator.plan_week._build_kpi_selection_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr("rps.orchestrator.plan_week._resolve_latest_historical_week_versions", lambda *_args, **_kwargs: {})
    monkeypatch.setattr("rps.orchestrator.plan_week.build_athlete_state_snapshot_prompt_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr("rps.orchestrator.plan_week.build_planning_context_snapshot_prompt_block", lambda *_args, **_kwargs: "")

    def _fake_run_agent_multi_output(*_args, **kwargs):
        task_value = kwargs["tasks"][0].value
        if task_value == "CREATE_PHASE_STRUCTURE":
            store.save_document(
                athlete_id,
                ArtifactType.PHASE_STRUCTURE,
                "2026-11--2026-13__new",
                {
                    "meta": {
                        "artifact_type": "PHASE_STRUCTURE",
                        "version_key": "2026-11--2026-13__new",
                        "iso_week_range": "2026-11--2026-13",
                        "created_at": "2026-04-03T00:00:00Z",
                    },
                    "data": {},
                },
                producer_agent="phase_architect",
                run_id=kwargs["run_id"],
                update_latest=True,
            )
        elif task_value == "CREATE_PHASE_PREVIEW":
            store.save_document(
                athlete_id,
                ArtifactType.PHASE_PREVIEW,
                "2026-11--2026-13__new",
                {
                    "meta": {
                        "artifact_type": "PHASE_PREVIEW",
                        "version_key": "2026-11--2026-13__new",
                        "iso_week_range": "2026-11--2026-13",
                        "created_at": "2026-04-03T00:00:01Z",
                    },
                    "data": {},
                },
                producer_agent="phase_architect",
                run_id=kwargs["run_id"],
                update_latest=True,
            )
        else:
            pytest.fail(f"Unexpected task {task_value}")
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
    _write_minimal_scenario_chain(store, athlete_id)
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

    monkeypatch.setattr("rps.orchestrator.plan_week._build_user_data_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr("rps.orchestrator.plan_week._build_kpi_selection_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr("rps.orchestrator.plan_week._resolve_latest_historical_week_versions", lambda *_args, **_kwargs: {})
    monkeypatch.setattr("rps.orchestrator.plan_week.build_athlete_state_snapshot_prompt_block", lambda *_args, **_kwargs: "")
    monkeypatch.setattr("rps.orchestrator.plan_week.build_planning_context_snapshot_prompt_block", lambda *_args, **_kwargs: "")
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
    _write_minimal_scenario_chain(store, athlete_id)
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

    runtime = SimpleNamespace(
        workspace_root=tmp_path,
        reasoning_effort=None,
        reasoning_summary=None,
    )

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


def test_create_season_plan_injects_resolved_logistics_and_zone_context(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured_inputs: list[str] = []

    def _fake_runtime_for(_agent_name):
        return SimpleNamespace(workspace_root=tmp_path)

    def _fake_run_agent_multi_output(*_args, **kwargs):
        captured_inputs.append(kwargs["user_input"])
        return {"ok": True, "produced": True}

    monkeypatch.setattr("rps.orchestrator.season_flow.run_agent_multi_output", _fake_run_agent_multi_output)

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace("test_athlete")
    store.latest_path("test_athlete", ArtifactType.ATHLETE_PROFILE).write_text("{}", encoding="utf-8")
    store.latest_path("test_athlete", ArtifactType.LOGISTICS).write_text(
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
    store.latest_path("test_athlete", ArtifactType.PLANNING_EVENTS).write_text(
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
    store.latest_path("test_athlete", ArtifactType.AVAILABILITY).write_text(
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
    store.latest_path("test_athlete", ArtifactType.ZONE_MODEL).write_text(
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
    _write_minimal_scenario_chain(store, "test_athlete", horizon_weeks=8)

    season_flow.create_season_plan(
        _fake_runtime_for,
        athlete_id="test_athlete",
        year=2026,
        week=12,
        run_id="run_plan",
        selected=None,
        override_text=None,
    )

    assert captured_inputs
    assert "**Resolved Logistics Context**" in captured_inputs[0]
    assert "Business trip" in captured_inputs[0]
    assert "**Resolved Zone Model Context**" in captured_inputs[0]
    assert "ftp_watts: 300" in captured_inputs[0]


def test_create_season_plan_uses_historical_activity_versions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured_inputs: list[str] = []

    def _fake_runtime_for(_agent_name):
        return SimpleNamespace(workspace_root=tmp_path)

    def _fake_run_agent_multi_output(*_args, **kwargs):
        captured_inputs.append(kwargs["user_input"])
        return {"ok": True, "produced": True}

    monkeypatch.setattr("rps.orchestrator.season_flow.run_agent_multi_output", _fake_run_agent_multi_output)

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace("test_athlete")
    store.latest_path("test_athlete", ArtifactType.ATHLETE_PROFILE).write_text("{}", encoding="utf-8")
    store.latest_path("test_athlete", ArtifactType.AVAILABILITY).write_text(
        json.dumps({"data": {"weekly_hours": {"min": 10, "typical": 12, "max": 14}, "fixed_rest_days": ["Mon"], "availability_table": []}}),
        encoding="utf-8",
    )
    store.latest_path("test_athlete", ArtifactType.PLANNING_EVENTS).write_text(
        json.dumps({"data": {"events": []}}),
        encoding="utf-8",
    )
    store.latest_path("test_athlete", ArtifactType.ZONE_MODEL).write_text(
        json.dumps({"data": {"model_metadata": {"ftp_watts": 300}, "zones": []}}),
        encoding="utf-8",
    )
    store.save_document(
        "test_athlete",
        ArtifactType.ACTIVITIES_ACTUAL,
        "2026-16",
        {"data": {"activities": []}},
        producer_agent="user",
        run_id="activities_actual_202616",
        update_latest=True,
    )
    store.save_document(
        "test_athlete",
        ArtifactType.ACTIVITIES_TREND,
        "2026-16",
        {
            "data": {
                "weekly_trends": [
                    {
                        "year": 2026,
                        "iso_week": 16,
                        "weekly_aggregates": {"activity_count": 5, "moving_time": "13:48", "work_kj": 7760},
                        "intensity_load_metrics": {"durability_index": 0.94},
                    }
                ]
            }
        },
        producer_agent="user",
        run_id="activities_trend_202616",
        update_latest=True,
    )
    _write_minimal_scenario_chain(store, "test_athlete")

    season_flow.create_season_plan(
        _fake_runtime_for,
        athlete_id="test_athlete",
        year=2026,
        week=17,
        run_id="run_plan",
        selected=None,
        override_text=None,
    )

    assert captured_inputs
    assert "latest historical version_key before target week 2026-17: 2026-16 and 2026-16" in captured_inputs[0]
    assert "**Resolved Activity Context**" in captured_inputs[0]
    assert "historical_reference_week: 2026-16" in captured_inputs[0]
    assert "activities_actual_version: 2026-16" in captured_inputs[0]
    assert "activities_trend_version: 2026-16" in captured_inputs[0]


def test_create_season_scenarios_injects_resolved_context(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured_inputs: list[str] = []

    def _fake_runtime_for(_agent_name):
        return SimpleNamespace(workspace_root=tmp_path)

    def _fake_run_agent_multi_output(*_args, **kwargs):
        captured_inputs.append(kwargs["user_input"])
        return {"ok": True, "produced": True}

    monkeypatch.setattr("rps.orchestrator.season_flow.run_agent_multi_output", _fake_run_agent_multi_output)

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace("test_athlete")
    store.latest_path("test_athlete", ArtifactType.ATHLETE_PROFILE).write_text(
        json.dumps(
            {
                "data": {
                    "profile": {
                        "athlete_id": "test_athlete",
                        "year": 2026,
                        "athlete_name": "Test Rider",
                        "athlete_story": "Long-distance rider",
                        "location_time_zone": "Europe/Berlin",
                        "primary_disciplines": ["Randonneuring"],
                        "training_age_years": 8,
                        "age": 45,
                        "body_mass_kg": 82.4,
                        "sex": "M",
                        "age_group": "Masters",
                        "endurance_anchor_w": 210,
                        "ambition_if_range": [0.68, 0.75],
                    },
                    "objectives": {"primary": "Finish 400 km A event", "secondary": [], "priority_order": []},
                    "constraints": {},
                    "strengths": [],
                    "limitations": [],
                    "risk_flags": [],
                    "success_criteria": [],
                    "measurement_assumptions": {},
                }
            }
        ),
        encoding="utf-8",
    )
    store.latest_path("test_athlete", ArtifactType.LOGISTICS).write_text(
        json.dumps(
            {"data": {"events": [{"date": "2026-03-19", "event_id": "LOG-1", "event_type": "TRAVEL", "status": "PLANNED", "impact": "AVAILABILITY", "description": "Business trip"}]}}
        ),
        encoding="utf-8",
    )
    store.latest_path("test_athlete", ArtifactType.PLANNING_EVENTS).write_text(
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
    store.latest_path("test_athlete", ArtifactType.AVAILABILITY).write_text(
        json.dumps({"data": {"weekly_hours": {"min": 10.5, "typical": 14.0, "max": 17.5}, "fixed_rest_days": ["Mon", "Fri"], "availability_table": [], "source_type": "manual", "source_ref": "ui", "notes": ""}}),
        encoding="utf-8",
    )
    store.save_document(
        "test_athlete",
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
        run_id="test_kpi_profile",
        update_latest=True,
    )

    season_flow.create_season_scenarios(
        _fake_runtime_for,
        athlete_id="test_athlete",
        year=2026,
        week=12,
        run_id="run_scenarios",
        override_text=None,
    )

    assert captured_inputs
    assert "**Resolved Athlete Context**" in captured_inputs[0]
    assert "athlete_name: Test Rider" in captured_inputs[0]
    assert "endurance_anchor_w: 210" in captured_inputs[0]
    assert "**Resolved KPI Context**" in captured_inputs[0]
    assert "**Resolved Availability Context**" in captured_inputs[0]
    assert "**Resolved Logistics Context**" in captured_inputs[0]
    assert "**Resolved Planning Event Context**" in captured_inputs[0]
    assert "**Deterministic Season Scenario Horizon Context**" in captured_inputs[0]
    assert "target_week_start_date: 2026-03-16" in captured_inputs[0]
    assert "last_event_date: 2026-05-10" in captured_inputs[0]
    assert "last_event_iso_week: 2026-19" in captured_inputs[0]
    assert "weeks_until_last_event_from_target_week_start: 7" in captured_inputs[0]
    assert "inclusive_planning_horizon_weeks: 8" in captured_inputs[0]
    assert "season_iso_week_range: 2026-12--2026-19" in captured_inputs[0]
    assert "**Deterministic Cadence Options Context**" in captured_inputs[0]
    assert "cadence 2:1" in captured_inputs[0]
    assert "phase_count_expected 3" in captured_inputs[0]


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
                        "iso_week_range": "2026-17--2026-19",
                        "weekly_load_corridor": {
                            "weekly_kj": {
                                "min": 7200,
                                "max": 8600,
                                "notes": "Season corridor",
                            }
                        },
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

    runtime = SimpleNamespace(
        workspace_root=tmp_path,
        reasoning_effort=None,
        reasoning_summary=None,
    )

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
    at.session_state["athlete_id"] = athlete_id
    at.run()

    assert len(at.error) == 0
    assert any(select.label == "Select KPI Profile" for select in at.selectbox)
    assert store.get_latest_version_key(athlete_id, ArtifactType.KPI_PROFILE) == profile_key


def test_kpi_profile_page_saves_canonical_meta():
    from rps.ui.pages.athlete_profile.kpi_profile import _build_selected_kpi_profile_document

    store = LocalArtifactStore(root=SETTINGS.workspace_root)
    athlete_id = "test_athlete"
    store.ensure_workspace(athlete_id)
    profile_key = "des_brevet_600_km_masters"
    selected_payload = json.loads(
        (Path("specs/kpi_profiles") / f"kpi_profile_{profile_key}.json").read_text(encoding="utf-8")
    )
    run_id = "ui_kpi_profile_test"
    document = _build_selected_kpi_profile_document(
        selected_payload,
        version_key=profile_key,
        run_id=run_id,
    )
    store.save_document(
        athlete_id,
        ArtifactType.KPI_PROFILE,
        profile_key,
        document,
        producer_agent="ui_kpi_profile",
        run_id=run_id,
        update_latest=True,
    )

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
    store.save_document(
        athlete_id,
        ArtifactType.ACTIVITIES_ACTUAL,
        "2026-14",
        generic_input,
        producer_agent="test",
        run_id="store_activities_actual_202614",
        update_latest=False,
    )
    store.save_document(
        athlete_id,
        ArtifactType.ACTIVITIES_TREND,
        "2026-14",
        generic_input,
        producer_agent="test",
        run_id="store_activities_trend_202614",
        update_latest=False,
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
    user_input = captured["kwargs"]["user_input"]
    assert "ACTIVITIES_ACTUAL version_key 2026-15" in user_input
    assert "ACTIVITIES_TREND version_key 2026-15" in user_input
    assert "**Deterministic Report Evidence Context**" in user_input
    assert "diagnostic_only: True" in user_input


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


def test_create_performance_report_backfills_target_week_activity_versions(monkeypatch, tmp_path):
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

    def _fake_refresh(args, logger=None):
        store.save_document(
            athlete_id,
            ArtifactType.ACTIVITIES_ACTUAL,
            "2026-14",
            generic_input,
            producer_agent="test",
            run_id="backfill_activities_actual_202614",
            update_latest=False,
        )
        store.save_document(
            athlete_id,
            ArtifactType.ACTIVITIES_TREND,
            "2026-14",
            generic_input,
            producer_agent="test",
            run_id="backfill_activities_trend_202614",
            update_latest=False,
        )
        return 0

    captured: dict[str, object] = {}

    def _fake_run_agent_multi_output(runtime, **kwargs):
        captured["kwargs"] = kwargs
        return {"ok": True, "produced": {"store_des_analysis_report": {"path": "dummy"}}}

    monkeypatch.setattr("rps.orchestrator.plan_week.run_intervals_pipeline", _fake_refresh)
    monkeypatch.setattr("rps.orchestrator.plan_week.run_agent_multi_output", _fake_run_agent_multi_output)

    runtime = SimpleNamespace(workspace_root=tmp_path)
    result = create_performance_report(
        lambda _agent_name: runtime,
        athlete_id=athlete_id,
        report_week=SimpleNamespace(year=2026, week=14),
        run_id_prefix="report_ui",
    )

    assert result["ok"] is True
    user_input = captured["kwargs"]["user_input"]
    assert "ACTIVITIES_ACTUAL version_key 2026-14" in user_input
    assert "ACTIVITIES_TREND version_key 2026-14" in user_input


def test_create_performance_report_skips_when_target_week_activity_versions_missing(monkeypatch, tmp_path):
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

    monkeypatch.setattr("rps.orchestrator.plan_week.run_intervals_pipeline", lambda *args, **kwargs: 0)

    runtime = SimpleNamespace(workspace_root=tmp_path)
    result = create_performance_report(
        lambda _agent_name: runtime,
        athlete_id=athlete_id,
        report_week=SimpleNamespace(year=2026, week=14),
        run_id_prefix="report_ui",
    )

    assert result["ok"] is False
    assert "ACTIVITIES_ACTUAL" in result["message"]
    assert "ACTIVITIES_TREND" in result["message"]


def test_data_operations_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/athlete_profile/data_operations.py")
    at.run()
    assert len(at.error) == 0
    labels = [button.label for button in at.button]
    assert "Create Backup" in labels


def test_feed_forward_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/performance/feed_forward.py")
    at.run(timeout=10)
    assert len(at.error) == 0


def test_feed_forward_requires_selected_week_report():
    at = AppTest.from_file("src/rps/ui/pages/performance/feed_forward.py")
    at.run(timeout=10)
    assert len(at.error) == 0
    button = next(
        button for button in at.button if "Run Feed Forward" in button.label
    )
    assert button.disabled is True


def test_feed_forward_source_uses_selected_week_report_versions():
    source = Path("src/rps/ui/pages/performance/feed_forward.py").read_text(encoding="utf-8")
    assert 'workspace_get_version({{"artifact_type":"DES_ANALYSIS_REPORT","version_key":"{selected_week_key}"}})' in source
    assert 'store.load_latest(athlete_id, ArtifactType.DES_ANALYSIS_REPORT)' not in source


def test_feed_forward_source_injects_resolved_selected_week_context():
    source = Path("src/rps/ui/pages/performance/feed_forward.py").read_text(encoding="utf-8")
    assert "build_resolved_des_evaluation_context" in source
    assert "build_resolved_season_phase_feed_forward_context" in source
    assert "save_athlete_state_snapshot" in source
    assert "save_planning_context_snapshot" in source
    assert "save_advisory_memory" in source
    assert 'workspace_get_version({{"artifact_type":"DES_ANALYSIS_REPORT","version_key":"{selected_week_key}"}})' in source
    assert 'workspace_get_version({{"artifact_type":"SEASON_PHASE_FEED_FORWARD","version_key":"{selected_week_key}"}})' in source


def test_coach_source_preloads_week_scoped_activity_versions():
    source = Path("src/rps/ui/pages/coach.py").read_text(encoding="utf-8")
    assert "_coach_memory_blocks" in source
    assert "Workspace memory (auto-loaded, preferred)." in source
    assert "ArtifactType.ADVISORY_MEMORY" in source
    assert '"workspace_get_version", {"artifact_type": "ACTIVITIES_TREND", "version_key": week_key}' in source
    assert '"workspace_get_version", {"artifact_type": "ACTIVITIES_ACTUAL", "version_key": week_key}' in source


def test_week_planner_prompt_requires_percent_on_both_sides_of_ranges():
    source = Path("prompts/agents/week_planner.md").read_text(encoding="utf-8")
    assert "valid: `68%-72%`, `80%-82%`" in source
    assert "invalid: `68-72%`, `80-82%`" in source


def test_performance_report_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/performance/report.py")
    at.run(timeout=10)
    assert len(at.error) == 0


def test_performance_report_page_shows_single_active_job_message():
    from rps.ui.shared import get_iso_year_week

    year, week = get_iso_year_week()
    at = AppTest.from_file("src/rps/ui/pages/performance/report.py")
    at.session_state[f"report_job_test_athlete_{year:04d}{week:02d}"] = {
        "thread": None,
        "status": "running",
        "message": "Creating performance report...",
        "reasonings": [],
        "logs": [],
        "result": None,
        "run_id": "test-report-run",
    }
    at.run(timeout=10)

    assert len(at.error) == 0
    creating_infos = [info for info in at.info if info.value == "Creating performance report..."]
    assert len(creating_infos) == 1


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
