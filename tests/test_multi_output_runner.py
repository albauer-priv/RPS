import logging
from pathlib import Path
from types import SimpleNamespace

from rps.agents import multi_output_runner
from rps.agents.knowledge_injection import (
    build_injection_block,
    extract_load_estimation_section,
    resolve_agent_injection_items,
)


def test_normalize_phase_guardrails_flattens_recovery_rules_list():
    document = {
        "meta": {"artifact_type": "PHASE_GUARDRAILS"},
        "data": {
            "execution_non_negotiables": {
                "recovery_protection_rules": [
                    "Keep Monday easy.",
                    "Protect long-ride recovery.",
                ]
            },
            "load_guardrails": {"weekly_kj_bands": []},
        },
    }

    normalized = multi_output_runner.normalize_phase_guardrails_document(document)

    assert (
        normalized["data"]["execution_non_negotiables"]["recovery_protection_rules"]
        == "Keep Monday easy. | Protect long-ride recovery."
    )


def test_normalize_phase_guardrails_preserves_degenerate_band():
    document = {
        "meta": {"artifact_type": "PHASE_GUARDRAILS"},
        "data": {
            "load_guardrails": {
                "weekly_kj_bands": [
                    {"week": "2026-17", "band": {"min": 8470, "max": 8470, "notes": "S5 Level 5"}}
                ]
            }
        },
    }

    normalized = multi_output_runner.normalize_phase_guardrails_document(document)

    band = normalized["data"]["load_guardrails"]["weekly_kj_bands"][0]["band"]
    assert band["min"] == 8470.0
    assert band["max"] == 8470.0


def test_build_injection_block_for_phase_architect_includes_required_docs():
    combined = build_injection_block("phase_architect", mode="phase_guardrails")

    assert "file_naming_spec.md" in combined
    assert "principles_durability_first_cycling.md" in combined
    assert "season__phase_contract.md" in combined
    assert "phase_guardrails.schema.json" in combined
    assert "zone_model.schema.json" in combined


def test_week_planner_prompt_treats_availability_as_shared_latest():
    prompt_path = Path(__file__).resolve().parents[1] / "prompts" / "agents" / "week_planner.md"
    prompt_text = prompt_path.read_text(encoding="utf-8")

    assert "latest valid state remains authoritative until replaced" in prompt_text
    assert "must cover target week" not in prompt_text


def test_week_planner_prompt_forbids_hyphenated_loop_headers():
    prompt_path = Path(__file__).resolve().parents[1] / "prompts" / "agents" / "week_planner.md"
    prompt_text = prompt_path.read_text(encoding="utf-8")

    assert "valid loop header: `3x`" in prompt_text
    assert "invalid loop header: `- 3x`" in prompt_text


def test_week_planner_prompt_uses_wellness_body_mass_for_kpi_gating():
    prompt_path = Path(__file__).resolve().parents[1] / "prompts" / "agents" / "week_planner.md"
    prompt_text = prompt_path.read_text(encoding="utf-8")

    assert "WELLNESS.data.body_mass_kg" in prompt_text
    assert "authoritative and required body-mass value" in prompt_text


def test_planner_prompts_honor_resolved_context_blocks():
    prompts_dir = Path(__file__).resolve().parents[1] / "prompts" / "agents"
    for name in ("week_planner.md", "phase_architect.md", "season_planner.md"):
        prompt_text = (prompts_dir / name).read_text(encoding="utf-8")
        assert "Resolved ... Context" in prompt_text
        assert "Do NOT search, infer, or reinterpret the same facts again" in prompt_text


