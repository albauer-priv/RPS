from rps.planning.contracts import (
    blocking_messages,
    derive_expected_average_weekly_kj_range,
    validate_phase_against_execution_context,
    validate_season_plan_against_phase_load_context,
    validate_season_plan_against_phase_slots,
    validate_snapshot_freshness,
    validate_week_plan_against_week_context,
)


def test_validate_snapshot_freshness_blocks_stale_authoritative_snapshot() -> None:
    snapshot = {"data": {"source_versions": {"availability": "2026-01"}}}

    issues = validate_snapshot_freshness(
        snapshot_payload=snapshot,
        expected_source_versions={"availability": "2026-02"},
        authoritative=True,
        snapshot_label="ATHLETE_STATE_SNAPSHOT",
    )

    assert blocking_messages(issues)
    assert issues[0].code == "snapshot_stale_source_version"


def test_validate_season_plan_against_phase_slots_rejects_resized_phase() -> None:
    season_plan = {
        "data": {
            "phases": [
                {"phase_id": "P01", "iso_week_range": "2026-21--2026-22"},
            ]
        }
    }
    slot_context = {
        "coverage_matches_horizon": True,
        "phase_slots": [
            {"phase_id": "P01", "iso_week_range": "2026-21--2026-23", "length_weeks": 3, "phase_intent": "durability_build"},
        ],
    }

    issues = validate_season_plan_against_phase_slots(
        season_plan_payload=season_plan,
        phase_slot_context=slot_context,
    )

    assert any(issue.code == "season_phase_slot_mismatch" for issue in issues)


def test_validate_season_plan_against_phase_slots_rejects_phase_intent_mismatch() -> None:
    season_plan = {
        "data": {
            "phases": [
                {"phase_id": "P01", "iso_week_range": "2026-21--2026-23", "phase_intent": "durability_build"},
            ]
        }
    }
    slot_context = {
        "coverage_matches_horizon": True,
        "phase_slots": [
            {"phase_id": "P01", "iso_week_range": "2026-21--2026-23", "length_weeks": 3, "phase_intent": "vo2_build"},
        ],
    }

    issues = validate_season_plan_against_phase_slots(
        season_plan_payload=season_plan,
        phase_slot_context=slot_context,
    )

    assert any(issue.code == "season_phase_intent_mismatch" for issue in issues)


def test_validate_season_plan_against_phase_load_context_requires_taper_reduction() -> None:
    season_plan = {
        "data": {
            "phases": [
                {
                    "phase_id": "P01",
                    "phase_type": "BUILD",
                    "phase_intent": "durability_build",
                    "build_subtype": "durability_build",
                    "allowed_forbidden_semantics": {"allowed_intensity_domains": ["ENDURANCE", "TEMPO"], "forbidden_intensity_domains": ["VO2MAX"]},
                    "weekly_load_corridor": {"weekly_kj": {"min": 8000, "max": 10000}},
                },
                {
                    "phase_id": "P02",
                    "phase_type": "TAPER",
                    "phase_intent": "taper_freshening",
                    "build_subtype": None,
                    "allowed_forbidden_semantics": {"allowed_intensity_domains": ["ENDURANCE", "TEMPO"], "forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"]},
                    "weekly_load_corridor": {"weekly_kj": {"min": 8000, "max": 10000}},
                },
            ],
            "body_metadata": {"phase_taxonomy_version": "canonical_phase_taxonomy_v1"},
        }
    }
    load_context = {
        "phases": [
            {
                "phase_id": "P01",
                "phase_intent": "durability_build",
                "recommended_phase_corridor": {"min": 7000, "max": 11000},
                "event_taper_trace": {},
            },
            {
                "phase_id": "P02",
                "phase_intent": "taper_freshening",
                "recommended_phase_corridor": {"min": 6000, "max": 10000},
                "event_taper_trace": {"has_a_event": True},
            },
        ]
    }

    issues = validate_season_plan_against_phase_load_context(
        season_plan_payload=season_plan,
        season_phase_load_context=load_context,
    )

    assert any(issue.code == "a_event_peak_taper_not_reduced" for issue in issues)


def test_validate_season_plan_against_phase_load_context_checks_selected_scenario_contract() -> None:
    season_plan = {
        "data": {
            "selected_scenario_contract": {"selected_scenario_id": "A", "load_posture": "conservative"},
            "phases": [],
            "body_metadata": {"phase_taxonomy_version": "canonical_phase_taxonomy_v1"},
        }
    }
    load_context = {
        "selected_scenario_contract": {"selected_scenario_id": "B", "load_posture": "balanced_progressive"},
        "phases": [{"phase_id": "P01", "phase_intent": "general_base", "recommended_phase_corridor": {"min": 1, "max": 2}, "event_taper_trace": {}}],
    }

    issues = validate_season_plan_against_phase_load_context(
        season_plan_payload=season_plan,
        season_phase_load_context=load_context,
    )

    assert any(issue.code == "season_selected_scenario_contract_mismatch" for issue in issues)


