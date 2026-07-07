from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from rps.agents.crewai_bundle_normalization import (
    _normalize_final_season_plan_semantics,
    _normalize_publication_link,
)
from rps.agents.crewai_context_blocks import (
    _contract_context_blocks_for_task,
)
from rps.crewai_runtime import load_crewai_config_bundle
from rps.crewai_runtime.bindings import (
    build_agent_blueprints,
    build_task_blueprints,
)
from rps.crewai_runtime.guardrails import (
    artifact_envelope_basic,
    artifact_schema_valid,
    guardrail_runtime_context,
)
from rps.crewai_runtime.models import (
    PhaseDraftBundleModel,
    PhaseWeekDraftBlueprintModel,
    SeasonEventAnchorModel,
    SeasonLoadEnvelopeModel,
    SeasonMacrocycleDraftModel,
    SeasonPhaseBlueprintModel,
    SeasonPhaseDraftBlueprintModel,
    SeasonPhaseSemanticContractModel,
    SeasonPlanBundleModel,
    SeasonPlanDraftBundleModel,
)


def test_normalize_final_season_plan_semantics_enriches_trace_and_guardrails() -> None:
    def _input_payload(artifact: str, version_key: str, run_id: str) -> dict[str, object]:
        return {
            "meta": {
                "artifact_type": artifact,
                "version": "1.0",
                "schema_version": "1.0",
                "version_key": version_key,
                "run_id": run_id,
            }
        }

    document = {
        "meta": {
            "artifact_type": "SEASON_PLAN",
            "data_confidence": "HIGH",
            "trace_data": [
                {
                    "artifact": "ACTIVITIES_ACTUAL",
                    "version": "1.0",
                    "schema_version": "1.0",
                    "version_key": "2026-21",
                    "run_id": "run-actual",
                }
            ],
            "trace_events": [],
        },
        "data": {
            "season_intent_principles": {
                "season_objective": "Strong execution over 200 km with durability reserve for longer brevet demands."
            },
            "phases": [
                {
                    "phase_id": "P02",
                    "phase_intent": "durability_build",
                    "phase_type": "BUILD",
                    "build_subtype": "durability_build",
                    "weekly_load_corridor": {"weekly_kj": {"notes": ""}},
                    "overview": {"non_negotiables": []},
                },
                {
                    "phase_id": "P04",
                    "phase_intent": "taper_freshening",
                    "phase_type": "TAPER",
                    "build_subtype": None,
                    "weekly_load_corridor": {"weekly_kj": {"notes": ""}},
                    "overview": {"non_negotiables": []},
                },
            ],
            "assumptions_unknowns": {"revisit_items": []},
            "justification": {"phase_justifications": []},
            "principles_scientific_foundation": {
                "principle_applications": [{"principle": "Durability-first", "influence": "Season remains durability-led."}],
                "scientific_foundation": {
                    "publications": [
                        {
                            "authors": "Mujika, I., & Padilla, S.",
                            "year": 2003,
                            "title": "Scientific bases for precompetition tapering strategies",
                            "link": "https://pubmed.ncbi.nlm.nih.gov/12495777/",
                        },
                        {
                            "authors": "Stöggl, T. L., & Sperlich, B.",
                            "year": 2014,
                            "title": "Polarized training has greater impact on key endurance variables than threshold, high intensity, or high volume training",
                            "link": "https://pubmed.ncbi.nlm.nih.gov/24549140/",
                        },
                    ]
                },
            },
            "phase_transitions_guardrails": {
                "conservative_triggers": [],
                "absolute_no_go_rules": [],
            },
        },
    }
    season_phase_load_context = {
        "season_allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
        "phases": [
            {
                "phase_id": "P02",
                "phase_intent": "durability_build",
                "phase_type": "BUILD",
                "build_subtype": "durability_build",
                "role_week_load_bands": [],
                "event_taper_trace": {"events": []},
            },
            {
                "phase_id": "P04",
                "phase_intent": "taper_freshening",
                "phase_type": "TAPER",
                "build_subtype": None,
                "role_week_load_bands": [],
                "event_taper_trace": {"events": [{"date": "2026-09-12", "type": "A"}]},
            },
        ],
    }
    approved_planning_bundle = {
        "phase_blueprints": [
            {
                "phase_id": "P02",
                "allowed_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
                "forbidden_domains": ["VO2MAX"],
                "allowed_load_modalities": ["NONE", "K3"],
            },
            {
                "phase_id": "P04",
                "allowed_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
                "forbidden_domains": ["THRESHOLD", "VO2MAX"],
                "allowed_load_modalities": ["NONE"],
            },
        ]
    }
    with guardrail_runtime_context(
        season_phase_load_context=season_phase_load_context,
        selected_scenario_contract={
            "selected_scenario_id": "B",
            "load_posture": "balanced_progressive",
            "recovery_margin": "medium",
            "fatigue_exposure": "moderate",
            "specificity_density": "controlled",
        },
        approved_planning_bundle=approved_planning_bundle,
        athlete_profile_payload=_input_payload("ATHLETE_PROFILE", "profile_v1", "run-profile"),
        kpi_profile_payload=_input_payload("KPI_PROFILE", "kpi_v1", "run-kpi"),
        availability_payload=_input_payload("AVAILABILITY", "avail_v1", "run-avail"),
        logistics_payload=_input_payload("LOGISTICS", "log_v1", "run-log"),
        planning_events_payload=_input_payload("PLANNING_EVENTS", "events_v1", "run-events"),
        zone_model_payload=_input_payload("ZONE_MODEL", "zone_v1", "run-zone"),
    ):
        normalized = _normalize_final_season_plan_semantics(document)

    trace_data_artifacts = {entry["artifact"] for entry in normalized["meta"]["trace_data"]}
    trace_event_artifacts = {entry["artifact"] for entry in normalized["meta"]["trace_events"]}
    assert {"ATHLETE_PROFILE", "KPI_PROFILE", "AVAILABILITY", "LOGISTICS", "ZONE_MODEL"}.issubset(trace_data_artifacts)
    assert "PLANNING_EVENTS" in trace_event_artifacts
    publications = normalized["data"]["principles_scientific_foundation"]["scientific_foundation"]["publications"]
    assert any(pub["link"] == "https://pubmed.ncbi.nlm.nih.gov/12840640/" for pub in publications)
    assert any(pub["link"] == "https://pubmed.ncbi.nlm.nih.gov/24550842/" for pub in publications)
    durability_non_negotiables = normalized["data"]["phases"][0]["overview"]["non_negotiables"]
    taper_non_negotiables = normalized["data"]["phases"][1]["overview"]["non_negotiables"]
    assert any("readiness" in item.lower() for item in durability_non_negotiables)
    assert any("load-band labels only" in item.lower() for item in taper_non_negotiables)
    assert any(
        "first Build phase" in item or "first Build" in item
        for item in normalized["data"]["phase_transitions_guardrails"]["conservative_triggers"]
    )
    assert any(
        "load-band labels only" in item.lower()
        for item in normalized["data"]["phase_transitions_guardrails"]["absolute_no_go_rules"]
    )
    assert normalized["data"]["selected_scenario_contract"]["selected_scenario_id"] == "B"

