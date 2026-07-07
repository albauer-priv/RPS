from __future__ import annotations

import json
import os
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from rps.agents.crewai_builders import _task_tools_for_blueprint
from rps.agents.crewai_output_extraction import (
    _coerce_artifact_envelope,
)
from rps.agents.crewai_task_execution import (
    _TASK_BLUEPRINT_BY_AGENT_TASK,
    _build_crewai_task,
    _build_internal_task_description,
    _compact_internal_user_input,
    _extract_authoritative_runtime_blocks,
)
from rps.agents.runtime import AgentRuntime
from rps.agents.tasks import AgentTask
from rps.crewai_runtime import guardrails as crewai_guardrails
from rps.crewai_runtime import load_crewai_config_bundle
from rps.crewai_runtime import telemetry as crewai_telemetry
from rps.crewai_runtime.bindings import (
    build_agent_blueprints,
    build_task_blueprints,
    collect_native_agent_kwargs,
    configured_task_context_names,
    output_model_for_kind,
    output_model_for_task,
)
from rps.crewai_runtime.guardrails import (
    build_task_guardrail_kwargs,
    guardrail_runtime_context,
    resolve_task_policy,
)
from rps.crewai_runtime.knowledge import (
    _compact_knowledge_query,
    build_crewai_knowledge_kwargs,
    resolve_agent_knowledge_profile,
    resolve_crew_knowledge_profile,
)
from rps.crewai_runtime.memory import (
    build_agent_memory_value,
    build_crew_memory_kwargs,
    build_memory_instance,
    resolve_agent_memory_profile,
    resolve_crew_memory_profile,
)
from rps.crewai_runtime.models import (
    PlanningDraftModel,
)
from rps.crewai_runtime.skills import build_crewai_skill_kwargs, resolve_agent_skill_profile
from rps.orchestrator import season_flow
from rps.prompts.loader import PromptLoader
from rps.ui.run_store import load_events
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType


def _set_module_attrs(module: types.ModuleType, **attrs: Any) -> None:
    for key, value in attrs.items():
        setattr(module, key, value)


