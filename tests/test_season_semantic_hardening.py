from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_season_skills_preserve_inherited_cadence_semantics() -> None:
    synthesis = _read("skills/season/plan-synthesis/SKILL.md")
    audit = _read("skills/season/audit/SKILL.md")

    assert "inherited Scenario authority" in synthesis
    assert "must not replace it" in audit or "different cadence than the selected Scenario" in audit
    assert "MINI_RESET" in synthesis or "mini-reset" in synthesis
    assert "RELOAD" in synthesis or "reload" in synthesis
    assert "target macrocycles" in synthesis
    assert "A-event peak cluster" in synthesis
    assert "cluster-member" in synthesis


def test_season_skills_preserve_durability_without_intensity_free_collapse() -> None:
    macrocycle = _read("skills/season/macrocycle-architecture/SKILL.md")
    governance = _read("skills/season/governance-review/SKILL.md")
    synthesis = _read("skills/season/plan-synthesis/SKILL.md")
    phase_intensity = _read("skills/phase/intensity-distribution/SKILL.md")
    scenario = _read("skills/season/scenario-generation/SKILL.md")

    assert "durability-first is not intensity-free" in macrocycle
    assert "RECOVERY" in governance
    assert "dominant `ENDURANCE`" in governance
    assert "`B` events receive only rehearsal" in governance
    assert "must not reconstruct season authority backward from Phase Guardrails" in synthesis
    assert "Scenario A = robust completion-first" in scenario
    assert "Scenario B = durability-forward target plan" in scenario
    assert "Scenario C = ambitious performance-forward long build" in scenario
    assert "must not be only `lower / medium / higher weekly kJ` variants" in scenario
    assert "`allowed_domains` are permissions, not obligations" in scenario
    assert "Phase intent and intensity semantics:" in synthesis
    assert "Phase intent and intensity semantics:" in phase_intensity
    assert "`TRANSITION` | `transition_recovery`" in synthesis
    assert "K3` appears only under `allowed_load_modalities`" in synthesis
    assert "Intensity is not the main escalation lever; fatigue-context specificity is." in phase_intensity
    assert "`specificity_build`" in synthesis
    assert "`season_archetype`" in scenario
    assert "ceiling_first_durability" in scenario


def test_season_scenario_prompt_carries_local_vo2_guardrail_rule() -> None:
    prompt = _read("prompts/agents/season_scenario.md")
    task_config = _read("config/crewai/tasks.yaml")
    scenario_skill = _read("skills/season/scenario-generation/SKILL.md")

    assert "If Scenario C includes `VO2MAX` in `allowed_domains`" in prompt
    assert "`decision_notes` and/or `kpi_guardrail_notes`" in prompt
    assert "omit `VO2MAX` from Scenario C" in prompt
    assert 'Do not let Scenario C become "the VO2 scenario" by default.' in prompt
    assert "If Scenario C includes `VO2MAX` in `allowed_domains`" in task_config
    assert "If Scenario C includes `VO2MAX`" in scenario_skill


def test_season_macrocycle_guidance_supports_multi_a_event_conflict_resolution() -> None:
    macrocycle = _read("skills/season/macrocycle-architecture/SKILL.md")
    audit = _read("skills/season/audit/SKILL.md")

    assert "one or more priority `A` event anchors" in macrocycle
    assert "equal-priority `A` events" in macrocycle
    assert "do not force a second independent macrocycle" in macrocycle
    assert "each target macrocycle ends in either one `A` event or one explicit `A`-event peak cluster" in audit
    assert "multi-`A` spacing requires a peak cluster or downgrade" in audit