def test_normalize_final_season_plan_semantics_deduplicates_trace_data_by_artifact_and_version_key() -> None:
    document = {
        "meta": {
            "artifact_type": "SEASON_PLAN",
            "trace_data": [
                {
                    "artifact": "ATHLETE_PROFILE",
                    "version": "1.0",
                    "schema_version": "1.0",
                    "version_key": "profile_v1",
                    "run_id": "raw-run",
                },
                {
                    "artifact": "AVAILABILITY",
                    "version": "1.0",
                    "schema_version": "1.0",
                    "version_key": "avail_v1",
                    "run_id": "raw-avail-run",
                },
            ],
            "trace_events": [],
        },
        "data": {
            "season_intent_principles": {"season_objective": "Strong 200 km A-event execution."},
            "phases": [],
            "assumptions_unknowns": {"revisit_items": []},
        },
    }

    def _input_payload(artifact: str, version_key: str, run_id: str) -> dict[str, object]:
        return {
            "meta": {
                "artifact_type": artifact,
                "version": "1.0",
                "schema_version": "1.0",
                "version_key": version_key,
                "run_id": run_id,
            }
        }

    with guardrail_runtime_context(
        athlete_profile_payload=_input_payload("ATHLETE_PROFILE", "profile_v1", "resolved-run"),
        availability_payload=_input_payload("AVAILABILITY", "avail_v1", "resolved-avail-run"),
    ):
        normalized = _normalize_final_season_plan_semantics(document)

    trace_data = normalized["meta"]["trace_data"]
    assert len([entry for entry in trace_data if entry["artifact"] == "ATHLETE_PROFILE"]) == 1
    assert len([entry for entry in trace_data if entry["artifact"] == "AVAILABILITY"]) == 1
    assert next(entry for entry in trace_data if entry["artifact"] == "ATHLETE_PROFILE")["run_id"] == "resolved-run"
    assert next(entry for entry in trace_data if entry["artifact"] == "AVAILABILITY")["run_id"] == "resolved-avail-run"

