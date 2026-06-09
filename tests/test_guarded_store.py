from pathlib import Path

import pytest

from rps.planning.deterministic_context import build_load_capacity_block
from rps.workspace.guarded_store import GuardedValidatedStore
from rps.workspace.iso_helpers import parse_iso_week, parse_iso_week_range
from rps.workspace.schema_registry import SchemaRegistry, SchemaValidationError, validate_or_raise
from rps.workspace.season_plan_service import resolve_season_plan_phase_info
from rps.workspace.types import ArtifactType


def _store(tmp_path):
    return GuardedValidatedStore(
        athlete_id="test_athlete",
        schema_dir=tmp_path,
        workspace_root=tmp_path,
    )


def _full_selected_scenario_contract() -> dict[str, object]:
    return {
        "selected_scenario_id": "B",
        "scenario_name": "Balanced build, controlled pressure",
        "selection_source": "user",
        "selection_rationale": "",
        "load_posture": "Moderate-to-progressive load with planned resets.",
        "recovery_margin": "Moderate recovery margin.",
        "fatigue_exposure": "Moderate fatigue exposure.",
        "specificity_density": "Moderate-to-high specificity density.",
        "load_philosophy": "Moderate-to-progressive load with planned resets.",
        "risk_profile": "Moderate risk option.",
        "best_suited_if": "Stable recovery supports systematic progression.",
        "key_differences": "More progression than A, more control than C.",
        "main_payoff": "Best balance of adaptation and control.",
        "main_cost": "More accumulated fatigue than A.",
        "constraint_summary": [
            "Fixed rest days are Monday and Friday.",
            "Weekly availability is typical 14.0 h."
        ],
        "event_alignment_notes": [
            "Matches the horizon well.",
            "B events remain rehearsal markers."
        ],
        "risk_flags": [
            "Becomes less forgiving if continuity breaks.",
            "Can under-deliver if resets are ignored."
        ],
        "kpi_guardrail_notes": [
            "Keep progression inside KPI limits."
        ],
        "decision_notes": [
            "This is the middle path."
        ],
        "season_archetype": "none",
        "allowed_intensity_domains": [
            "NONE",
            "RECOVERY",
            "ENDURANCE",
            "TEMPO",
            "SWEET_SPOT",
            "THRESHOLD",
            "VO2MAX",
        ],
        "forbidden_intensity_domains": [],
        "deload_cadence": "2:1:1",
        "phase_length_weeks": 4,
        "phase_count_expected": 4,
        "full_phases": 4,
        "shortened_phases": [],
        "max_shortened_phases": 0,
        "shortening_budget_weeks": 0,
    }


def _schema_registry() -> SchemaRegistry:
    return SchemaRegistry(Path("specs/schemas"))


def test_season_contract_contexts_build_selected_structure_from_latest_payloads(tmp_path):
    store = _store(tmp_path)
    season_plan = {"meta": {"iso_week": "2026-21"}}
    scenarios_payload = {
        "data": {
            "planning_horizon_weeks": 17,
            "scenarios": [
                {
                    "scenario_id": "C",
                    "name": "Selected scenario",
                    "scenario_guidance": {
                        "deload_cadence": "3:1",
                        "phase_length_weeks": 4,
                        "phase_count_expected": 5,
                        "phase_plan_summary": {
                            "full_phases": 3,
                            "shortened_phases": [{"len": 3, "count": 1}, {"len": 2, "count": 1}],
                        },
                    },
                }
            ],
        }
    }
    selection_payload = {"data": {"selected_scenario_id": "C"}}

    def _load_latest_optional(artifact_type):
        if artifact_type == ArtifactType.SEASON_SCENARIOS:
            return scenarios_payload
        if artifact_type == ArtifactType.SEASON_SCENARIO_SELECTION:
            return selection_payload
        return {}

    store._load_latest_optional = _load_latest_optional

    phase_slots, _phase_load = store._season_contract_contexts(season_plan)

    assert phase_slots["selected_scenario_id"] == "C"
    assert phase_slots["phase_slots"]
    assert phase_slots["phase_slots"][0]["phase_id"] == "P01"


def test_phase_guardrails_event_window_matches_structured_events(tmp_path):
    store = _store(tmp_path)
    season_plan = {
        "data": {
            "global_constraints": {
                "availability_assumptions": [],
                "risk_constraints": [],
                "planned_event_windows": ["2026-04-11 (B)", "2026-05-16 (A)"],
                "recovery_protection": {"fixed_rest_days": ["Mon"], "notes": "Protect Mon rest day."},
            }
        }
    }
    document = {
        "data": {
            "phase_summary": {
                "non_negotiables": ["Protect Mon rest day."],
                "key_risks_warnings": [],
            },
            "events_constraints": {
                "events": [
                    {"date": "2026-04-11", "week": "2026-15", "type": "B", "constraint": "B event"},
                    {"date": "2026-05-16", "week": "2026-20", "type": "A", "constraint": "A event"},
                ]
            },
            "execution_non_negotiables": {
                "recovery_protection_rules": "Protect Mon rest day.",
            },
        }
    }

    store._enforce_phase_guardrails_constraints(document, season_plan)


def test_phase_guardrails_accepts_free_text_event_window_markers(tmp_path):
    store = _store(tmp_path)
    season_plan = {
        "data": {
            "global_constraints": {
                "availability_assumptions": [],
                "risk_constraints": [],
                "planned_event_windows": [
                    "2026-04-25 B event rehearsal window",
                    "2026-05-16 A event peak window",
                ],
                "recovery_protection": {"fixed_rest_days": [], "notes": []},
            }
        }
    }
    document = {
        "data": {
            "phase_summary": {"non_negotiables": [], "key_risks_warnings": []},
            "events_constraints": {
                "events": [
                    {"date": "2026-04-25", "week": "2026-17", "type": "B", "constraint": "B event"},
                    {"date": "2026-05-16", "week": "2026-20", "type": "A", "constraint": "A event"},
                ]
            },
            "execution_non_negotiables": {"recovery_protection_rules": ""},
        }
    }

    store._enforce_phase_guardrails_constraints(document, season_plan)


