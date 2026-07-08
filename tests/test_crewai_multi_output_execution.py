from __future__ import annotations

import json
import sys
import types
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from rps.agents.crewai_task_execution import (
    _execute_crewai_multiagent_crew,
    _run_multicrew_cycle,
    run_agent_multi_output_crewai,
)
from rps.agents.runtime import AgentRuntime
from rps.agents.tasks import AgentTask
from rps.crewai_runtime import load_crewai_config_bundle
from rps.crewai_runtime.bindings import (
    build_agent_blueprints,
    build_task_blueprints,
)
from rps.crewai_runtime.guardrails_week import (
    review_decision_integrity,
)
from rps.crewai_runtime.models import (
    ArtifactEnvelopeModel,
    ConstraintAuditModel,
    DESAnalysisBundleModel,
    LoadGovernanceAuditModel,
    PhaseBundleDecisionModel,
    PhaseBundleManagerSynthesisModel,
    PhaseGuardrailsPayloadModel,
    PhasePreviewPayloadModel,
    PhaseReviewDecisionModel,
    PhaseStructurePayloadModel,
    PhaseWeekDraftBlueprintModel,
    PlanningDraftModel,
    ReportReviewDecisionModel,
    SeasonEventAnchorModel,
    SeasonMacrocycleDraftModel,
    SeasonPhaseBlueprintDraftOutputModel,
    SeasonPhaseDraftBlueprintModel,
    SeasonPlanManagerSynthesisModel,
    SeasonReviewDecisionModel,
    WeekDayBlueprintModel,
    WeekPlanBundleModel,
    WeekReviewDecisionModel,
    WeekWorkoutBlueprintModel,
)
from rps.prompts.loader import PromptLoader

JsonMap = dict[str, Any]


def _set_module_attrs(module: types.ModuleType, **attrs: Any) -> None:
    for key, value in attrs.items():
        setattr(module, key, value)