def test_normalize_final_season_plan_semantics_replaces_indirect_season_lineage_with_stored_run_ids() -> None:
    document = {
        "meta": {
            "artifact_type": "SEASON_PLAN",
            "trace_upstream": [
                {
                    "artifact": "SEASON_SCENARIO_SELECTION",
                    "version": "1.0",
                    "schema_version": "1.0",
                    "version_key": "2026-24__20260611_093936",
                    "run_id": "20260611_093936",
                },
                {
                    "artifact": "SEASON_SCENARIOS",
                    "version": "1.0",
                    "schema_version": "1.0",
                    "version_key": "2026-24__20260611_093850",
                    "run_id": "20260611_093850",
                },
            ],
            "trace_data": [],
            "trace_events": [],
        },
        "data": {
            "season_intent_principles": {"season_objective": "Strong 200 km A-event execution."},
            "phases": [],
            "assumptions_unknowns": {"revisit_items": []},
        },
    }

    with guardrail_runtime_context(
        season_scenario_selection_payload={
            "meta": {
                "artifact_type": "SEASON_SCENARIO_SELECTION",
                "version": "1.0",
                "schema_version": "1.1",
                "version_key": "2026-24__20260611_093936",
                "run_id": "ui_selection_20260611_093936",
            }
        },
        season_scenarios_payload={
            "meta": {
                "artifact_type": "SEASON_SCENARIOS",
                "version": "1.0",
                "schema_version": "1.0",
                "version_key": "2026-24__20260611_093850",
                "run_id": "ui_scenarios_20260611_093850",
            }
        },
    ):
        normalized = _normalize_final_season_plan_semantics(document)

    assert normalized["meta"]["trace_upstream"] == [
        {
            "artifact": "SEASON_SCENARIO_SELECTION",
            "version": "1.0",
            "schema_version": "1.1",
            "version_key": "2026-24__20260611_093936",
            "run_id": "ui_selection_20260611_093936",
        },
        {
            "artifact": "SEASON_SCENARIOS",
            "version": "1.0",
            "schema_version": "1.0",
            "version_key": "2026-24__20260611_093850",
            "run_id": "ui_scenarios_20260611_093850",
        },
    ]

def test_taper_selection_rules_block_sweet_spot_extensive() -> None:
    rules_text = Path("config/planning/week_workout_selection_rules.yaml").read_text(encoding="utf-8")

    assert "row_id: TAPER-BLOCK-SST-EXTENSIVE" in rules_text
    assert "protocol_variant: SWEET_SPOT_EXTENSIVE" in rules_text
    assert "phase_intent: taper_freshening" in rules_text
    assert "allowed: false" in rules_text

def test_unknown_publication_links_fail_closed() -> None:
    assert _normalize_publication_link("Unverified study title", "https://example.com/paper") == ""