def test_validate_season_plan_against_phase_load_context_blocks_endurance_only_collapse() -> None:
    season_plan = {
        "data": {
            "body_metadata": {"phase_taxonomy_version": "canonical_phase_taxonomy_v1"},
            "phases": [
                {
                    "phase_id": "P01",
                    "phase_type": "BASE",
                    "phase_intent": "aerobic_base",
                    "weekly_load_corridor": {"weekly_kj": {"min": 3000, "max": 5000}},
                    "allowed_forbidden_semantics": {"allowed_intensity_domains": ["ENDURANCE"], "forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"]},
                },
                {
                    "phase_id": "P02",
                    "phase_type": "BUILD",
                    "phase_intent": "durability_build",
                    "build_subtype": "durability_build",
                    "weekly_load_corridor": {"weekly_kj": {"min": 4500, "max": 6500}},
                    "allowed_forbidden_semantics": {"allowed_intensity_domains": ["ENDURANCE"], "forbidden_intensity_domains": ["VO2MAX"]},
                },
            ]
        }
    }
    load_context = {
        "season_allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT"],
        "phases": [
            {
                "phase_id": "P01",
                "phase_intent": "aerobic_base",
                "recommended_phase_corridor": {"min": 2500, "max": 5500},
                "event_taper_trace": {},
            },
            {
                "phase_id": "P02",
                "phase_intent": "durability_build",
                "recommended_phase_corridor": {"min": 4000, "max": 7000},
                "event_taper_trace": {},
            },
        ],
    }

    issues = validate_season_plan_against_phase_load_context(
        season_plan_payload=season_plan,
        season_phase_load_context=load_context,
    )

    assert any(issue.code == "season_intensity_domains_collapsed_to_endurance_only" for issue in issues)


def test_validate_season_plan_against_phase_load_context_allows_phase_narrowing() -> None:
    season_plan = {
        "data": {
            "body_metadata": {"phase_taxonomy_version": "canonical_phase_taxonomy_v1"},
            "phases": [
                {
                    "phase_id": "P01",
                    "phase_type": "BASE",
                    "phase_intent": "aerobic_base",
                    "weekly_load_corridor": {"weekly_kj": {"min": 3000, "max": 5000}},
                    "allowed_forbidden_semantics": {"allowed_intensity_domains": ["ENDURANCE"], "forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"]},
                },
                {
                    "phase_id": "P02",
                    "phase_type": "BUILD",
                    "phase_intent": "durability_build",
                    "build_subtype": "durability_build",
                    "weekly_load_corridor": {"weekly_kj": {"min": 4500, "max": 6500}},
                    "allowed_forbidden_semantics": {"allowed_intensity_domains": ["ENDURANCE", "TEMPO"], "forbidden_intensity_domains": ["VO2MAX"]},
                },
            ]
        }
    }
    load_context = {
        "season_allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT"],
        "phases": [
            {
                "phase_id": "P01",
                "phase_intent": "aerobic_base",
                "recommended_phase_corridor": {"min": 2500, "max": 5500},
                "event_taper_trace": {},
            },
            {
                "phase_id": "P02",
                "phase_intent": "durability_build",
                "recommended_phase_corridor": {"min": 4000, "max": 7000},
                "event_taper_trace": {},
            },
        ],
    }

    issues = validate_season_plan_against_phase_load_context(
        season_plan_payload=season_plan,
        season_phase_load_context=load_context,
    )

    assert not any(issue.code == "season_intensity_domains_collapsed_to_endurance_only" for issue in issues)


def test_derive_expected_average_weekly_kj_range_uses_role_week_load_bands() -> None:
    season_plan = {
        "data": {
            "phases": [
                {
                    "iso_week_range": "2026-21--2026-23",
                    "weekly_load_corridor": {"weekly_kj": {"min": 7000, "max": 10000}},
                    "role_week_load_bands": [
                        {"week": "2026-21", "role": "LOAD_1", "band": {"min": 7200, "max": 9500}},
                        {"week": "2026-22", "role": "LOAD_2", "band": {"min": 8100, "max": 10300}},
                        {"week": "2026-23", "role": "MINI_RESET", "band": {"min": 6800, "max": 8200}},
                    ],
                },
                {
                    "iso_week_range": "2026-24--2026-25",
                    "weekly_load_corridor": {"weekly_kj": {"min": 5000, "max": 8000}},
                    "role_week_load_bands": [
                        {"week": "2026-24", "role": "LOAD_1", "band": {"min": 6100, "max": 7600}},
                        {"week": "2026-25", "role": "RELOAD", "band": {"min": 6400, "max": 7900}},
                    ],
                },
            ]
        }
    }

    derived = derive_expected_average_weekly_kj_range(season_plan_payload=season_plan)

    assert derived == {"min": 6920, "max": 8700}


