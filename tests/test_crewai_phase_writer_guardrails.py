from __future__ import annotations

from pathlib import Path

import pytest

from rps.agents.crewai_bundle_normalization import (
    _normalize_final_season_plan_semantics,
)
from rps.agents.crewai_context_blocks import (
    _phase_writer_authority_context_block,
)
from rps.agents.tasks import AgentTask
from rps.crewai_runtime import guardrails_utilities as crewai_guardrails_utilities
from rps.crewai_runtime.guardrails_context import guardrail_runtime_context
from rps.crewai_runtime.guardrails_phase import (
    phase_execution_context_match,
    phase_week_role_load_coherence,
    phase_weeks_match_range,
)
from rps.crewai_runtime.guardrails_season import (
    season_writer_bundle_match,
)


def test_phase_structure_writer_guardrails_pre_normalize_exact_phase_authority() -> None:
    expected_contract = {
        "selected_scenario_id": "B",
        "constraint_summary": [
            "Indoor trainer availability supports continuity when travel or weather reduces outdoor options."
        ],
        "risk_flags": ["Preserve recovery margin through controlled progression."],
    }
    candidate = {
        "meta": {"artifact_type": "PHASE_STRUCTURE", "iso_week_range": "2026-24--2026-25"},
        "data": {
            "inherited_scenario_contract": {
                "selected_scenario_id": "B",
                "constraint_summary": [
                    "Indoor trainer availability supports continuity when travel or weather reduces outdoor work."
                ],
                "risk_flags": ["Paraphrased risk flag."],
            },
            "upstream_intent": {"primary_objective": "Wrong objective"},
            "structural_phase_elements": {
                "allowed_day_roles": ["ENDURANCE", "QUALITY"],
                "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
                "allowed_load_modalities": ["NONE", "K3"],
            },
            "execution_principles": {
                "load_intensity_handling": {"forbidden_intensity_domains": ["VO2MAX"]},
            },
            "load_ranges": {
                "weekly_kj_bands": [
                    {"week": "2026-24", "band": {"min": 6000, "max": 7000}},
                    {"week": "2026-25", "band": {"min": 6100, "max": 7100}},
                ],
                "source": "wrong.json",
            },
            "week_skeleton_logic": {
                "week_roles": {
                    "week_roles": [
                        {"week": "2026-24", "role": "LOAD_1"},
                        {"week": "2026-25", "role": "RELOAD"},
                    ]
                }
            },
        },
    }
    phase_guardrails = {
        "meta": {"artifact_type": "PHASE_GUARDRAILS", "version_key": "2026-24--2026-25__20260608_090000"},
        "data": {
            "load_guardrails": {
                "weekly_kj_bands": [
                    {"week": "2026-24", "band": {"min": 7200, "max": 8200}},
                    {"week": "2026-25", "band": {"min": 7300, "max": 8300}},
                ]
            }
        },
    }
    wrapped_context_match = crewai_guardrails_utilities._with_guardrail_telemetry(
        "phase_structure",
        "phase_execution_context_match",
        phase_execution_context_match,
    )
    wrapped_weeks_match = crewai_guardrails_utilities._with_guardrail_telemetry(
        "phase_structure",
        "phase_weeks_match_range",
        phase_weeks_match_range,
    )
    wrapped_load_coherence = crewai_guardrails_utilities._with_guardrail_telemetry(
        "phase_structure",
        "phase_week_role_load_coherence",
        phase_week_role_load_coherence,
    )

    with guardrail_runtime_context(
        artifact_type="PHASE_STRUCTURE",
        loaded_inputs={
            "phase_guardrails": {
                "ok": True,
                "document": phase_guardrails,
                "version_key": "2026-24--2026-25__20260608_090000",
            },
        },
        phase_execution_context={
            "inherited_scenario_contract": expected_contract,
            "phase_allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
            "phase_forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
            "phase_allowed_load_modalities": ["NONE"],
            "phase_primary_objective": "Rebuild load tolerance with controlled sweet spot support.",
            "week_role_by_iso_week": {"2026-24": "LOAD_1", "2026-25": "RELOAD"},
            "phase_role_week_load_bands": [
                {"week": "2026-24", "role": "LOAD_1", "band": {"min": 7200, "max": 8200}},
                {"week": "2026-25", "role": "RELOAD", "band": {"min": 7300, "max": 8300}},
            ],
        },
    ):
        ok_context, repaired_context = wrapped_context_match(candidate)
        ok_weeks, repaired_weeks = wrapped_weeks_match(candidate)
        ok_coherence, repaired_coherence = wrapped_load_coherence(candidate)

    assert ok_context is True, repaired_context
    assert ok_weeks is True, repaired_weeks
    assert ok_coherence is True, repaired_coherence
    assert repaired_context["data"]["structural_phase_elements"]["allowed_intensity_domains"] == [
        "RECOVERY",
        "ENDURANCE",
        "TEMPO",
        "SWEET_SPOT",
    ]
    assert repaired_context["data"]["structural_phase_elements"]["allowed_load_modalities"] == ["NONE"]
    assert repaired_context["data"]["execution_principles"]["load_intensity_handling"][
        "forbidden_intensity_domains"
    ] == ["THRESHOLD", "VO2MAX"]
    assert repaired_context["data"]["upstream_intent"]["primary_objective"] == (
        "Rebuild load tolerance with controlled sweet spot support."
    )
    assert repaired_context["data"]["inherited_scenario_contract"] == expected_contract
    assert repaired_context["data"]["load_ranges"]["weekly_kj_bands"] == [
        {"week": "2026-24", "band": {"min": 7200, "max": 8200}},
        {"week": "2026-25", "band": {"min": 7300, "max": 8300}},
    ]
    assert (
        repaired_context["data"]["load_ranges"]["source"]
        == "phase_guardrails_2026-24--2026-25__20260608_090000.json"
    )