def test_skill_config_validation_rejects_non_operational_crew_skill(tmp_path: Path) -> None:
    root = tmp_path
    crewai_dir = root / "config" / "crewai"
    crewai_dir.mkdir(parents=True)
    (root / "skills").symlink_to(Path("skills").resolve(), target_is_directory=True)
    source_dir = Path("config/crewai")
    for name in [
        "agents.yaml",
        "tasks.yaml",
        "skills.yaml",
        "knowledge_sources.yaml",
        "memory_policy.yaml",
        "task_policies.yaml",
        "flow_persistence.yaml",
        "runtime_profiles.yaml",
    ]:
        (crewai_dir / name).write_text((source_dir / name).read_text(encoding="utf-8"), encoding="utf-8")
    skills_path = crewai_dir / "skills.yaml"
    skills_path.write_text(
        skills_path.read_text(encoding="utf-8").replace(
            "skills/shared/runtime-boundaries",
            "skills/week/revision-methodology",
            1,
        ),
        encoding="utf-8",
    )

    try:
        load_crewai_config_bundle(root=root)
    except ValueError as exc:
        assert "non-operational skills" in str(exc)
    else:  # pragma: no cover - defensive failure path
        raise AssertionError("Expected load_crewai_config_bundle() to reject a crew-level method skill.")

def test_runtime_profile_validation_rejects_unknown_model(tmp_path: Path) -> None:
    root = tmp_path
    crewai_dir = root / "config" / "crewai"
    crewai_dir.mkdir(parents=True)
    (root / "skills").symlink_to(Path("skills").resolve(), target_is_directory=True)
    source_dir = Path("config/crewai")
    for name in [
        "agents.yaml",
        "tasks.yaml",
        "skills.yaml",
        "knowledge_sources.yaml",
        "memory_policy.yaml",
        "task_policies.yaml",
        "flow_persistence.yaml",
        "runtime_profiles.yaml",
    ]:
        (crewai_dir / name).write_text((source_dir / name).read_text(encoding="utf-8"), encoding="utf-8")
    runtime_profiles_path = crewai_dir / "runtime_profiles.yaml"
    runtime_profiles_path.write_text(
        runtime_profiles_path.read_text(encoding="utf-8").replace("gpt-5.4-mini", "bad-model", 1),
        encoding="utf-8",
    )

    try:
        load_crewai_config_bundle(root=root)
    except ValueError as exc:
        assert "Unknown model references in runtime_profiles.yaml" in str(exc)
    else:  # pragma: no cover - defensive failure path
        raise AssertionError("Expected load_crewai_config_bundle() to reject an unknown runtime-profile model.")

def test_artifact_envelope_guardrail_rejects_missing_meta_and_accepts_basic_shape() -> None:
    ok, payload = artifact_envelope_basic(
        SimpleNamespace(
            raw=json.dumps({"meta": {"artifact_type": "WEEK_PLAN", "schema_id": "WeekPlanInterface"}, "data": {}})
        )
    )
    assert ok is True
    assert payload["meta"]["artifact_type"] == "WEEK_PLAN"

    failed, message = artifact_envelope_basic(SimpleNamespace(raw=json.dumps({"data": {}})))
    assert failed is False
    assert "top-level 'meta' and 'data'" in message

def test_artifact_schema_valid_guardrail_uses_concrete_json_schema() -> None:
    payload = {
        "meta": {
            "artifact_type": "SEASON_SCENARIO_SELECTION",
            "schema_id": "SeasonScenarioSelectionInterface",
            "schema_version": "1.1",
            "version": "1.0",
            "version_key": "2026-20__20260517_160725",
            "authority": "Informational",
            "owner_agent": "Season-Scenario-Agent",
            "run_id": "run-1",
            "created_at": "2026-05-17T16:07:25Z",
            "scope": "Season",
            "iso_week": "2026-20",
            "iso_week_range": "2026-20--2026-37",
            "temporal_scope": {"from": "2026-05-11", "to": "2026-09-13"},
            "trace_upstream": [],
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "UNKNOWN",
            "notes": "",
        },
        "data": {
            "season_scenarios_ref": "season_scenarios/latest.json",
            "selected_scenario_id": "B",
            "selection_source": "system",
            "selection_rationale": "Balanced choice.",
            "notes": ["ok"],
            "kpi_moving_time_rate_guidance_selection": None,
        },
    }

    ok, validated = artifact_schema_valid(payload)
    assert ok is True
    assert validated["data"]["selected_scenario_id"] == "B"

    invalid = json.loads(json.dumps(payload))
    invalid["data"]["selected_scenario_id"] = "D"
    failed, message = artifact_schema_valid(invalid)
    assert failed is False
    assert "season_scenario_selection.schema.json" in message
    assert "selected_scenario_id" in message

