from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from rps.agents.crewai_output_extraction import (
    _assemble_phase_draft_bundle,
    _assemble_season_plan_draft_bundle,
    _collect_typed,
    _extract_structured_output,
    _extract_typed_output,
)
from rps.crewai_runtime import load_crewai_config_bundle
from rps.crewai_runtime.bindings import (
    build_task_blueprints,
    should_bind_crewai_output_model,
)
from rps.crewai_runtime.guardrails_context import guardrail_runtime_context
from rps.crewai_runtime.guardrails_generic import typed_output_present
from rps.crewai_runtime.guardrails_registry import (
    build_task_guardrail_kwargs,
    resolve_task_policy,
)
from rps.crewai_runtime.guardrails_season import season_bundle_audit_slot_integrity
from rps.crewai_runtime.models import (
    ConstraintAuditModel,
    LoadGovernanceAuditModel,
    PhaseBundleDecisionModel,
    PhaseBundleManagerSynthesisModel,
    PhaseGuardrailsPayloadModel,
    PhasePreviewPayloadModel,
    PhaseStructurePayloadModel,
    SeasonEventAnchorModel,
    SeasonMacrocycleDraftModel,
    SeasonPhaseBlueprintDraftOutputModel,
    SeasonPhaseDraftBlueprintModel,
    SeasonPlanManagerSynthesisModel,
)


def _typed_task(pydantic_output: object) -> SimpleNamespace:
    return SimpleNamespace(output=SimpleNamespace(pydantic=pydantic_output))


def test_season_bundle_audit_slot_integrity_rejects_row_shaped_constraint_findings() -> None:
    ok, reason = season_bundle_audit_slot_integrity(
        {
            "event_priority": {},
            "macrocycle": {},
            "phase_blueprints": [
                {
                    "phase_id": "P01",
                    "iso_week_range": "2026-21--2026-23",
                    "scenario_cadence": "2:1",
                }
            ],
            "constraints": [
                {
                    "constraint_type": "availability",
                    "status": "warning",
                    "summary": "Weekday time is limited.",
                }
            ],
            "load_governance": [],
        }
    )

    assert ok is False
    assert "canonical audit objects" in reason


def test_season_bundle_audit_slot_integrity_accepts_canonical_audit_objects() -> None:
    ok, payload = season_bundle_audit_slot_integrity(
        {
            "event_priority": {},
            "macrocycle": {},
            "phase_blueprints": [
                {
                    "phase_id": "P01",
                    "iso_week_range": "2026-21--2026-23",
                    "scenario_cadence": "2:1",
                }
            ],
            "constraints": [
                {
                    "blocking_issues": [],
                    "warnings": ["Keep fixed rest days."],
                    "recommended_adjustments": [],
                    "applied_sources": ["availability"],
                }
            ],
            "load_governance": [
                {
                    "blocking_issues": [],
                    "warnings": [],
                    "recommended_adjustments": [],
                    "cadence_authority_preserved": True,
                    "durability_first_respected": True,
                }
            ],
        }
    )

    assert ok is True
    assert payload["constraints"][0]["applied_sources"] == ["availability"]


def test_assemble_season_plan_draft_bundle_merges_typed_sibling_outputs() -> None:
    manager_synthesis = SeasonPlanManagerSynthesisModel(
        event_priority=SeasonEventAnchorModel(primary_a_events=["2026-09-12"]),
        macrocycle=SeasonMacrocycleDraftModel(deload_cadence="3:1"),
    )
    tasks_by_name = {
        "season_constraint_review": _typed_task(
            ConstraintAuditModel(applied_sources=["availability"])
        ),
        "season_historical_context_review": _typed_task(
            ConstraintAuditModel(applied_sources=["history"])
        ),
        "season_kpi_guidance_review": _typed_task(
            ConstraintAuditModel(applied_sources=["kpi_profile"])
        ),
        "season_load_corridor_draft": _typed_task(
            LoadGovernanceAuditModel(cadence_authority_preserved=True)
        ),
        "season_progression_review": _typed_task(
            LoadGovernanceAuditModel(cadence_authority_preserved=False)
        ),
        "season_phase_blueprint_draft": _typed_task(
            SeasonPhaseBlueprintDraftOutputModel(
                phase_blueprints=[
                    SeasonPhaseDraftBlueprintModel(
                        phase_id="P01",
                        iso_week_range="2026-21--2026-23",
                        scenario_cadence="2:1",
                    )
                ]
            )
        ),
    }
    task_blueprints = {name: SimpleNamespace(execution_policy={}) for name in tasks_by_name}

    assembled = _assemble_season_plan_draft_bundle(
        manager_synthesis,
        result=SimpleNamespace(),
        tasks_by_name=tasks_by_name,
        task_blueprints=task_blueprints,
    )

    assert [item.applied_sources for item in assembled.constraints] == [
        ["availability"],
        ["history"],
        ["kpi_profile"],
    ]
    assert [item.cadence_authority_preserved for item in assembled.load_governance] == [True, False]
    assert [item.phase_id for item in assembled.phase_blueprints] == ["P01"]
    assert assembled.event_priority.primary_a_events == ["2026-09-12"]
    assert assembled.macrocycle.deload_cadence == "3:1"