def test_phase_structure_writer_guardrails_fail_cleanly_without_execution_context_authority() -> None:
    candidate = {
        "meta": {"artifact_type": "PHASE_STRUCTURE", "iso_week_range": "2026-24--2026-25"},
        "data": {
            "structural_phase_elements": {
                "allowed_day_roles": ["ENDURANCE", "QUALITY"],
                "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
                "allowed_load_modalities": ["NONE", "K3"],
            },
            "load_ranges": {
                "weekly_kj_bands": [
                    {"week": "2026-24", "band": {"min": 7200, "max": 8200}},
                    {"week": "2026-25", "band": {"min": 7300, "max": 8300}},
                ]
            },
        },
    }
    wrapped = crewai_guardrails_utilities._with_guardrail_telemetry(
        "phase_structure",
        "phase_execution_context_match",
        phase_execution_context_match,
    )

    with guardrail_runtime_context(
        artifact_type="PHASE_STRUCTURE",
        loaded_inputs={
            "phase_guardrails": {
                "ok": True,
                "document": {
                    "data": {
                        "load_guardrails": {
                            "weekly_kj_bands": [
                                {"week": "2026-24", "band": {"min": 7200, "max": 8200}},
                                {"week": "2026-25", "band": {"min": 7300, "max": 8300}},
                            ]
                        }
                    }
                },
                "version_key": "2026-24--2026-25__20260608_090000",
            }
        },
        phase_execution_context={},
    ):
        ok, message = wrapped(candidate)

    assert ok is False
    assert "pre_guardrail_normalization_failed" in message
    assert "phase_execution_context.phase_allowed_intensity_domains" in message

def test_phase_structure_writer_guardrails_fail_cleanly_without_phase_guardrails_bands() -> None:
    candidate = {
        "meta": {"artifact_type": "PHASE_STRUCTURE", "iso_week_range": "2026-24--2026-25"},
        "data": {
            "structural_phase_elements": {
                "allowed_day_roles": ["ENDURANCE", "QUALITY"],
                "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
                "allowed_load_modalities": ["NONE", "K3"],
            },
            "load_ranges": {
                "weekly_kj_bands": [
                    {"week": "2026-24", "band": {"min": 7200, "max": 8200}},
                    {"week": "2026-25", "band": {"min": 7300, "max": 8300}},
                ]
            },
        },
    }
    wrapped = crewai_guardrails_utilities._with_guardrail_telemetry(
        "phase_structure",
        "phase_execution_context_match",
        phase_execution_context_match,
    )

    with guardrail_runtime_context(
        artifact_type="PHASE_STRUCTURE",
        loaded_inputs={},
        phase_execution_context={
            "phase_allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
            "phase_forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
            "phase_allowed_load_modalities": ["NONE"],
            "inherited_scenario_contract": {"selected_scenario_id": "B"},
            "week_role_by_iso_week": {"2026-24": "LOAD_1", "2026-25": "RELOAD"},
            "phase_role_week_load_bands": [
                {"week": "2026-24", "role": "LOAD_1", "band": {"min": 7200, "max": 8200}},
                {"week": "2026-25", "role": "RELOAD", "band": {"min": 7300, "max": 8300}},
            ],
        },
    ):
        ok, message = wrapped(candidate)

    assert ok is False
    assert "pre_guardrail_normalization_failed" in message
    assert "phase_guardrails.data.load_guardrails.weekly_kj_bands" in message

def test_phase_structure_writer_guardrails_fail_cleanly_without_inherited_scenario_contract() -> None:
    candidate = {
        "meta": {"artifact_type": "PHASE_STRUCTURE", "iso_week_range": "2026-24--2026-25"},
        "data": {
            "inherited_scenario_contract": {"selected_scenario_id": "B"},
            "structural_phase_elements": {
                "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
                "allowed_load_modalities": ["NONE", "K3"],
            },
            "load_ranges": {
                "weekly_kj_bands": [
                    {"week": "2026-24", "band": {"min": 7200, "max": 8200}},
                    {"week": "2026-25", "band": {"min": 7300, "max": 8300}},
                ]
            },
        },
    }
    wrapped = crewai_guardrails_utilities._with_guardrail_telemetry(
        "phase_structure",
        "phase_execution_context_match",
        phase_execution_context_match,
    )

    with guardrail_runtime_context(
        artifact_type="PHASE_STRUCTURE",
        loaded_inputs={
            "phase_guardrails": {
                "ok": True,
                "document": {
                    "data": {
                        "load_guardrails": {
                            "weekly_kj_bands": [
                                {"week": "2026-24", "band": {"min": 7200, "max": 8200}},
                                {"week": "2026-25", "band": {"min": 7300, "max": 8300}},
                            ]
                        }
                    }
                },
                "version_key": "2026-24--2026-25__20260608_090000",
            }
        },
        phase_execution_context={
            "phase_allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
            "phase_forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
            "phase_allowed_load_modalities": ["NONE"],
            "week_role_by_iso_week": {"2026-24": "LOAD_1", "2026-25": "RELOAD"},
        },
    ):
        ok, message = wrapped(candidate)

    assert ok is False
    assert "pre_guardrail_normalization_failed" in message
    assert "phase_execution_context.inherited_scenario_contract" in message