def test_artifact_schema_valid_normalizes_schema_sensitive_meta_before_validation() -> None:
    payload = {
        "meta": {
            "artifact_type": "SEASON_SCENARIO_SELECTION",
            "schema_id": "SeasonPlanInterface",
            "schema_version": "20260518_175726",
            "version": "2026-20",
            "version_key": "2026-20__20260517_160725",
            "authority": "Binding",
            "owner_agent": "Season-Planner",
            "run_id": "run-1",
            "created_at": "2026-05-17T16:07:25Z",
            "scope": "Season",
            "iso_week": "2026-20",
            "iso_week_range": "2026-20--2026-37",
            "temporal_scope": {"from": "2026-05-11", "to": "2026-09-13"},
            "trace_upstream": [
                {"artifact": "SEASON_SCENARIOS", "version": "20260518_103858", "run_id": "run-a"},
            ],
            "trace_data": [
                {"artifact": "ATHLETE_PROFILE", "version": "20260315_091949", "run_id": "run-b"},
            ],
            "trace_events": [
                {"artifact": "PLANNING_EVENTS", "version": "2026-20", "run_id": "run-c"},
            ],
            "data_confidence": "UNKNOWN",
            "notes": "",
        },
        "data": {
            "season_scenarios_ref": "season_scenarios/latest.json",
            "selected_scenario_id": "B",
            "selection_source": "system",
            "selection_rationale": "Balanced choice.",
            "notes": ["ok"],
            "kpi_moving_time_rate_guidance_selection": None,
        },
    }

    ok, validated = artifact_schema_valid(payload)

    assert ok is True
    meta = validated["meta"]
    assert meta["schema_id"] == "SeasonScenarioSelectionInterface"
    assert meta["schema_version"] == "1.1"
    assert meta["authority"] == "Informational"
    assert meta["owner_agent"] == "Season-Scenario-Agent"
    assert meta["version"] == "1.0"
    assert meta["trace_upstream"][0]["version"] == "1.0"
    assert meta["trace_upstream"][0]["version_key"] == "20260518_103858"
    assert meta["trace_data"][0]["version"] == "1.0"
    assert meta["trace_data"][0]["version_key"] == "20260315_091949"
    assert meta["trace_events"][0]["version"] == "1.0"
    assert meta["trace_events"][0]["version_key"] == "2026-20"

def test_season_plan_bundle_accepts_phase_blueprints_with_inherited_cadence_roles() -> None:
    model = SeasonPlanBundleModel(
        event_priority=SeasonEventAnchorModel(),
        macrocycle=SeasonMacrocycleDraftModel(deload_cadence="2:1:1", phase_length_weeks=4),
        season_load_envelope=SeasonLoadEnvelopeModel(
            expected_average_weekly_kj_range={"min": 7600, "max": 9300},
            expected_high_load_weeks_count=2,
            expected_deload_or_low_load_weeks_count=1,
        ),
        season_semantic_notes=["Frame the objective against the A event."],
        phase_blueprints=[
            SeasonPhaseBlueprintModel(
                phase_id="P03",
                iso_week_range="2026-26--2026-29",
                scenario_cadence="2:1:1",
                cadence_week_roles=["LOAD_1", "LOAD_2", "MINI_RESET", "RELOAD"],
                phase_type="BUILD",
                phase_intent="sst_build",
                build_subtype="sst_build",
                phase_taxonomy_version="canonical_phase_taxonomy_v1",
                event_constraints=[],
                load_corridor_min=7600,
                load_corridor_max=9300,
                availability_cap_kj=10000,
                baseline_load_kj=8000,
                season_phase_role="sst_build",
                role_week_load_bands=["2026-26 LOAD_1 min 7600 max 8400"],
                progression_trace=["source deterministic season phase load context"],
                load_feasibility_status="feasible",
                taper_intent="none",
                allowed_domains=["RECOVERY", "ENDURANCE", "TEMPO"],
                forbidden_domains=["THRESHOLD", "VO2MAX"],
                semantic_contract=SeasonPhaseSemanticContractModel(
                    methodology_family="extensive_subthreshold_build",
                    threshold_role="secondary",
                    event_load_policy="event_load_support_only",
                    taper_policy="not_applicable",
                    writer_semantic_notes=["Keep threshold secondary to SST-led work."],
                ),
            )
        ],
    )

    assert model.phase_blueprints[0].scenario_cadence == "2:1:1"
    assert model.phase_blueprints[0].cadence_week_roles == ["LOAD_1", "LOAD_2", "MINI_RESET", "RELOAD"]
    assert model.phase_blueprints[0].availability_cap_kj == 10000

