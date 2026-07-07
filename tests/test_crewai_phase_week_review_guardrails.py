from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from rps.agents.crewai_context_blocks import (
    _contract_context_blocks_for_task,
    _phase_bundle_finalize_authority_freeze_block,
    _phase_bundle_finalize_has_bound_contracts,
)
from rps.agents.crewai_task_execution import (
    _run_phase_bundle_document,
)
from rps.agents.runtime import AgentRuntime
from rps.crewai_runtime import load_crewai_config_bundle
from rps.crewai_runtime.bindings import (
    build_agent_blueprints,
    build_task_blueprints,
)
from rps.crewai_runtime.guardrails_context import guardrail_runtime_context
from rps.crewai_runtime.models import (
    PhaseWeekBlueprintModel,
)
from rps.prompts.loader import PromptLoader


def test_phase_and_week_finalizers_declare_deterministic_contract_tools() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    blueprints = build_task_blueprints(bundle)

    assert blueprints["phase_bundle_finalize"].config["tools"] == [
        "workspace_get_phase_execution_context",
        "workspace_get_phase_slot_contract",
    ]
    assert blueprints["week_plan_finalize"].config["tools"] == [
        "workspace_get_week_calendar_context",
        "workspace_get_phase_execution_context",
    ]

def test_contract_context_blocks_for_phase_and_week_finalizers_include_bound_contracts() -> None:
    with guardrail_runtime_context(
        phase_slot_context={"phase_slots": [{"phase_id": "P01"}]},
        phase_execution_context={
            "phase_id": "P01",
            "phase_range": "2026-24--2026-25",
            "phase_type": "BUILD",
            "phase_intent": "shortened_re_entry",
            "build_subtype": "durability_build",
            "phase_allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
            "phase_forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
            "phase_allowed_load_modalities": ["NONE"],
            "phase_role_week_load_bands": [
                {"week": "2026-24", "role": "LOAD_1", "band": {"min": 7200, "max": 8200}}
            ],
            "week_role_by_iso_week": {"2026-24": "LOAD_1", "2026-25": "RELOAD"},
            "phase_primary_objective": "Rebuild load tolerance.",
            "phase_s5_bands": [],
        },
        week_calendar_context={"target_iso_week": "2026-21", "phase_week_role": "LOAD_1"},
    ):
        phase_blocks = _contract_context_blocks_for_task(
            crew_name="phase_planning",
            task_name="phase_bundle_finalize",
        )
        week_blocks = _contract_context_blocks_for_task(
            crew_name="week_planning",
            task_name="week_plan_finalize",
        )

    assert any("Deterministic Phase Execution Contract" in block for block in phase_blocks)
    assert any("Deterministic Season Phase Slot Contract" in block for block in phase_blocks)
    assert any("Do not delegate or rediscover week roles" in block for block in phase_blocks)
    assert any("Phase Finalizer Authority Freeze" in block for block in phase_blocks)
    assert any("do not call workspace tools to rediscover them" in block for block in phase_blocks)
    assert any("Deterministic Week Calendar Contract" in block for block in week_blocks)
    assert any("Deterministic Phase Execution Contract" in block for block in week_blocks)
    assert any("Do not delegate or rediscover active week role" in block for block in week_blocks)

def test_phase_bundle_finalize_authority_freeze_block_contains_exact_fields() -> None:
    with guardrail_runtime_context(
        phase_slot_context={"phase_id": "P01", "phase_range": "2026-24--2026-25"},
        phase_execution_context={
            "phase_id": "P01",
            "phase_range": "2026-24--2026-25",
            "phase_type": "BUILD",
            "phase_intent": "shortened_re_entry",
            "build_subtype": "durability_build",
            "phase_allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
            "phase_forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
            "phase_allowed_load_modalities": ["NONE"],
            "phase_role_week_load_bands": [
                {"week": "2026-24", "role": "LOAD_1", "band": {"min": 7200, "max": 8200}}
            ],
            "week_role_by_iso_week": {"2026-24": "LOAD_1", "2026-25": "RELOAD"},
            "phase_primary_objective": "Rebuild load tolerance.",
        },
    ):
        block = _phase_bundle_finalize_authority_freeze_block()

    assert "Phase Finalizer Authority Freeze" in block
    assert "\"phase_allowed_intensity_domains\"" in block
    assert "\"phase_forbidden_intensity_domains\"" in block
    assert "\"phase_allowed_load_modalities\"" in block
    assert "\"phase_role_week_load_bands\"" in block
    assert "\"week_role_by_iso_week\"" in block
    assert "\"phase_primary_objective\": \"Rebuild load tolerance.\"" in block