def test_run_agent_multi_output_crewai_persists_typed_output(monkeypatch) -> None:
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-key")
    monkeypatch.setenv("RPS_LLM_MODEL", "openai/gpt-5-mini")
    fake_crewai = types.ModuleType("crewai")
    fake_tools = types.ModuleType("crewai.tools")

    class FakeLLM:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    created_agents: list[dict[str, object]] = []

    class FakeAgent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.llm = kwargs.get("llm")
            created_agents.append(kwargs)

    class FakeTask:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.output_pydantic = kwargs.get("output_pydantic")
            self.output_json = kwargs.get("output_json")
            self.output = None

    captured_crew: dict[str, object] = {"crews": [], "tasks_by_crew": []}

    class FakeCrew:
        def __init__(self, *, tasks, **kwargs):
            self.tasks = tasks
            self.kwargs = kwargs
            captured_crew["crews"].append(kwargs)
            captured_crew["agents"] = kwargs.get("agents", [])
            captured_crew["max_agents"] = max(
                int(captured_crew.get("max_agents", 0)),
                len(kwargs.get("agents", [])),
            )
            captured_crew["tasks"] = tasks
            cast(list[list[object]], captured_crew["tasks_by_crew"]).append(list(tasks))
            if kwargs.get("manager_agent") is not None:
                captured_crew["manager_agent"] = kwargs.get("manager_agent")
            captured_crew["process"] = kwargs.get("process")

        def _build_output(self, task):
            model_cls = task.output_pydantic or task.output_json
            if model_cls is None:
                payload = {
                    "meta": {
                        "artifact_type": "SEASON_PLAN",
                        "schema_id": "SeasonPlanInterface",
                        "schema_version": "1.0",
                    },
                    "data": {},
                }
                task.output = SimpleNamespace(pydantic=None, raw=json.dumps(payload))
                return task.output
            if task.output_json is not None and task.output_pydantic is None:
                payload = {
                    "meta": {
                        "artifact_type": "SEASON_PLAN",
                        "schema_id": "SeasonPlanInterface",
                        "schema_version": "1.0",
                    },
                    "data": {"assumptions_unknowns": []},
                }
                task.output = SimpleNamespace(
                    pydantic=None,
                    json_dict=payload,
                    raw=json.dumps(payload),
                )
                return task.output
            if model_cls is SeasonPlanManagerSynthesisModel:
                model = model_cls(
                    event_priority=SeasonEventAnchorModel(),
                    macrocycle=SeasonMacrocycleDraftModel(),
                )
            elif model_cls is ConstraintAuditModel:
                model = model_cls()
            elif model_cls is LoadGovernanceAuditModel:
                model = model_cls()
            elif model_cls is SeasonPhaseBlueprintDraftOutputModel:
                model = model_cls(
                    phase_blueprints=[
                        SeasonPhaseDraftBlueprintModel(
                            phase_id="P01",
                            iso_week_range="2026-20--2026-22",
                            scenario_cadence="2:1",
                            cadence_week_roles=["LOAD_1", "LOAD_2", "DELOAD"],
                            phase_type="BASE",
                            phase_intent="shortened_re_entry",
                        )
                    ]
                )
            elif model_cls is SeasonReviewDecisionModel:
                model = model_cls(status="approved", writer_ready_summary="ready")
            elif model_cls is PlanningDraftModel:
                model = model_cls()
            elif model_cls is WeekPlanBundleModel:
                model = model_cls(
                    day_blueprints=[
                        WeekDayBlueprintModel(
                            day=day,
                            date=date_value,
                            day_role="REST",
                        )
                        for day, date_value in [
                            ("Mon", "2026-05-11"),
                            ("Tue", "2026-05-12"),
                            ("Wed", "2026-05-13"),
                            ("Thu", "2026-05-14"),
                            ("Fri", "2026-05-15"),
                            ("Sat", "2026-05-16"),
                            ("Sun", "2026-05-17"),
                        ]
                    ],
                    workout_blueprints=[
                        WeekWorkoutBlueprintModel(
                            workout_id="W1",
                            date="2026-05-12",
                            day_role="ENDURANCE",
                            planned_duration_minutes=60,
                            planned_kj=500,
                        )
                    ],
                )
            elif model_cls is WeekReviewDecisionModel:
                model = model_cls(status="approved", writer_ready_summary="ready")
            elif model_cls is DESAnalysisBundleModel:
                model = model_cls()
            elif model_cls is ReportReviewDecisionModel:
                model = model_cls(status="approved", writer_ready_summary="ready")
            else:
                model = model_cls()
            task.output = SimpleNamespace(
                pydantic=model if task.output_pydantic is not None else None,
                json_dict=model.model_dump() if task.output_json is not None and hasattr(model, "model_dump") else None,
                raw=model.model_dump_json(),
            )
            return task.output

        def kickoff(self):
            for task in self.tasks:
                self._build_output(task)
            return self.tasks[-1].output

    class FakeProcess:
        sequential = "sequential"
        hierarchical = "hierarchical"

    def _tool(name: str):
        def _decorate(func):
            func.tool_name = name
            return func

        return _decorate

    _set_module_attrs(
        fake_crewai,
        LLM=FakeLLM,
        Agent=FakeAgent,
        Task=FakeTask,
        Crew=FakeCrew,
        Process=FakeProcess,
    )
    _set_module_attrs(fake_tools, tool=_tool)

    monkeypatch.setitem(sys.modules, "crewai", fake_crewai)
    monkeypatch.setitem(sys.modules, "crewai.tools", fake_tools)

    saved = {"ok": True, "path": "/tmp/out.json", "version_key": "2026-19__x", "run_id": "run-1"}

    def _fake_guard_put_validated(self, **kwargs):
        return saved

    monkeypatch.setattr(
        "rps.agents.crewai_task_execution.GuardedValidatedStore.guard_put_validated",
        _fake_guard_put_validated,
    )
    monkeypatch.setattr(
        "rps.agents.crewai_task_execution.normalize_season_plan_draft_bundle",
        lambda _bundle: {
            "event_priority": {"primary_a_events": ["A Event"]},
            "macrocycle": {"deload_cadence": "2:1"},
            "season_load_envelope": {"expected_average_weekly_kj_range": {"min": 7000, "max": 9000}},
            "season_semantic_notes": ["Frame the objective against the A event."],
            "phase_blueprints": [
                {
                    "phase_id": "P01",
                    "iso_week_range": "2026-20--2026-22",
                    "scenario_cadence": "2:1",
                    "cadence_week_roles": ["LOAD_1", "LOAD_2", "DELOAD"],
                    "phase_type": "BASE",
                    "phase_intent": "shortened_re_entry",
                    "phase_taxonomy_version": "canonical_phase_taxonomy_v1",
                    "allowed_domains": ["ENDURANCE", "TEMPO"],
                    "forbidden_domains": ["THRESHOLD", "VO2MAX"],
                    "semantic_contract": {
                        "methodology_family": "compressed_reentry",
                        "threshold_role": "forbidden",
                        "event_load_policy": "no_event_load_exception",
                        "taper_policy": "not_applicable",
                        "writer_semantic_notes": ["Keep the phase recovery-protective."],
                    },
                }
            ],
        },
    )
    monkeypatch.setattr(
        "rps.agents.crewai_task_execution._validate_normalized_season_bundle",
        lambda planning_bundle, **kwargs: planning_bundle,
    )

    runtime = AgentRuntime(
        model="openai/gpt-5-mini",
        temperature=1.0,
        reasoning_effort="medium",
        reasoning_summary="auto",
        max_completion_tokens=8000,
        prompt_loader=PromptLoader(Path("prompts")),
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime/athletes"),
    )

    result = run_agent_multi_output_crewai(
        runtime,
        agent_name="season_planner",
        athlete_id="i150546",
        tasks=[AgentTask.CREATE_SEASON_PLAN],
        user_input="Create the season plan.",
        run_id="run-1",
        model_override="gpt-5.4-nano",
    )

    crews = cast(list[JsonMap], captured_crew["crews"])
    assert result["ok"] is True
    assert result["produced"]["store_season_plan"] == saved
    assert isinstance(captured_crew["agents"], list)
    assert int(cast(int, captured_crew["max_agents"])) >= 7
    assert crews[0].get("manager_agent") is None
    assert crews[0].get("process") == "sequential"
    assert crews[1].get("manager_agent") is None
    assert crews[1].get("process") == "sequential"
    planning_crews = [crew for crew in crews if crew.get("planning") is True]
    assert planning_crews == []
    final_season_task = next(
        task
        for task_group in cast(list[list[object]], captured_crew["tasks_by_crew"])
        for task in task_group
        if getattr(task, "kwargs", {}).get("name") == "season_plan_finalize"
    )
    assert getattr(final_season_task, "output_json", None) is None
    assert getattr(final_season_task, "output_pydantic", None) is SeasonPlanManagerSynthesisModel
    macrocycle_agent = next(agent for agent in created_agents if agent["role"] == "Reverse-plan season macrocycles")
    assert "reasoning" not in macrocycle_agent
    assert "max_reasoning_attempts" not in macrocycle_agent
    assert getattr(macrocycle_agent["llm"], "kwargs", {}).get("model") == "gpt-5.4"
    writer_agent = next(agent for agent in created_agents if agent["role"] == "Persisted season artefact serializer")
    assert "reasoning" not in writer_agent
    assert writer_agent["allow_delegation"] is False
    assert writer_agent["max_iter"] == 2
    assert writer_agent["respect_context_window"] is True
    assert writer_agent["cache"] is False
    assert getattr(writer_agent["llm"], "kwargs", {}).get("model") == "gpt-5.4-mini"
    manager_agent = next(agent for agent in created_agents if agent["role"] == "Internal season planning synthesizer")
    assert manager_agent["allow_delegation"] is False
    assert manager_agent["max_iter"] == 5