def test_draft_bundle_models_accept_legacy_semantic_hints_before_normalization() -> None:
    season_model = SeasonPlanDraftBundleModel(
        event_priority=SeasonEventAnchorModel(),
        macrocycle=SeasonMacrocycleDraftModel(deload_cadence="2:1:1"),
        phase_blueprints=[
            SeasonPhaseDraftBlueprintModel(
                phase_id="P01",
                iso_week_range="2026-21--2026-23",
                scenario_cadence="2:1:1",
                phase_type="PREPARATION",
                phase_intent="base_preparation",
                role_week_load_bands=["legacy"],
            )
        ],
    )
    phase_model = PhaseDraftBundleModel(
        phase_range="2026-21--2026-23",
        phase_type="PREPARATION",
        phase_intent="base_preparation",
        week_blueprints=[
            PhaseWeekDraftBlueprintModel(
                week="2026-21",
                week_role="LOAD_2",
            )
        ],
        guardrails={"phase_summary": {}},
        structure={"upstream_intent": {}},
        preview={"phase_intent_summary": {}},
        constraint_audit={"blocking_issues": [], "warnings": [], "recommended_adjustments": [], "applied_sources": []},
        load_governance_audit={
            "blocking_issues": [],
            "warnings": [],
            "recommended_adjustments": [],
            "cadence_authority_preserved": True,
            "durability_first_respected": True,
        },
        decision_summary={"cadence_application_notes": [], "override_rationale": []},
    )

    assert season_model.phase_blueprints[0].phase_intent == "base_preparation"
    assert phase_model.week_blueprints[0].week_role == "LOAD_2"

def test_season_plan_finalize_declares_deterministic_contract_tools() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    blueprints = build_task_blueprints(bundle)

    assert blueprints["season_plan_finalize"].config["tools"] == [
        "workspace_get_phase_slot_contract",
        "workspace_get_season_phase_load_context",
    ]

def test_season_phase_blueprint_draft_declares_deterministic_contract_tools() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    blueprints = build_task_blueprints(bundle)

    assert blueprints["season_phase_blueprint_draft"].config["tools"] == [
        "workspace_get_phase_slot_contract",
        "workspace_get_season_phase_load_context",
    ]

def test_contract_context_blocks_for_season_finalize_include_bound_contracts() -> None:
    with guardrail_runtime_context(
        phase_slot_context={"phase_slots": [{"phase_id": "P01"}]},
        season_phase_load_context={"phases": [{"phase_id": "P01"}]},
    ):
        blocks = _contract_context_blocks_for_task(
            crew_name="season_planning",
            task_name="season_plan_finalize",
        )

    assert any("Deterministic Season Phase Slot Contract" in block for block in blocks)
    assert any("Deterministic Season Phase Load Contract" in block for block in blocks)
    assert any("Season audit-slot ownership" in block for block in blocks)
    assert any("Do not search the workspace" in block for block in blocks)

def test_season_plan_manager_disables_free_delegation_via_yaml_override() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    agent_blueprints = build_agent_blueprints(bundle)

    assert agent_blueprints["season_plan_manager"].config["allow_delegation"] is False
