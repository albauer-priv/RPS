from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from rps.agents.crewai_output_extraction import (
    _classify_season_audit_item,
    _extract_structured_output,
    _freeze_season_bundle_audit_slots,
    coerce_season_plan_draft_bundle_slots,
)
from rps.crewai_runtime import guardrails as crewai_guardrails
from rps.crewai_runtime import load_crewai_config_bundle
from rps.crewai_runtime.bindings import (
    build_task_blueprints,
    should_bind_crewai_output_model,
)
from rps.crewai_runtime.guardrails import (
    resolve_task_policy,
    season_bundle_audit_slot_integrity,
)
from rps.crewai_runtime.guardrails_context import guardrail_runtime_context
from rps.crewai_runtime.models import (
    ConstraintAuditModel,
    LoadGovernanceAuditModel,
    SeasonPlanDraftBundleModel,
)


def test_classify_season_audit_item_recognizes_constraint_and_governance_shapes() -> None:
    assert _classify_season_audit_item(
        {
            "blocking_issues": [],
            "warnings": [],
            "recommended_adjustments": [],
            "applied_sources": [],
        }
    ) == "constraint"
    assert _classify_season_audit_item(
        {
            "blocking_issues": [],
            "warnings": [],
            "recommended_adjustments": [],
            "cadence_authority_preserved": True,
            "durability_first_respected": True,
        }
    ) == "governance"

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

def test_freeze_season_bundle_audit_slots_overlays_canonical_specialist_outputs() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    blueprints = build_task_blueprints(bundle)
    final_output = {
        "event_priority": {},
        "macrocycle": {},
        "phase_blueprints": [{"phase_id": "P01", "iso_week_range": "2026-21--2026-23", "scenario_cadence": "2:1"}],
        "constraints": [{"constraint_type": "availability", "status": "warning", "summary": "bad shape"}],
        "load_governance": [{"status": "warning", "summary": "bad governance shape"}],
    }
    tasks_by_name = {
        "season_constraint_review": SimpleNamespace(
            output=SimpleNamespace(
                pydantic=ConstraintAuditModel(
                    blocking_issues=[],
                    warnings=["Fixed rest days are binding."],
                    recommended_adjustments=[],
                    applied_sources=["availability"],
                )
            )
        ),
        "season_historical_context_review": SimpleNamespace(
            output=SimpleNamespace(
                pydantic=ConstraintAuditModel(
                    blocking_issues=[],
                    warnings=["Recent disruption argues for caution."],
                    recommended_adjustments=[],
                    applied_sources=["history"],
                )
            )
        ),
        "season_kpi_guidance_review": SimpleNamespace(
            output=SimpleNamespace(
                pydantic=ConstraintAuditModel(
                    blocking_issues=[],
                    warnings=["Pacing guidance remains secondary to constraints."],
                    recommended_adjustments=[],
                    applied_sources=["kpi_profile"],
                )
            )
        ),
        "season_load_corridor_draft": SimpleNamespace(
            output=SimpleNamespace(
                pydantic=LoadGovernanceAuditModel(
                    blocking_issues=[],
                    warnings=["Use a conservative ramp class."],
                    recommended_adjustments=[],
                    cadence_authority_preserved=True,
                    durability_first_respected=True,
                )
            )
        ),
        "season_progression_review": SimpleNamespace(
            output=SimpleNamespace(
                pydantic=LoadGovernanceAuditModel(
                    blocking_issues=[],
                    warnings=["Keep build entry readiness-gated."],
                    recommended_adjustments=[],
                    cadence_authority_preserved=True,
                    durability_first_respected=True,
                )
            )
        ),
    }

    frozen = _freeze_season_bundle_audit_slots(
        final_output,
        result=SimpleNamespace(),
        tasks_by_name=tasks_by_name,
        task_blueprints=blueprints,
    )

    assert [item["applied_sources"] for item in frozen["constraints"]] == [
        ["availability"],
        ["history"],
        ["kpi_profile"],
    ]
    assert all("summary" not in item for item in frozen["constraints"])
    assert len(frozen["load_governance"]) == 2
    assert all("status" not in item for item in frozen["load_governance"])

def test_classify_season_audit_item_fails_on_mixed_or_unknown_shapes() -> None:
    with pytest.raises(RuntimeError, match="Mixed season audit-slot content"):
        _classify_season_audit_item(
            {
                "blocking_issues": [],
                "warnings": [],
                "recommended_adjustments": [],
                "applied_sources": [],
                "cadence_authority_preserved": True,
            }
        )
    with pytest.raises(RuntimeError, match="Unclassifiable season audit-slot item"):
        _classify_season_audit_item({"foo": "bar"})