def test_derive_expected_average_weekly_kj_range_falls_back_to_legacy_band_notes() -> None:
    season_plan = {
        "data": {
            "phases": [
                {
                    "iso_week_range": "2026-21--2026-22",
                    "weekly_load_corridor": {
                        "weekly_kj": {
                            "notes": [
                                "2026-21: LOAD 7000-9000",
                                "2026-22: RELOAD 6500-8500",
                            ]
                        }
                    },
                }
            ]
        }
    }

    derived = derive_expected_average_weekly_kj_range(season_plan_payload=season_plan)

    assert derived == {"min": 6750, "max": 8750}


def test_validate_season_plan_against_phase_load_context_blocks_vo2_in_taper_intent() -> None:
    season_plan = {
        "data": {
            "phases": [
                {
                    "phase_id": "P05",
                    "phase_type": "TAPER",
                    "phase_intent": "taper_freshening",
                    "weekly_load_corridor": {"weekly_kj": {"min": 5000, "max": 7000}},
                    "allowed_forbidden_semantics": {"allowed_intensity_domains": ["ENDURANCE", "VO2MAX"], "forbidden_intensity_domains": ["THRESHOLD"]},
                }
            ],
            "body_metadata": {"phase_taxonomy_version": "canonical_phase_taxonomy_v1"},
            "season_load_envelope": {"expected_average_weekly_kj_range": {"min": 5000, "max": 7000}},
        }
    }
    load_context = {
        "season_archetype": "none",
        "season_allowed_intensity_domains": ["ENDURANCE", "VO2MAX"],
        "phases": [
            {
                "phase_id": "P05",
                "phase_intent": "taper_freshening",
                "recommended_phase_corridor": {"min": 5000, "max": 7000},
                "event_taper_trace": {"has_a_event": True},
            }
        ],
    }

    issues = validate_season_plan_against_phase_load_context(
        season_plan_payload=season_plan,
        season_phase_load_context=load_context,
    )

    assert any(issue.code == "season_peak_taper_vo2max_conflict" for issue in issues)


def test_validate_season_plan_against_phase_load_context_warns_on_objective_event_mismatch() -> None:
    season_plan = {
        "data": {
            "body_metadata": {"phase_taxonomy_version": "canonical_phase_taxonomy_v1"},
            "season_intent_principles": {"season_objective": "Strong 300-400 km execution."},
            "phases": [
                {
                    "phase_id": "P01",
                    "phase_type": "TAPER",
                    "phase_intent": "taper_freshening",
                    "build_subtype": None,
                    "weekly_load_corridor": {
                        "weekly_kj": {
                            "min": 6000,
                            "max": 9000,
                            "notes": "Inherited role-week load guardrails (season-level, not week prescriptions): 2026-37: EVENT 6000-9000.",
                        }
                    },
                    "allowed_forbidden_semantics": {
                        "allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO"],
                        "allowed_load_modalities": ["NONE"],
                        "forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
                    },
                    "events_constraints": [
                        {
                            "window": "2026-09-12",
                            "type": "A",
                            "constraint": "A event receives dedicated taper-contained event handling.",
                        }
                    ],
                }
            ],
            "season_load_envelope": {"expected_average_weekly_kj_range": {"min": 6000, "max": 9000}},
        }
    }
    load_context = {
        "season_allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT"],
        "phases": [
            {
                "phase_id": "P01",
                "phase_intent": "taper_freshening",
                "recommended_phase_corridor": {"min": 6000, "max": 9000},
                "role_week_load_bands": [{"week": "2026-37", "role": "EVENT", "band": {"min": 6000, "max": 9000}}],
                "event_taper_trace": {
                    "has_a_event": True,
                    "events": [{"date": "2026-09-12", "week": "2026-37", "type": "A", "name": "Brevet 200 km"}],
                },
            }
        ],
    }

    issues = validate_season_plan_against_phase_load_context(
        season_plan_payload=season_plan,
        season_phase_load_context=load_context,
    )

    assert any(issue.code == "season_objective_event_mismatch_warning" and issue.severity == "warning" for issue in issues)