def test_normalize_season_scenarios_uses_last_planning_event_week():
    document = {
        "meta": {
            "artifact_type": "SEASON_SCENARIOS",
            "iso_week": "2026-17",
            "iso_week_range": "2026-17--2026-34",
            "temporal_scope": {"from": "2026-04-20", "to": "2026-08-23"},
            "trace_data": [
                {"artifact": "ATHLETE_PROFILE", "run_id": "athlete"},
                {"artifact": "PLANNING_EVENTS", "run_id": "events"},
                {"artifact": "LOGISTICS", "run_id": "logistics"},
            ],
            "trace_events": [
                {"artifact": "PLANNING_EVENTS", "run_id": "events"},
                {"artifact": "LOGISTICS", "run_id": "logistics"},
            ],
        },
        "data": {
            "planning_horizon_weeks": 18,
            "scenarios": [
                {
                    "scenario_id": "B",
                    "scenario_guidance": {
                        "deload_cadence": "3:1",
                        "phase_length_weeks": 4,
                        "phase_count_expected": 5,
                        "max_shortened_phases": 2,
                        "shortening_budget_weeks": 2,
                        "phase_plan_summary": {
                            "full_phases": 4,
                            "shortened_phases": [{"len": 3, "count": 2}],
                        },
                    },
                },
                {
                    "scenario_id": "C",
                    "scenario_guidance": {
                        "deload_cadence": "2:1",
                        "phase_length_weeks": 3,
                        "phase_count_expected": 6,
                        "max_shortened_phases": 2,
                        "shortening_budget_weeks": 0,
                        "phase_plan_summary": {"full_phases": 6, "shortened_phases": []},
                    },
                },
            ],
        },
    }
    planning_events = {
        "data": {
            "events": [
                {"type": "B", "date": "2026-04-25"},
                {"type": "A", "date": "2026-05-16"},
                {"type": "A", "date": "2026-09-12"},
            ]
        }
    }

    normalized = multi_output_runner.normalize_season_scenarios_document(
        document,
        planning_events_document=planning_events,
    )

    assert normalized["meta"]["iso_week_range"] == "2026-17--2026-37"
    assert normalized["meta"]["temporal_scope"] == {"from": "2026-04-20", "to": "2026-09-13"}
    assert normalized["data"]["planning_horizon_weeks"] == 21
    assert normalized["meta"]["trace_data"] == [
        {"artifact": "ATHLETE_PROFILE", "version": "1.0", "run_id": "athlete"},
        {"artifact": "LOGISTICS", "version": "1.0", "run_id": "logistics"},
    ]
    assert normalized["meta"]["trace_events"] == [
        {"artifact": "PLANNING_EVENTS", "version": "1.0", "run_id": "events"},
    ]

    scenario_b = normalized["data"]["scenarios"][0]["scenario_guidance"]
    assert scenario_b["phase_count_expected"] == 6
    assert scenario_b["shortening_budget_weeks"] == 3
    assert scenario_b["phase_plan_summary"] == {
        "full_phases": 4,
        "shortened_phases": [{"len": 3, "count": 1}, {"len": 2, "count": 1}],
    }

    scenario_c = normalized["data"]["scenarios"][1]["scenario_guidance"]
    assert scenario_c["phase_count_expected"] == 7
    assert scenario_c["max_shortened_phases"] == 0
    assert scenario_c["shortening_budget_weeks"] == 0
    assert scenario_c["phase_plan_summary"] == {"full_phases": 7, "shortened_phases": []}


def test_normalize_season_scenarios_never_emits_one_week_shortened_phase():
    document = {
        "meta": {
            "artifact_type": "SEASON_SCENARIOS",
            "iso_week": "2026-17",
            "iso_week_range": "2026-17--2026-20",
        },
        "data": {
            "planning_horizon_weeks": 21,
            "scenarios": [
                {
                    "scenario_id": "A",
                    "scenario_guidance": {
                        "deload_cadence": "3:1",
                        "phase_length_weeks": 4,
                        "max_shortened_phases": 1,
                    },
                }
            ],
        },
    }

    normalized = multi_output_runner.normalize_season_scenarios_document(document)
    summary = normalized["data"]["scenarios"][0]["scenario_guidance"]["phase_plan_summary"]

    assert summary == {
        "full_phases": 4,
        "shortened_phases": [{"len": 3, "count": 1}, {"len": 2, "count": 1}],
    }


def test_normalize_season_scenarios_canonicalizes_intensity_domains():
    document = {
        "meta": {
            "artifact_type": "SEASON_SCENARIOS",
            "iso_week": "2026-17",
            "iso_week_range": "2026-17--2026-19",
        },
        "data": {
            "planning_horizon_weeks": 3,
            "scenarios": [
                {
                    "scenario_id": "A",
                    "scenario_guidance": {
                        "deload_cadence": "2:1",
                        "phase_length_weeks": 3,
                        "intensity_guidance": {
                            "allowed_domains": [
                                "ENDURANCE",
                                "HIGH_INTENSITY_DENSITY",
                                "TEMPO",
                                "TEMPO",
                            ],
                            "avoid_domains": [
                                "LIMITED_VO2MAX",
                                "VO2MAX",
                                "ENDURANCE",
                                "RECOVERY",
                                "NONE",
                            ],
                        },
                    },
                }
            ],
        },
    }

    normalized = multi_output_runner.normalize_season_scenarios_document(document)
    guidance = normalized["data"]["scenarios"][0]["scenario_guidance"]["intensity_guidance"]

    assert guidance["allowed_domains"] == ["ENDURANCE_LOW", "TEMPO"]
    assert guidance["avoid_domains"] == ["VO2MAX"]


