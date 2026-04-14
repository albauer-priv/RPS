from pathlib import Path

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


def test_build_injection_block_for_phase_architect_includes_required_docs():
    combined = build_injection_block("phase_architect", mode="phase_guardrails")

    assert "file_naming_spec.md" in combined
    assert "principles_durability_first_cycling.md" in combined
    assert "season__phase_contract.md" in combined
    assert "phase_guardrails.schema.json" in combined
    assert "zone_model.schema.json" in combined


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