def test_phase_structure_guardrail_mismatch_emits_contract_diagnostics(monkeypatch: pytest.MonkeyPatch) -> None:
    candidate = {
        "meta": {"artifact_type": "PHASE_STRUCTURE", "iso_week_range": "2026-24--2026-25"},
        "structure": {
            "inherited_scenario_contract": {
                "selected_scenario_id": "A",
                "constraint_summary": ["raw nested drift"],
            }
        },
        "data": {
            "inherited_scenario_contract": {
                "selected_scenario_id": "A",
                "constraint_summary": ["candidate drift"],
            },
            "structural_phase_elements": {
                "allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
                "allowed_load_modalities": ["NONE"],
            },
            "execution_principles": {
                "load_intensity_handling": {
                    "forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
                }
            },
            "load_ranges": {
                "weekly_kj_bands": [
                    {"week": "2026-24", "band": {"min": 7200, "max": 8200}},
                    {"week": "2026-25", "band": {"min": 7300, "max": 8300}},
                ]
            },
            "week_skeleton_logic": {
                "week_roles": {
                    "week_roles": [
                        {"week": "2026-24", "role": "LOAD_1"},
                        {"week": "2026-25", "role": "RELOAD"},
                    ]
                }
            },
        },
    }
    wrapped = crewai_guardrails_utilities._with_guardrail_telemetry(
        "phase_structure",
        "phase_execution_context_match",
        phase_execution_context_match,
    )
    monkeypatch.setattr(
        crewai_guardrails_utilities,
        "normalize_artifact_candidate_for_task_guardrails",
        lambda result: result,
    )
    emitted: list[dict[str, object]] = []
    monkeypatch.setattr(
        crewai_guardrails_utilities,
        "emit_runtime_event",
        lambda **kwargs: emitted.append(kwargs),
    )

    with guardrail_runtime_context(
        artifact_type="PHASE_STRUCTURE",
        loaded_inputs={
            "phase_guardrails": {
                "ok": True,
                "document": {
                    "data": {
                        "inherited_scenario_contract": {
                            "selected_scenario_id": "B",
                            "constraint_summary": ["guardrails fallback"],
                        },
                        "load_guardrails": {
                            "weekly_kj_bands": [
                                {"week": "2026-24", "band": {"min": 7200, "max": 8200}},
                                {"week": "2026-25", "band": {"min": 7300, "max": 8300}},
                            ]
                        },
                    }
                },
                "version_key": "2026-24--2026-25__20260608_090000",
            }
        },
        phase_execution_context={
            "inherited_scenario_contract": {
                "selected_scenario_id": "B",
                "constraint_summary": ["execution context authority"],
            },
            "phase_allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
            "phase_forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
            "phase_allowed_load_modalities": ["NONE"],
            "week_role_by_iso_week": {"2026-24": "LOAD_1", "2026-25": "RELOAD"},
            "phase_role_week_load_bands": [
                {"week": "2026-24", "role": "LOAD_1", "band": {"min": 7200, "max": 8200}},
                {"week": "2026-25", "role": "RELOAD", "band": {"min": 7300, "max": 8300}},
            ],
        },
    ):
        ok, message = wrapped(candidate)

    assert ok is False
    assert "phase_inherited_scenario_contract_mismatch" in message
    assert emitted
    reason = str(emitted[-1]["reason"])
    assert "phase_contract_diag=" in reason
    assert "execution_context_contract=yes" in reason
    assert "bundle_contract=no" in reason
    assert "raw_structure_contract=yes" in reason
    assert "raw_candidate_contract=yes" in reason
    assert "phase_guardrails_contract=yes" in reason
    assert "source=candidate_or_late_rewrite" in reason
    assert "mismatch_path=data.inherited_scenario_contract.constraint_summary[0]" in reason