def test_season_scenario_prompt_delegates_calendar_math_to_runtime():
    prompt_path = Path(__file__).resolve().parents[1] / "prompts" / "agents" / "season_scenario.md"
    prompt_text = prompt_path.read_text(encoding="utf-8")

    assert "runtime canonicalizes deterministic calendar/math fields before store" in prompt_text.lower()
    assert "phase_count_expected = ceil(planning_horizon_weeks / phase_length_weeks)" not in prompt_text


def test_build_injection_block_for_season_scenario_excludes_selection_schema_noise():
    combined = build_injection_block("season_scenario", mode="scenario")

    assert "season_scenario_selection_interface_spec.md" not in combined
    assert "season_scenario_selection.schema.json" not in combined
    assert "agenda_enum_spec.md" not in combined


def test_build_injection_block_for_season_planner_uses_season_section():
    combined = build_injection_block("season_planner", mode="season_plan")
    items = resolve_agent_injection_items("season_planner", mode="season_plan")
    load_spec = next(
        item
        for item in items
        if isinstance(item, dict) and item.get("label") == "LoadEstimationSpec"
    )

    assert "LoadEstimationSpec" in combined
    assert load_spec.get("section") == "season"


def test_extract_load_estimation_section_for_season_excludes_phase_corridor_rules():
    source = (
        Path(__file__).resolve().parents[1]
        / "specs"
        / "knowledge"
        / "_shared"
        / "sources"
        / "specs"
        / "load_estimation_spec.md"
    ).read_text(encoding="utf-8")

    season_only = extract_load_estimation_section(source, "season")

    assert "## 3) Per-Workout Load Estimation (Binding)" in season_only
    assert "### 5.1 Season-Planner" in season_only
    assert "## 4) Weekly Corridor Derivation (Phase-Architect) (Binding)" not in season_only
    assert "### 5.2 Phase-Architect" not in season_only


def test_extract_load_estimation_section_for_general_plus_phase_includes_phase_rules():
    source = (
        Path(__file__).resolve().parents[1]
        / "specs"
        / "knowledge"
        / "_shared"
        / "sources"
        / "specs"
        / "load_estimation_spec.md"
    ).read_text(encoding="utf-8")

    phase_bundle = extract_load_estimation_section(source, "general+phase")

    assert "## 4) Weekly Corridor Derivation (Phase-Architect) (Binding)" in phase_bundle
    assert "### 5.2 Phase-Architect" in phase_bundle
    assert "### 5.1 Season-Planner" not in phase_bundle


def test_injection_mode_for_tasks_returns_expected_mode():
    mode = multi_output_runner.injection_mode_for_tasks([multi_output_runner.AgentTask.CREATE_PHASE_GUARDRAILS])

    assert mode == "phase_guardrails"


def test_run_agent_multi_output_skips_forced_store_on_terminal_stop(monkeypatch):
    create_calls: list[dict[str, object]] = []

    def _fake_create_response(client, payload, logger, stream_handlers=None):
        del client, logger, stream_handlers
        create_calls.append(payload)
        return multi_output_runner.LiteLLMResponse(
            id="resp_1",
            output=[],
            output_text=(
                "STOP_REASON: Required binding artefact invalid.\n"
                'MISSING_BINDING_ARTEFACTS: ["KPI_PROFILE"]\n'
                'NEXT_ACTION: ["Fix KPI profile metadata"]'
            ),
            usage=None,
        )

    def _fail_guard_put_validated(*args, **kwargs):
        raise AssertionError("guard_put_validated must not run for terminal STOP responses")

    monkeypatch.setattr(multi_output_runner, "create_response", _fake_create_response)
    monkeypatch.setattr(
        multi_output_runner.GuardedValidatedStore,
        "guard_put_validated",
        _fail_guard_put_validated,
    )

    runtime = multi_output_runner.AgentRuntime(
        client=SimpleNamespace(config=None),
        model="openai/gpt-5.4-mini",
        temperature=None,
        reasoning_effort=None,
        reasoning_summary=None,
        max_completion_tokens=None,
        prompt_loader=SimpleNamespace(combined_system_prompt=lambda agent_name: f"prompt for {agent_name}"),
        vs_resolver=SimpleNamespace(id_for_store_name=lambda store_name: store_name),
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime"),
    )

    result = multi_output_runner.run_agent_multi_output(
        runtime,
        agent_name="performance_analysis",
        agent_vs_name="vs_rps_all_agents",
        athlete_id="i150546",
        tasks=[multi_output_runner.AgentTask.CREATE_DES_ANALYSIS_REPORT],
        user_input="Analyze week 2026-15.",
        run_id="run_123",
    )

    assert result["ok"] is False
    assert result["error"] == "MODEL_STOPPED_ON_BLOCKER"
    assert "produced" in result and result["produced"] == {}
    assert len(create_calls) == 1