def test_phase_bundle_finalize_bound_contract_detector_requires_both_contexts() -> None:
    with guardrail_runtime_context(
        phase_execution_context={"phase_id": "P01"},
        phase_slot_context={"phase_id": "P01"},
    ):
        assert _phase_bundle_finalize_has_bound_contracts() is True
    with guardrail_runtime_context(
        phase_execution_context={"phase_id": "P01"},
        phase_slot_context={},
    ):
        assert _phase_bundle_finalize_has_bound_contracts() is False

def test_run_phase_bundle_document_narrows_only_finalizer_tools_with_bound_contracts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    bundle = load_crewai_config_bundle(root=Path("."))
    task_blueprints = build_task_blueprints(bundle)
    agent_blueprints = build_agent_blueprints(bundle)
    captured: dict[str, object] = {}

    def _fake_execute(**kwargs):
        captured["tools_override_by_task"] = kwargs.get("tools_override_by_task")
        return {"guardrails": {}, "structure": {}, "preview": {}}

    monkeypatch.setattr("rps.agents.crewai_task_execution._execute_crewai_multiagent_crew", _fake_execute)
    tool_map = {
        name: SimpleNamespace(name=name)
        for name in [
            "workspace_get_latest",
            "workspace_get_phase_context",
            "workspace_get_phase_execution_context",
            "workspace_get_phase_slot_contract",
        ]
    }

    with guardrail_runtime_context(
        phase_execution_context={"phase_id": "P01"},
        phase_slot_context={"phase_id": "P01"},
    ):
        _run_phase_bundle_document(
            runtime=runtime,
            bundle=bundle,
            user_input="Create phase bundle.",
            task_blueprints=task_blueprints,
            agent_blueprints=agent_blueprints,
            agent_cls=object,
            crewai_llm_cls=object,
            crew_cls=object,
            task_cls=object,
            process_cls=object,
            tools=tool_map,
            athlete_id="i150546",
            run_id="run-phase",
        )

    assert captured["tools_override_by_task"] == {"phase_bundle_finalize": []}

def test_run_phase_bundle_document_keeps_finalizer_tools_without_bound_contracts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    bundle = load_crewai_config_bundle(root=Path("."))
    task_blueprints = build_task_blueprints(bundle)
    agent_blueprints = build_agent_blueprints(bundle)
    captured: dict[str, object] = {}

    def _fake_execute(**kwargs):
        captured["tools_override_by_task"] = kwargs.get("tools_override_by_task")
        return {"guardrails": {}, "structure": {}, "preview": {}}

    monkeypatch.setattr("rps.agents.crewai_task_execution._execute_crewai_multiagent_crew", _fake_execute)

    with guardrail_runtime_context(
        phase_execution_context={"phase_id": "P01"},
        phase_slot_context={},
    ):
        _run_phase_bundle_document(
            runtime=runtime,
            bundle=bundle,
            user_input="Create phase bundle.",
            task_blueprints=task_blueprints,
            agent_blueprints=agent_blueprints,
            agent_cls=object,
            crewai_llm_cls=object,
            crew_cls=object,
            task_cls=object,
            process_cls=object,
            tools={},
            athlete_id="i150546",
            run_id="run-phase",
        )

    assert captured["tools_override_by_task"] is None
    with guardrail_runtime_context(
        phase_execution_context={},
        phase_slot_context={"phase_id": "P01"},
    ):
        assert _phase_bundle_finalize_has_bound_contracts() is False

def test_phase_and_week_managers_disable_free_delegation_via_yaml_override() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    agent_blueprints = build_agent_blueprints(bundle)

    assert agent_blueprints["phase_bundle_manager"].config["allow_delegation"] is False
    assert agent_blueprints["week_plan_manager"].config["allow_delegation"] is False