def test_coerce_season_plan_draft_bundle_slots_moves_misplaced_items_before_strict_validation() -> None:
    raw_bundle = {
        "event_priority": {},
        "macrocycle": {},
        "phase_blueprints": [],
        "constraints": [
            {
                "blocking_issues": [],
                "warnings": [],
                "recommended_adjustments": [],
                "cadence_authority_preserved": True,
                "durability_first_respected": True,
            }
        ],
        "load_governance": [
            {
                "blocking_issues": [],
                "warnings": [],
                "recommended_adjustments": [],
                "applied_sources": ["availability"],
            }
        ],
    }

    coerced = coerce_season_plan_draft_bundle_slots(raw_bundle)
    validated = SeasonPlanDraftBundleModel.model_validate(coerced)

    assert validated.constraints[0].applied_sources == ["availability"]
    assert validated.load_governance[0].cadence_authority_preserved is True

def test_coerce_season_plan_draft_bundle_slots_accepts_singular_aliases_and_appends_them() -> None:
    raw_bundle = {
        "event_priority": {},
        "macrocycle": {},
        "phase_blueprints": [],
        "constraints": [
            {
                "blocking_issues": [],
                "warnings": [],
                "recommended_adjustments": [],
                "applied_sources": ["existing"],
            }
        ],
        "constraint_audit": {
            "blocking_issues": [],
            "warnings": [],
            "recommended_adjustments": [],
            "applied_sources": ["alias"],
        },
        "load_governance": [
            {
                "blocking_issues": [],
                "warnings": [],
                "recommended_adjustments": [],
                "cadence_authority_preserved": True,
                "durability_first_respected": True,
            }
        ],
        "load_governance_audit": {
            "blocking_issues": [],
            "warnings": [],
            "recommended_adjustments": [],
            "cadence_authority_preserved": False,
            "durability_first_respected": True,
        },
    }

    coerced = coerce_season_plan_draft_bundle_slots(raw_bundle)
    validated = SeasonPlanDraftBundleModel.model_validate(coerced)

    assert "constraint_audit" not in coerced
    assert "load_governance_audit" not in coerced
    assert [item.applied_sources for item in validated.constraints] == [["existing"], ["alias"]]
    assert [item.cadence_authority_preserved for item in validated.load_governance] == [True, False]

def test_season_plan_finalize_pre_guardrail_normalization_projects_singular_audit_aliases() -> None:
    candidate = {
        "event_priority": {},
        "macrocycle": {},
        "phase_blueprints": [],
        "constraint_audit": {
            "blocking_issues": [],
            "warnings": [],
            "recommended_adjustments": [],
            "applied_sources": ["alias"],
        },
        "load_governance_audit": {
            "blocking_issues": [],
            "warnings": [],
            "recommended_adjustments": [],
            "cadence_authority_preserved": True,
            "durability_first_respected": True,
        },
    }

    with guardrail_runtime_context(task_name="season_plan_finalize"):
        normalized = crewai_guardrails.normalize_artifact_candidate_for_task_guardrails(candidate)

    assert "constraint_audit" not in normalized
    assert "load_governance_audit" not in normalized
    assert normalized["constraints"][0]["applied_sources"] == ["alias"]
    assert normalized["load_governance"][0]["cadence_authority_preserved"] is True

def test_season_plan_finalize_pre_guardrail_normalization_decodes_raw_json_object_string() -> None:
    candidate = json.dumps(
        {
            "event_priority": {},
            "macrocycle": {},
            "phase_blueprints": [],
            "constraint_audit": {
                "blocking_issues": [],
                "warnings": [],
                "recommended_adjustments": [],
                "applied_sources": ["alias"],
            },
        }
    )

    with guardrail_runtime_context(task_name="season_plan_finalize"):
        normalized = crewai_guardrails.normalize_artifact_candidate_for_task_guardrails(candidate)

    assert isinstance(normalized, dict)
    assert normalized["phase_blueprints"] == []
    assert normalized["constraints"][0]["applied_sources"] == ["alias"]

def test_season_plan_finalize_pre_guardrail_normalization_decodes_fenced_json_object_string() -> None:
    candidate = """Here is the final bundle.

```json
{"event_priority": {}, "macrocycle": {}, "phase_blueprints": []}
```
"""

    with guardrail_runtime_context(task_name="season_plan_finalize"):
        normalized = crewai_guardrails.normalize_artifact_candidate_for_task_guardrails(candidate)

    assert isinstance(normalized, dict)
    assert normalized["phase_blueprints"] == []