def test_run_agent_multi_output_logs_week_sensitive_tool_warnings(monkeypatch, caplog):
    responses = [
        multi_output_runner.LiteLLMResponse(
            id="resp_warn_1",
            output=[
                {
                    "type": "function_call",
                    "name": "workspace_get_latest",
                    "arguments": '{"artifact_type":"ACTIVITIES_TREND"}',
                    "call_id": "call_1",
                }
            ],
            output_text="",
            usage=None,
        ),
        multi_output_runner.LiteLLMResponse(
            id="resp_warn_2",
            output=[],
            output_text="",
            usage=None,
        ),
    ]

    def _fake_create_response(client, payload, logger, stream_handlers=None):
        del client, payload, logger, stream_handlers
        return responses.pop(0)

    monkeypatch.setattr(multi_output_runner, "create_response", _fake_create_response)
    monkeypatch.setattr(
        multi_output_runner,
        "read_tool_handlers",
        lambda ctx: {
            "workspace_get_latest": lambda args: {
                "ok": True,
                "artifact_type": args["artifact_type"],
                "_tool_warning": "ACTIVITIES_TREND is week-sensitive. Prefer workspace_get_version.",
            }
        },
    )

    runtime = multi_output_runner.AgentRuntime(
        client=SimpleNamespace(config=None),
        model="openai/gpt-5.4-mini",
        temperature=None,
        reasoning_effort=None,
        reasoning_summary=None,
        max_completion_tokens=None,
        prompt_loader=SimpleNamespace(combined_system_prompt=lambda agent_name: f"prompt for {agent_name}"),
        vs_resolver=SimpleNamespace(id_for_store_name=lambda store_name: store_name),
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime"),
    )

    with caplog.at_level(logging.WARNING, logger="rps.agents.multi_output_runner"):
        result = multi_output_runner.run_agent_multi_output(
            runtime,
            agent_name="coach",
            agent_vs_name="vs_rps_all_agents",
            athlete_id="i150546",
            tasks=[],
            user_input="Summarize current status.",
            run_id="run_warn",
        )

    assert result["ok"] is True
    assert "week-sensitive" in caplog.text


def test_optional_missing_feed_forward_reads_log_at_info(monkeypatch, caplog):
    responses = [
        multi_output_runner.LiteLLMResponse(
            id="resp_optional_1",
            output=[
                {
                    "type": "function_call",
                    "name": "workspace_get_version",
                    "arguments": '{"artifact_type":"SEASON_PHASE_FEED_FORWARD","version_key":"2026-17"}',
                    "call_id": "call_optional_1",
                }
            ],
            output_text="",
            usage=None,
        ),
        multi_output_runner.LiteLLMResponse(
            id="resp_optional_2",
            output=[],
            output_text="",
            usage=None,
        ),
    ]

    def _fake_create_response(client, payload, logger, stream_handlers=None):
        del client, payload, logger, stream_handlers
        return responses.pop(0)

    monkeypatch.setattr(multi_output_runner, "create_response", _fake_create_response)
    monkeypatch.setattr(
        multi_output_runner,
        "read_tool_handlers",
        lambda ctx: {
            "workspace_get_version": lambda args: (_ for _ in ()).throw(
                FileNotFoundError(
                    f"No artifact version found: runtime/athletes/i150546/data/plans/season/season_phase_feed_forward_{args['version_key']}.json"
                )
            )
        },
    )

    runtime = multi_output_runner.AgentRuntime(
        client=SimpleNamespace(config=None),
        model="openai/gpt-5.4-mini",
        temperature=None,
        reasoning_effort=None,
        reasoning_summary=None,
        max_completion_tokens=None,
        prompt_loader=SimpleNamespace(combined_system_prompt=lambda agent_name: f"prompt for {agent_name}"),
        vs_resolver=SimpleNamespace(id_for_store_name=lambda store_name: store_name),
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime"),
    )

    with caplog.at_level(logging.INFO, logger="rps.agents.multi_output_runner"):
        result = multi_output_runner.run_agent_multi_output(
            runtime,
            agent_name="phase_architect",
            agent_vs_name="vs_rps_all_agents",
            athlete_id="i150546",
            tasks=[],
            user_input="Load optional feed forward context.",
            run_id="run_optional",
        )

    assert result["ok"] is True
    assert "Optional read tool missing workspace_get_version" in caplog.text
    assert "Read tool failed workspace_get_version" not in caplog.text