def test_phase_guardrails_matches_structured_assumptions_and_risks(tmp_path):
    store = _store(tmp_path)
    season_plan = {
        "data": {
            "global_constraints": {
                "availability_assumptions": ["Fixed rest days Mon and Fri."],
                "risk_constraints": ["Travel disruption may reduce execution quality."],
                "planned_event_windows": [],
                "recovery_protection": {"fixed_rest_days": ["Mon", "Fri"], "notes": "Protect recovery anchors."},
            }
        }
    }
    document = {
        "data": {
            "phase_summary": {
                "non_negotiables": ["Fixed rest days Mon and Fri."],
                "key_risks_warnings": ["Travel disruption may reduce execution quality."],
            },
            "events_constraints": {"events": []},
            "execution_non_negotiables": {
                "recovery_protection_rules": "Protect recovery anchors.",
            },
        }
    }

    store._enforce_phase_guardrails_constraints(document, season_plan)


def test_phase_guardrails_accepts_recovery_notes_string(tmp_path):
    store = _store(tmp_path)
    season_plan = {
        "data": {
            "global_constraints": {
                "availability_assumptions": [],
                "risk_constraints": [],
                "planned_event_windows": [],
                "recovery_protection": {"fixed_rest_days": [], "notes": "Single recovery note."},
            }
        }
    }
    document = {
        "data": {
            "execution_non_negotiables": {
                "recovery_protection_rules": "Single recovery note.",
            },
            "events_constraints": {"events": []},
        }
    }

    store._enforce_phase_guardrails_constraints(document, season_plan)


def test_phase_guardrails_rejects_band_above_explicit_feasible_max(tmp_path):
    store = _store(tmp_path)
    season_plan = {
        "data": {
            "global_constraints": {
                "availability_assumptions": [],
                "risk_constraints": [],
                "planned_event_windows": [],
                "recovery_protection": {"fixed_rest_days": [], "notes": []},
            }
        }
    }
    document = {
        "data": {
            "phase_summary": {"non_negotiables": [], "key_risks_warnings": []},
            "events_constraints": {"events": []},
            "execution_non_negotiables": {"recovery_protection_rules": ""},
            "load_guardrails": {
                "weekly_kj_bands": [
                    {
                        "week": "2026-17",
                        "band": {
                            "min": 9000,
                            "max": 10600,
                            "notes": "Execution impossible because feasible max is 8470 planned_Load_kJ/week.",
                        },
                    }
                ]
            },
        }
    }

    with pytest.raises(SchemaValidationError) as exc:
        store._enforce_phase_guardrails_constraints(document, season_plan)

    assert any("explicit feasible max 8470" in err for err in exc.value.errors)


def test_phase_structure_event_window_matches_semantically(tmp_path):
    store = _store(tmp_path)
    season_plan = {
        "data": {
            "global_constraints": {
                "availability_assumptions": [],
                "risk_constraints": [],
                "planned_event_windows": ["2026-04-11 (B)"],
                "recovery_protection": {"fixed_rest_days": [], "notes": []},
            }
        }
    }
    document = {
        "meta": {"iso_week_range": "2026-14--2026-16"},
        "data": {
            "upstream_intent": {
                "constraints": [
                    "Planned event 2026-04-11 with type B must be preserved.",
                ]
            },
            "execution_principles": {"recovery_protection": {"fixed_non_training_days": []}},
            "load_ranges": {
                "weekly_kj_bands": [],
                "source": "phase_guardrails_2026-14--2026-16.json",
            },
        },
    }

    store._load_phase_guardrails_for_range = lambda _expected: (
        {
            "data": {
                "load_guardrails": {
                    "weekly_kj_bands": [],
                }
            }
        },
        "2026-14--2026-16",
    )

    store._enforce_phase_structure_constraints(document, season_plan)


def test_phase_structure_accepts_free_text_event_window_markers(tmp_path):
    store = _store(tmp_path)
    season_plan = {
        "data": {
            "global_constraints": {
                "availability_assumptions": [],
                "risk_constraints": [],
                "planned_event_windows": ["2026-04-25 B event rehearsal window"],
                "recovery_protection": {"fixed_rest_days": [], "notes": []},
            }
        }
    }
    document = {
        "meta": {"iso_week_range": "2026-17--2026-19"},
        "data": {
            "upstream_intent": {
                "constraints": [
                    "Preserve the planned event on 2026-04-25 with type B as a controlled rehearsal.",
                ]
            },
            "execution_principles": {"recovery_protection": {"fixed_non_training_days": []}},
            "load_ranges": {
                "weekly_kj_bands": [],
                "source": "phase_guardrails_2026-17--2026-19.json",
            },
        },
    }

    store._load_phase_guardrails_for_range = lambda _expected: (
        {
            "data": {
                "load_guardrails": {
                    "weekly_kj_bands": [],
                }
            }
        },
        "2026-17--2026-19",
    )

    store._enforce_phase_structure_constraints(document, season_plan)


def test_phase_structure_matches_constraints_as_list_items(tmp_path):
    store = _store(tmp_path)
    season_plan = {
        "data": {
            "global_constraints": {
                "availability_assumptions": ["Fixed rest days Mon and Fri."],
                "risk_constraints": ["Travel disruption may reduce execution quality."],
                "planned_event_windows": [],
                "recovery_protection": {"fixed_rest_days": ["Mon", "Fri"], "notes": ["Protect recovery anchors."]},
            }
        }
    }
    document = {
        "meta": {"iso_week_range": "2026-14--2026-16"},
        "data": {
            "upstream_intent": {
                "constraints": [
                    "Fixed rest days Mon and Fri.",
                    "Travel disruption may reduce execution quality.",
                    "Protect recovery anchors.",
                ]
            },
            "execution_principles": {
                "recovery_protection": {"fixed_non_training_days": ["Fri", "Mon"]},
            },
            "load_ranges": {
                "weekly_kj_bands": [],
                "source": "phase_guardrails_2026-14--2026-16.json",
            },
        },
    }

    store._load_phase_guardrails_for_range = lambda _expected: (
        {
            "data": {
                "load_guardrails": {
                    "weekly_kj_bands": [],
                }
            }
        },
        "2026-14--2026-16",
    )

    store._enforce_phase_structure_constraints(document, season_plan)