def test_season_plan_finalize_pre_guardrail_normalization_appends_singular_aliases() -> None:
    candidate = {
        "event_priority": {},
        "macrocycle": {},
        "phase_blueprints": [],
        "constraints": [
            {
                "blocking_issues": [],
                "warnings": [],
                "recommended_adjustments": [],
                "applied_sources": ["existing"],
            }
        ],
        "constraint_audit": {
            "blocking_issues": [],
            "warnings": [],
            "recommended_adjustments": [],
            "applied_sources": ["alias"],
        },
    }

    with guardrail_runtime_context(task_name="season_plan_finalize"):
        normalized = crewai_guardrails.normalize_artifact_candidate_for_task_guardrails(candidate)

    assert [item["applied_sources"] for item in normalized["constraints"]] == [["existing"], ["alias"]]

def test_extract_structured_output_supports_json_mode_for_internal_tasks() -> None:
    task_output = SimpleNamespace(json_dict={"constraints": [], "load_governance": []}, raw=None)
    task_obj = SimpleNamespace(output=task_output)

    extracted = _extract_structured_output(
        SimpleNamespace(json_dict={"constraints": [], "load_governance": []}),
        task_obj,
        task_name="season_plan_finalize",
        output_mode="json",
    )

    assert extracted == {"constraints": [], "load_governance": []}

def test_extract_structured_output_parses_raw_json_for_internal_tasks() -> None:
    payload = {"constraints": [], "load_governance": []}
    task_obj = SimpleNamespace(output=SimpleNamespace(json_dict=None, raw=json.dumps(payload)))

    extracted = _extract_structured_output(
        SimpleNamespace(json_dict=None, raw=json.dumps(payload)),
        task_obj,
        task_name="season_plan_finalize",
        output_mode="json",
    )

    assert extracted == payload

def test_extract_structured_output_parses_fenced_raw_json_for_internal_tasks() -> None:
    payload = {"event_priority": {}, "macrocycle": {}, "phase_blueprints": []}
    raw = "```json\n" + json.dumps(payload) + "\n```"
    task_obj = SimpleNamespace(output=SimpleNamespace(json_dict=None, raw=raw))

    extracted = _extract_structured_output(
        SimpleNamespace(json_dict=None, raw=raw),
        task_obj,
        task_name="season_plan_finalize",
        output_mode="json",
    )

    assert extracted == payload

def test_internal_json_season_finalizer_does_not_bind_strict_output_model() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    task_blueprints = build_task_blueprints(bundle)
    task_blueprint = task_blueprints["season_plan_finalize"]
    artifact_task_blueprint = task_blueprints["season_plan"]

    assert resolve_task_policy(task_blueprint, bundle.task_policies).output_mode == "json"
    assert should_bind_crewai_output_model(task_blueprint, output_mode="json") is False
    assert resolve_task_policy(artifact_task_blueprint, bundle.task_policies).output_mode == "json"
    assert should_bind_crewai_output_model(artifact_task_blueprint, output_mode="json") is True

def test_season_macrocycle_and_finalize_guidance_support_multi_a_event_backplanning() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    blueprints = build_task_blueprints(bundle)

    macrocycle_description = blueprints["season_macrocycle_draft"].description
    blueprint_draft_description = blueprints["season_phase_blueprint_draft"].description
    season_finalize_description = blueprints["season_plan_finalize"].description
    season_finalize_expected_output = blueprints["season_plan_finalize"].expected_output

    assert "`constraints[]` contains constraint-audit entries only" in season_finalize_description
    assert "`load_governance[]` contains governance-audit entries only" in season_finalize_description
    assert "`cadence_authority_preserved` plus `durability_first_respected` belong only inside `load_governance[]`" in season_finalize_description
    assert "emit top-level `event_priority`, `macrocycle`, and `phase_blueprints`" in season_finalize_description
    assert "singular top-level `constraint_audit` and `load_governance_audit` keys are invalid" in season_finalize_description
    assert "`constraints[]` are owned by `season_constraint_review`, `season_historical_context_review`, and `season_kpi_guidance_review`" in season_finalize_description
    assert "`load_governance[]` are owned by `season_load_corridor_draft` and `season_progression_review`" in season_finalize_description
    assert "`constraint_type`, `status`, or `summary`" in season_finalize_description
    assert "Return exactly one structured object with top-level `phase_blueprints` only" in blueprint_draft_description
    assert "`phase_blueprints` are owned here first" in blueprint_draft_description
    assert "raw JSON object only" in season_finalize_description
    assert "`season_phase_blueprint_draft` task" in season_finalize_description
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
        assert "constraint_audit" in text
        assert "load_governance_audit" in text
        assert "season_constraint_review" in text
        assert "season_historical_context_review" in text
        assert "season_kpi_guidance_review" in text
        assert "season_load_corridor_draft" in text
        assert "season_progression_review" in text
        assert "constraint_type" in text
        assert "summary" in text

    assert "phase_blueprints" in blueprint_prompt_text
    assert "Do not emit a full Season bundle." in blueprint_prompt_text
    assert "Return exactly one structured object with top-level `phase_blueprints`." in blueprint_prompt_text
