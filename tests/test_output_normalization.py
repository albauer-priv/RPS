from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from rps.agents.output_normalization import (
    extract_planning_events_document,
    injection_mode_for_tasks,
    normalize_phase_guardrails_document,
    normalize_phase_guardrails_document_from_execution_context,
    normalize_phase_preview_document,
    normalize_phase_structure_document,
    normalize_phase_structure_document_from_execution_context,
    normalize_season_scenarios_document,
    normalize_workout_inline_loop_headers,
    normalize_workout_percent_ranges,
)
from rps.agents.tasks import AgentTask
from rps.crewai_runtime.models import PhasePreviewPayloadModel
from rps.planning.phase_authority import persisted_phase_weekly_kj_bands
from rps.workspace.schema_registry import SchemaRegistry, validate_or_raise


def test_normalize_phase_guardrails_recovery_rules_and_band_order() -> None:
    document = {
        "meta": {"artifact_type": "PHASE_GUARDRAILS"},
        "data": {
            "execution_non_negotiables": {"recovery_protection_rules": ["rest day", "sleep"]},
            "load_guardrails": {"weekly_kj_bands": [{"band": {"min": 8000, "max": 6200}}]},
        },
    }

    normalized = normalize_phase_guardrails_document(document)

    assert normalized["data"]["execution_non_negotiables"]["recovery_protection_rules"] == "rest day | sleep"
    assert normalized["data"]["load_guardrails"]["weekly_kj_bands"][0]["band"] == {"min": 6200.0, "max": 8000.0}


def test_normalize_phase_guardrails_projects_season_constraints() -> None:
    document = {
        "meta": {
            "artifact_type": "PHASE_GUARDRAILS",
            "trace_upstream": [
                {
                    "artifact": "SEASON_PLAN",
                    "version": "1.0",
                    "schema_version": "1.0",
                    "version_key": "2026-21__20260520_080000",
                    "run_id": "20260520_080000",
                },
                {
                    "artifact": "SEASON_SCENARIO_SELECTION",
                    "version": "1.0",
                    "schema_version": "1.1",
                    "version_key": "2026-21__20260520_075500",
                    "run_id": "20260520_075500",
                },
                {
                    "artifact": "SEASON_SCENARIOS",
                    "version": "1.0",
                    "schema_version": "1.0",
                    "version_key": "2026-21__20260520_075000",
                    "run_id": "20260520_075000",
                },
            ],
        },
        "data": {
            "phase_summary": {
                "non_negotiables": ["Exact phase range is 2026-21--2026-23."],
                "key_risks_warnings": ["Do not drift into threshold or VO2MAX work."],
            },
            "events_constraints": {"events": []},
            "execution_non_negotiables": {
                "recovery_protection_rules": "Respect locked rest days.",
            },
            "load_guardrails": {"weekly_kj_bands": []},
        },
    }
    season_plan = {
        "meta": {
            "artifact_type": "SEASON_PLAN",
            "version": "1.0",
            "schema_version": "1.0",
            "version_key": "2026-21__20260520_080000",
            "run_id": "ui_season_plan_2026W21_20260520T080000Z",
        },
        "data": {
            "global_constraints": {
                "availability_assumptions": [
                    "Weekly availability is bounded by min 10.5 h, typical 14.0 h, max 17.5 h.",
                    "Fixed rest days are Monday and Friday.",
                ],
                "risk_constraints": [
                    "Moderate fatigue accumulation may blunt one or two key weeks if recovery is underestimated.",
                ],
                "planned_event_windows": [
                    "2026-15 B Brevet 200 km Toelzer-Land-Runde",
                    "2026-05-16 (A)",
                ],
                "recovery_protection": {
                    "notes": [
                        "Respect the locked rest days as hard recovery boundaries.",
                        "Use the shortened phases to restore continuity before the full build.",
                    ]
                },
            }
        }
    }
    season_selection = {
        "meta": {
            "artifact_type": "SEASON_SCENARIO_SELECTION",
            "version": "1.0",
            "schema_version": "1.1",
            "version_key": "2026-21__20260520_075500",
            "run_id": "ui_season_scenario_selection_2026_21_20260520T075500Z",
        }
    }
    season_scenarios = {
        "meta": {
            "artifact_type": "SEASON_SCENARIOS",
            "version": "1.0",
            "schema_version": "1.0",
            "version_key": "2026-21__20260520_075000",
            "run_id": "ui_season_scenarios_2026_21_20260520T075000Z",
        }
    }

    normalized = normalize_phase_guardrails_document(
        document,
        season_plan_document=season_plan,
        season_scenario_selection_document=season_selection,
        season_scenarios_document=season_scenarios,
    )

    non_negotiables = normalized["data"]["phase_summary"]["non_negotiables"]
    assert "Weekly availability is bounded by min 10.5 h, typical 14.0 h, max 17.5 h." in non_negotiables
    assert "Fixed rest days are Monday and Friday." in non_negotiables
    assert "2026-15 B Brevet 200 km Toelzer-Land-Runde" in non_negotiables
    assert (
        "Moderate fatigue accumulation may blunt one or two key weeks if recovery is underestimated."
        in normalized["data"]["phase_summary"]["key_risks_warnings"]
    )
    recovery_rules = normalized["data"]["execution_non_negotiables"]["recovery_protection_rules"]
    assert "Respect locked rest days." in recovery_rules
    assert "Respect the locked rest days as hard recovery boundaries." in recovery_rules
    assert "Use the shortened phases to restore continuity before the full build." in recovery_rules
    assert normalized["data"]["events_constraints"]["events"] == [
        {
            "date": "2026-05-16",
            "week": "2026-20",
            "type": "A",
            "constraint": "Planned season event window preserved from season_plan: 2026-05-16 (A)",
        }
    ]
    assert normalized["meta"]["trace_upstream"] == [
        {
            "artifact": "SEASON_PLAN",
            "version": "1.0",
            "schema_version": "1.0",
            "version_key": "2026-21__20260520_080000",
            "run_id": "ui_season_plan_2026W21_20260520T080000Z",
        },
        {
            "artifact": "SEASON_SCENARIO_SELECTION",
            "version": "1.0",
            "schema_version": "1.1",
            "version_key": "2026-21__20260520_075500",
            "run_id": "ui_season_scenario_selection_2026_21_20260520T075500Z",
        },
        {
            "artifact": "SEASON_SCENARIOS",
            "version": "1.0",
            "schema_version": "1.0",
            "version_key": "2026-21__20260520_075000",
            "run_id": "ui_season_scenarios_2026_21_20260520T075000Z",
        },
    ]