def test_phase_structure_is_repaired_from_season_and_guardrails_before_validation(tmp_path):
    store = _store(tmp_path)
    season_plan = {
        "data": {
            "global_constraints": {
                "availability_assumptions": ["Fixed rest days Mon and Fri."],
                "risk_constraints": ["Travel disruption may reduce execution quality."],
                "planned_event_windows": ["2026-04-25 B event rehearsal window"],
                "recovery_protection": {
                    "fixed_rest_days": ["Mon", "Fri"],
                    "notes": ["Protect recovery anchors."],
                },
            }
        }
    }
    document = {
        "meta": {"iso_week_range": "2026-17--2026-19"},
        "data": {
            "upstream_intent": {"constraints": ["Do not widen the phase beyond 2026-17--2026-19."]},
            "execution_principles": {
                "recovery_protection": {"fixed_non_training_days": ["Mon", "Fri"]},
            },
            "load_ranges": {
                "weekly_kj_bands": [],
                "source": "Deterministic Load Capacity Context",
            },
        },
    }

    store._load_phase_guardrails_for_range = lambda _expected: (
        {
            "data": {
                "load_guardrails": {
                    "weekly_kj_bands": [
                        {
                            "week": "2026-17",
                            "band": {"min": 7000, "max": 8200, "notes": "Band"},
                        }
                    ],
                }
            }
        },
        "2026-17--2026-19__20260520_094539",
    )

    store._enforce_phase_structure_constraints(document, season_plan)
    assert document["data"]["load_ranges"]["source"] == "phase_guardrails_2026-17--2026-19__20260520_094539.json"


def test_phase_structure_accepts_combined_recovery_notes_constraint(tmp_path):
    store = _store(tmp_path)
    season_plan = {
        "data": {
            "global_constraints": {
                "availability_assumptions": [],
                "risk_constraints": [],
                "planned_event_windows": [],
                "recovery_protection": {
                    "fixed_rest_days": ["Mon", "Fri"],
                    "notes": [
                        "Fixed rest days from AVAILABILITY are non-negotiable and must be preserved downstream.",
                        "When travel compresses the week, reduce ambition before reducing recovery protection.",
                        "After each A event, recovery and re-entry must be baseline-anchored rather than peak-anchored.",
                    ],
                },
            }
        }
    }
    document = {
        "meta": {"iso_week_range": "2026-17--2026-19"},
        "data": {
            "upstream_intent": {
                "constraints": [
                    "Fixed rest days from AVAILABILITY are non-negotiable and must be preserved downstream. | "
                    "When travel compresses the week, reduce ambition before reducing recovery protection. | "
                    "After each A event, recovery and re-entry must be baseline-anchored rather than peak-anchored."
                ]
            },
            "execution_principles": {
                "recovery_protection": {"fixed_non_training_days": ["Mon", "Fri"]},
            },
            "load_ranges": {
                "weekly_kj_bands": [],
                "source": "phase_guardrails_2026-17--2026-19.json",
            },
        },
    }

    store._load_phase_guardrails_for_range = lambda _expected: (
        {
            "data": {
                "load_guardrails": {
                    "weekly_kj_bands": [],
                }
            }
        },
        "2026-17--2026-19",
    )

    store._enforce_phase_structure_constraints(document, season_plan)