def test_phase_writer_authority_context_block_frontloads_exact_phase_fields() -> None:
    phase_structure = {
        "meta": {"version_key": "2026-24--2026-25__20260608_091500"},
        "data": {
            "upstream_intent": {
                "phase_type": "BUILD",
                "phase_intent": "shortened_re_entry",
                "build_subtype": "durability_build",
                "phase_taxonomy_version": "v2",
                "primary_objective": "Rebuild load tolerance.",
            }
        },
    }

    with guardrail_runtime_context(
        phase_execution_context={
            "phase_allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
            "phase_forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
            "phase_allowed_load_modalities": ["NONE"],
            "phase_primary_objective": "Rebuild load tolerance.",
            "week_role_by_iso_week": {"2026-24": "LOAD_1", "2026-25": "RELOAD"},
            "phase_role_week_load_bands": [
                {"week": "2026-24", "role": "LOAD_1", "band": {"min": 7200, "max": 8200}},
                {"week": "2026-25", "role": "RELOAD", "band": {"min": 7300, "max": 8300}},
            ],
        }
    ):
        structure_block = _phase_writer_authority_context_block(
            AgentTask.CREATE_PHASE_STRUCTURE,
            {
                "phase_guardrails": {
                    "version_key": "2026-24--2026-25__20260608_090000",
                }
            },
        )
        preview_block = _phase_writer_authority_context_block(
            AgentTask.CREATE_PHASE_PREVIEW,
            {
                "phase_structure": {
                    "document": phase_structure,
                    "version_key": "2026-24--2026-25__20260608_091500",
                }
            },
        )

    assert "Exact writer authority" in structure_block
    assert "\"allowed_intensity_domains\"" in structure_block
    assert "\"phase_guardrails_source\": \"phase_guardrails_2026-24--2026-25__20260608_090000.json\"" in structure_block
    assert "\"phase_role_week_load_bands\"" in structure_block
    assert "Exact writer authority" in preview_block
    assert "\"rest_days\": \"REST -> NONE/NONE\"" in preview_block
    assert "\"recovery_days\": \"RECOVERY -> RECOVERY\"" in preview_block
    assert "\"phase_structure_source\": \"phase_structure_2026-24--2026-25__20260608_091500.json\"" in preview_block

def test_phase_active_files_frontload_exact_legality_and_operational_none_rules() -> None:
    tasks_text = Path("config/crewai/tasks.yaml").read_text(encoding="utf-8")
    guardrails_skill_text = Path("skills/phase/guardrails-authoring/SKILL.md").read_text(encoding="utf-8")
    structure_skill_text = Path("skills/phase/structure-authoring/SKILL.md").read_text(encoding="utf-8")
    writer_skill_text = Path("skills/phase/artifact-writing/SKILL.md").read_text(encoding="utf-8")
    preview_skill_text = Path("skills/phase/preview-synthesis/SKILL.md").read_text(encoding="utf-8")
    finalizer_prompt_text = Path("prompts/agents/phase_bundle_manager.md").read_text(encoding="utf-8")
    finalizer_skill_text = Path("skills/phase/bundle-synthesis/SKILL.md").read_text(encoding="utf-8")

    assert "do not add `NONE`" in tasks_text
    assert "do not include `NONE` in `PHASE_STRUCTURE.allowed_intensity_domains`" in tasks_text
    assert "`upstream_intent.constraints` is a closed field for real inherited planning facts only" in tasks_text
    assert "Invalid examples: `Use the injected role-week banding exactly.`" in tasks_text
    assert "use that wording rather than paraphrasing it" in tasks_text
    assert "do not call `workspace_get_phase_execution_context` or `workspace_get_phase_slot_contract`" in tasks_text
    assert "Exact week bands come from persisted Season phase authority and must be copied, not recomputed from S5." in tasks_text
    assert "canonical `quality_intent` is `Stabilization`" in tasks_text
    assert "must formally trace the exact stored `PHASE_GUARDRAILS`" in tasks_text
    assert "must formally trace the exact stored `PHASE_STRUCTURE`" in tasks_text
    assert "Treat inherited scenario contract as season posture ceiling only" in guardrails_skill_text
    assert "allowed_intensity_domains" in structure_skill_text
    assert "do not add `NONE`" in structure_skill_text
    assert "must not contain runtime/process rules" in structure_skill_text
    assert "use that wording rather than paraphrasing it" in structure_skill_text
    assert "Invalid examples:" in structure_skill_text
    assert "must not include `NONE`" in writer_skill_text
    assert "weekly_kj_bands` must be copied from injected deterministic phase authority" in writer_skill_text
    assert "phase legality fields remain separate from the scenario ceiling" in writer_skill_text
    assert "Preview may use `NONE` only on `REST` or fixed non-training days" in preview_skill_text
    assert "Phase Finalizer Authority Freeze" in finalizer_prompt_text
    assert "do not serialize runtime/process/governance rules into `structure.upstream_intent.constraints`" in finalizer_prompt_text
    assert "keep that wording instead of paraphrasing it" in finalizer_prompt_text
    assert "do not call `workspace_get_phase_execution_context` or `workspace_get_phase_slot_contract`" in finalizer_prompt_text
    assert "Compact authority-freeze example" in finalizer_skill_text
    assert "keep runtime/process/governance rules out of `structure.upstream_intent.constraints`" in finalizer_skill_text
    assert "keep that wording instead of paraphrasing it" in finalizer_skill_text
    assert "use tools only as fallback for genuinely missing authority fields" in finalizer_skill_text