def test_run_agent_multi_output_crewai_phase_bundle_split(monkeypatch) -> None:
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-key")
    monkeypatch.setenv("RPS_LLM_MODEL", "openai/gpt-5-mini")
    fake_crewai = types.ModuleType("crewai")
    fake_tools = types.ModuleType("crewai.tools")

    class FakeLLM:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    created_agents: list[dict[str, object]] = []

    class FakeAgent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.llm = kwargs.get("llm")
            created_agents.append(kwargs)

    class FakeTask:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.output_pydantic = kwargs.get("output_pydantic")
            self.description = kwargs["description"]
            self.output = None

    captured_crew: dict[str, object] = {"crews": []}

    class FakeCrew:
        def __init__(self, *, tasks, **kwargs):
            self.tasks = tasks
            self.kwargs = kwargs
            captured_crew["crews"].append(kwargs)
            captured_crew["agents"] = kwargs.get("agents", [])
            captured_crew["max_agents"] = max(
                int(captured_crew.get("max_agents", 0)),
                len(kwargs.get("agents", [])),
            )
            captured_crew["tasks"] = tasks
            if kwargs.get("manager_agent") is not None:
                captured_crew["manager_agent"] = kwargs.get("manager_agent")
            captured_crew["process"] = kwargs.get("process")

        def _build_output(self, task):
            model_cls = task.output_pydantic
            if model_cls is PhaseBundleManagerSynthesisModel:
                model = model_cls(
                    phase_range="2026-17--2026-19",
                    phase_id="P01",
                    phase_type="Base",
                    phase_intent="general_base",
                    cadence_source="season_plan",
                    week_blueprints=[
                        PhaseWeekDraftBlueprintModel(
                            week="2026-17",
                            phase_role="Base",
                            week_role="LOAD_1",
                            s5_band_min=5000,
                            s5_band_max=6000,
                        )
                    ],
                    constraint_audit=ConstraintAuditModel(),
                    load_governance_audit=LoadGovernanceAuditModel(),
                    decision_summary=PhaseBundleDecisionModel(),
                )
            elif model_cls is PhaseGuardrailsPayloadModel:
                model = model_cls(phase_intent="general_base")
            elif model_cls is PhaseStructurePayloadModel:
                model = model_cls(phase_intent="general_base")
            elif model_cls is PhasePreviewPayloadModel:
                model = model_cls(phase_intent="general_base")
            elif model_cls is PhaseReviewDecisionModel:
                model = model_cls(status="approved", writer_ready_summary="ready")
            elif model_cls is PlanningDraftModel:
                model = model_cls()
            elif model_cls is None:
                payload = {
                    "meta": {
                        "artifact_type": "PHASE_GUARDRAILS",
                        "schema_id": "PhaseGuardrailsInterface",
                        "schema_version": "1.0",
                        "owner_agent": "Phase-Artifact-Writer",
                    },
                    "data": {},
                }
                task.output = SimpleNamespace(pydantic=None, raw=json.dumps(payload))
                return task.output
            else:
                model = model_cls()
            task.output = SimpleNamespace(pydantic=model, raw=model.model_dump_json())
            return task.output

        def kickoff(self):
            for task in self.tasks:
                self._build_output(task)
            return self.tasks[-1].output

    class FakeProcess:
        sequential = "sequential"
        hierarchical = "hierarchical"

    def _tool(name: str):
        def _decorate(func):
            func.tool_name = name
            return func

        return _decorate

    _set_module_attrs(
        fake_crewai,
        LLM=FakeLLM,
        Agent=FakeAgent,
        Task=FakeTask,
        Crew=FakeCrew,
        Process=FakeProcess,
    )
    _set_module_attrs(fake_tools, tool=_tool)

    monkeypatch.setitem(sys.modules, "crewai", fake_crewai)
    monkeypatch.setitem(sys.modules, "crewai.tools", fake_tools)

    captured: dict[str, object] = {}

    def _fake_guard_put_validated(self, **kwargs):
        captured.update(kwargs)
        return {"ok": True, "path": "/tmp/phase.json", "version_key": "2026-17__x", "run_id": "run-phase"}

    monkeypatch.setattr(
        "rps.agents.crewai_task_execution.GuardedValidatedStore.guard_put_validated",
        _fake_guard_put_validated,
    )
    monkeypatch.setattr(
        "rps.agents.crewai_task_execution.normalize_phase_draft_bundle",
        lambda payload: payload,
    )
    monkeypatch.setattr(
        "rps.agents.crewai_task_execution._validate_normalized_phase_bundle",
        lambda payload, **_: payload,
    )

    runtime = AgentRuntime(
        model="openai/gpt-5-mini",
        temperature=1.0,
        reasoning_effort="medium",
        reasoning_summary="auto",
        max_completion_tokens=8000,
        prompt_loader=PromptLoader(Path("prompts")),
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime/athletes"),
    )

    result = run_agent_multi_output_crewai(
        runtime,
        agent_name="phase_architect",
        athlete_id="i150546",
        tasks=[AgentTask.CREATE_PHASE_GUARDRAILS],
        user_input="Create phase guardrails.",
        run_id="run-phase",
    )

    crews = cast(list[JsonMap], captured_crew["crews"])
    assert result["ok"] is True
    document = captured["document"]
    assert isinstance(document, dict)
    meta = document["meta"]
    assert meta["artifact_type"] == "PHASE_GUARDRAILS"
    assert meta["owner_agent"] == "Phase-Artifact-Writer"
    assert isinstance(captured_crew["agents"], list)
    assert int(cast(int, captured_crew["max_agents"])) >= 7
    assert crews[0].get("manager_agent") is None
    assert crews[0].get("process") == "sequential"
    assert crews[1].get("manager_agent") is None
    assert crews[1].get("process") == "sequential"
    planning_crews = [crew for crew in crews if crew.get("planning") is True]
    assert planning_crews == []
    band_agent = next(agent for agent in created_agents if agent["role"] == "Phase weekly corridor specialist")
    assert "reasoning" not in band_agent
    assert "max_reasoning_attempts" not in band_agent
    assert getattr(band_agent["llm"], "kwargs", {}).get("model") == "gpt-5.4-mini"
    writer_agent = next(agent for agent in created_agents if agent["role"] == "Persisted phase artefact serializer")
    assert "reasoning" not in writer_agent
    assert writer_agent["allow_delegation"] is False
    assert writer_agent["max_iter"] == 2
    assert writer_agent["respect_context_window"] is True
    assert getattr(writer_agent["llm"], "kwargs", {}).get("model") == "gpt-5.4-mini"