def test_phase_structure_store_builds_phase_scoped_capacity_context(tmp_path, monkeypatch):
    store = _store(tmp_path)
    captured: dict[str, object] = {}

    season_plan = {
        "data": {
            "phases": [
                {
                    "phase_id": "P01",
                    "cycle": "Base",
                    "phase_intent": "shortened_re_entry",
                    "iso_week_range": "2026-21--2026-23",
                }
            ]
        }
    }
    phase_slots = {
        "phase_slots": [
            {
                "phase_id": "P01",
                "phase_label": "Shortened Re-Entry",
                "iso_week_range": "2026-21--2026-23",
                "scenario_cadence": "2:1:1",
                "cadence_week_roles": [
                    "SHORTENED_RE_ENTRY",
                    "SHORTENED_CONSOLIDATION",
                    "SHORTENED_MINI_RESET",
                ],
            }
        ]
    }

    def fake_load_latest_optional(artifact_type):
        if artifact_type == ArtifactType.AVAILABILITY:
            return {"data": {"availability_table": {"weekly_hours": {"min": 10.5, "typical": 14.0, "max": 17.5}}}}
        if artifact_type == ArtifactType.SEASON_SCENARIO_SELECTION:
            return {"data": {}}
        return {}

    def fake_build_load_capacity_block(
        *,
        target_week=None,
        phase_range=None,
        athlete_profile_payload=None,
        availability_payload=None,
        logistics_payload=None,
        zone_model_payload=None,
        season_plan_payload=None,
        phase_guardrails_payload=None,
        season_allowed_intensity_domains=None,
        wellness_payload=None,
        kpi_profile_payload=None,
        kpi_rate_band=None,
        previous_load_kj=None,
        baseline_load_kj=None,
        week_role_by_week=None,
        phase_role_by_week=None,
        scenario_cadence=None,
    ):
        kwargs = {
            "target_week": target_week,
            "phase_range": phase_range,
            "athlete_profile_payload": athlete_profile_payload,
            "availability_payload": availability_payload,
            "logistics_payload": logistics_payload,
            "zone_model_payload": zone_model_payload,
            "season_plan_payload": season_plan_payload,
            "phase_guardrails_payload": phase_guardrails_payload,
            "season_allowed_intensity_domains": season_allowed_intensity_domains,
            "wellness_payload": wellness_payload,
            "kpi_profile_payload": kpi_profile_payload,
            "kpi_rate_band": kpi_rate_band,
            "previous_load_kj": previous_load_kj,
            "baseline_load_kj": baseline_load_kj,
            "week_role_by_week": week_role_by_week,
            "phase_role_by_week": phase_role_by_week,
            "scenario_cadence": scenario_cadence,
        }
        captured.update(kwargs)

        class _Block:
            payload = {"s5_bands": [{"week": "2026-21", "band": {"min": 7000, "max": 8000}}]}

        return _Block()

    monkeypatch.setattr(store, "_load_latest_optional", fake_load_latest_optional)
    monkeypatch.setattr("rps.workspace.guarded_store.build_load_capacity_block", fake_build_load_capacity_block)

    phase_info = resolve_season_plan_phase_info(season_plan, parse_iso_week("2026-21"))
    assert phase_info is not None

    payload = store._load_phase_capacity_context_for_store(
        target_week=parse_iso_week("2026-21"),
        phase_range=parse_iso_week_range("2026-21--2026-23"),
        season_plan=season_plan,
        phase_info=phase_info,
        phase_slots=phase_slots,
    )

    assert payload["s5_bands"] == [{"week": "2026-21", "band": {"min": 7000, "max": 8000}}]
    assert captured["target_week"] == parse_iso_week("2026-21")
    assert captured["phase_range"] == parse_iso_week_range("2026-21--2026-23")
    assert captured["season_plan_payload"] == season_plan
    assert captured["week_role_by_week"] == {
        "2026-21": "SHORTENED_RE_ENTRY",
        "2026-22": "SHORTENED_CONSOLIDATION",
        "2026-23": "SHORTENED_MINI_RESET",
    }
    assert captured["phase_role_by_week"] == {
        "2026-21": "Base",
        "2026-22": "Base",
        "2026-23": "Base",
    }
    assert captured["scenario_cadence"] == "2:1:1"


def test_phase_structure_store_logs_capacity_builder_failures(tmp_path, monkeypatch, caplog):
    store = _store(tmp_path)
    season_plan = {
        "data": {
            "phases": [
                {
                    "phase_id": "P01",
                    "cycle": "Base",
                    "phase_intent": "shortened_re_entry",
                    "iso_week_range": "2026-21--2026-23",
                }
            ]
        }
    }
    phase_slots = {
        "phase_slots": [
            {
                "phase_id": "P01",
                "iso_week_range": "2026-21--2026-23",
                "scenario_cadence": "2:1:1",
                "cadence_week_roles": [
                    "SHORTENED_RE_ENTRY",
                    "SHORTENED_CONSOLIDATION",
                    "SHORTENED_MINI_RESET",
                ],
            }
        ]
    }

    monkeypatch.setattr(store, "_load_latest_optional", lambda _artifact_type: {})

    def fail_build_load_capacity_block(**_kwargs):
        raise TypeError("unexpected keyword argument")

    monkeypatch.setattr("rps.workspace.guarded_store.build_load_capacity_block", fail_build_load_capacity_block)
    phase_info = resolve_season_plan_phase_info(season_plan, parse_iso_week("2026-21"))
    assert phase_info is not None

    with caplog.at_level("ERROR"):
        payload = store._load_phase_capacity_context_for_store(
            target_week=parse_iso_week("2026-21"),
            phase_range=parse_iso_week_range("2026-21--2026-23"),
            season_plan=season_plan,
            phase_info=phase_info,
            phase_slots=phase_slots,
        )

    assert payload == {}
    assert "Failed to build phase-scoped load-capacity context due to invalid builder arguments" in caplog.text


def test_build_load_capacity_block_rejects_unknown_kwargs() -> None:
    with pytest.raises(TypeError):
        build_load_capacity_block(planning_events_payload={})  # type: ignore[call-arg]


def test_phase_guardrails_missing_structured_event_still_fails(tmp_path):
    store = _store(tmp_path)
    season_plan = {
        "data": {
            "global_constraints": {
                "availability_assumptions": [],
                "risk_constraints": [],
                "planned_event_windows": ["2026-04-11 (B)"],
                "recovery_protection": {"fixed_rest_days": [], "notes": []},
            }
        }
    }
    document = {"data": {"events_constraints": {"events": []}}}

    with pytest.raises(SchemaValidationError) as exc:
        store._enforce_phase_guardrails_constraints(document, season_plan)

    assert any("planned_event_windows" in err for err in exc.value.errors)


