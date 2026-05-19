from pathlib import Path

from rps.agents.tasks import OUTPUT_SPECS, AgentTask
from rps.workspace.artifact_metadata import canonicalize_artifact_envelope_meta
from rps.workspace.guarded_store import GuardedValidatedStore
from rps.workspace.types import ArtifactType


def _minimal_season_plan_document() -> dict[str, object]:
    return {
        "meta": {
            "artifact_type": "SEASON_PLAN",
            "schema_id": "season_plan.schema.json",
            "schema_version": "1.0",
            "version": "2026-21",
            "authority": "Binding",
            "owner_agent": "Invented writer",
            "run_id": "llm-run",
            "created_at": "2026-05-18T19:47:00Z",
            "scope": "Season",
            "iso_week": "2026-21",
            "iso_week_range": "2026-21--2026-37",
            "temporal_scope": {"from": "2026-05-18", "to": "2026-09-13"},
            "trace_upstream": [
                {
                    "artifact": "ATHLETE_PROFILE",
                    "version": "20260315_091949",
                    "run_id": "athlete_profile__i150546__20260315_091949",
                }
            ],
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "HIGH",
            "notes": "agent hint",
        },
        "data": {
            "body_metadata": {
                "planning_horizon_weeks": 17,
                "kpi_profile_ref": "des_brevet_200_400_km_masters",
                "athlete_profile_ref": "athlete_profile__i150546__20260315_091949",
                "moving_time_rate_guidance": {
                    "segment": "fast_competitive",
                    "w_per_kg": {"min": 2.2, "max": 2.8},
                    "kj_per_kg_per_hour": {"min": 7.9, "max": 10.1},
                    "notes": "Moving-time guidance.",
                },
                "body_mass_kg": 92.0,
            },
            "season_intent_principles": {
                "season_objective": "Build durable endurance for the A event.",
                "success_definition": "event-focused",
                "non_negotiable_principles": ["Protect fixed rest days."],
                "kJ_corridor_design_notes": ["Use deterministic load corridors."],
            },
            "phases": [
                {
                    "phase_id": "P01",
                    "name": "Base",
                    "date_range": {"from": "2026-05-18", "to": "2026-06-07"},
                    "iso_week_range": "2026-21--2026-23",
                    "cycle": "Base",
                    "deload": True,
                    "deload_rationale": "Conservative opening block.",
                    "narrative": "Restore durable aerobic consistency.",
                    "overview": {
                        "core_focus_and_characteristics": ["Endurance consistency."],
                        "phase_goals": {
                            "primary": "Restore consistency.",
                            "secondary": "Protect recovery.",
                        },
                        "metabolic_focus": "Aerobic endurance.",
                        "expected_adaptations": ["Improved durability."],
                        "evaluation_focus": ["Consistency."],
                        "phase_exit_assumptions": ["No unresolved fatigue."],
                        "typical_duration_intensity_pattern": "Endurance only.",
                        "non_negotiables": ["No threshold work."],
                    },
                    "weekly_load_corridor": {
                        "weekly_kj": {
                            "min": 7426,
                            "max": 9901,
                            "kj_per_kg_min": 81,
                            "kj_per_kg_max": 108,
                            "notes": "Reference mass 92 kg.",
                        }
                    },
                    "allowed_forbidden_semantics": {
                        "allowed_intensity_domains": ["ENDURANCE"],
                        "allowed_load_modalities": ["NONE"],
                        "forbidden_intensity_domains": ["SWEET_SPOT", "THRESHOLD", "VO2MAX"],
                    },
                    "structural_emphasis": {
                        "typical_focus": "Long endurance.",
                        "not_emphasized": "High intensity.",
                    },
                    "events_constraints": [],
                }
            ],
            "global_constraints": {
                "availability_assumptions": ["Fixed rest days Mon and Fri."],
                "planned_event_windows": ["2026-09-12 (A)"],
                "risk_constraints": ["Missed blocks require replan."],
                "recovery_protection": {
                    "fixed_rest_days": ["Mon", "Fri"],
                    "notes": ["Rest days are locked."],
                },
            },
            "season_load_envelope": {
                "expected_average_weekly_kj_range": {"min": 7426, "max": 9901},
                "expected_high_load_weeks_count": 7,
                "expected_deload_or_low_load_weeks_count": 6,
            },
            "assumptions_unknowns": {
                "assumptions": ["Availability remains stable."],
                "uncertainties": ["Illness may force replanning."],
                "revisit_items": ["Review before peak."],
            },
            "phase_transitions_guardrails": {
                "expected_progression": "P01 to P05 in order.",
                "conservative_triggers": ["Unresolved fatigue."],
                "absolute_no_go_rules": ["No rest-day override."],
            },
            "justification": {
                "summary": "Scenario-driven macrocycle.",
                "citations": [
                    {
                        "source_type": "evidence",
                        "source_id": "athlete_state_snapshot",
                        "section": "resolved context",
                        "rationale": "Loads derive from runtime context.",
                    }
                ],
                "phase_justifications": [
                    {
                        "phase_id": "P01",
                        "intensity_distribution": "ENDURANCE.",
                        "overload_pattern": "Conservative.",
                        "kJ_first_statement": "Stay inside corridor.",
                        "citations": ["athlete_state_snapshot"],
                    }
                ],
            },
            "principles_scientific_foundation": {
                "principle_applications": [
                    {"principle": "Specificity", "influence": "Endurance focus."}
                ],
                "scientific_foundation": {
                    "publications": [
                        {
                            "authors": "Mujika and Padilla",
                            "year": 2003,
                            "title": "Scientific bases for precompetition tapering strategies",
                            "link": "https://pubmed.ncbi.nlm.nih.gov/12744717/",
                        }
                    ],
                    "plan_alignment_check": "Aligned.",
                    "rationale": "Durability-first.",
                },
            },
            "explicit_forbidden_content": [
                "phase definitions (phase plans)",
                "weekly schedules",
                "day-by-day structure",
                "workouts or interval prescriptions",
                "numeric progression rules",
                "daily or session-level kJ targets",
            ],
            "self_check": {
                "planning_horizon_is_at_least_8_weeks": True,
                "every_phase_defines_weekly_kj_corridor": True,
                "every_phase_includes_kj_per_kg_guardrails_and_reference_mass": True,
                "every_phase_maps_to_cycle_and_deload_intent": True,
                "every_phase_includes_narrative_and_metabolic_focus": True,
                "every_phase_includes_evaluation_focus_and_exit_assumptions": True,
                "season_load_envelope_and_assumptions_documented": True,
                "principles_and_scientific_foundation_documented": True,
                "allowed_forbidden_domains_listed": True,
                "no_phase_or_week_planning_content": True,
                "header_includes_implements_iso_week_range_trace": True,
            },
        },
    }