def _open_object_schema_findings(schema: object, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            additional = schema.get("additionalProperties", "<missing>")
            if additional is not False:
                findings.append(f"{path}: additionalProperties={additional!r}")
        if "additionalProperties" in schema and schema.get("additionalProperties") is not False:
            findings.append(f"{path}: explicit additionalProperties={schema.get('additionalProperties')!r}")
        for key, value in schema.items():
            if isinstance(value, (dict, list)) and key not in {"default", "examples"}:
                findings.extend(_open_object_schema_findings(value, f"{path}.{key}"))
    elif isinstance(schema, list):
        for index, item in enumerate(schema):
            findings.extend(_open_object_schema_findings(item, f"{path}[{index}]"))
    return findings


def test_crewai_config_bundle_loads_known_agents_and_tasks() -> None:
    bundle = load_crewai_config_bundle(root=Path("."))

    agent_defs = bundle.agents["agents"]
    task_defs = bundle.tasks["tasks"]
    knowledge_defs = bundle.knowledge_sources["agents"]
    flow_defs = bundle.flow_persistence["flows"]
    assert "conversation_manager" in agent_defs
    assert "week_recommendation_specialist" in agent_defs
    assert "week_planner" in agent_defs
    assert "season_plan_manager" in agent_defs
    assert "phase_bundle_manager" in agent_defs
    assert "week_plan_manager" in knowledge_defs
    assert flow_defs["season"]["persist"] is True
    assert flow_defs["coach"]["persist"] is False
    assert bundle.runtime_profiles["crews"]["season_planning"]["planning"]["enabled"] is False
    assert bundle.runtime_profiles["crews"]["phase_planning"]["planning"]["enabled"] is False
    assert bundle.runtime_profiles["crews"]["phase_planning"]["planning"]["model"] == "gpt-5.4-mini"
    assert bundle.runtime_profiles["agents"]["season_plan_manager"]["model"] == "gpt-5.4-mini"
    assert bundle.runtime_profiles["agents"]["season_plan_manager"]["reasoning"]["enabled"] is False
    assert bundle.runtime_profiles["agents"]["macrocycle_architect"]["model"] == "gpt-5.4"
    assert bundle.runtime_profiles["agents"]["macrocycle_architect"]["reasoning"]["enabled"] is False
    assert bundle.runtime_profiles["agents"]["week_artifact_writer"]["reasoning"]["enabled"] is False
    assert bundle.skills["agents"]["week_revision_specialist"]["skill"] == "skills/week/revision-methodology"
    assert bundle.skills["crews"]["coach_conversation"]["skills"] == [
        "skills/shared/runtime-boundaries",
        "skills/shared/resolved-context-consumption",
        "skills/shared/traceability-and-naming",
    ]
    assert task_defs["classify_turn"]["agent"] == "conversation_manager"
    assert task_defs["create_week_preview"]["agent"] == "week_revision_specialist"
    assert task_defs["season_scenario_selection"]["agent"] == "season_scenario"
    assert task_defs["season_scenario_selection"]["kind"] == "persisted_artifact"
    assert task_defs["week_plan"]["agent"] == "week_artifact_writer"
    assert task_defs["season_plan"]["agent"] == "season_artifact_writer"
    assert task_defs["phase_guardrails"]["agent"] == "phase_artifact_writer"
    assert _TASK_BLUEPRINT_BY_AGENT_TASK[AgentTask.CREATE_SEASON_SCENARIO_SELECTION] == "season_scenario_selection"

def test_coerce_artifact_envelope_extracts_wrapped_raw_payload() -> None:
    envelope = {
        "meta": {"artifact_type": "SEASON_SCENARIOS"},
        "data": {"scenarios": []},
    }
    wrapped = {
        "raw": json.dumps(envelope),
        "pydantic": None,
        "json_dict": None,
        "tasks_output": [
            {
                "raw": json.dumps(envelope),
            }
        ],
        "token_usage": {"prompt_tokens": 123},
    }

    assert _coerce_artifact_envelope(wrapped) == envelope

def test_crewai_blueprints_build_from_yaml() -> None:
    bundle = load_crewai_config_bundle(root=Path("."))
    agents = build_agent_blueprints(bundle)
    tasks = build_task_blueprints(bundle)

    assert agents["conversation_manager"].goal
    assert agents["season_plan_auditor"].goal
    assert agents["season_plan_auditor"].config["prompt_agent"] == "season_plan_auditor"
    assert agents["phase_guardrail_band_specialist"].config["prompt_agent"] == "guardrails_specialist"
    assert agents["week_recommendation_specialist"].knowledge_profile["sources"]
    assert agents["week_recommendation_specialist"].skill_profile["agent_skill"] == "skills/week/recommendation-and-adjustment"
    assert agents["week_recommendation_specialist"].skill_profile["paths"] == ["skills/week/recommendation-and-adjustment"]
    assert tasks["classify_turn"].output_kind == "turn_mode"
    assert tasks["form_adjustment_intent"].output_kind == "adjustment_intent"
    assert tasks["week_plan"].output_kind == "artifact_envelope"
    assert tasks["phase_bundle_finalize"].output_kind == "phase_bundle_draft"
    assert tasks["phase_bundle_finalize"].context_names == (
        "phase_context_read",
        "phase_evidence_alignment",
        "phase_guardrail_band_draft",
        "phase_execution_rules_draft",
        "phase_structure_draft",
        "phase_cadence_recovery_draft",
        "phase_intensity_distribution_draft",
        "phase_event_integration_draft",
        "phase_preview_draft",
    )
    assert tasks["phase_bundle_finalize"].execution_policy["guardrails"] == (
        "typed_output_present",
        "phase_bundle_integrity",
        "phase_week_role_load_coherence",
        "phase_bundle_review_readiness",
    )
    assert tasks["season_plan_finalize"].output_kind == "season_plan_draft_bundle"

def test_task_policy_resolution_and_guardrail_kwargs() -> None:
    bundle = load_crewai_config_bundle(root=Path("."))
    tasks = build_task_blueprints(bundle)

    preview_policy = resolve_task_policy(tasks["create_week_preview"], bundle.task_policies)
    artifact_policy = resolve_task_policy(tasks["week_plan"], bundle.task_policies)
    season_finalize_policy = resolve_task_policy(tasks["season_plan_finalize"], bundle.task_policies)

    assert preview_policy.output_mode == "pydantic"
    assert "coach_preview_summary_complete" in preview_policy.guardrails
    assert artifact_policy.output_mode == "json"
    assert season_finalize_policy.output_mode == "json"
    assert "artifact_schema_valid" in artifact_policy.guardrails
    assert "week_corridor_and_capacity_check" in artifact_policy.guardrails
    assert "week_active_corridor_match" in artifact_policy.guardrails
    assert "week_recovery_day_load_check" in artifact_policy.guardrails
    assert "week_agenda_shape_and_calendar_check" in artifact_policy.guardrails
    assert "week_daily_availability_check" in artifact_policy.guardrails
    assert "week_phase_role_alignment_check" in artifact_policy.guardrails
    assert "week_workout_structure_policy_check" in artifact_policy.guardrails
    assert "week_exportability_check" in artifact_policy.guardrails
    assert "season_scenario_selection_shape" in resolve_task_policy(
        tasks["season_scenario_selection"], bundle.task_policies
    ).guardrails
    assert "artifact_schema_valid" in resolve_task_policy(
        tasks["season_scenario_selection"], bundle.task_policies
    ).guardrails
    assert "phase_s5_band_match" in resolve_task_policy(tasks["phase_guardrails"], bundle.task_policies).guardrails
    assert "phase_weeks_match_range" in resolve_task_policy(tasks["phase_structure"], bundle.task_policies).guardrails
    assert "season_bundle_audit_slot_integrity" in resolve_task_policy(
        tasks["season_plan_finalize"], bundle.task_policies
    ).guardrails
    assert "season_phase_load_feasibility" in resolve_task_policy(
        tasks["season_plan_finalize"], bundle.task_policies
    ).guardrails
    assert "phase_week_role_load_coherence" in resolve_task_policy(
        tasks["phase_structure"], bundle.task_policies
    ).guardrails
    kwargs = build_task_guardrail_kwargs(tasks["week_plan"], bundle.task_policies)
    assert kwargs["guardrail_max_retries"] == 2
    assert callable(kwargs["guardrails"][0]) or callable(kwargs["guardrail"])
    guardrail = kwargs["guardrails"][0] if "guardrails" in kwargs else kwargs["guardrail"]
    assert "return" not in getattr(guardrail, "__annotations__", {})

def test_planning_draft_model_schema_is_openai_strict_compatible() -> None:
    schema = PlanningDraftModel.model_json_schema()

    assert schema["additionalProperties"] is False
    assert schema["properties"]["details"]["type"] == "array"
    assert "additionalProperties" not in schema["properties"]["details"]

def test_crewai_output_models_are_openai_strict_compatible() -> None:
    output_kinds = {
        "turn_mode",
        "planning_draft",
        "week_context_assessment",
        "coaching_recommendation",
        "adjustment_intent",
        "pending_resolution_result",
        "coach_preview_summary",
        "artifact_envelope",
        "coach_preview",
        "coach_apply",
        "season_event_anchor",
        "season_macrocycle_draft",
        "season_phase_blueprint_draft",
        "season_plan_audit",
        "season_plan_draft_bundle",
        "season_plan_bundle",
        "season_review_decision",
        "phase_guardrails_payload",
        "phase_structure_payload",
        "phase_preview_payload",
        "constraint_audit",
        "load_governance_audit",
        "phase_bundle_draft",
        "phase_bundle",
        "phase_review_decision",
        "week_plan_bundle",
        "week_review_decision",
        "des_analysis_bundle",
        "report_review_decision",
        "replan_instruction",
    }

    findings: list[str] = []
    for output_kind in sorted(output_kinds):
        model = output_model_for_kind(output_kind)
        for finding in _open_object_schema_findings(model.model_json_schema()):
            findings.append(f"{output_kind}.{model.__name__}: {finding}")

    bundle = load_crewai_config_bundle(root=Path("."))
    for task in build_task_blueprints(bundle).values():
        model = output_model_for_task(task)
        for finding in _open_object_schema_findings(model.model_json_schema()):
            findings.append(f"task:{task.name}.{model.__name__}: {finding}")

    assert findings == []

def test_guardrail_failure_emits_runtime_event(monkeypatch) -> None:
    bundle = load_crewai_config_bundle(root=Path("."))
    tasks = build_task_blueprints(bundle)
    emitted: list[dict[str, object]] = []

    def _emit(**kwargs):
        emitted.append(kwargs)

    monkeypatch.setattr(crewai_guardrails, "emit_runtime_event", _emit)
    kwargs = build_task_guardrail_kwargs(tasks["season_scenario_selection"], bundle.task_policies)
    invalid = {
        "meta": {"artifact_type": "SEASON_SCENARIO_SELECTION", "schema_id": "SeasonScenarioSelectionInterface"},
        "data": {"selected_scenario_id": "D", "season_scenarios_ref": "season_scenarios/latest.json"},
    }

    with guardrail_runtime_context(root=Path("."), athlete_id="i150546", run_id="run-1", component="test"):
        failed = [guardrail(invalid) for guardrail in kwargs["guardrails"]]

    assert any(ok is False for ok, _payload in failed)
    assert any(event["event_type"] == "CREW_TASK_GUARDRAIL_FAILED" for event in emitted)
    assert any(event["guardrail"] == "season_scenario_selection_shape" for event in emitted)

def test_create_season_plan_aborts_before_crew_when_selection_binding_fails(
    monkeypatch, tmp_path: Path
) -> None:
    invoked = False

    def _fake_run_agent_multi_output(*args, **kwargs):
        nonlocal invoked
        invoked = True
        return {"ok": True}

    monkeypatch.setattr(season_flow, "run_agent_multi_output", _fake_run_agent_multi_output)

    store = LocalArtifactStore(root=tmp_path)
    athlete_id = "i150546"
    store.ensure_workspace(athlete_id)
    store.save_document(
        athlete_id,
        ArtifactType.ATHLETE_PROFILE,
        "2026-22",
        {"data": {}},
        producer_agent="test",
        run_id="profile",
        update_latest=True,
    )
    store.save_document(
        athlete_id,
        ArtifactType.AVAILABILITY,
        "2026-22",
        {"data": {"weekly_hours": {"typical": 12.0}, "fixed_rest_days": ["Mon", "Fri"]}},
        producer_agent="test",
        run_id="availability",
        update_latest=True,
    )
    store.save_document(
        athlete_id,
        ArtifactType.SEASON_SCENARIOS,
        "2026-22__new",
        {
            "meta": {"version_key": "2026-22__new", "run_id": "scenarios-new"},
            "data": {
                "planning_horizon_weeks": 16,
                "scenarios": [
                    {
                        "scenario_id": "B",
                        "name": "Balanced build",
                        "load_philosophy": "balanced_progressive",
                        "risk_profile": "medium",
                        "best_suited_if": "Stable recovery",
                        "key_differences": "Balanced pressure",
                        "main_payoff": "Repeatable progression",
                        "main_cost": "Less conservative than A",
                        "scenario_guidance": {
                            "recovery_margin": "medium",
                            "fatigue_exposure": "moderate",
                            "specificity_density": "controlled",
                            "constraint_summary": ["Preserve continuity."],
                            "event_alignment_notes": ["B-event rehearsal"],
                            "risk_flags": [],
                            "kpi_guardrail_notes": ["Stay repeatable."],
                            "decision_notes": ["Selected for test."],
                            "deload_cadence": "2:1:1",
                            "phase_length_weeks": 4,
                            "phase_count_expected": 4,
                            "phase_plan_summary": {"full_phases": 4, "shortened_phases": []},
                            "max_shortened_phases": 0,
                            "shortening_budget_weeks": 0,
                            "intensity_guidance": {"allowed_domains": ["ENDURANCE", "TEMPO"], "avoid_domains": ["VO2MAX"]},
                        },
                    }
                ],
            },
        },
        producer_agent="test",
        run_id="scenarios-new",
        update_latest=True,
    )
    store.save_document(
        athlete_id,
        ArtifactType.SEASON_SCENARIO_SELECTION,
        "2026-22__sel",
        {
            "meta": {
                "version_key": "2026-22__sel",
                "run_id": "selection",
                "trace_upstream": [
                    {"artifact": "SEASON_SCENARIOS", "version": "2026-22__old", "version_key": "2026-22__old", "run_id": "scenarios-old"}
                ],
            },
            "data": {
                "season_scenarios_ref": "2026-22__old",
                "selected_scenario_id": "B",
                "selection_source": "user",
                "selection_rationale": "Balanced choice",
                "notes": ["stale selection"],
                "kpi_moving_time_rate_guidance_selection": None,
            },
        },
        producer_agent="test",
        run_id="selection",
        update_latest=True,
    )

    result = season_flow.create_season_plan(
        lambda _agent_name: SimpleNamespace(workspace_root=tmp_path),
        athlete_id=athlete_id,
        year=2026,
        week=22,
        run_id="season-plan",
        selected=None,
    )

    assert result["ok"] is False
    assert result["reason_code"] == "selection_stale_vs_scenarios"
    assert invoked is False

def test_emit_runtime_exception_event_records_structured_llm_failure(tmp_path: Path) -> None:
    try:
        raise RuntimeError(
            "Error code: 429 - {'error': {'message': 'You exceeded your current quota.', 'type': 'insufficient_quota', 'code': 'insufficient_quota'}}"
        )
    except RuntimeError as exc:
        crewai_telemetry.emit_runtime_exception_event(
            root=tmp_path,
            athlete_id="athlete",
            run_id="run-llm-failure",
            exc=exc,
            crew="season_planning",
            task="season_plan",
        )

    events = load_events(tmp_path, "athlete", "run-llm-failure")
    assert events[-1]["type"] == "LLM_REQUEST_FAILED"
    assert events[-1]["error_code"] == "insufficient_quota"
    assert events[-1]["error_type"] == "insufficient_quota"
    assert events[-1]["status_code"] == "429"
    assert "current quota" in str(events[-1]["reason"])

def test_build_memory_instance_injects_rps_openai_credentials(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeMemory:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    crewai_module = SimpleNamespace(Memory=FakeMemory)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-rps-key")
    monkeypatch.setenv("RPS_LLM_BASE_URL", "https://example.invalid/v1")

    memory = build_memory_instance(
        crewai_module,
        storage="runtime/athletes/i150546/memory/test",
        embedder={"provider": "openai", "config": {"model_name": "text-embedding-3-small"}},
        llm=None,
    )

    assert memory is not None
    embedder = captured["embedder"]
    assert isinstance(embedder, dict)
    assert embedder["config"]["api_key"] == "test-rps-key"
    assert embedder["config"]["base_url"] == "https://example.invalid/v1"
    assert embedder["config"]["api_base"] == "https://example.invalid/v1"
    assert os.environ["OPENAI_API_KEY"] == "test-rps-key"

def test_build_crew_memory_kwargs_normalizes_top_level_embedder(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeMemory:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    crewai_module = SimpleNamespace(Memory=FakeMemory)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-rps-key")
    monkeypatch.setenv("RPS_LLM_BASE_URL", "https://example.invalid/v1")

    kwargs = build_crew_memory_kwargs(
        crewai_module,
        profile={
            "enabled": True,
            "storage": "runtime/athletes/i150546/memory/test",
            "embedder": {"provider": "openai", "config": {"model_name": "text-embedding-3-small"}},
            "llm": None,
        },
    )

    embedder = kwargs["embedder"]
    assert isinstance(embedder, dict)
    assert embedder["config"]["api_key"] == "test-rps-key"
    assert embedder["config"]["base_url"] == "https://example.invalid/v1"
    assert embedder["config"]["api_base"] == "https://example.invalid/v1"

def test_build_crewai_knowledge_kwargs_mirrors_rps_openai_env(monkeypatch, tmp_path: Path) -> None:
    skill_root = tmp_path
    source = skill_root / "sample.md"
    source.write_text("knowledge", encoding="utf-8")
    monkeypatch.setattr("rps.crewai_runtime.knowledge._KNOWLEDGE_SEARCH_GUARDS_READY", False)

    class FakeStringKnowledgeSource:
        def __init__(self, *, content: str):
            self.content = content

    class FakeKnowledgeStorage:
        def search(self, query, *args, **kwargs):
            self.last_query = query
            return []

    fake_module = types.ModuleType("crewai.knowledge.source.string_knowledge_source")
    _set_module_attrs(fake_module, StringKnowledgeSource=FakeStringKnowledgeSource)
    fake_storage_module = types.ModuleType("crewai.knowledge.storage.knowledge_storage")
    _set_module_attrs(fake_storage_module, KnowledgeStorage=FakeKnowledgeStorage)
    monkeypatch.setitem(sys.modules, "crewai.knowledge.source.string_knowledge_source", fake_module)
    monkeypatch.setitem(sys.modules, "crewai.knowledge.storage.knowledge_storage", fake_storage_module)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-rps-key")

    kwargs = build_crewai_knowledge_kwargs(
        root=skill_root,
        profile={"sources": [{"path": "sample.md"}], "knowledge_config": {}},
    )

    assert "knowledge_sources" in kwargs
    assert os.environ["OPENAI_API_KEY"] == "test-rps-key"
    storage = FakeKnowledgeStorage()
    storage.search("System and agent instructions: " + ("x " * 5000) + "Current Task: compact me")
    assert isinstance(storage.last_query, str)
    assert len(storage.last_query) <= 4000

def test_knowledge_and_memory_profiles_resolve_from_config() -> None:
    bundle = load_crewai_config_bundle(root=Path("."))

    coach_knowledge = resolve_agent_knowledge_profile(bundle, agent_name="week_recommendation_specialist")
    season_knowledge = resolve_crew_knowledge_profile(bundle, crew_name="season_planning")
    coach_memory = resolve_crew_memory_profile(
        bundle,
        crew_name="coach_conversation",
        athlete_id="i150546",
        surface="coach",
    )
    season_memory = resolve_crew_memory_profile(
        bundle,
        crew_name="season_planning",
        athlete_id="i150546",
        surface="default",
    )
    specialist_memory = resolve_agent_memory_profile(
        bundle,
        agent_name="week_recommendation_specialist",
        athlete_id="i150546",
        surface="coach",
    )

    assert coach_knowledge["sources"]
    assert season_knowledge["sources"]
    assert coach_memory["enabled"] is True
    assert coach_memory["scope"] == "/athlete/i150546/coach/shared"
    assert season_memory["enabled"] is False
    assert specialist_memory["mode"] == "slice_read_only"
    assert "/athlete/i150546/coach/accepted_patterns" in specialist_memory["additional_read_scopes"]
    writer_memory = resolve_agent_memory_profile(
        bundle,
        agent_name="week_artifact_writer",
        athlete_id="i150546",
        surface="default",
    )
    assert writer_memory["mode"] == "read_only"

def test_planning_specialists_resolve_without_static_knowledge() -> None:
    bundle = load_crewai_config_bundle(root=Path("."))

    for agent_name in (
        "season_context_specialist",
        "season_plan_manager",
        "phase_context_specialist",
        "phase_bundle_manager",
        "week_context_specialist",
        "week_plan_manager",
    ):
        profile = resolve_agent_knowledge_profile(bundle, agent_name=agent_name)
        assert profile["sources"] == []

def test_compact_knowledge_query_caps_large_prompt_text() -> None:
    giant = (
        "System and agent instructions:\n# System prompt\n"
        + ("boilerplate " * 5000)
        + "\nCurrent Task: Summarize the active season constraints and event anchors."
    )

    compacted = _compact_knowledge_query(giant)

    assert isinstance(compacted, str)
    assert "Current Task:" in compacted
    assert len(compacted) <= 4000
    assert len(compacted.split()) <= 600

def test_compact_internal_user_input_preserves_priority_markers() -> None:
    giant = (
        "## Task Context The following is the full task you are helping complete. "
        + ("boilerplate " * 2500)
        + "Current Task: Define peak window logic for the selected season. "
        + ("filler " * 1500)
        + "Current Step Extract the primary anchor event and taper placement constraints. "
        + "Context from previous steps: Scenario C selected. "
        + "Use the latest season-level SEASON_SCENARIO_SELECTION and SEASON_SCENARIOS as context."
    )

    compacted = _compact_internal_user_input(giant)

    assert "Current Task:" in compacted
    assert "Current Step" in compacted
    assert "Context from previous steps:" in compacted
    assert "Use the latest" in compacted
    assert len(compacted) <= 2800
    assert len(compacted.split()) <= 450

def test_extract_authoritative_runtime_blocks_preserves_snapshot_and_resolved_context() -> None:
    user_input = """
## Task Context
boilerplate text

**Athlete State Snapshot**
snapshot_ref: athlete_state_snapshot_2026-21__20260519_122903.json
event_candidates:
- A event

## Current Step
Use the event list.

**Resolved Planning Event Context**
- Event 1
- Event 2

**Deterministic Season Phase Slot Context**
- slot data
""".strip()

    blocks = _extract_authoritative_runtime_blocks(user_input)

    assert len(blocks) == 3
    assert blocks[0].startswith("**Athlete State Snapshot**")
    assert "snapshot_ref:" in blocks[0]
    assert blocks[1].startswith("**Resolved Planning Event Context**")
    assert blocks[2].startswith("**Deterministic Season Phase Slot Context**")

def test_internal_task_description_is_tool_first_and_compact() -> None:
    runtime = AgentRuntime(
        model="gpt-5.4-mini",
        temperature=0.2,
        reasoning_effort="medium",
        reasoning_summary="auto",
        max_completion_tokens=8000,
        prompt_loader=PromptLoader(Path("prompts")),
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime"),
    )
    bundle = load_crewai_config_bundle(root=Path("."))
    task_blueprints = build_task_blueprints(bundle)

    description = _build_internal_task_description(
        runtime,
        agent_name="peak_window_specialist",
        prompt_agent="event_priority_anchor_specialist",
        bundle=bundle,
        crew_name="season_planning",
        task_blueprint=task_blueprints["season_peak_window_review"],
        user_input=(
            "## Task Context The following is the full task you are helping complete. "
            + ("boilerplate " * 2000)
            + "Current Task: Define peak-window and taper-window logic for the season plan. "
            + "Current Step Use the selected scenario, planning events, and season context."
            + "\n\n**Athlete State Snapshot**\n"
            + "snapshot_ref: athlete_state_snapshot_2026-21__20260519_122903.json\n"
            + "event_candidates:\n- A event\n"
            + "\n**Resolved Planning Event Context**\n"
            + "- Event 1\n- Event 2\n"
        ),
    )

    assert "Shared system instructions for all agents." not in description
    assert "payload_json" in description
    assert "call the tool instead of asking the user for it" in description
    assert "If prior specialist context already contains the needed facts" in description
    assert "Do not create, write, or verify workspace files unless the active task explicitly exposes a write-capable tool" in description
    assert "If you are blocked after relevant tool attempts" in description
    assert "Current Task: Define peak-window and taper-window logic for the season plan." in description
    assert "Authoritative runtime context:" in description
    assert "**Athlete State Snapshot**" in description
    assert "**Resolved Planning Event Context**" in description

def test_season_event_and_peak_tasks_expose_workspace_read_tools() -> None:
    bundle = load_crewai_config_bundle(root=Path("."))
    task_blueprints = build_task_blueprints(bundle)

    event_tools = task_blueprints["season_event_priority_review"].config.get("tools")
    peak_tools = task_blueprints["season_peak_window_review"].config.get("tools")
    macrocycle_tools = task_blueprints["season_macrocycle_draft"].config.get("tools")

    assert event_tools == ["workspace_get_input", "workspace_get_latest", "workspace_get_version"]
    assert peak_tools == ["workspace_get_input", "workspace_get_latest", "workspace_get_version"]
    assert macrocycle_tools == [
        "workspace_get_input",
        "workspace_get_latest",
        "workspace_get_phase_slot_contract",
    ]

def test_season_specialist_task_scopes_are_explicitly_separated() -> None:
    bundle = load_crewai_config_bundle(root=Path("."))
    task_blueprints = build_task_blueprints(bundle)

    constraint_description = task_blueprints["season_constraint_review"].description
    historical_description = task_blueprints["season_historical_context_review"].description
    kpi_description = task_blueprints["season_kpi_guidance_review"].description

    assert "hard and soft constraints only" in constraint_description
    assert "historical continuity" in constraint_description
    assert "recent tolerance, disruption risk, and continuity evidence only" in historical_description
    assert "Do not restate fixed rest days, phase corridors, event taper handling, or KPI pacing semantics as primary findings" in historical_description
    assert "Keep the output centered on pacing/rate-band interpretation" in kpi_description
    assert "Do not restate fixed rest days, availability bounds, phase corridors, load caps, event-anchor/taper handling, or historical continuity as primary findings" in kpi_description

def test_agent_memory_read_only_mode_uses_slice() -> None:
    class FakeMemory:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def slice(self, **kwargs):
            self.calls.append(kwargs)
            return {"slice": kwargs}

        def scope(self, scope: str):
            raise AssertionError(f"read_only mode must not request writable scope {scope}")

    shared = FakeMemory()
    value = build_agent_memory_value(
        shared_memory=shared,
        profile={"mode": "read_only", "scope": "/athlete/i150546/planning/week/writer"},
    )

    assert value == {
        "slice": {
            "scopes": ["/athlete/i150546/planning/week/writer"],
            "read_only": True,
        }
    }
    assert shared.calls

def test_native_agent_kwargs_defaults_and_yaml_override() -> None:
    writer_kwargs = collect_native_agent_kwargs("week_artifact_writer", {})
    assert writer_kwargs["allow_delegation"] is False
    assert writer_kwargs["max_iter"] == 2
    assert writer_kwargs["respect_context_window"] is True
    assert writer_kwargs["cache"] is False

    manager_kwargs = collect_native_agent_kwargs("week_plan_manager", {"max_iter": 7})
    assert manager_kwargs["allow_delegation"] is True
    assert manager_kwargs["max_iter"] == 7
    assert manager_kwargs["respect_context_window"] is True

def test_configured_task_context_names_normalizes_yaml_values() -> None:
    assert configured_task_context_names({"context": "task_a"}) == ("task_a",)
    assert configured_task_context_names({"context": ["task_a", "task_b"]}) == ("task_a", "task_b")

def test_task_scoped_tools_and_callback_are_attached() -> None:
    bundle = load_crewai_config_bundle(root=Path("."))
    tasks = build_task_blueprints(bundle)
    tool_map = {
        name: SimpleNamespace(name=name)
        for name in [
            "workspace_get_input",
            "workspace_get_latest",
            "workspace_get_version",
            "workspace_get_phase_slot_contract",
            "workspace_get_phase_context",
            "workspace_get_week_calendar_context",
            "workspace_get_phase_execution_context",
        ]
    }

    assert _task_tools_for_blueprint(
        tasks["week_context_read"], tool_map
    ) == [
        tool_map["workspace_get_input"],
        tool_map["workspace_get_latest"],
        tool_map["workspace_get_version"],
        tool_map["workspace_get_phase_context"],
        tool_map["workspace_get_week_calendar_context"],
        tool_map["workspace_get_phase_execution_context"],
    ]
    assert _task_tools_for_blueprint(tasks["week_plan"], tool_map) == []
    assert _task_tools_for_blueprint(tasks["season_macrocycle_draft"], tool_map) == [
        tool_map["workspace_get_input"],
        tool_map["workspace_get_latest"],
        tool_map["workspace_get_phase_slot_contract"],
    ]

    class FakeTask:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    task = _build_crewai_task(
        task_cls=FakeTask,
        bundle=bundle,
        task_blueprint=tasks["week_context_read"],
        agent=object(),
        description="test",
        runtime=SimpleNamespace(workspace_root=Path(".")),
        crew_name="week_planning",
        athlete_id="i150546",
        run_id="run-1",
        tools=tool_map,
    )

    assert task.kwargs["tools"] == [
        tool_map["workspace_get_input"],
        tool_map["workspace_get_latest"],
        tool_map["workspace_get_version"],
        tool_map["workspace_get_phase_context"],
        tool_map["workspace_get_week_calendar_context"],
        tool_map["workspace_get_phase_execution_context"],
    ]
    assert task.kwargs["name"] == "week_context_read"
    assert callable(task.kwargs["callback"])

def test_build_crewai_task_tools_override_takes_precedence() -> None:
    bundle = load_crewai_config_bundle(root=Path("."))
    tasks = build_task_blueprints(bundle)
    tool_map = {
        name: SimpleNamespace(name=name)
        for name in [
            "workspace_get_phase_execution_context",
            "workspace_get_phase_slot_contract",
        ]
    }

    class FakeTask:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    task = _build_crewai_task(
        task_cls=FakeTask,
        bundle=bundle,
        task_blueprint=tasks["phase_bundle_finalize"],
        agent=SimpleNamespace(llm=None),
        description="test",
        runtime=AgentRuntime(
            model="openai/gpt-5-mini",
            temperature=1.0,
            reasoning_effort="medium",
            reasoning_summary="auto",
            max_completion_tokens=8000,
            prompt_loader=PromptLoader(Path("prompts")),
            schema_dir=Path("specs/schemas"),
            workspace_root=Path("runtime/athletes"),
        ),
        crew_name="phase_planning",
        tools=tool_map,
        tools_override=[],
    )

    assert "tools" not in task.kwargs

def test_skill_kwargs_resolve_native_crewai_skill_paths() -> None:
    bundle = load_crewai_config_bundle(root=Path("."))
    profile = resolve_agent_skill_profile(bundle, agent_name="week_revision_specialist", crew_name="coach_conversation")
    kwargs = build_crewai_skill_kwargs(root=Path("."), profile=profile)
    assert profile["agent_skill"] == "skills/week/revision-methodology"
    assert profile["crew_skills"] == [
        "skills/shared/runtime-boundaries",
        "skills/shared/resolved-context-consumption",
        "skills/shared/traceability-and-naming",
    ]
    skill_paths = [Path(path) for path in kwargs["skills"]]
    assert Path("skills/week/revision-methodology").resolve() in skill_paths
    assert Path("skills/shared/runtime-boundaries").resolve() in skill_paths

def test_coach_evidence_source_guidance_is_in_active_skills() -> None:
    coach_skill = Path("skills/conversation/guarded-operations/SKILL.md").read_text(encoding="utf-8")
    recommendation_skill = Path("skills/week/recommendation-and-adjustment/SKILL.md").read_text(encoding="utf-8")
    manifest = Path("skills/shared/durability-methodology/references/evidence_library_manifest.md")
    core_table = Path("skills/shared/durability-methodology/references/durability_reference_table_core.md")
    applied_table = Path("skills/shared/durability-methodology/references/durability_reference_table_applied.md")

    assert manifest.exists()
    assert core_table.exists()
    assert applied_table.exists()
    assert "references/library/" in coach_skill
    assert "evidence_library_manifest.md" in manifest.read_text(encoding="utf-8") or "canonical local evidence library" in manifest.read_text(encoding="utf-8")
    assert "durability_reference_table_core.md" in coach_skill
    assert "durability_reference_table_applied.md" in coach_skill
    assert "omit it instead of inventing" in coach_skill
    assert "pubmed.ncbi.nlm.nih.gov" in coach_skill
    assert "Maunder/Seiler/Kilding/Plews" in coach_skill
    assert "available primary-source result" in recommendation_skill
    assert "omit it instead of inventing PMID, DOI, URL, journal, or year details" in recommendation_skill
    assert "use only verified study conclusions" in recommendation_skill

def test_coach_recommendation_answer_discipline_is_configured() -> None:
    recommendation_skill = Path("skills/week/recommendation-and-adjustment/SKILL.md").read_text(encoding="utf-8")
    finalizer_skill = Path("skills/conversation/routing-and-finalization/SKILL.md").read_text(encoding="utf-8")
    coach_chat_source = Path("src/rps/crewai_runtime/coach_chat.py").read_text(encoding="utf-8")

    assert "Answer like an experienced cycling coach" in recommendation_skill
    assert "Finalize replies as an experienced cycling coach" in finalizer_skill
    assert "Answer like an experienced cycling coach" in coach_chat_source
    assert "Write as an experienced cycling coach" in coach_chat_source
    assert "Answer simple why-questions with compact coach prose" in recommendation_skill
    assert "Answer simple advisory questions with compact coach prose" in finalizer_skill
    assert "Answer simple why-questions with compact coach prose" in coach_chat_source
    assert "Use domain calculations, IF targets, thresholds, citations, and source claims only when" in coach_chat_source
    assert "finalize_reply_style_repair" in coach_chat_source
    assert "Use natural coach language and reserve DONE, READY, OUTPUT" in coach_chat_source