def test_run_agent_multi_output_crewai_week_plan_uses_sequential_specialist_execution(monkeypatch) -> None:
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-key")
    monkeypatch.setenv("RPS_LLM_MODEL", "openai/gpt-5-mini")
    fake_crewai = types.ModuleType("crewai")
    fake_tools = types.ModuleType("crewai.tools")

    class FakeLLM:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    created_agents: list[dict[str, object]] = []

    class FakeAgent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.llm = kwargs.get("llm")
            created_agents.append(kwargs)

    class FakeTask:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.output_pydantic = kwargs.get("output_pydantic")
            self.output_json = kwargs.get("output_json")
            self.output = None

    captured_crew: dict[str, object] = {"crews": []}

    class FakeCrew:
        def __init__(self, *, tasks, **kwargs):
            self.tasks = tasks
            self.kwargs = kwargs
            captured_crew["crews"].append(kwargs)

        def kickoff(self):
            task = self.tasks[-1]
            model_cls = task.output_pydantic or task.output_json
            if model_cls is WeekPlanBundleModel:
                model = model_cls(
                    day_blueprints=[
                        WeekDayBlueprintModel(day="Mon", date="2026-05-11", day_role="REST"),
                        WeekDayBlueprintModel(day="Tue", date="2026-05-12", day_role="QUALITY"),
                        WeekDayBlueprintModel(day="Wed", date="2026-05-13", day_role="ENDURANCE"),
                        WeekDayBlueprintModel(day="Thu", date="2026-05-14", day_role="ENDURANCE"),
                        WeekDayBlueprintModel(day="Fri", date="2026-05-15", day_role="REST"),
                        WeekDayBlueprintModel(day="Sat", date="2026-05-16", day_role="LONG"),
                        WeekDayBlueprintModel(day="Sun", date="2026-05-17", day_role="ENDURANCE"),
                    ],
                    workout_blueprints=[
                        WeekWorkoutBlueprintModel(
                            workout_id="W1",
                            date="2026-05-12",
                            day_role="QUALITY",
                            planned_duration_minutes=75,
                            planned_kj=650,
                        )
                    ],
                )
            elif model_cls is WeekReviewDecisionModel:
                model = model_cls(status="approved", writer_ready_summary="ready")
            elif model_cls is ArtifactEnvelopeModel:
                model = model_cls(
                    meta={
                        "artifact_type": "WEEK_PLAN",
                        "schema_id": "WeekPlanInterface",
                        "schema_version": "1.2",
                    },
                    data={"workouts": []},
                )
            else:
                model = model_cls()
            task.output = SimpleNamespace(
                pydantic=model if task.output_pydantic is not None else None,
                json_dict=model.model_dump() if hasattr(model, "model_dump") else None,
                raw=model.model_dump_json(),
            )
            return task.output

    class FakeProcess:
        sequential = "sequential"
        hierarchical = "hierarchical"

    def _tool(name: str):
        def _decorate(func):
            func.tool_name = name
            return func

        return _decorate

    _set_module_attrs(
        fake_crewai,
        LLM=FakeLLM,
        Agent=FakeAgent,
        Task=FakeTask,
        Crew=FakeCrew,
        Process=FakeProcess,
    )
    _set_module_attrs(fake_tools, tool=_tool)

    monkeypatch.setitem(sys.modules, "crewai", fake_crewai)
    monkeypatch.setitem(sys.modules, "crewai.tools", fake_tools)

    runtime = AgentRuntime(
        model="openai/gpt-5-mini",
        temperature=1.0,
        reasoning_effort="medium",
        reasoning_summary="auto",
        max_completion_tokens=8000,
        prompt_loader=PromptLoader(Path("prompts")),
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime/athletes"),
    )

    bundle = load_crewai_config_bundle(root=Path.cwd())
    agent_blueprints = build_agent_blueprints(bundle)
    task_blueprints = build_task_blueprints(bundle)
    tools = {
        name: SimpleNamespace(name=name)
        for name in (
            "workspace_get_input",
            "workspace_get_latest",
            "workspace_get_version",
            "workspace_get_phase_context",
            "workspace_get_week_calendar_context",
            "workspace_get_phase_execution_context",
        )
    }

    result = _execute_crewai_multiagent_crew(
        agent_cls=FakeAgent,
        crewai_llm_cls=FakeLLM,
        crew_cls=FakeCrew,
        task_cls=FakeTask,
        process_cls=FakeProcess,
        runtime=runtime,
        bundle=bundle,
        manager_agent_name="week_plan_manager",
        crew_name="week_planning",
        crew_task_names=(
            "week_context_read",
            "week_evidence_alignment",
            "week_constraint_review",
            "week_load_target_draft",
            "week_revision_draft",
            "week_workout_text_draft",
            "week_plan_finalize",
        ),
        final_task_name="week_plan_finalize",
        task_blueprints=task_blueprints,
        agent_blueprints=agent_blueprints,
        tools=tools,
        user_input="Create week plan.",
        athlete_id="i150546",
        run_id="run-week",
        execution_mode="sequential",
    )

    crews = cast(list[JsonMap], captured_crew["crews"])
    assert result.model_dump()["day_blueprints"]
    assert crews[0].get("manager_agent") is None
    assert crews[0].get("process") == "sequential"
    manager_agent = next(agent for agent in created_agents if agent["role"] == "Internal week bundle synthesizer")
    assert getattr(manager_agent["llm"], "kwargs", {}).get("model") == "gpt-5.4-mini"