def test_assemble_phase_draft_bundle_merges_typed_sibling_outputs() -> None:
    manager_synthesis = PhaseBundleManagerSynthesisModel(
        phase_range="2026-24--2026-25",
        phase_id="P01",
        constraint_audit=ConstraintAuditModel(applied_sources=["availability"]),
        load_governance_audit=LoadGovernanceAuditModel(),
        decision_summary=PhaseBundleDecisionModel(cadence_source="season"),
    )
    guardrails_payload = PhaseGuardrailsPayloadModel(phase_intent="shortened_re_entry")
    structure_payload = PhaseStructurePayloadModel(phase_intent="shortened_re_entry")
    preview_payload = PhasePreviewPayloadModel(phase_intent="shortened_re_entry")
    tasks_by_name = {
        "phase_guardrail_band_draft": _typed_task(guardrails_payload),
        "phase_structure_draft": _typed_task(structure_payload),
        "phase_preview_draft": _typed_task(preview_payload),
    }

    assembled = _assemble_phase_draft_bundle(
        manager_synthesis,
        result=SimpleNamespace(),
        tasks_by_name=tasks_by_name,
    )

    assert assembled.phase_range == "2026-24--2026-25"
    assert assembled.guardrails == guardrails_payload
    assert assembled.structure == structure_payload
    assert assembled.preview == preview_payload
    assert assembled.constraint_audit.applied_sources == ["availability"]
    assert assembled.decision_summary.cadence_source == "season"


def _valid_phase_manager_synthesis() -> PhaseBundleManagerSynthesisModel:
    return PhaseBundleManagerSynthesisModel(
        phase_range="2026-24--2026-25",
        phase_id="P01",
        constraint_audit=ConstraintAuditModel(),
        load_governance_audit=LoadGovernanceAuditModel(),
        decision_summary=PhaseBundleDecisionModel(),
    )


@pytest.mark.parametrize(
    "sibling_task_name",
    ["phase_guardrail_band_draft", "phase_structure_draft", "phase_preview_draft"],
)
def test_assemble_phase_draft_bundle_raises_when_a_sibling_output_is_malformed(sibling_task_name: str) -> None:
    # Mirrors the real production failure: a sibling task's guardrail passes (raw text
    # present) but strict pydantic parsing failed, so .output.pydantic is None. Assembly
    # must raise a clear, task-named error -- not silently substitute the wrong task's data.
    all_siblings = {
        "phase_guardrail_band_draft": _typed_task(PhaseGuardrailsPayloadModel(phase_intent="general_base")),
        "phase_structure_draft": _typed_task(PhaseStructurePayloadModel(phase_intent="general_base")),
        "phase_preview_draft": _typed_task(PhasePreviewPayloadModel(phase_intent="general_base")),
    }
    all_siblings[sibling_task_name] = SimpleNamespace(output=SimpleNamespace(pydantic=None, raw="malformed"))

    with pytest.raises(RuntimeError, match=sibling_task_name):
        _assemble_phase_draft_bundle(
            _valid_phase_manager_synthesis(),
            result=SimpleNamespace(pydantic=_valid_phase_manager_synthesis()),
            tasks_by_name=all_siblings,
        )


@pytest.mark.parametrize(
    "sibling_task_name",
    ["phase_guardrail_band_draft", "phase_structure_draft", "phase_preview_draft"],
)
def test_assemble_phase_draft_bundle_raises_when_a_sibling_task_did_not_run(sibling_task_name: str) -> None:
    all_siblings = {
        "phase_guardrail_band_draft": _typed_task(PhaseGuardrailsPayloadModel(phase_intent="general_base")),
        "phase_structure_draft": _typed_task(PhaseStructurePayloadModel(phase_intent="general_base")),
        "phase_preview_draft": _typed_task(PhasePreviewPayloadModel(phase_intent="general_base")),
    }
    del all_siblings[sibling_task_name]

    with pytest.raises(RuntimeError, match=sibling_task_name):
        _assemble_phase_draft_bundle(
            _valid_phase_manager_synthesis(),
            result=SimpleNamespace(pydantic=_valid_phase_manager_synthesis()),
            tasks_by_name=all_siblings,
        )