def test_phase_guardrails_writer_guardrails_pre_normalize_exact_phase_authority() -> None:
    candidate = {
        "meta": {"artifact_type": "PHASE_GUARDRAILS", "iso_week_range": "2026-24--2026-25"},
        "data": {
            "phase_summary": {"primary_objective": "Wrong objective"},
            "load_guardrails": {
                "weekly_kj_bands": [
                    {"week": "2026-24", "band": {"min": 7893, "max": 8626}},
                ]
            },
            "allowed_forbidden_semantics": {
                "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
                "forbidden_intensity_domains": ["VO2MAX"],
                "allowed_load_modalities": ["NONE"],
                "quality_density": {"quality_intent": "Build"},
            },
            "inherited_scenario_contract": {
                "allowed_intensity_domains": ["ENDURANCE"],
                "forbidden_intensity_domains": ["VO2MAX", "THRESHOLD"],
            },
        },
    }
    season_plan = {
        "data": {
            "selected_scenario_contract": {
                "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
                "forbidden_intensity_domains": ["VO2MAX"],
            }
        }
    }
    with guardrail_runtime_context(
        artifact_type="PHASE_GUARDRAILS",
        loaded_inputs={"season_plan": {"ok": True, "document": season_plan}},
        phase_execution_context={
            "phase_type": "BASE",
            "phase_intent": "shortened_re_entry",
            "phase_primary_objective": "Re-establish stable training continuity without overreaching.",
            "phase_allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
            "phase_forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
            "phase_allowed_load_modalities": ["NONE", "K3"],
            "phase_role_week_load_bands": [
                {"week": "2026-24", "role": "SHORTENED_RE_ENTRY", "band": {"min": 7893, "max": 10148}},
                {"week": "2026-25", "role": "SHORTENED_CONSOLIDATION", "band": {"min": 9020, "max": 11275}},
            ],
        },
    ):
        repaired = crewai_guardrails_utilities.normalize_artifact_candidate_for_task_guardrails(candidate)

    assert repaired["data"]["load_guardrails"]["weekly_kj_bands"][0]["band"]["max"] == 10148
    assert repaired["data"]["load_guardrails"]["weekly_kj_bands"][0]["band"]["notes"] == (
        "role SHORTENED_RE_ENTRY; S5 deterministic band is 7893-10148; feasible band max is 10148"
    )
    assert "role" not in repaired["data"]["load_guardrails"]["weekly_kj_bands"][0]
    assert repaired["data"]["phase_summary"]["primary_objective"] == (
        "Re-establish stable training continuity without overreaching."
    )
    assert repaired["data"]["allowed_forbidden_semantics"]["allowed_intensity_domains"] == [
        "RECOVERY",
        "ENDURANCE",
        "TEMPO",
        "SWEET_SPOT",
    ]
    assert repaired["data"]["allowed_forbidden_semantics"]["forbidden_intensity_domains"] == [
        "THRESHOLD",
        "VO2MAX",
    ]
    assert repaired["data"]["allowed_forbidden_semantics"]["quality_density"]["quality_intent"] == "Stabilization"
    assert repaired["data"]["inherited_scenario_contract"] == season_plan["data"]["selected_scenario_contract"]