def test_review_finalizers_declare_deterministic_contract_tools() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    blueprints = build_task_blueprints(bundle)

    assert blueprints["season_review"].config["tools"] == [
        "workspace_get_phase_slot_contract",
        "workspace_get_season_phase_load_context",
    ]
    assert blueprints["phase_review"].config["tools"] == [
        "workspace_get_phase_execution_context",
        "workspace_get_phase_slot_contract",
    ]
    assert blueprints["week_review"].config["tools"] == [
        "workspace_get_week_calendar_context",
        "workspace_get_phase_execution_context",
    ]

def test_contract_context_blocks_for_review_finalizers_include_bound_contracts() -> None:
    with guardrail_runtime_context(
        phase_slot_context={"phase_slots": [{"phase_id": "P01"}]},
        season_phase_load_context={"phases": [{"phase_id": "P01"}]},
        phase_execution_context={"phase_id": "P01", "phase_s5_bands": []},
        week_calendar_context={"target_iso_week": "2026-21", "phase_week_role": "LOAD_1"},
    ):
        season_blocks = _contract_context_blocks_for_task(
            crew_name="season_review",
            task_name="season_review",
        )
        phase_blocks = _contract_context_blocks_for_task(
            crew_name="phase_review",
            task_name="phase_review",
        )
        week_blocks = _contract_context_blocks_for_task(
            crew_name="week_review",
            task_name="week_review",
        )

    assert any("Deterministic Season Phase Slot Contract" in block for block in season_blocks)
    assert any("Deterministic Season Phase Load Contract" in block for block in season_blocks)
    assert any("Season review rule" in block for block in season_blocks)
    assert any("Candidate Season Bundle is the authoritative review subject" in block for block in season_blocks)
    assert any("Deterministic Phase Execution Contract" in block for block in phase_blocks)
    assert any("Phase review rule" in block for block in phase_blocks)
    assert any("Candidate Phase Bundle is the authoritative review subject" in block for block in phase_blocks)
    assert any("Deterministic Week Calendar Contract" in block for block in week_blocks)
    assert any("Week review rule" in block for block in week_blocks)
    assert any("Candidate Week Bundle is the authoritative review subject" in block for block in week_blocks)

def test_season_review_tasks_reference_injected_candidate_bundle() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    blueprints = build_task_blueprints(bundle)

    assert "injected candidate season bundle" in blueprints["season_governance_review"].config["description"]
    assert "injected candidate season bundle" in blueprints["season_constraints_review"].config["description"]
    assert "injected candidate season bundle" in blueprints["season_plan_audit"].config["description"]
    assert "synthetic `candidate_season_bundle`" in blueprints["season_review"].config["description"]

def test_phase_and_week_review_tasks_reference_injected_candidate_bundle() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    blueprints = build_task_blueprints(bundle)

    assert "injected candidate phase bundle" in blueprints["phase_structure_review"].config["description"]
    assert "synthetic `candidate_phase_bundle`" in blueprints["phase_contract_review"].config["description"]
    assert "synthetic `candidate_phase_bundle`" in blueprints["phase_review"].config["description"]
    assert "injected candidate week bundle" in blueprints["week_contract_review"].config["description"]
    assert "synthetic `candidate_week_bundle`" in blueprints["week_review"].config["description"]

def test_review_managers_disable_free_delegation_via_yaml_override() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    agent_blueprints = build_agent_blueprints(bundle)

    assert agent_blueprints["season_review_manager"].config["allow_delegation"] is False
    assert agent_blueprints["phase_review_manager"].config["allow_delegation"] is False
    assert agent_blueprints["week_review_manager"].config["allow_delegation"] is False

def test_season_review_manager_disables_reasoning_agent_path() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    review_manager = bundle.runtime_profiles["agents"]["season_review_manager"]
    assert review_manager["model"] == "gpt-5.4-mini"
    assert review_manager["reasoning"]["enabled"] is False

def test_phase_and_week_review_managers_disable_reasoning_agent_path() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    profiles = bundle.runtime_profiles["agents"]

    phase_review_manager = profiles["phase_review_manager"]
    week_review_manager = profiles["week_review_manager"]

    assert phase_review_manager["model"] == "gpt-5.4-mini"
    assert phase_review_manager["reasoning"]["enabled"] is False
    assert week_review_manager["model"] == "gpt-5.4-mini"
    assert week_review_manager["reasoning"]["enabled"] is False