def test_run_multicrew_cycle_replays_only_sanitized_replan_context(tmp_path) -> None:
    captured_inputs: list[str] = []

    def _planning_runner(loop_input: str) -> dict[str, object]:
        captured_inputs.append(loop_input)
        return {"bundle": "candidate", "warnings": []}

    decisions: Iterator[dict[str, object]] = iter(
        [
            {
                "status": "replan_required",
                "blocking_issues": ["Old blocker that must not be replayed wholesale."],
                "warnings": ["Stale warning that should not be forwarded."],
                "replan_instructions": [
                    {
                        "target_specialists": ["Week Planner"],
                        "issues_to_fix": ["Reduce weekly kJ into active band."],
                        "must_preserve": ["Fixed rest days Mon and Fri."],
                        "priority_order": ["Bring weekly kJ into band first."],
                        "max_scope_of_change": "Adjust durations only.",
                    }
                ],
                "writer_ready_summary": "Use the repaired draft only.",
            },
            {
                "status": "approved",
                "warnings": [],
                "blocking_issues": [],
                "replan_instructions": [],
                "writer_ready_summary": "",
            },
        ]
    )

    def _review_runner(loop_input: str, planning_bundle: dict[str, object]) -> dict[str, object]:
        return next(decisions)

    planning_bundle, review_decision = _run_multicrew_cycle(
        runtime=AgentRuntime(
            model="gpt-5.4-mini",
            temperature=None,
            reasoning_effort=None,
            reasoning_summary=None,
            max_completion_tokens=None,
            prompt_loader=SimpleNamespace(),
            schema_dir=tmp_path,
            workspace_root=tmp_path,
        ),
        bundle=SimpleNamespace(),
        user_input="Create week plan.",
        planning_runner=_planning_runner,
        review_runner=_review_runner,
        max_replan_rounds=2,
    )

    assert planning_bundle == {"bundle": "candidate", "warnings": []}
    assert review_decision["status"] == "approved"
    assert len(captured_inputs) == 2
    second_input = captured_inputs[1]
    assert "Active replan instructions" in second_input
    assert "Reduce weekly kJ into active band." in second_input
    assert "Stale warning that should not be forwarded." not in second_input
    assert "Old blocker that must not be replayed wholesale." not in second_input