def test_phase_preview_writer_guardrails_pre_normalize_shared_skeleton_semantics() -> None:
    candidate = {
        "meta": {"artifact_type": "PHASE_PREVIEW", "iso_week_range": "2026-24--2026-25"},
        "data": {
            "phase_intent_summary": {"primary_objective": "Wrong objective"},
            "weekly_agenda_preview": [
                {
                    "week": "2026-24",
                    "days": [
                        {"day_of_week": "Mon", "day_role": "REST", "intensity_domain": "TEMPO", "load_modality": "K3"},
                        {"day_of_week": "Tue", "day_role": "RECOVERY", "intensity_domain": "ENDURANCE", "load_modality": "K3"},
                        {"day_of_week": "Wed", "day_role": "QUALITY", "intensity_domain": "THRESHOLD", "load_modality": "NONE"},
                        {"day_of_week": "Thu", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE"},
                        {"day_of_week": "Fri", "day_role": "REST", "intensity_domain": "SWEET_SPOT", "load_modality": "K3"},
                        {"day_of_week": "Sat", "day_role": "QUALITY", "intensity_domain": "SWEET_SPOT", "load_modality": "NONE"},
                        {"day_of_week": "Sun", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE"},
                    ],
                },
                {
                    "week": "",
                    "days": [
                        {"day_of_week": "Mon", "day_role": "REST", "intensity_domain": "TEMPO", "load_modality": "K3"},
                        {"day_of_week": "Tue", "day_role": "RECOVERY", "intensity_domain": "ENDURANCE", "load_modality": "K3"},
                        {"day_of_week": "Wed", "day_role": "QUALITY", "intensity_domain": "THRESHOLD", "load_modality": "NONE"},
                        {"day_of_week": "Thu", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE"},
                        {"day_of_week": "Fri", "day_role": "REST", "intensity_domain": "SWEET_SPOT", "load_modality": "K3"},
                        {"day_of_week": "Sat", "day_role": "QUALITY", "intensity_domain": "SWEET_SPOT", "load_modality": "NONE"},
                        {"day_of_week": "Sun", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE"},
                    ],
                },
            ],
        },
    }
    phase_structure = {
        "meta": {"artifact_type": "PHASE_STRUCTURE"},
        "data": {
            "upstream_intent": {
                "phase_intent": "shortened_re_entry",
                "build_subtype": None,
                "primary_objective": "Rebuild load tolerance with controlled sweet spot support.",
            },
            "structural_phase_elements": {
                "allowed_day_roles": ["REST", "RECOVERY", "ENDURANCE", "QUALITY"],
                "allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
                "allowed_load_modalities": ["NONE"],
            },
            "execution_principles": {
                "load_intensity_handling": {"max_quality_days_per_week": 1},
                "recovery_protection": {"fixed_non_training_days": ["Mon", "Fri"]},
            },
            "week_skeleton_logic": {
                "week_roles": {
                    "week_roles": [
                        {"week": "2026-24", "role": "LOAD_1"},
                        {"week": "2026-25", "role": "RELOAD"},
                    ]
                }
            },
        },
    }
    with guardrail_runtime_context(
        artifact_type="PHASE_PREVIEW",
        loaded_inputs={
            "phase_structure": {
                "ok": True,
                "document": phase_structure,
                "version_key": "2026-24--2026-25__20260608_091500",
            }
        },
    ):
        repaired = crewai_guardrails_utilities.normalize_artifact_candidate_for_task_guardrails(candidate)

    assert repaired["data"]["phase_intent_summary"]["primary_objective"] == (
        "Rebuild load tolerance with controlled sweet spot support."
    )
    days = repaired["data"]["weekly_agenda_preview"][0]["days"]
    assert days[0]["intensity_domain"] == "NONE"
    assert days[0]["load_modality"] == "NONE"
    assert days[1]["day_role"] == "QUALITY"
    assert days[1]["intensity_domain"] == "TEMPO"
    assert days[2]["day_role"] == "RECOVERY"
    assert days[2]["intensity_domain"] == "RECOVERY"
    assert days[2]["load_modality"] == "NONE"
    assert days[5]["day_role"] == "ENDURANCE"
    assert days[5]["intensity_domain"] == "ENDURANCE"
    assert repaired["data"]["weekly_agenda_preview"][1]["week"] == "2026-25"

def test_season_writer_bundle_match_repairs_deterministic_writer_drift() -> None:
    approved_bundle = {
        "season_load_envelope": {
            "expected_average_weekly_kj_range": {"min": 9516, "max": 12892},
            "expected_high_load_weeks_count": 7,
            "expected_deload_or_low_load_weeks_count": 5,
        },
        "phase_blueprints": [
            {
                "phase_id": "P01",
                "phase_type": "BASE",
                "phase_intent": "shortened_re_entry",
                "build_subtype": None,
                "phase_taxonomy_version": "canonical_phase_taxonomy_v1",
                "allowed_domains": ["ENDURANCE", "TEMPO"],
                "allowed_load_modalities": ["NONE", "K3"],
                "forbidden_domains": ["THRESHOLD", "VO2MAX"],
            }
        ],
    }
    output = {
        "data": {
            "body_metadata": {"phase_taxonomy_version": "canonical_phase_taxonomy_v1"},
            "season_load_envelope": {
                "expected_average_weekly_kj_range": {"min": 9000, "max": 14000},
                "expected_high_load_weeks_count": 7,
                "expected_deload_or_low_load_weeks_count": 5,
            },
            "phases": [
                {
                    "phase_id": "P01",
                    "phase_type": "BASE",
                    "phase_intent": "shortened_re_entry",
                    "build_subtype": None,
                    "allowed_forbidden_semantics": {
                        "allowed_intensity_domains": ["ENDURANCE", "TEMPO"],
                        "allowed_load_modalities": ["NONE", "K3"],
                        "forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
                    },
                }
            ],
        }
    }

    with guardrail_runtime_context(approved_planning_bundle=approved_bundle):
        ok, repaired = season_writer_bundle_match(output)

    assert ok is True
    assert repaired["data"]["season_load_envelope"] == approved_bundle["season_load_envelope"]
    phase = repaired["data"]["phases"][0]
    assert phase["phase_type"] == "BASE"
    assert phase["phase_intent"] == "shortened_re_entry"
    assert phase["allowed_forbidden_semantics"]["allowed_intensity_domains"] == ["ENDURANCE", "TEMPO"]
    assert phase["allowed_forbidden_semantics"]["allowed_load_modalities"] == ["NONE", "K3"]
    assert phase["allowed_forbidden_semantics"]["forbidden_intensity_domains"] == ["THRESHOLD", "VO2MAX"]

def test_normalize_final_season_plan_semantics_projects_events_guardrails_and_warning() -> None:
    document = {
        "meta": {"artifact_type": "SEASON_PLAN"},
        "data": {
            "season_intent_principles": {
                "season_objective": "Stable long-duration performance over 300-400 km."
            },
            "phases": [
                {
                    "phase_id": "P01",
                    "phase_type": "BASE",
                    "phase_intent": "shortened_re_entry",
                    "build_subtype": None,
                    "weekly_load_corridor": {"weekly_kj": {"min": 7800, "max": 9800, "notes": "Base corridor."}},
                    "allowed_forbidden_semantics": {
                        "allowed_intensity_domains": ["ENDURANCE"],
                        "allowed_load_modalities": ["K3"],
                        "forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
                    },
                    "events_constraints": [{"window": "2026-21--2026-23", "type": "B", "constraint": "stale"}],
                },
                {
                    "phase_id": "P02",
                    "phase_type": "TAPER",
                    "phase_intent": "taper_freshening",
                    "build_subtype": None,
                    "weekly_load_corridor": {"weekly_kj": {"min": 7000, "max": 8800, "notes": "Taper corridor."}},
                    "allowed_forbidden_semantics": {
                        "allowed_intensity_domains": ["ENDURANCE"],
                        "allowed_load_modalities": ["K3"],
                        "forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
                    },
                    "events_constraints": [],
                },
            ],
            "justification": {
                "summary": "Summary.",
                "citations": [{"source_type": "contract", "source_id": "x", "section": "y", "rationale": "z"}],
                "phase_justifications": [
                    {"phase_id": "P01", "intensity_distribution": "x", "overload_pattern": "y", "kJ_first_statement": "P01 corridor.", "citations": ["c1"]},
                    {"phase_id": "P02", "intensity_distribution": "x", "overload_pattern": "y", "kJ_first_statement": "P02 corridor.", "citations": ["c1"]},
                ],
            },
            "principles_scientific_foundation": {
                "principle_applications": [{"principle": "Durability-first progression", "influence": "x"}],
                "scientific_foundation": {
                    "publications": [{"authors": "Seiler, S.", "year": 2010, "title": "Intensity distribution", "link": "https://example.com"}],
                    "plan_alignment_check": "Aligned",
                    "rationale": "x",
                },
            },
            "assumptions_unknowns": {
                "assumptions": ["a"],
                "uncertainties": ["u"],
                "revisit_items": ["r"],
            },
        },
    }
    with guardrail_runtime_context(
        approved_planning_bundle={
            "phase_blueprints": [
                {"phase_id": "P01", "allowed_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"], "allowed_load_modalities": ["NONE", "K3"], "forbidden_domains": ["THRESHOLD", "VO2MAX"]},
                {"phase_id": "P02", "allowed_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"], "allowed_load_modalities": ["NONE"], "forbidden_domains": ["THRESHOLD", "VO2MAX"]},
            ]
        },
        season_phase_load_context={
            "season_allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT"],
            "phases": [
                {
                    "phase_id": "P01",
                    "phase_type": "BASE",
                    "phase_intent": "shortened_re_entry",
                    "build_subtype": None,
                    "role_week_load_bands": [{"week": "2026-21", "role": "LOAD_1", "band": {"min": 7800, "max": 8600}}],
                    "event_taper_trace": {"events": []},
                },
                {
                    "phase_id": "P02",
                    "phase_type": "TAPER",
                    "phase_intent": "taper_freshening",
                    "build_subtype": None,
                    "role_week_load_bands": [{"week": "2026-37", "role": "EVENT", "band": {"min": 7000, "max": 8800}}],
                    "event_taper_trace": {
                        "events": [{"date": "2026-09-12", "week": "2026-37", "type": "A", "name": "Brevet 200 km"}]
                    },
                },
            ],
        },
    ):
        normalized = _normalize_final_season_plan_semantics(document)

    p01 = normalized["data"]["phases"][0]
    p02 = normalized["data"]["phases"][1]
    assert p01["allowed_forbidden_semantics"]["allowed_load_modalities"] == ["NONE", "K3"]
    assert p02["allowed_forbidden_semantics"]["allowed_load_modalities"] == ["NONE"]
    assert p01["events_constraints"] == []
    assert p02["events_constraints"] == [
        {
            "window": "2026-09-12",
            "type": "A",
            "constraint": "A event receives dedicated taper-contained event handling.",
        }
    ]
    assert "2026-21: LOAD_1 7800-8600" in p01["weekly_load_corridor"]["weekly_kj"]["notes"]
    assert any("Warning:" in item for item in normalized["data"]["assumptions_unknowns"]["revisit_items"])
    assert any(
        "Durability" in publication["title"]
        for publication in normalized["data"]["principles_scientific_foundation"]["scientific_foundation"]["publications"]
    )

def test_normalize_final_season_plan_semantics_rewrites_positive_forbidden_threshold_narrative() -> None:
    document = {
        "meta": {"artifact_type": "SEASON_PLAN"},
        "data": {
            "season_intent_principles": {"season_objective": "Strong 300 km execution."},
            "phases": [
                {
                    "phase_id": "P01",
                    "phase_type": "BUILD",
                    "phase_intent": "durability_build",
                    "build_subtype": "durability_build",
                    "narrative": "Controlled THRESHOLD support appears throughout this build.",
                    "weekly_load_corridor": {"weekly_kj": {"min": 9000, "max": 10800}},
                    "allowed_forbidden_semantics": {
                        "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                        "allowed_load_modalities": ["NONE", "K3"],
                        "forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
                    },
                    "overview": {
                        "metabolic_focus": "THRESHOLD-led durability focus.",
                        "expected_adaptations": ["Controlled THRESHOLD support appears throughout this build."],
                        "non_negotiables": ["THRESHOLD remains secondary inside this block."],
                    },
                    "structural_emphasis": {"typical_focus": "threshold-led long-ride stability."},
                }
            ],
            "justification": {
                "phase_justifications": [
                    {
                        "phase_id": "P01",
                        "intensity_distribution": "controlled threshold support with steady pressure",
                        "overload_pattern": "Build logic.",
                        "kJ_first_statement": "P01 corridor.",
                        "citations": [],
                    }
                ]
            },
            "principles_scientific_foundation": {
                "principle_applications": [],
                "scientific_foundation": {"publications": []},
            },
            "assumptions_unknowns": {"revisit_items": []},
            "phase_transitions_guardrails": {"conservative_triggers": [], "absolute_no_go_rules": []},
        },
    }

    with guardrail_runtime_context(
        approved_planning_bundle={
            "phase_blueprints": [
                {
                    "phase_id": "P01",
                    "phase_type": "BUILD",
                    "phase_intent": "durability_build",
                    "build_subtype": "durability_build",
                    "allowed_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                    "allowed_load_modalities": ["NONE", "K3"],
                    "forbidden_domains": ["THRESHOLD", "VO2MAX"],
                }
            ]
        },
        season_phase_load_context={
            "season_allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
            "phases": [
                {
                    "phase_id": "P01",
                    "phase_type": "BUILD",
                    "phase_intent": "durability_build",
                    "build_subtype": "durability_build",
                    "role_week_load_bands": [],
                    "event_taper_trace": {},
                }
            ],
        },
    ):
        normalized = _normalize_final_season_plan_semantics(document)

    phase = normalized["data"]["phases"][0]
    assert phase["narrative"].startswith("Durability-led build emphasizing fatigue resistance")
    assert phase["overview"]["metabolic_focus"] == (
        "Durability-first pressure through endurance-led work with controlled tempo and sweet spot support."
    )
    assert phase["overview"]["expected_adaptations"] == [
        "Improved fatigue resistance and long-ride stability through endurance-led work with controlled tempo and sweet spot support."
    ]
    assert "THRESHOLD remains forbidden in this phase identity." in phase["overview"]["non_negotiables"]
    assert phase["structural_emphasis"]["typical_focus"] == (
        "Hard-late stability, preload, back-to-back resilience, and long-ride tolerance."
    )
    justification = normalized["data"]["justification"]["phase_justifications"][0]
    assert justification["intensity_distribution"] == (
        "Endurance-led work with controlled tempo and sweet spot support supporting durability-first build logic."
    )
    assert phase["allowed_forbidden_semantics"]["forbidden_intensity_domains"] == ["THRESHOLD", "VO2MAX"]

def test_normalize_final_season_plan_semantics_rewrites_positive_forbidden_vo2max_narrative() -> None:
    document = {
        "meta": {"artifact_type": "SEASON_PLAN"},
        "data": {
            "season_intent_principles": {"season_objective": "Strong 200 km A-event execution."},
            "phases": [
                {
                    "phase_id": "P02",
                    "phase_type": "BUILD",
                    "phase_intent": "specificity_build",
                    "build_subtype": "specificity_build",
                    "narrative": "Controlled VO2MAX support appears near the event.",
                    "weekly_load_corridor": {"weekly_kj": {"min": 9800, "max": 11200}},
                    "allowed_forbidden_semantics": {
                        "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
                        "allowed_load_modalities": ["NONE", "K3"],
                        "forbidden_intensity_domains": ["VO2MAX"],
                    },
                    "overview": {
                        "metabolic_focus": "VO2MAX-led specificity work.",
                        "expected_adaptations": ["VO2MAX maintenance near the event."],
                        "non_negotiables": ["VO2MAX remains secondary here."],
                    },
                    "structural_emphasis": {"typical_focus": "vo2max-led terrain rehearsal."},
                }
            ],
            "justification": {
                "phase_justifications": [
                    {
                        "phase_id": "P02",
                        "intensity_distribution": "controlled VO2MAX support under specificity pressure",
                        "overload_pattern": "Specificity logic.",
                        "kJ_first_statement": "P02 corridor.",
                        "citations": [],
                    }
                ]
            },
            "principles_scientific_foundation": {
                "principle_applications": [],
                "scientific_foundation": {"publications": []},
            },
            "assumptions_unknowns": {"revisit_items": []},
            "phase_transitions_guardrails": {"conservative_triggers": [], "absolute_no_go_rules": []},
        },
    }

    with guardrail_runtime_context(
        approved_planning_bundle={
            "phase_blueprints": [
                {
                    "phase_id": "P02",
                    "phase_type": "BUILD",
                    "phase_intent": "specificity_build",
                    "build_subtype": "specificity_build",
                    "allowed_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
                    "allowed_load_modalities": ["NONE", "K3"],
                    "forbidden_domains": ["VO2MAX"],
                }
            ]
        },
        season_phase_load_context={
            "season_allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
            "phases": [
                {
                    "phase_id": "P02",
                    "phase_type": "BUILD",
                    "phase_intent": "specificity_build",
                    "build_subtype": "specificity_build",
                    "role_week_load_bands": [],
                    "event_taper_trace": {},
                }
            ],
        },
    ):
        normalized = _normalize_final_season_plan_semantics(document)

    phase = normalized["data"]["phases"][0]
    assert phase["narrative"].startswith(
        "Event-near specificity build emphasizing pacing, fueling, terrain handling"
    )
    assert phase["overview"]["metabolic_focus"] == (
        "Event-near specificity through endurance-led work with controlled tempo, sweet spot, and threshold support."
    )
    assert phase["overview"]["expected_adaptations"] == [
        "Improved pacing, fueling, and terrain-specific execution through endurance-led work with controlled tempo, sweet spot, and threshold support."
    ]
    assert "VO2MAX remains forbidden in this phase identity." in phase["overview"]["non_negotiables"]
    assert phase["structural_emphasis"]["typical_focus"] == (
        "Pacing, fueling, terrain handling, and logistics under event-near specificity."
    )
    justification = normalized["data"]["justification"]["phase_justifications"][0]
    assert justification["intensity_distribution"] == (
        "Endurance-led work with controlled tempo, sweet spot, and threshold support supporting event-near specificity."
    )