def test_typed_output_present_rejects_raw_only_fallback() -> None:
    # A task whose LLM response failed strict pydantic validation still has
    # non-empty raw text; typed_output_present must not accept that as "typed".
    task_output = SimpleNamespace(pydantic=None, json_dict=None, raw="not valid structured output")

    ok, reason = typed_output_present(task_output)

    assert ok is False
    assert "typed" in reason.lower()


def test_typed_output_present_accepts_pydantic_payload() -> None:
    model = ConstraintAuditModel(applied_sources=["availability"])
    task_output = SimpleNamespace(pydantic=model, json_dict=None, raw=model.model_dump_json())

    ok, payload = typed_output_present(task_output)

    assert ok is True
    assert payload is model


def test_typed_output_present_wired_through_guardrail_wrapper_checks_raw_pydantic() -> None:
    # Regression test for a real production bug: the CrewAI-facing guardrail callable is
    # built by build_task_guardrail_kwargs -> _with_guardrail_telemetry, which pre-normalizes
    # the raw TaskOutput into a plain dict (via normalize_artifact_candidate_for_task_guardrails
    # -> _coerce_mapping) before calling the guardrail function. typed_output_present must see
    # the RAW TaskOutput -- it checks whether CrewAI's own output_pydantic binding succeeded,
    # not content shape -- so calling it in isolation (as the tests above do) never exercises
    # this wiring and would not have caught the regression that shipped in c24baad.
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    task_blueprints = build_task_blueprints(bundle)
    task_blueprint = task_blueprints["season_plan_finalize"]
    assert resolve_task_policy(task_blueprint, bundle.task_policies).guardrails == ("typed_output_present",)

    wrapped_guardrail = build_task_guardrail_kwargs(task_blueprint, bundle.task_policies)["guardrail"]

    valid_model = SeasonPlanManagerSynthesisModel(
        event_priority=SeasonEventAnchorModel(), macrocycle=SeasonMacrocycleDraftModel()
    )
    valid_output = SimpleNamespace(pydantic=valid_model, json_dict=None, raw=valid_model.model_dump_json())
    invalid_output = SimpleNamespace(pydantic=None, json_dict=None, raw="not valid structured output")

    with guardrail_runtime_context(task_name="season_plan_finalize"):
        ok_valid, _ = wrapped_guardrail(valid_output)
        ok_invalid, reason_invalid = wrapped_guardrail(invalid_output)

    assert ok_valid is True
    assert ok_invalid is False
    assert "typed" in str(reason_invalid).lower()


def test_extract_typed_output_does_not_fall_back_to_crew_result_for_sibling_tasks() -> None:
    # season_phase_blueprint_draft's own pydantic parsing failed (guardrail should have
    # caught this and retried, but if it somehow didn't): the crew-level `result` reflects
    # a *different* task (the crew's final task), so falling back to it here would silently
    # return the wrong task's data instead of surfacing that this task's output is missing.
    sibling_task_obj = SimpleNamespace(output=SimpleNamespace(pydantic=None, raw="malformed"))
    crew_result = SimpleNamespace(pydantic=SeasonPlanManagerSynthesisModel(
        event_priority=SeasonEventAnchorModel(), macrocycle=SeasonMacrocycleDraftModel()
    ))

    extracted = _extract_typed_output(crew_result, sibling_task_obj, allow_crew_result_fallback=False)

    assert extracted is None


def test_collect_typed_raises_when_sibling_task_output_is_unavailable() -> None:
    tasks_by_name = {
        "season_constraint_review": SimpleNamespace(output=SimpleNamespace(pydantic=None, raw="malformed")),
    }
    task_blueprints = {"season_constraint_review": SimpleNamespace(execution_policy={"output_mode": "pydantic"})}
    crew_result = SimpleNamespace(pydantic=SeasonPlanManagerSynthesisModel(
        event_priority=SeasonEventAnchorModel(), macrocycle=SeasonMacrocycleDraftModel()
    ))

    with pytest.raises(RuntimeError, match="season_constraint_review"):
        _collect_typed(
            ("season_constraint_review",),
            result=crew_result,
            tasks_by_name=tasks_by_name,
            task_blueprints=task_blueprints,
        )


def test_extract_structured_output_supports_json_mode_for_internal_tasks() -> None:
    task_output = SimpleNamespace(json_dict={"constraints": [], "load_governance": []}, raw=None)
    task_obj = SimpleNamespace(output=task_output)

    extracted = _extract_structured_output(
        SimpleNamespace(json_dict={"constraints": [], "load_governance": []}),
        task_obj,
        task_name="season_plan_audit",
        output_mode="json",
    )

    assert extracted == {"constraints": [], "load_governance": []}