def test_review_decision_integrity_rejects_approved_blocking_issues() -> None:
    ok, message = review_decision_integrity(
        {
            "status": "approved",
            "blocking_issues": ["Still broken."],
            "warnings": [],
            "replan_instructions": [],
            "writer_ready_summary": "ready",
        }
    )

    assert ok is False
    assert "must not include blocking_issues" in message

def test_review_decision_integrity_requires_writer_ready_summary_for_approval() -> None:
    ok, message = review_decision_integrity(
        {
            "status": "approved",
            "blocking_issues": [],
            "warnings": [],
            "replan_instructions": [],
            "writer_ready_summary": "",
        }
    )

    assert ok is False
    assert "must include non-empty writer_ready_summary" in message

def test_review_decision_integrity_requires_replan_instructions_for_replan() -> None:
    ok, message = review_decision_integrity(
        {
            "status": "replan_required",
            "blocking_issues": ["Needs repair."],
            "warnings": [],
            "replan_instructions": [],
            "writer_ready_summary": "fix it",
        }
    )

    assert ok is False
    assert "must include replan_instructions" in message

def test_run_agent_multi_output_crewai_normalizes_feed_forward_owner(monkeypatch) -> None:
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-key")
    monkeypatch.setenv("RPS_LLM_MODEL", "openai/gpt-5-mini")
    fake_crewai = types.ModuleType("crewai")
    fake_tools = types.ModuleType("crewai.tools")

    class FakeLLM:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeAgent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeTask:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.output_pydantic = kwargs.get("output_pydantic")
            self.output = None

    class FakeCrew:
        def __init__(self, *, tasks, **kwargs):
            self.tasks = tasks
            self.kwargs = kwargs

        def kickoff(self):
            task = self.tasks[0]
            model_cls = task.output_pydantic
            payload = {
                "meta": {
                    "artifact_type": "SEASON_PHASE_FEED_FORWARD",
                    "schema_id": "SeasonPhaseFeedForwardInterface",
                    "schema_version": "1.0",
                    "owner_agent": "Performance-Analyst",
                },
                "data": {},
            }
            if model_cls is None:
                task.output = SimpleNamespace(pydantic=None, raw=json.dumps(payload))
                return task.output
            envelope = model_cls(**payload)
            task.output = SimpleNamespace(pydantic=envelope, raw=envelope.model_dump_json())
            return task.output

    class FakeProcess:
        sequential = "sequential"

    def _tool(name: str):
        def _decorate(func):
            func.tool_name = name
            return func

        return _decorate

    _set_module_attrs(
        fake_crewai,
        LLM=FakeLLM,
        Agent=FakeAgent,
        Task=FakeTask,
        Crew=FakeCrew,
        Process=FakeProcess,
    )
    _set_module_attrs(fake_tools, tool=_tool)

    monkeypatch.setitem(sys.modules, "crewai", fake_crewai)
    monkeypatch.setitem(sys.modules, "crewai.tools", fake_tools)

    captured: dict[str, object] = {}

    def _fake_guard_put_validated(self, **kwargs):
        captured.update(kwargs)
        return {"ok": True, "path": "/tmp/out.json", "version_key": "2026-19__x", "run_id": "run-ff"}

    monkeypatch.setattr(
        "rps.agents.crewai_task_execution.GuardedValidatedStore.guard_put_validated",
        _fake_guard_put_validated,
    )

    runtime = AgentRuntime(
        model="openai/gpt-5-mini",
        temperature=1.0,
        reasoning_effort="medium",
        reasoning_summary="auto",
        max_completion_tokens=8000,
        prompt_loader=PromptLoader(Path("prompts")),
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime/athletes"),
    )

    result = run_agent_multi_output_crewai(
        runtime,
        agent_name="season_planner",
        athlete_id="i150546",
        tasks=[AgentTask.CREATE_SEASON_PHASE_FEED_FORWARD],
        user_input="Create season-phase feed-forward.",
        run_id="run-ff",
    )

    assert result["ok"] is True
    document = captured["document"]
    assert isinstance(document, dict)
    meta = document["meta"]
    assert meta["owner_agent"] == "Season-Artifact-Writer"