def test_normalize_phase_guardrails_from_execution_context_prefers_exact_runtime_authority() -> None:
    document = {
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
    execution_context = {
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
    }

    normalized = normalize_phase_guardrails_document_from_execution_context(
        document,
        season_plan_document=season_plan,
        phase_execution_context=execution_context,
    )

    assert normalized["data"]["load_guardrails"]["weekly_kj_bands"] == persisted_phase_weekly_kj_bands(
        execution_context["phase_role_week_load_bands"]
    )
    assert normalized["data"]["load_guardrails"]["weekly_kj_bands"][0]["band"]["notes"] == (
        "role SHORTENED_RE_ENTRY; S5 deterministic band is 7893-10148; feasible band max is 10148"
    )
    assert normalized["data"]["phase_summary"]["primary_objective"] == execution_context["phase_primary_objective"]
    assert normalized["data"]["allowed_forbidden_semantics"]["allowed_intensity_domains"] == (
        execution_context["phase_allowed_intensity_domains"]
    )
    assert normalized["data"]["allowed_forbidden_semantics"]["forbidden_intensity_domains"] == (
        execution_context["phase_forbidden_intensity_domains"]
    )
    assert normalized["data"]["allowed_forbidden_semantics"]["allowed_load_modalities"] == (
        execution_context["phase_allowed_load_modalities"]
    )
    assert normalized["data"]["allowed_forbidden_semantics"]["quality_density"]["quality_intent"] == "Stabilization"
    assert normalized["data"]["inherited_scenario_contract"] == season_plan["data"]["selected_scenario_contract"]


def test_normalize_phase_guardrails_from_execution_context_requires_exact_bands() -> None:
    document = {
        "meta": {"artifact_type": "PHASE_GUARDRAILS"},
        "data": {"load_guardrails": {"weekly_kj_bands": []}},
    }

    try:
        normalize_phase_guardrails_document_from_execution_context(
            document,
            season_plan_document=None,
            phase_execution_context={"phase_role_week_load_bands": []},
        )
    except ValueError as exc:
        assert "phase_role_week_load_bands" in str(exc)
    else:
        raise AssertionError("Expected normalize_phase_guardrails_document_from_execution_context to fail.")


def test_persisted_phase_weekly_kj_bands_drop_role_and_materialize_deterministic_notes() -> None:
    serialized = persisted_phase_weekly_kj_bands(
        [
            {"week": "2026-24", "role": "SHORTENED_RE_ENTRY", "band": {"min": 7893, "max": 10148}},
            {"week": "2026-25", "role": "SHORTENED_CONSOLIDATION", "band": {"min": 11275, "max": 9020}},
        ]
    )

    assert serialized == [
        {
            "week": "2026-24",
            "band": {
                "min": 7893,
                "max": 10148,
                "notes": "role SHORTENED_RE_ENTRY; S5 deterministic band is 7893-10148; feasible band max is 10148",
            },
        },
        {
            "week": "2026-25",
            "band": {
                "min": 9020,
                "max": 11275,
                "notes": "role SHORTENED_CONSOLIDATION; S5 deterministic band is 9020-11275; feasible band max is 11275",
            },
        },
    ]


def test_normalize_phase_structure_projects_constraints_and_guardrails_source() -> None:
    document = {
        "meta": {
            "artifact_type": "PHASE_STRUCTURE",
            "trace_upstream": [
                {
                    "artifact": "SEASON_PLAN",
                    "version": "1.0",
                    "schema_version": "1.0",
                    "version_key": "2026-21__20260520_080000",
                    "run_id": "20260520_080000",
                },
                {
                    "artifact": "SEASON_SCENARIO_SELECTION",
                    "version": "1.0",
                    "schema_version": "1.1",
                    "version_key": "2026-21__20260520_075500",
                    "run_id": "20260520_075500",
                },
                {
                    "artifact": "SEASON_SCENARIOS",
                    "version": "1.0",
                    "schema_version": "1.0",
                    "version_key": "2026-21__20260520_075000",
                    "run_id": "20260520_075000",
                },
            ],
        },
        "data": {
            "upstream_intent": {
                "constraints": [
                    "Do not widen the phase beyond 2026-21--2026-23.",
                    "Weekly availability is bounded by min 10.5 h, typical 14.0 h, max 17.5 h.",
                    "Weekly availability is bounded by min 10.5 h, typical 14.0 h, max 17.5 h.",
                    "Moderate fatigue accumulation may blunt one or two key weeks if recovery is underestimated.",
                    "Respect the locked rest days as hard recovery boundaries.",
                    "2026-15 B Brevet 200 km Toelzer-Land-Runde",
                ],
            },
            "load_ranges": {"source": "Deterministic Load Capacity Context"},
        },
    }
    season_plan = {
        "meta": {
            "artifact_type": "SEASON_PLAN",
            "version": "1.0",
            "schema_version": "1.0",
            "version_key": "2026-21__20260520_080000",
            "run_id": "ui_season_plan_2026W21_20260520T080000Z",
        },
        "data": {
            "global_constraints": {
                "availability_assumptions": [
                    "Weekly availability is bounded by min 10.5 h, typical 14.0 h, max 17.5 h.",
                ],
                "risk_constraints": [
                    "Moderate fatigue accumulation may blunt one or two key weeks if recovery is underestimated.",
                ],
                "planned_event_windows": ["2026-15 B Brevet 200 km Toelzer-Land-Runde"],
                "recovery_protection": {
                    "notes": ["Respect the locked rest days as hard recovery boundaries."]
                },
            }
        }
    }
    season_selection = {
        "meta": {
            "artifact_type": "SEASON_SCENARIO_SELECTION",
            "version": "1.0",
            "schema_version": "1.1",
            "version_key": "2026-21__20260520_075500",
            "run_id": "ui_season_scenario_selection_2026_21_20260520T075500Z",
        }
    }
    season_scenarios = {
        "meta": {
            "artifact_type": "SEASON_SCENARIOS",
            "version": "1.0",
            "schema_version": "1.0",
            "version_key": "2026-21__20260520_075000",
            "run_id": "ui_season_scenarios_2026_21_20260520T075000Z",
        }
    }
    phase_guardrails = {
        "meta": {
            "artifact_type": "PHASE_GUARDRAILS",
            "version": "1.0",
            "schema_version": "1.0",
            "run_id": "plan_hub_phase_bundle",
        },
        "data": {
            "load_guardrails": {
                "weekly_kj_bands": [
                    {"week": "2026-21", "band": {"min": 7329, "max": 8372, "notes": "x"}}
                ]
            }
        },
    }

    normalized = normalize_phase_structure_document(
        document,
        season_plan_document=season_plan,
        season_scenario_selection_document=season_selection,
        season_scenarios_document=season_scenarios,
        phase_guardrails_document=phase_guardrails,
        phase_guardrails_version_key="2026-21--2026-23__20260520_094539",
    )

    assert normalized["data"]["upstream_intent"]["constraints"] == [
        "Weekly availability is bounded by min 10.5 h, typical 14.0 h, max 17.5 h.",
        "Moderate fatigue accumulation may blunt one or two key weeks if recovery is underestimated.",
        "Respect the locked rest days as hard recovery boundaries.",
        "Do not widen the phase beyond 2026-21--2026-23.",
        "2026-15 B Brevet 200 km Toelzer-Land-Runde",
    ]
    assert normalized["data"]["load_ranges"]["weekly_kj_bands"] == [
        {"week": "2026-21", "band": {"min": 7329, "max": 8372, "notes": "x"}}
    ]
    assert (
        normalized["data"]["load_ranges"]["source"]
        == "phase_guardrails_2026-21--2026-23__20260520_094539.json"
    )
    assert normalized["meta"]["trace_upstream"] == [
        {
            "artifact": "SEASON_PLAN",
            "version": "1.0",
            "schema_version": "1.0",
            "version_key": "2026-21__20260520_080000",
            "run_id": "ui_season_plan_2026W21_20260520T080000Z",
        },
        {
            "artifact": "SEASON_SCENARIO_SELECTION",
            "version": "1.0",
            "schema_version": "1.1",
            "version_key": "2026-21__20260520_075500",
            "run_id": "ui_season_scenario_selection_2026_21_20260520T075500Z",
        },
        {
            "artifact": "SEASON_SCENARIOS",
            "version": "1.0",
            "schema_version": "1.0",
            "version_key": "2026-21__20260520_075000",
            "run_id": "ui_season_scenarios_2026_21_20260520T075000Z",
        },
        {
            "artifact": "PHASE_GUARDRAILS",
            "version": "1.0",
            "schema_version": "1.0",
            "version_key": "2026-21--2026-23__20260520_094539",
            "run_id": "plan_hub_phase_bundle",
        },
    ]


def test_normalize_phase_structure_canonicalizes_paraphrased_constraints_by_known_fact_group() -> None:
    document = {
        "meta": {"artifact_type": "PHASE_STRUCTURE", "trace_upstream": []},
        "data": {
            "upstream_intent": {
                "constraints": [
                    "Weekday training has to fit into compact Tue-Thu windows, with longer work shifting to the weekend.",
                    "Weekday training must fit compact Tue-Thu windows, with longer work shifting to the weekend.",
                    "Indoor trainer access preserves continuity when weather or travel disrupts outdoor riding.",
                    "Indoor trainer access is available and may be used for continuity when weather or travel disrupt outdoor riding.",
                    "Business travel has previously caused missed sessions, so the scenario needs some resilience without becoming overly conservative.",
                    "Business travel has previously caused missed sessions, so the season should retain resilience without becoming overly conservative.",
                    "Monday and Friday are fixed no-ride days.",
                    "Fixed no-ride days are preserved across the season.",
                    "Do not escalate to VO2MAX; it is forbidden for this season.",
                    "Do not escalate to VO2MAX; it is forbidden for this season.",
                ]
            }
        },
    }
    season_plan = {
        "data": {
            "global_constraints": {
                "availability_assumptions": [
                    "Weekday training has to fit into compact Tue-Thu windows, with longer work shifting to the weekend.",
                    "Indoor trainer access preserves continuity when weather or travel disrupts outdoor riding.",
                    "Monday and Friday are fixed no-ride days.",
                ],
                "risk_constraints": [
                    "Business travel has previously caused missed sessions, so the scenario needs some resilience without becoming overly conservative.",
                ],
                "planned_event_windows": [],
                "recovery_protection": {"notes": []},
            }
        }
    }

    normalized = normalize_phase_structure_document(document, season_plan_document=season_plan)

    assert normalized["data"]["upstream_intent"]["constraints"] == [
        "Weekday training has to fit into compact Tue-Thu windows, with longer work shifting to the weekend.",
        "Indoor trainer access preserves continuity when weather or travel disrupts outdoor riding.",
        "Monday and Friday are fixed no-ride days.",
        "Business travel has previously caused missed sessions, so the scenario needs some resilience without becoming overly conservative.",
        "Do not escalate to VO2MAX; it is forbidden for this season.",
    ]


def test_normalize_phase_structure_preserves_exact_phase_legality() -> None:
    document = {
        "meta": {"artifact_type": "PHASE_STRUCTURE", "iso_week_range": "2026-24--2026-25"},
        "data": {
            "structural_phase_elements": {
                "allowed_day_roles": ["REST", "RECOVERY", "ENDURANCE", "QUALITY"],
                "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
                "allowed_load_modalities": ["NONE", "K3"],
            }
        },
    }
    season_plan = {
        "data": {
            "phases": [
                {
                    "iso_week_range": "2026-24--2026-25",
                    "allowed_forbidden_semantics": {
                        "allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
                        "allowed_load_modalities": ["NONE"],
                        "forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
                    }
                }
            ]
        }
    }

    normalized = normalize_phase_structure_document(document, season_plan_document=season_plan)

    assert normalized["data"]["structural_phase_elements"]["allowed_intensity_domains"] == [
        "RECOVERY",
        "ENDURANCE",
        "TEMPO",
        "SWEET_SPOT",
    ]
    assert "NONE" not in normalized["data"]["structural_phase_elements"]["allowed_intensity_domains"]


def test_normalize_phase_structure_from_execution_context_prefers_exact_runtime_authority() -> None:
    document = {
        "meta": {"artifact_type": "PHASE_STRUCTURE", "iso_week_range": "2026-24--2026-25"},
        "data": {
            "inherited_scenario_contract": {
                "selected_scenario_id": "B",
                "constraint_summary": ["Paraphrased constraint summary"],
            },
            "upstream_intent": {"primary_objective": "Wrong objective"},
            "structural_phase_elements": {
                "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
                "allowed_load_modalities": ["NONE", "K3"],
            },
            "execution_principles": {
                "load_intensity_handling": {"forbidden_intensity_domains": ["VO2MAX"]},
            },
            "load_ranges": {"source": "wrong.json"},
        },
    }
    phase_guardrails = {
        "data": {
            "load_guardrails": {
                "weekly_kj_bands": [
                    {"week": "2026-24", "band": {"min": 7200, "max": 8200}},
                    {"week": "2026-25", "band": {"min": 7300, "max": 8300}},
                ]
            }
        }
    }

    normalized = normalize_phase_structure_document_from_execution_context(
        document,
        phase_execution_context={
            "phase_type": "BASE",
            "phase_intent": "shortened_re_entry",
            "inherited_scenario_contract": {
                "selected_scenario_id": "B",
                "constraint_summary": [
                    "Indoor trainer availability supports continuity when travel or weather reduces outdoor options."
                ],
            },
            "phase_allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
            "phase_forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
            "phase_allowed_load_modalities": ["NONE"],
            "phase_primary_objective": "Rebuild load tolerance.",
        },
        phase_guardrails_document=phase_guardrails,
        phase_guardrails_version_key="2026-24--2026-25__20260608_090000",
        season_plan_document=None,
    )

    assert normalized["data"]["structural_phase_elements"]["allowed_intensity_domains"] == [
        "RECOVERY",
        "ENDURANCE",
        "TEMPO",
        "SWEET_SPOT",
    ]
    assert normalized["data"]["structural_phase_elements"]["allowed_load_modalities"] == ["NONE"]
    assert normalized["data"]["execution_principles"]["load_intensity_handling"][
        "forbidden_intensity_domains"
    ] == ["THRESHOLD", "VO2MAX"]
    assert normalized["data"]["upstream_intent"]["primary_objective"] == "Rebuild load tolerance."
    assert normalized["data"]["inherited_scenario_contract"]["constraint_summary"] == [
        "Indoor trainer availability supports continuity when travel or weather reduces outdoor options."
    ]
    assert (
        normalized["data"]["load_ranges"]["source"]
        == "phase_guardrails_2026-24--2026-25__20260608_090000.json"
    )
    assert normalized["data"]["execution_principles"]["load_intensity_handling"]["quality_intent"] == "Stabilization"


def test_normalize_phase_structure_from_execution_context_requires_inherited_contract() -> None:
    document = {
        "meta": {"artifact_type": "PHASE_STRUCTURE", "iso_week_range": "2026-24--2026-25"},
        "data": {"upstream_intent": {"primary_objective": "Wrong objective"}},
    }
    phase_guardrails = {
        "data": {
            "load_guardrails": {
                "weekly_kj_bands": [
                    {"week": "2026-24", "band": {"min": 7200, "max": 8200}},
                    {"week": "2026-25", "band": {"min": 7300, "max": 8300}},
                ]
            }
        }
    }

    try:
        normalize_phase_structure_document_from_execution_context(
            document,
            phase_execution_context={
                "phase_type": "BASE",
                "phase_intent": "shortened_re_entry",
                "phase_allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
                "phase_forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
                "phase_allowed_load_modalities": ["NONE"],
                "phase_primary_objective": "Rebuild load tolerance.",
            },
            phase_guardrails_document=phase_guardrails,
            phase_guardrails_version_key="2026-24--2026-25__20260608_090000",
            season_plan_document=None,
        )
    except ValueError as exc:
        assert "inherited_scenario_contract" in str(exc)
    else:
        raise AssertionError("Expected normalize_phase_structure_document_from_execution_context to fail.")


def test_normalize_phase_structure_prefers_execution_context_contract_over_guardrails_fallback() -> None:
    document = {
        "meta": {"artifact_type": "PHASE_STRUCTURE", "iso_week_range": "2026-24--2026-25"},
        "data": {
            "inherited_scenario_contract": {"selected_scenario_id": "A", "constraint_summary": ["candidate drift"]},
            "upstream_intent": {"primary_objective": "Wrong objective"},
        },
    }
    phase_guardrails = {
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
    }

    normalized = normalize_phase_structure_document(
        document,
        phase_execution_context={
            "inherited_scenario_contract": {
                "selected_scenario_id": "C",
                "constraint_summary": ["execution context authority"],
            }
        },
        phase_guardrails_document=phase_guardrails,
        phase_guardrails_version_key="2026-24--2026-25__20260608_090000",
        season_plan_document=None,
    )

    assert normalized["data"]["inherited_scenario_contract"] == {
        "selected_scenario_id": "C",
        "constraint_summary": ["execution context authority"],
    }


def test_normalize_phase_structure_falls_back_to_guardrails_contract_when_execution_context_missing() -> None:
    document = {
        "meta": {"artifact_type": "PHASE_STRUCTURE", "iso_week_range": "2026-24--2026-25"},
        "data": {
            "inherited_scenario_contract": {"selected_scenario_id": "A", "constraint_summary": ["candidate drift"]},
        },
    }
    phase_guardrails = {
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
    }

    normalized = normalize_phase_structure_document(
        document,
        phase_execution_context=None,
        phase_guardrails_document=phase_guardrails,
        phase_guardrails_version_key="2026-24--2026-25__20260608_090000",
        season_plan_document=None,
    )

    assert normalized["data"]["inherited_scenario_contract"] == {
        "selected_scenario_id": "B",
        "constraint_summary": ["guardrails fallback"],
    }


def test_normalize_phase_preview_repairs_traceability_rest_days_and_quality_cap() -> None:
    document = {
        "meta": {"artifact_type": "PHASE_PREVIEW", "authority": "Binding"},
        "data": {
            "traceability": {"derived_from": ["Season plan version 2026-21__20260520_084154"]},
            "weekly_agenda_preview": [
                {
                    "week": "2026-22",
                    "days": [
                        {"day_of_week": "Mon", "day_role": "REST", "intensity_domain": "TEMPO", "load_modality": "K3", "notes": "wrong"},
                        {"day_of_week": "Tue", "day_role": "QUALITY", "intensity_domain": "ENDURANCE", "load_modality": "NONE", "notes": "ok"},
                        {"day_of_week": "Wed", "day_role": "QUALITY", "intensity_domain": "TEMPO", "load_modality": "NONE", "notes": "ok"},
                        {"day_of_week": "Thu", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE", "notes": "ok"},
                        {"day_of_week": "Fri", "day_role": "REST", "intensity_domain": "SWEET_SPOT", "load_modality": "K3", "notes": "wrong"},
                        {"day_of_week": "Sat", "day_role": "QUALITY", "intensity_domain": "SWEET_SPOT", "load_modality": "NONE", "notes": "excess"},
                        {"day_of_week": "Sun", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE", "notes": "ok"},
                    ],
                }
            ],
        },
    }
    phase_structure = {
        "meta": {
            "artifact_type": "PHASE_STRUCTURE",
            "version": "1.0",
            "schema_version": "1.0",
            "run_id": "phase_structure_run",
        },
        "data": {
            "structural_phase_elements": {
                "allowed_day_roles": ["REST", "RECOVERY", "ENDURANCE", "QUALITY"],
                "allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
                "allowed_load_modalities": ["NONE"],
            },
            "execution_principles": {
                "load_intensity_handling": {"max_quality_days_per_week": 2},
                "recovery_protection": {"fixed_non_training_days": ["Mon", "Fri"]},
            },
        }
    }

    normalized = normalize_phase_preview_document(
        document,
        phase_structure_document=phase_structure,
        phase_structure_version_key="2026-21--2026-23__20260520_112942",
    )

    assert (
        "phase_structure_2026-21--2026-23__20260520_112942.json"
        in normalized["data"]["traceability"]["derived_from"]
    )
    assert normalized["meta"]["authority"] == "Informational"
    assert normalized["meta"]["trace_upstream"][0]["artifact"] == "PHASE_STRUCTURE"
    assert normalized["meta"]["trace_upstream"][0]["version_key"] == "2026-21--2026-23__20260520_112942"
    days = normalized["data"]["weekly_agenda_preview"][0]["days"]
    assert days[0]["intensity_domain"] == "NONE"
    assert days[0]["load_modality"] == "NONE"
    assert days[4]["intensity_domain"] == "NONE"
    assert days[4]["load_modality"] == "NONE"
    assert days[5]["day_role"] == "ENDURANCE"
    assert days[5]["intensity_domain"] == "ENDURANCE"
    assert (
        normalized["data"]["week_to_week_narrative"]["what_will_not_change"]
        == "The preview reflects the current phase-derived skeleton: fixed rest days, recovery semantics, and allowed day-role/domain shape stay aligned unless an explicit replan changes upstream phase authority."
    )
    assert "Week planning may add concrete workout detail" in normalized["data"]["week_to_week_narrative"]["what_is_flexible"]
    assert "inherited_scenario_contract" not in normalized["data"]


def test_normalize_phase_preview_backfills_blank_week_keys_from_shared_skeleton() -> None:
    document = {
        "meta": {"artifact_type": "PHASE_PREVIEW", "authority": "Informational", "iso_week_range": "2026-24--2026-25"},
        "data": {
            "traceability": {"derived_from": ["phase_structure_2026-24--2026-25__20260609_070455.json"]},
            "phase_intent_summary": {"phase_intent": "shortened_re_entry"},
            "weekly_agenda_preview": [
                {
                    "week": "",
                    "days": [
                        {"day_of_week": "Mon", "day_role": "REST", "intensity_domain": "NONE", "load_modality": "NONE"},
                        {"day_of_week": "Tue", "day_role": "QUALITY", "intensity_domain": "TEMPO", "load_modality": "NONE"},
                        {"day_of_week": "Wed", "day_role": "RECOVERY", "intensity_domain": "RECOVERY", "load_modality": "NONE"},
                        {"day_of_week": "Thu", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE"},
                        {"day_of_week": "Fri", "day_role": "REST", "intensity_domain": "NONE", "load_modality": "NONE"},
                        {"day_of_week": "Sat", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE"},
                        {"day_of_week": "Sun", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE"},
                    ],
                },
                {
                    "week": "   ",
                    "days": [
                        {"day_of_week": "Mon", "day_role": "REST", "intensity_domain": "NONE", "load_modality": "NONE"},
                        {"day_of_week": "Tue", "day_role": "QUALITY", "intensity_domain": "TEMPO", "load_modality": "NONE"},
                        {"day_of_week": "Wed", "day_role": "RECOVERY", "intensity_domain": "RECOVERY", "load_modality": "NONE"},
                        {"day_of_week": "Thu", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE"},
                        {"day_of_week": "Fri", "day_role": "REST", "intensity_domain": "NONE", "load_modality": "NONE"},
                        {"day_of_week": "Sat", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE"},
                        {"day_of_week": "Sun", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE"},
                    ],
                },
            ],
        },
    }
    phase_structure = {
        "meta": {
            "artifact_type": "PHASE_STRUCTURE",
            "version": "1.0",
            "schema_version": "1.0",
            "run_id": "phase_structure_run",
        },
        "data": {
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
                        {"week": "2026-24", "role": "SHORTENED_RE_ENTRY"},
                        {"week": "2026-25", "role": "SHORTENED_CONSOLIDATION"},
                    ]
                }
            },
            "upstream_intent": {
                "phase_intent": "shortened_re_entry",
                "primary_objective": "Rebuild load tolerance.",
            },
        },
    }

    normalized = normalize_phase_preview_document(
        document,
        phase_structure_document=phase_structure,
        phase_structure_version_key="2026-24--2026-25__20260609_070455",
    )

    assert [week["week"] for week in normalized["data"]["weekly_agenda_preview"]] == ["2026-24", "2026-25"]


def test_normalize_phase_preview_rejects_week_count_mismatch_vs_shared_skeleton() -> None:
    document = {
        "meta": {"artifact_type": "PHASE_PREVIEW", "authority": "Informational", "iso_week_range": "2026-24--2026-25"},
        "data": {
            "traceability": {"derived_from": ["phase_structure_2026-24--2026-25__20260609_070455.json"]},
            "weekly_agenda_preview": [
                {"week": "", "days": []},
            ],
        },
    }
    phase_structure = {
        "meta": {
            "artifact_type": "PHASE_STRUCTURE",
            "version": "1.0",
            "schema_version": "1.0",
            "run_id": "phase_structure_run",
        },
        "data": {
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
                        {"week": "2026-24", "role": "SHORTENED_RE_ENTRY"},
                        {"week": "2026-25", "role": "SHORTENED_CONSOLIDATION"},
                    ]
                }
            },
            "upstream_intent": {"phase_intent": "shortened_re_entry"},
        },
    }

    with pytest.raises(ValueError, match="weekly_agenda_preview must match exact shared skeleton week coverage"):
        normalize_phase_preview_document(
            document,
            phase_structure_document=phase_structure,
            phase_structure_version_key="2026-24--2026-25__20260609_070455",
        )


def test_normalize_phase_structure_replaces_synthetic_guardrails_trace_run_id() -> None:
    document = {
        "meta": {
            "artifact_type": "PHASE_STRUCTURE",
            "trace_upstream": [
                {
                    "artifact": "PHASE_GUARDRAILS",
                    "version": "1.0",
                    "schema_version": "1.0",
                    "version_key": "2026-24--2026-25__20260609_160308",
                    "run_id": "run_20260609_155823",
                }
            ],
        },
        "data": {},
    }
    phase_guardrails = {
        "meta": {
            "artifact_type": "PHASE_GUARDRAILS",
            "version": "1.0",
            "schema_version": "1.0",
            "version_key": "2026-24--2026-25__20260609_160308",
            "run_id": "plan_hub_phase_2026W24_20260609_155818_phase_bundle",
        },
        "data": {
            "load_guardrails": {
                "weekly_kj_bands": [
                    {"week": "2026-24", "band": {"min": 7893, "max": 10148, "notes": "x"}}
                ]
            }
        },
    }

    normalized = normalize_phase_structure_document(
        document,
        phase_guardrails_document=phase_guardrails,
        phase_guardrails_version_key="2026-24--2026-25__20260609_160308",
    )

    assert normalized["meta"]["trace_upstream"] == [
        {
            "artifact": "PHASE_GUARDRAILS",
            "version": "1.0",
            "schema_version": "1.0",
            "version_key": "2026-24--2026-25__20260609_160308",
            "run_id": "plan_hub_phase_2026W24_20260609_155818_phase_bundle",
        }
    ]


def test_normalize_phase_preview_replaces_duplicate_trace_entries_with_canonical_structure_ref() -> None:
    document = {
        "meta": {
            "artifact_type": "PHASE_PREVIEW",
            "trace_upstream": [
                {
                    "artifact": "PHASE_STRUCTURE",
                    "version": "1.0",
                    "schema_version": "1.0",
                    "version_key": "2026-24--2026-25__20260609_070455.json",
                    "run_id": "runtime-owned",
                },
                {
                    "artifact": "SEASON_PLAN",
                    "version": "1.0",
                    "schema_version": "1.0",
                    "version_key": "2026-24__20260608_160322",
                    "run_id": "runtime-owned",
                },
            ],
        },
        "data": {
            "weekly_agenda_preview": [{"week": "2026-24", "days": []}],
        },
    }
    phase_structure = {
        "meta": {
            "artifact_type": "PHASE_STRUCTURE",
            "version": "1.0",
            "schema_version": "1.0",
            "run_id": "plan_hub_phase_2026W24_20260609_070024_phase_bundle",
        },
        "data": {
            "structural_phase_elements": {
                "allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
                "allowed_load_modalities": ["NONE"],
            },
            "execution_principles": {
                "load_intensity_handling": {"max_quality_days_per_week": 1},
                "recovery_protection": {"fixed_non_training_days": ["Mon", "Fri"]},
            },
            "week_skeleton_logic": {"week_roles": {"week_roles": [{"week": "2026-24", "role": "SHORTENED_RE_ENTRY"}]}},
            "upstream_intent": {"phase_intent": "shortened_re_entry"},
        },
    }

    normalized = normalize_phase_preview_document(
        document,
        phase_structure_document=phase_structure,
        phase_structure_version_key="2026-24--2026-25__20260609_070455",
    )

    assert normalized["meta"]["trace_upstream"] == [
        {
            "artifact": "PHASE_STRUCTURE",
            "version": "1.0",
            "schema_version": "1.0",
            "version_key": "2026-24--2026-25__20260609_070455",
            "run_id": "plan_hub_phase_2026W24_20260609_070024_phase_bundle",
        }
    ]


def test_phase_preview_payload_model_accepts_structured_weekly_agenda_preview() -> None:
    model = PhasePreviewPayloadModel(
        phase_intent_summary={"phase_intent": "shortened_re_entry", "primary_objective": "Rebuild load tolerance."},
        feel_overview={"dominant_theme": "Calm re-entry"},
        weekly_agenda_preview=[
            {
                "week": "2026-24",
                "days": [
                    {
                        "day_of_week": "Mon",
                        "day_role": "REST",
                        "intensity_domain": "NONE",
                        "load_modality": "NONE",
                        "notes": "Fixed rest",
                    }
                ],
            }
        ],
        week_to_week_narrative={
            "what_will_not_change": "Fixed rest and allowed domain shape stay aligned.",
            "what_is_flexible": "Week planning may add concrete workout detail.",
        },
        deviation_rules=["rule"],
    )

    assert model.weekly_agenda_preview[0].week == "2026-24"
    assert model.weekly_agenda_preview[0].days[0].day_role == "REST"
    assert model.phase_intent_summary.phase_intent == "shortened_re_entry"
    assert model.feel_overview.dominant_theme == "Calm re-entry"
    assert "Week planning may add concrete workout detail." == model.week_to_week_narrative.what_is_flexible


def test_phase_preview_payload_model_rejects_legacy_list_shape() -> None:
    with pytest.raises(ValidationError):
        PhasePreviewPayloadModel(
            phase_intent_summary=["summary"],
            feel_overview=["feel"],
            week_to_week_narrative=["narrative"],
        )


def test_extract_planning_events_document_parses_workspace_payload() -> None:
    payload = {"ok": True, "content": '{"data":{"events":[{"type":"A","date":"2026-05-10"}]}}'}
    parsed = extract_planning_events_document(payload)
    assert parsed == {"data": {"events": [{"type": "A", "date": "2026-05-10"}]}}


def test_normalize_season_scenarios_derives_horizon_from_events() -> None:
    document = {
        "meta": {"artifact_type": "SEASON_SCENARIOS", "iso_week": "2026-19", "trace_events": [], "trace_data": []},
        "data": {
            "planning_horizon_weeks": 1,
            "scenarios": [
                {
                    "scenario_id": "S1",
                    "scenario_guidance": {"deload_cadence": "3:1", "intensity_guidance": {"allowed_domains": ["ENDURANCE"], "avoid_domains": ["NONE", "THRESHOLD"]}},
                }
            ],
        },
    }
    events = {"data": {"events": [{"type": "A", "date": "2026-06-14"}]}}

    normalized = normalize_season_scenarios_document(document, planning_events_document=events)

    assert normalized["meta"]["iso_week_range"] == "2026-19--2026-24"
    assert normalized["data"]["planning_horizon_weeks"] == 6
    guidance = normalized["data"]["scenarios"][0]["scenario_guidance"]
    assert guidance["intensity_guidance"]["allowed_domains"] == ["ENDURANCE"]
    assert guidance["intensity_guidance"]["avoid_domains"] == ["THRESHOLD"]


def test_normalize_season_scenarios_repairs_agent_payload_for_schema() -> None:
    def _scenario(scenario_id: str, cadence: str) -> dict[str, object]:
        return {
            "scenario_id": scenario_id,
            "name": f"Scenario {scenario_id}",
            "core_idea": "Build durable readiness.",
            "load_philosophy": "Progress conservatively.",
            "risk_profile": "Moderate risk.",
            "key_differences": ["Uses deterministic cadence math.", "Keeps recovery explicit."],
            "best_suited_if": "The athlete wants reliable completion.",
            "typical_week_feel": "Structured but manageable.",
            "main_payoff": "More reliable execution.",
            "main_cost": "Less upside than the riskiest option.",
            "what_gets_prioritized": "Consistency and durability.",
            "what_gets_de_emphasized": "Unnecessary high-intensity escalation.",
            "scenario_guidance": {
                "recovery_margin": "medium",
                "fatigue_exposure": "moderate",
                "specificity_density": "controlled",
                "deload_cadence": cadence,
                "phase_length_weeks": 99,
                "event_alignment_notes": "Aligns to the target event.",
                "risk_flags": ["Watch cumulative fatigue."],
                "fixed_rest_days": ["Mon", "Fri"],
                "constraint_summary": ["Respect fixed rest days."],
                "kpi_guardrail_notes": ["Stay in sustainable endurance bands."],
                "decision_notes": ["Use as default if risk control matters."],
                "intensity_guidance": {
                    "allowed_domains": ["ENDURANCE", "TEMPO"],
                    "avoid_domains": ["NONE", "THRESHOLD"],
                },
                "assumptions": ["Availability is stable."],
                "unknowns": ["Late travel unknown."],
            },
        }

    document = {
        "meta": {
            "artifact_type": "SEASON_SCENARIOS",
            "schema_id": "Wrong",
            "schema_version": "2026-20",
            "version": "2026-20_A01",
            "version_key": "2026-20__20260517_160725",
            "authority": "Binding",
            "owner_agent": "Season-Planner",
            "run_id": "season_scenarios_2026-20_A01",
            "created_at": "2026-05-17T16:07:25Z",
            "scope": "Athlete: i150546",
            "iso_week": "2026-20",
            "iso_week_range": "2026-20--2026-37",
            "temporal_scope": {"from": "2026-05-11", "to": "2026-09-13"},
            "trace_upstream": [
                "athlete_profile.ui_athlete_profile_20260315T091949Z",
                "planning_events.ui_planning_events_20260504T094650Z",
                "athlete_state_snapshot_2026-20__20260517_160725.json",
            ],
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "UNKNOWN",
            "notes": [],
        },
        "data": {
            "kpi_profile_ref": "kpi_profile.latest",
            "athlete_profile_ref": "athlete_profile.ui_athlete_profile_20260315T091949Z",
            "planning_horizon_weeks": 18,
            "notes": "Agent emitted a scalar note.",
            "scenarios": [_scenario("A", "2:1"), _scenario("B", "3:1"), _scenario("C", "2:1:1")],
        },
    }

    normalized = normalize_season_scenarios_document(document)

    assert normalized["meta"]["version"] == "1.0"
    assert normalized["meta"]["scope"] == "Season"
    assert normalized["meta"]["schema_id"] == "SeasonScenariosInterface"
    assert normalized["meta"]["schema_version"] == "1.0"
    assert normalized["meta"]["authority"] == "Informational"
    assert normalized["meta"]["owner_agent"] == "Season-Scenario-Agent"
    assert all(isinstance(entry, dict) for entry in normalized["meta"]["trace_upstream"])
    assert isinstance(normalized["data"]["notes"], list)
    assert all(isinstance(scenario["key_differences"], str) for scenario in normalized["data"]["scenarios"])
    assert all(isinstance(scenario["typical_week_feel"], str) for scenario in normalized["data"]["scenarios"])
    assert all(isinstance(scenario["main_payoff"], str) for scenario in normalized["data"]["scenarios"])

    registry = SchemaRegistry(Path("specs/schemas"))
    validate_or_raise(registry.validator_for("season_scenarios.schema.json"), normalized)


def test_injection_mode_for_tasks_is_single_mode_only() -> None:
    assert injection_mode_for_tasks([AgentTask.CREATE_PHASE_GUARDRAILS]) == "phase_guardrails"
    assert injection_mode_for_tasks([AgentTask.CREATE_PHASE_GUARDRAILS, AgentTask.CREATE_WEEK_PLAN]) is None


def test_normalize_workout_percent_ranges_repairs_missing_middle_percent() -> None:
    assert normalize_workout_percent_ranges("- 3h44m 68-72% 85-90rpm") == "- 3h44m 68%-72% 85-90rpm"


def test_normalize_workout_inline_loop_headers_splits_inline_repeat_step() -> None:
    assert normalize_workout_inline_loop_headers("- 3x 12m 80%-84% 88-94rpm") == "3x\n- 12m 80%-84% 88-94rpm"


def test_normalize_workout_inline_loop_headers_preserves_non_loop_step() -> None:
    text = "- 12m 80%-84% 88-94rpm"
    assert normalize_workout_inline_loop_headers(text) == text