def test_meta_builder_canonicalizes_schema_fields_and_trace_version_keys() -> None:
    schema = GuardedValidatedStore(
        athlete_id="i150546",
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime"),
    ).schemas.get_schema("season_plan.schema.json")
    document = _minimal_season_plan_document()

    normalized = canonicalize_artifact_envelope_meta(
        document,
        artifact_type=ArtifactType.SEASON_PLAN,
        schema=schema,
        run_id="ui_season_plan_2026W21_20260518_190440",
    )

    meta = normalized["meta"]
    assert meta["schema_id"] == "SeasonPlanInterface"
    assert meta["owner_agent"] == "Season-Artifact-Writer"
    assert meta["version"] == "1.0"
    assert meta["run_id"] == "ui_season_plan_2026W21_20260518_190440"
    assert meta["trace_upstream"][0]["schema_version"] == "1.0"
    assert meta["trace_upstream"][0]["version"] == "1.0"
    assert meta["trace_upstream"][0]["version_key"] == "20260315_091949"
    assert document["meta"]["schema_id"] == "season_plan.schema.json"


def test_meta_builder_wraps_data_only_payload_for_envelope_schema() -> None:
    schema = GuardedValidatedStore(
        athlete_id="i150546",
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime"),
    ).schemas.get_schema("season_plan.schema.json")
    document = _minimal_season_plan_document()

    normalized = canonicalize_artifact_envelope_meta(
        document["data"],
        artifact_type=ArtifactType.SEASON_PLAN,
        schema=schema,
        run_id="run-1",
    )

    assert set(normalized) == {"meta", "data"}
    assert normalized["meta"]["schema_id"] == "SeasonPlanInterface"
    assert normalized["data"] == document["data"]


def test_guarded_store_persists_season_plan_with_agent_owned_bad_meta(tmp_path) -> None:
    store = GuardedValidatedStore(
        athlete_id="i150546",
        schema_dir=Path("specs/schemas"),
        workspace_root=tmp_path,
    )

    result = store.guard_put_validated(
        output_spec=OUTPUT_SPECS[AgentTask.CREATE_SEASON_PLAN],
        document=_minimal_season_plan_document(),
        run_id="ui_season_plan_2026W21_20260518_190440",
        producer_agent="season_planner",
    )

    saved = store.store.load_version(
        "i150546",
        ArtifactType.SEASON_PLAN,
        str(result["version_key"]),
    )
    meta = saved["meta"]
    assert meta["schema_id"] == "SeasonPlanInterface"
    assert meta["owner_agent"] == "Season-Artifact-Writer"
    assert meta["trace_upstream"][0]["version_key"] == "20260315_091949"