def test_validate_phase_against_execution_context_checks_roles_and_s5() -> None:
    phase_payload = {
        "data": {
            "load_ranges": {
                "weekly_kj_bands": [
                    {"week": "2026-21", "band": {"min": 1000, "max": 2000}},
                ]
            },
            "week_skeleton_logic": {
                "week_roles": {"week_roles": [{"week": "2026-21", "role": "DELOAD"}]}
            },
        }
    }
    context = {
        "week_role_by_iso_week": {"2026-21": "LOAD_1"},
        "phase_s5_bands": [{"week": "2026-21", "band": {"min": 1000, "max": 2000}}],
    }

    issues = validate_phase_against_execution_context(
        phase_payload=phase_payload,
        phase_execution_context=context,
    )

    assert any(issue.code == "phase_week_role_mismatch" for issue in issues)


def test_validate_phase_against_execution_context_checks_inherited_scenario_contract() -> None:
    phase_payload = {
        "data": {
            "inherited_scenario_contract": {"selected_scenario_id": "A", "load_posture": "conservative"},
            "load_ranges": {"weekly_kj_bands": [{"week": "2026-21", "band": {"min": 1000, "max": 2000}}]},
            "week_skeleton_logic": {"week_roles": {"week_roles": [{"week": "2026-21", "role": "LOAD_1"}]}},
        }
    }
    context = {
        "inherited_scenario_contract": {"selected_scenario_id": "B", "load_posture": "balanced_progressive"},
        "week_role_by_iso_week": {"2026-21": "LOAD_1"},
        "phase_s5_bands": [{"week": "2026-21", "band": {"min": 1000, "max": 2000}}],
    }

    issues = validate_phase_against_execution_context(
        phase_payload=phase_payload,
        phase_execution_context=context,
    )

    assert any(issue.code == "phase_inherited_scenario_contract_mismatch" for issue in issues)


def test_validate_week_plan_against_week_context_checks_active_band() -> None:
    week_plan = {
        "data": {
            "week_summary": {
                "weekly_load_corridor_kj": {"min": 1000, "max": 2000},
                "planned_weekly_load_kj": 2500,
            },
            "agenda": [
                {"day": "Mon", "date": "2026-05-18", "day_role": "ENDURANCE"},
            ],
        }
    }
    context = {
        "active_weekly_kj_band": {"min": 1000, "max": 2000},
        "day_matrix": [{"day": "Mon", "date": "2026-05-18"}],
        "phase_week_role": "LOAD_1",
    }

    issues = validate_week_plan_against_week_context(
        week_plan_payload=week_plan,
        week_calendar_context=context,
    )

    assert any(issue.code == "week_planned_load_outside_active_band" for issue in issues)


def test_validate_week_plan_against_week_context_checks_inherited_planning_posture() -> None:
    week_plan = {
        "data": {
            "inherited_planning_posture": {"selected_scenario_id": "A", "load_posture": "conservative"},
            "week_summary": {
                "weekly_load_corridor_kj": {"min": 1000, "max": 2000},
                "planned_weekly_load_kj": 1500,
            },
            "agenda": [
                {"day": "Mon", "date": "2026-05-18", "day_role": "ENDURANCE"},
            ],
        }
    }
    context = {
        "inherited_planning_posture": {"selected_scenario_id": "B", "load_posture": "balanced_progressive"},
        "active_weekly_kj_band": {"min": 1000, "max": 2000},
        "day_matrix": [{"day": "Mon", "date": "2026-05-18"}],
        "phase_week_role": "LOAD_1",
    }

    issues = validate_week_plan_against_week_context(
        week_plan_payload=week_plan,
        week_calendar_context=context,
    )

    assert any(issue.code == "week_inherited_planning_posture_mismatch" for issue in issues)


def test_validate_week_plan_against_week_context_accepts_matching_inherited_planning_posture() -> None:
    week_plan = {
        "data": {
            "inherited_planning_posture": {"selected_scenario_id": "B", "load_posture": "balanced_progressive"},
            "week_summary": {
                "weekly_load_corridor_kj": {"min": 1000, "max": 2000},
                "planned_weekly_load_kj": 1500,
            },
            "agenda": [
                {"day": "Mon", "date": "2026-05-18", "day_role": "ENDURANCE"},
            ],
        }
    }
    context = {
        "inherited_planning_posture": {"selected_scenario_id": "B", "load_posture": "balanced_progressive"},
        "active_weekly_kj_band": {"min": 1000, "max": 2000},
        "day_matrix": [{"day": "Mon", "date": "2026-05-18"}],
        "phase_week_role": "LOAD_1",
    }

    issues = validate_week_plan_against_week_context(
        week_plan_payload=week_plan,
        week_calendar_context=context,
    )

    assert not any(issue.code == "week_inherited_planning_posture_mismatch" for issue in issues)