def test_extract_structured_output_parses_raw_json_for_internal_tasks() -> None:
    payload: dict[str, object] = {"constraints": [], "load_governance": []}
    task_obj = SimpleNamespace(output=SimpleNamespace(json_dict=None, raw=json.dumps(payload)))

    extracted = _extract_structured_output(
        SimpleNamespace(json_dict=None, raw=json.dumps(payload)),
        task_obj,
        task_name="season_plan_audit",
        output_mode="json",
    )

    assert extracted == payload


def test_extract_structured_output_parses_fenced_raw_json_for_internal_tasks() -> None:
    payload: dict[str, object] = {"event_priority": {}, "macrocycle": {}}
    raw = "```json\n" + json.dumps(payload) + "\n```"
    task_obj = SimpleNamespace(output=SimpleNamespace(json_dict=None, raw=raw))

    extracted = _extract_structured_output(
        SimpleNamespace(json_dict=None, raw=raw),
        task_obj,
        task_name="season_plan_audit",
        output_mode="json",
    )

    assert extracted == payload


def test_season_finalize_uses_pydantic_output_mode_and_binds_strict_output_model() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    task_blueprints = build_task_blueprints(bundle)
    task_blueprint = task_blueprints["season_plan_finalize"]
    artifact_task_blueprint = task_blueprints["season_plan"]

    assert resolve_task_policy(task_blueprint, bundle.task_policies).output_mode == "pydantic"
    assert should_bind_crewai_output_model(task_blueprint, output_mode="pydantic") is True
    assert resolve_task_policy(artifact_task_blueprint, bundle.task_policies).output_mode == "json"
    assert should_bind_crewai_output_model(artifact_task_blueprint, output_mode="json") is True


def test_phase_bundle_finalize_uses_pydantic_output_mode_and_binds_strict_output_model() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    task_blueprints = build_task_blueprints(bundle)
    task_blueprint = task_blueprints["phase_bundle_finalize"]

    assert resolve_task_policy(task_blueprint, bundle.task_policies).output_mode == "pydantic"
    assert should_bind_crewai_output_model(task_blueprint, output_mode="pydantic") is True


def test_season_macrocycle_and_finalize_guidance_support_multi_a_event_backplanning() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    blueprints = build_task_blueprints(bundle)

    macrocycle_description = blueprints["season_macrocycle_draft"].description
    blueprint_draft_description = blueprints["season_phase_blueprint_draft"].description
    season_finalize_description = blueprints["season_plan_finalize"].description
    season_finalize_expected_output = blueprints["season_plan_finalize"].expected_output

    assert "`constraints[]`, `load_governance[]`, and `phase_blueprints` are not part of this task's output" in season_finalize_description
    assert "assembled deterministically from those tasks' own typed outputs" in season_finalize_description
    assert "do not reproduce, paraphrase, or reference their shapes here" in season_finalize_description
    assert "emit top-level `event_priority` and `macrocycle`" in season_finalize_description
    assert "`season_constraint_review`/`season_historical_context_review`/`season_kpi_guidance_review`" in season_finalize_description
    assert "`season_load_corridor_draft`/`season_progression_review`" in season_finalize_description
    assert "`season_phase_blueprint_draft`" in season_finalize_description
    assert "Return exactly one structured object with top-level `phase_blueprints` only" in blueprint_draft_description
    assert "`phase_blueprints` are owned here first" in blueprint_draft_description
    assert "no longer reproduces them" in blueprint_draft_description
    assert "multiple target macrocycles" in macrocycle_description
    assert "A-event peak cluster" in macrocycle_description
    assert "final A-event is the only reverse-planning anchor" in season_finalize_description
    assert "backplanned macrocycles overlap" in season_finalize_description
    assert "season justification must classify each A-event" in season_finalize_expected_output

    prompt_text = Path("prompts/agents/season_plan_manager.md").read_text(encoding="utf-8")
    blueprint_prompt_text = Path("prompts/agents/season_phase_blueprint_specialist.md").read_text(encoding="utf-8")
    skill_text = Path("skills/season/plan-synthesis/SKILL.md").read_text(encoding="utf-8")

    for text in (prompt_text, skill_text):
        assert "event_priority" in text
        assert "macrocycle" in text
        assert "phase_blueprints" in text
        assert "constraints[]" in text
        assert "load_governance[]" in text
        assert "season_constraint_review" in text
        assert "season_historical_context_review" in text
        assert "season_kpi_guidance_review" in text
        assert "season_load_corridor_draft" in text
        assert "season_progression_review" in text
        assert "assembled deterministically" in text

    assert "phase_blueprints" in blueprint_prompt_text
    assert "Do not emit a full Season bundle." in blueprint_prompt_text
    assert "Return exactly one structured object with top-level `phase_blueprints`." in blueprint_prompt_text