def test_bounded_phase_and_week_specialists_disable_reasoning_agent_path() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    profiles = bundle.runtime_profiles["agents"]

    for agent_name in (
        "phase_guardrail_band_specialist",
        "phase_structure_specialist",
        "phase_cadence_recovery_specialist",
        "phase_intensity_distribution_specialist",
        "phase_event_integration_specialist",
        "phase_constraint_auditor",
        "phase_governance_auditor",
        "phase_structure_reviewer",
        "week_recommendation_specialist",
        "week_load_target_specialist",
        "week_revision_specialist",
        "week_consistency_auditor",
        "week_load_governance_reviewer",
    ):
        assert profiles[agent_name]["reasoning"]["enabled"] is False, agent_name

def test_context_read_and_contract_review_tasks_use_narrow_tool_scopes() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    blueprints = build_task_blueprints(bundle)

    assert blueprints["season_context_read"].config["tools"] == [
        "workspace_get_input",
        "workspace_get_latest",
        "workspace_get_version",
        "workspace_get_phase_slot_contract",
        "workspace_get_season_phase_load_context",
    ]
    assert blueprints["phase_context_read"].config["tools"] == [
        "workspace_get_input",
        "workspace_get_latest",
        "workspace_get_version",
        "workspace_get_phase_context",
        "workspace_get_phase_execution_context",
        "workspace_get_phase_slot_contract",
    ]
    assert blueprints["week_context_read"].config["tools"] == [
        "workspace_get_input",
        "workspace_get_latest",
        "workspace_get_version",
        "workspace_get_phase_context",
        "workspace_get_week_calendar_context",
        "workspace_get_phase_execution_context",
    ]
    assert blueprints["report_context_read"].config["tools"] == [
        "workspace_get_input",
        "workspace_get_latest",
        "workspace_get_version",
    ]
    assert blueprints["season_contract_review"].config["tools"] == [
        "workspace_get_phase_slot_contract",
        "workspace_get_season_phase_load_context",
    ]
    assert blueprints["phase_contract_review"].config["tools"] == [
        "workspace_get_phase_execution_context",
        "workspace_get_phase_slot_contract",
    ]
    assert blueprints["week_contract_review"].config["tools"] == [
        "workspace_get_week_calendar_context",
        "workspace_get_phase_execution_context",
    ]

def test_feed_forward_and_report_review_managers_disable_free_delegation() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    agent_blueprints = build_agent_blueprints(bundle)

    assert agent_blueprints["conversation_manager"].config["allow_delegation"] is False
    assert agent_blueprints["season_feed_forward_manager"].config["allow_delegation"] is False
    assert agent_blueprints["phase_feed_forward_manager"].config["allow_delegation"] is False
    assert agent_blueprints["des_review_manager"].config["allow_delegation"] is False

def test_feed_forward_tasks_use_dedicated_manager_agents() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    blueprints = build_task_blueprints(bundle)

    assert blueprints["season_phase_feed_forward"].config["agent"] == "season_feed_forward_manager"
    assert blueprints["phase_feed_forward"].config["agent"] == "phase_feed_forward_manager"

def test_review_managers_use_dedicated_review_prompts() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    agent_blueprints = build_agent_blueprints(bundle)

    assert agent_blueprints["season_review_manager"].config["prompt_agent"] == "season_review_manager"
    assert agent_blueprints["phase_review_manager"].config["prompt_agent"] == "phase_review_manager"
    assert agent_blueprints["week_review_manager"].config["prompt_agent"] == "week_review_manager"
    assert agent_blueprints["des_review_manager"].config["prompt_agent"] == "des_review_manager"

def test_week_workout_authoring_specialist_uses_dedicated_prompt() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    agent_blueprints = build_agent_blueprints(bundle)

    assert agent_blueprints["week_workout_authoring_specialist"].config["prompt_agent"] == "week_workout_authoring_specialist"

def test_phase_week_blueprint_model_accepts_role_aware_s5_band() -> None:
    model = PhaseWeekBlueprintModel(
        week="2026-26",
        phase_role="Build",
        week_role="LOAD_1",
        s5_band_min=7600,
        s5_band_max=8400,
        role_progression_band="min 7500 max 8500",
        allowed_domains=["RECOVERY", "ENDURANCE", "TEMPO"],
        event_implication="none",
    )

    assert model.week_role == "LOAD_1"
    assert model.s5_band_max == 8400