def test_phase_preview_constraints_match_phase_structure(tmp_path):
    store = _store(tmp_path)
    document = {
        "meta": {"iso_week_range": "2026-21--2026-22"},
        "data": {
            "phase_intent_summary": {"phase_intent": "durability_build"},
            "traceability": {
                "derived_from": ["Season plan version 2026-21__20260520_084154"],
                "conflict_resolution": ["Escalate conflicts."],
            },
            "weekly_agenda_preview": [
                {
                    "week": "2026-21",
                    "days": [
                        {"day_of_week": "Mon", "day_role": "REST", "intensity_domain": "NONE", "load_modality": "NONE", "notes": "Fixed rest"},
                        {"day_of_week": "Tue", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE", "notes": "Steady"},
                        {"day_of_week": "Wed", "day_role": "QUALITY", "intensity_domain": "TEMPO", "load_modality": "NONE", "notes": "Focused work"},
                        {"day_of_week": "Thu", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE", "notes": "Steady"},
                        {"day_of_week": "Fri", "day_role": "REST", "intensity_domain": "NONE", "load_modality": "NONE", "notes": "Fixed rest"},
                        {"day_of_week": "Sat", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE", "notes": "Long ride"},
                        {"day_of_week": "Sun", "day_role": "RECOVERY", "intensity_domain": "RECOVERY", "load_modality": "NONE", "notes": "Easy"},
                    ],
                },
                {
                    "week": "2026-22",
                    "days": [
                        {"day_of_week": "Mon", "day_role": "REST", "intensity_domain": "TEMPO", "load_modality": "K3", "notes": "Fixed rest"},
                        {"day_of_week": "Tue", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE", "notes": "Steady"},
                        {"day_of_week": "Wed", "day_role": "QUALITY", "intensity_domain": "SWEET_SPOT", "load_modality": "NONE", "notes": "Focused work"},
                        {"day_of_week": "Thu", "day_role": "QUALITY", "intensity_domain": "TEMPO", "load_modality": "NONE", "notes": "Focused work"},
                        {"day_of_week": "Fri", "day_role": "REST", "intensity_domain": "SWEET_SPOT", "load_modality": "K3", "notes": "Fixed rest"},
                        {"day_of_week": "Sat", "day_role": "QUALITY", "intensity_domain": "ENDURANCE", "load_modality": "NONE", "notes": "Long ride"},
                        {"day_of_week": "Sun", "day_role": "RECOVERY", "intensity_domain": "RECOVERY", "load_modality": "NONE", "notes": "Easy"},
                    ],
                },
            ],
        },
    }

    store._load_phase_structure_for_range = lambda _expected: (
        {
            "data": {
                "structural_phase_elements": {
                    "allowed_day_roles": ["REST", "RECOVERY", "ENDURANCE", "QUALITY"],
                    "allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
                    "allowed_load_modalities": ["NONE"],
                },
                "upstream_intent": {"phase_intent": "durability_build"},
                "execution_principles": {
                    "load_intensity_handling": {
                        "max_quality_days_per_week": 1,
                        "forbidden_intensity_domains": ["VO2MAX", "THRESHOLD"],
                    },
                    "recovery_protection": {
                        "fixed_non_training_days": ["Mon", "Fri"],
                    },
                },
                "week_skeleton_logic": {
                    "week_roles": {
                        "week_roles": [
                            {"week": "2026-21", "role": "LOAD_1"},
                            {"week": "2026-22", "role": "LOAD_2"},
                        ]
                    }
                },
            }
        },
        "2026-21--2026-22__20260520_090000",
    )

    store._enforce_phase_preview_constraints(document)

    derived_from = document["data"]["traceability"]["derived_from"]
    assert "phase_structure_2026-21--2026-22__20260520_090000.json" in derived_from
    normalized_days = document["data"]["weekly_agenda_preview"][1]["days"]
    assert normalized_days[0]["intensity_domain"] == "NONE"
    assert normalized_days[4]["intensity_domain"] == "NONE"
    assert sum(1 for day in normalized_days if day["day_role"] == "QUALITY") == 1


def test_phase_preview_rejects_days_outside_structure_authority(tmp_path):
    store = _store(tmp_path)
    document = {
        "meta": {"iso_week_range": "2026-21--2026-21"},
        "data": {
            "phase_intent_summary": {"phase_intent": "durability_build"},
            "traceability": {
                "derived_from": ["phase_structure_2026-21--2026-21__20260520_090000.json"],
                "conflict_resolution": ["Escalate conflicts."],
            },
            "weekly_agenda_preview": [
                {
                    "week": "2026-21",
                    "days": [
                        {"day_of_week": "Mon", "day_role": "QUALITY", "intensity_domain": "TEMPO", "load_modality": "NONE", "notes": "Wrong fixed day"},
                        {"day_of_week": "Tue", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "K3", "notes": "Wrong modality"},
                        {"day_of_week": "Wed", "day_role": "QUALITY", "intensity_domain": "VO2MAX", "load_modality": "NONE", "notes": "Forbidden"},
                        {"day_of_week": "Thu", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE", "notes": "Steady"},
                        {"day_of_week": "Fri", "day_role": "REST", "intensity_domain": "NONE", "load_modality": "NONE", "notes": "Fixed rest"},
                        {"day_of_week": "Sat", "day_role": "QUALITY", "intensity_domain": "TEMPO", "load_modality": "NONE", "notes": "Too much quality"},
                        {"day_of_week": "Sun", "day_role": "RECOVERY", "intensity_domain": "RECOVERY", "load_modality": "NONE", "notes": "Easy"},
                    ],
                }
            ],
        },
    }

    store._load_phase_structure_for_range = lambda _expected: (
        {
            "data": {
                "structural_phase_elements": {
                    "allowed_day_roles": ["REST", "RECOVERY", "ENDURANCE", "QUALITY"],
                    "allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO"],
                    "allowed_load_modalities": ["NONE"],
                },
                "upstream_intent": {"phase_intent": "durability_build"},
                "execution_principles": {
                    "load_intensity_handling": {
                        "max_quality_days_per_week": 1,
                        "forbidden_intensity_domains": ["VO2MAX"],
                    },
                    "recovery_protection": {
                        "fixed_non_training_days": ["Mon", "Fri"],
                    },
                },
                "week_skeleton_logic": {
                    "week_roles": {
                        "week_roles": [
                            {"week": "2026-21", "role": "LOAD_1"},
                        ]
                    }
                },
            }
        },
        "2026-21--2026-21__20260520_090000",
    )

    store._enforce_phase_preview_constraints(document)

    days = document["data"]["weekly_agenda_preview"][0]["days"]
    assert days[0]["day_role"] == "REST"
    assert days[0]["intensity_domain"] == "NONE"
    assert days[1]["day_role"] == "QUALITY"
    assert days[1]["intensity_domain"] == "TEMPO"
    assert days[1]["load_modality"] == "NONE"
    assert days[2]["day_role"] == "RECOVERY"
    assert days[2]["intensity_domain"] == "RECOVERY"
    assert days[5]["day_role"] == "ENDURANCE"
    assert days[5]["intensity_domain"] == "ENDURANCE"
    assert days[6]["day_role"] == "ENDURANCE"
    assert days[6]["intensity_domain"] == "ENDURANCE"


def test_phase_preview_rejects_phase_intent_mismatch(tmp_path):
    store = _store(tmp_path)
    document = {
        "meta": {"iso_week_range": "2026-21--2026-21"},
        "data": {
            "phase_intent_summary": {"phase_intent": "specificity_build"},
            "traceability": {
                "derived_from": ["phase_structure_2026-21--2026-21__20260520_090000.json"],
                "conflict_resolution": ["Escalate conflicts."],
            },
            "weekly_agenda_preview": [
                {
                    "week": "2026-21",
                    "days": [
                        {"day_of_week": "Mon", "day_role": "REST", "intensity_domain": "NONE", "load_modality": "NONE", "notes": "Fixed rest"},
                        {"day_of_week": "Tue", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE", "notes": "Steady"},
                        {"day_of_week": "Wed", "day_role": "QUALITY", "intensity_domain": "TEMPO", "load_modality": "NONE", "notes": "Focused work"},
                        {"day_of_week": "Thu", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE", "notes": "Steady"},
                        {"day_of_week": "Fri", "day_role": "REST", "intensity_domain": "NONE", "load_modality": "NONE", "notes": "Fixed rest"},
                        {"day_of_week": "Sat", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE", "notes": "Long ride"},
                        {"day_of_week": "Sun", "day_role": "RECOVERY", "intensity_domain": "RECOVERY", "load_modality": "NONE", "notes": "Easy"},
                    ],
                }
            ],
        },
    }

    store._load_phase_structure_for_range = lambda _expected: (
        {
            "data": {
                "upstream_intent": {"phase_intent": "durability_build"},
                "structural_phase_elements": {
                    "allowed_day_roles": ["REST", "RECOVERY", "ENDURANCE", "QUALITY"],
                    "allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO"],
                    "allowed_load_modalities": ["NONE"],
                },
                "execution_principles": {
                    "load_intensity_handling": {
                        "max_quality_days_per_week": 1,
                        "forbidden_intensity_domains": ["VO2MAX"],
                    },
                    "recovery_protection": {"fixed_non_training_days": ["Mon", "Fri"]},
                },
                "week_skeleton_logic": {"week_roles": {"week_roles": [{"week": "2026-21", "role": "LOAD_1"}]}},
            }
        },
        "2026-21--2026-21__20260520_090000",
    )

    with pytest.raises(SchemaValidationError) as exc:
        store._enforce_phase_preview_constraints(document)

    assert any("phase_intent" in err for err in exc.value.errors)


def test_phase_preview_repairs_training_day_none_back_to_shared_skeleton(tmp_path):
    store = _store(tmp_path)
    document = {
        "meta": {"iso_week_range": "2026-21--2026-21"},
        "data": {
            "phase_intent_summary": {"phase_intent": "durability_build"},
            "traceability": {
                "derived_from": ["phase_structure_2026-21--2026-21__20260520_090000.json"],
                "conflict_resolution": ["Escalate conflicts."],
            },
            "weekly_agenda_preview": [
                {
                    "week": "2026-21",
                    "days": [
                        {"day_of_week": "Mon", "day_role": "REST", "intensity_domain": "NONE", "load_modality": "NONE"},
                        {"day_of_week": "Tue", "day_role": "ENDURANCE", "intensity_domain": "NONE", "load_modality": "NONE"},
                        {"day_of_week": "Wed", "day_role": "QUALITY", "intensity_domain": "TEMPO", "load_modality": "NONE"},
                        {"day_of_week": "Thu", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE"},
                        {"day_of_week": "Fri", "day_role": "REST", "intensity_domain": "NONE", "load_modality": "NONE"},
                        {"day_of_week": "Sat", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE"},
                        {"day_of_week": "Sun", "day_role": "RECOVERY", "intensity_domain": "RECOVERY", "load_modality": "NONE"},
                    ],
                }
            ],
        },
    }

    store._load_phase_structure_for_range = lambda _expected: (
        {
            "data": {
                "upstream_intent": {"phase_intent": "durability_build"},
                "structural_phase_elements": {
                    "allowed_day_roles": ["REST", "RECOVERY", "ENDURANCE", "QUALITY"],
                    "allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO"],
                    "allowed_load_modalities": ["NONE"],
                },
                "execution_principles": {
                    "load_intensity_handling": {
                        "max_quality_days_per_week": 1,
                        "forbidden_intensity_domains": ["VO2MAX"],
                    },
                    "recovery_protection": {"fixed_non_training_days": ["Mon", "Fri"]},
                },
                "week_skeleton_logic": {"week_roles": {"week_roles": [{"week": "2026-21", "role": "LOAD_1"}]}},
            }
        },
        "2026-21--2026-21__20260520_090000",
    )

    store._enforce_phase_preview_constraints(document)

    repaired_days = document["data"]["weekly_agenda_preview"][0]["days"]
    assert repaired_days[1]["day_role"] == "QUALITY"
    assert repaired_days[1]["intensity_domain"] == "TEMPO"
    assert repaired_days[1]["load_modality"] == "NONE"


def test_phase_guardrails_schema_accepts_full_inherited_contract() -> None:
    document = {
        "meta": {
            "artifact_type": "PHASE_GUARDRAILS",
            "schema_id": "PhaseGuardrailsInterface",
            "schema_version": "1.0",
            "version": "1.0",
            "version_key": "2026-26--2026-29__20260528_130000",
            "authority": "Binding",
            "owner_agent": "Phase-Artifact-Writer",
            "run_id": "phase_guardrails_run",
            "created_at": "2026-05-28T13:00:00Z",
            "scope": "Phase",
            "iso_week": "2026-26",
            "iso_week_range": "2026-26--2026-29",
            "temporal_scope": {"from": "2026-06-22", "to": "2026-07-19"},
            "trace_upstream": [],
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "HIGH",
            "notes": "",
        },
        "data": {
            "body_metadata": {
                "phase_id": "P02",
                "phase_taxonomy_version": "canonical_phase_taxonomy_v1",
                "phase_type": "BUILD",
                "phase_intent": "durability_build",
                "build_subtype": "durability_build",
                "phase_status": "Green",
                "change_type": "NEW",
                "derived_from": "SEASON_PLAN",
                "upstream_inputs": ["season_plan"],
            },
            "inherited_scenario_contract": _full_selected_scenario_contract(),
            "phase_summary": {
                "primary_objective": "Increase durability under controlled load.",
                "secondary_objectives": ["Preserve continuity."],
                "key_risks_warnings": ["Travel disruption may reduce execution quality."],
                "non_negotiables": ["Protect fixed rest days."],
            },
            "load_guardrails": {
                "weekly_kj_bands": [
                    {"week": "2026-26", "band": {"min": 12000, "max": 13000, "notes": "Band"}}
                ],
                "confidence_assumptions": {
                    "kj_estimation_method": "Mixed",
                    "confidence": {"kj": "HIGH"},
                    "ftp_watts_used": 300,
                    "zone_model_version": "2026-22",
                },
            },
            "allowed_forbidden_semantics": {
                "allowed_day_roles": ["REST", "RECOVERY", "ENDURANCE", "QUALITY"],
                "allowed_intensity_domains": ["NONE", "RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
                "allowed_load_modalities": ["NONE", "K3"],
                "quality_density": {
                    "max_quality_days_per_week": 2,
                    "quality_intent": "Build",
                    "forbidden_patterns": ["No adjacent quality stacking."],
                },
                "forbidden_day_roles": [],
                "forbidden_intensity_domains": ["VO2MAX"],
                "forbidden_load_modalities": [],
            },
            "events_constraints": {
                "events": [],
                "logistics_time_constraints": {
                    "travel_days": "No special travel-day restriction.",
                    "work_constraints": "No exceptional work constraint.",
                    "weather_or_indoor_constraints": "Indoor trainer preserves continuity.",
                },
            },
            "execution_non_negotiables": {
                "recovery_protection_rules": "Protect Monday and Friday.",
                "long_endurance_anchor_protection": "Preserve long-ride anchor quality.",
                "minimum_recovery_opportunities": "At least two recovery opportunities per week.",
                "no_catch_up_rule": "Do not catch up missed load.",
            },
            "escalation_change_control": {
                "warning_signals": ["Persistent fatigue."],
                "required_response": {
                    "week_planner_must": ["Reduce ambition before reducing recovery protection."],
                    "week_planner_must_not": ["Add catch-up load."],
                    "phase_architect_decides": "Whether the phase needs a broader reset.",
                },
            },
            "explicit_forbidden_content": [
                "day-by-day plans",
                "workouts or interval prescriptions",
                "durations, zones (Z1-Z7), %FTP",
                "daily kJ targets",
                "numeric progression rules",
                "recommendations that effectively plan the week level",
            ],
            "self_check": {
                "weekly_kj_bands_present": True,
                "max_quality_days_specified": True,
                "allowed_forbidden_enums_specified": True,
                "no_week_planning_content": True,
                "header_includes_implements_iso_week_range_trace": True,
            },
        },
    }

    validate_or_raise(_schema_registry().validator_for("phase_guardrails.schema.json"), document)


def test_phase_structure_schema_accepts_full_inherited_contract() -> None:
    document = {
        "meta": {
            "artifact_type": "PHASE_STRUCTURE",
            "schema_id": "PhaseStructureInterface",
            "schema_version": "1.0",
            "version": "1.0",
            "version_key": "2026-26--2026-29__20260528_130000",
            "authority": "Binding",
            "owner_agent": "Phase-Artifact-Writer",
            "run_id": "phase_structure_run",
            "created_at": "2026-05-28T13:00:00Z",
            "scope": "Phase",
            "iso_week": "2026-26",
            "iso_week_range": "2026-26--2026-29",
            "temporal_scope": {"from": "2026-06-22", "to": "2026-07-19"},
            "trace_upstream": [],
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "HIGH",
            "notes": "",
        },
        "data": {
            "upstream_intent": {
                "phase_intent": "durability_build",
                "phase_type": "BUILD",
                "phase_taxonomy_version": "canonical_phase_taxonomy_v1",
                "build_subtype": "durability_build",
                "primary_objective": "Increase durability under controlled load.",
                "phase_status": "Green",
                "non_negotiables": ["Protect fixed rest days."],
                "constraints": ["Travel disruption may reduce execution quality."],
                "key_risks_warnings": ["Persistent fatigue."],
            },
            "inherited_scenario_contract": _full_selected_scenario_contract(),
            "load_ranges": {
                "weekly_kj_bands": [
                    {"week": "2026-26", "band": {"min": 12000, "max": 13000, "notes": "Band"}}
                ],
                "source": "phase_guardrails_2026-26--2026-29__20260528_130000.json",
            },
            "execution_principles": {
                "load_intensity_handling": {
                    "max_quality_days_per_week": 2,
                    "allowed_intensity_domains": ["NONE", "RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
                    "forbidden_intensity_domains": ["VO2MAX"],
                    "load_modality_constraints": ["NONE", "K3"],
                    "quality_intent": "Build",
                },
                "recovery_protection": {
                    "fixed_non_training_days": ["Mon", "Fri"],
                    "mandatory_recovery_spacing_rules": [
                        "Keep at least one recovery opportunity between quality anchors when possible."
                    ],
                    "forbidden_sequences": [
                        "Do not place quality on both fixed non-training days."
                    ],
                    "long_endurance_anchor_protection": "Preserve the long endurance anchor on the most suitable weekend day.",
                },
                "consistency_over_optimization": {
                    "statements": ["Preserve continuity over catch-up loading."],
                },
            },
            "structural_phase_elements": {
                "allowed_day_roles": ["REST", "RECOVERY", "ENDURANCE", "QUALITY"],
                "allowed_intensity_domains": ["NONE", "RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
                "allowed_load_modalities": ["NONE", "K3"],
            },
            "week_skeleton_logic": {
                "week_roles": {
                    "week_roles": [
                        {"week": "2026-26", "role": "LOAD_1"},
                        {"week": "2026-27", "role": "LOAD_2"},
                        {"week": "2026-28", "role": "MINI_RESET"},
                        {"week": "2026-29", "role": "RELOAD"},
                    ],
                    "allowed_role_set": ["LOAD_1", "LOAD_2", "MINI_RESET", "RELOAD"],
                },
                "mandatory_elements": {
                    "recovery_opportunities_min": 2,
                    "endurance_anchor_required": True,
                },
                "optional_elements": {
                    "quality_days": {
                        "capped_by_upstream_limits": True,
                        "never_adjacent_unless_allowed": True,
                    },
                    "optional_flex_days": {
                        "removable_without_compensation": True,
                    },
                },
                "forbidden_patterns": ["No VO2MAX focus."],
            },
            "adaptation_rules": [
                "Progress through sustainable load growth.",
                "Use visible resets.",
                "Resume conservatively after disruption.",
            ],
            "relationships": {
                "guides": ["WEEK_PLAN"],
                "does_not_replace": ["PHASE_GUARDRAILS"],
            },
            "self_check": {
                "phase_status_respected": True,
                "phase_range_covered": True,
                "week_roles_defined_for_phase_range": True,
                "no_new_decision_introduced": True,
                "no_numeric_target_introduced": True,
                "no_kpi_gate_inferred": True,
            },
        },
    }

    validate_or_raise(_schema_registry().validator_for("phase_structure.schema.json"), document)


def test_week_plan_schema_rejects_full_contract_only_fields_in_inherited_planning_posture() -> None:
    document = {
        "meta": {
            "artifact_type": "WEEK_PLAN",
            "schema_id": "WeekPlanInterface",
            "schema_version": "1.2",
            "authority": "Binding",
            "owner_agent": "Week-Artifact-Writer",
            "run_id": "week_plan_run",
            "created_at": "2026-05-28T13:00:00Z",
            "scope": "Week",
            "iso_week": "2026-26",
            "data_confidence": "HIGH",
            "notes": "",
        },
        "data": {
            "inherited_planning_posture": {
                "selected_scenario_id": "B",
                "load_posture": "Moderate-to-progressive load with planned resets.",
                "recovery_margin": "Moderate recovery margin.",
                "fatigue_exposure": "Moderate fatigue exposure.",
                "specificity_density": "Moderate-to-high specificity density.",
                "season_archetype": "none",
                "allowed_intensity_domains": ["ENDURANCE", "TEMPO"],
                "forbidden_intensity_domains": [],
                "risk_flags": ["Persistent fatigue risk."],
                "phase_intent": "durability_build",
                "phase_week_role": "LOAD_1",
                "best_suited_if": "Should be rejected here."
            },
            "week_summary": {
                "week_objective": "Durability-led load week.",
                "weekly_load_corridor_kj": {"min": 9000, "max": 11000, "notes": "Band"},
                "planned_weekly_load_kj": 10000,
                "notes": "Stay inside the corridor.",
            },
            "agenda": [
                {"day": "Mon", "date": "2026-06-22", "day_role": "REST", "planned_duration": "00:00", "planned_kj": 0, "workout_id": None},
                {"day": "Tue", "date": "2026-06-23", "day_role": "ENDURANCE", "planned_duration": "01:30", "planned_kj": 1200, "workout_id": "W1"},
                {"day": "Wed", "date": "2026-06-24", "day_role": "QUALITY", "planned_duration": "01:30", "planned_kj": 1500, "workout_id": "W2"},
                {"day": "Thu", "date": "2026-06-25", "day_role": "ENDURANCE", "planned_duration": "01:30", "planned_kj": 1300, "workout_id": "W3"},
                {"day": "Fri", "date": "2026-06-26", "day_role": "REST", "planned_duration": "00:00", "planned_kj": 0, "workout_id": None},
                {"day": "Sat", "date": "2026-06-27", "day_role": "ENDURANCE", "planned_duration": "04:00", "planned_kj": 4200, "workout_id": "W4"},
                {"day": "Sun", "date": "2026-06-28", "day_role": "RECOVERY", "planned_duration": "01:00", "planned_kj": 800, "workout_id": "W5"}
            ],
            "workouts": [
                {"workout_id": "W1", "title": "Endurance", "date": "2026-06-23", "start": "08:00", "duration": "01:30:00", "workout_text": "ENDURANCE", "notes": ""},
                {"workout_id": "W2", "title": "Quality", "date": "2026-06-24", "start": "08:00", "duration": "01:30:00", "workout_text": "TEMPO", "notes": ""},
                {"workout_id": "W3", "title": "Endurance", "date": "2026-06-25", "start": "08:00", "duration": "01:30:00", "workout_text": "ENDURANCE", "notes": ""},
                {"workout_id": "W4", "title": "Long", "date": "2026-06-27", "start": "08:00", "duration": "04:00:00", "workout_text": "ENDURANCE", "notes": ""},
                {"workout_id": "W5", "title": "Recovery", "date": "2026-06-28", "start": "08:00", "duration": "01:00:00", "workout_text": "RECOVERY", "notes": ""}
            ],
        },
    }

    with pytest.raises(SchemaValidationError):
        validate_or_raise(_schema_registry().validator_for("week_plan.schema.json"), document)
