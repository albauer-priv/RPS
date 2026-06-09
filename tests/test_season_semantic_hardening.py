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
    normalized_task_config = " ".join(task_config.split())

    assert "Scenario C VO2MAX hard rule:" in prompt
    assert "`decision_notes` and/or `kpi_guardrail_notes`" in prompt
    assert "omit `VO2MAX` from Scenario C" in prompt
    assert "not primary identity" in prompt
    assert "Preferred copyable wording for Scenario C when `VO2MAX` is allowed" in prompt
    assert 'Do not let Scenario C become "the VO2 scenario" by default.' in prompt
    assert "Only future / in-horizon events are provided to this task." in prompt
    assert "Do not infer active scenario logic from past" in prompt
    assert "`allowed_domains` means eligibility for later assignment only" in prompt
    assert "`best_suited_if` must state explicit positive selection conditions" in prompt
    assert "Write `best_suited_if` as a short concrete selection sentence" in prompt
    assert "`stable recovery`" in prompt and "`continuity priority`" in prompt
    assert "`risk_flags` must state explicit negative selection conditions" in prompt
    assert "Write `risk_flags` as short concrete caution sentences" in prompt
    assert "`under-deliver`" in prompt and "`too aggressive`" in prompt
    assert "`core_idea` should say the central scenario promise" in prompt
    assert "`typical_week_feel` should describe how a representative week feels" in prompt
    assert "`event_alignment_notes` should describe only future active event logic" in prompt
    assert "`kpi_guardrail_notes` should explain pacing, efficiency, or metabolic guardrails" in prompt
    assert "`assumptions` should state what must remain true" in prompt
    assert "`unknowns` should state the uncertainties" in prompt
    assert "`season_archetype` defaults to `none`." in prompt
    assert "Objective mismatch may be named as unresolved upstream input context only." in prompt
    assert "Scenario C VO2MAX hard rule:" in normalized_task_config
    assert "Preferred copyable wording:" in task_config
    assert "not primary identity" in task_config
    assert "front-loaded, self-contained source of" in task_config
    assert "operational posture for scenario selection" in task_config
    assert "`scenario_guidance.recovery_margin`" in task_config
    assert "`scenario_guidance.fatigue_exposure`" in task_config
    assert "`scenario_guidance.specificity_density`" in task_config
    assert "Only future / in-horizon events are provided to this task" in normalized_task_config
    assert "`best_suited_if`" in task_config and "must carry explicit positive selection conditions" in task_config
    assert "Write `best_suited_if` as" in task_config
    assert "`systematic progression`" in task_config
    assert "`high load" in task_config and "tolerance`" in task_config
    assert "`risk_flags`" in task_config and "negative selection conditions" in task_config
    assert "Write `risk_flags` as" in task_config
    assert "`continuity break`" in task_config and "`recovery slip`" in task_config
    assert "`core_idea` = one-sentence" in task_config
    assert "`event_alignment_notes` = future-only active event logic" in task_config
    assert "`data.notes` = global layer clarifications" in task_config
    assert "mismatch may be named as unresolved input context only" in task_config
    assert "do not resolve it" in task_config
    assert "If Scenario C includes `VO2MAX`" in scenario_skill
    assert "Preferred copyable sentence when Scenario C allows `VO2MAX`" in scenario_skill
    assert "not primary identity" in scenario_skill
    assert "`scenario_guidance.deload_cadence` is not" in task_config
    assert "decorative phase math" in task_config
    assert "coherent cadence" in task_config and "per scenario" in task_config
    assert "must not become the default cadence for all scenarios" in prompt
    assert "Do not let recommendation-default cadence become the implicit cadence for all scenarios." in prompt
    assert "Scenarios may share identical `deload_cadence` only when the stored scenario fields explicitly say cadence is intentionally held constant" in scenario_skill
    assert "do not mirror the recommendation cadence blindly into all scenarios" in scenario_skill
    assert "only future / in-horizon events are provided to the scenario agent" in scenario_skill
    assert "do not infer active scenario logic from past or completed events" in scenario_skill
    assert "`allowed_domains` define eligibility for later assignment only" in scenario_skill
    assert "Ensure `best_suited_if` is a real positive selection gate" in scenario_skill
    assert "preferred example: `Choose when continuity priority and uncertain recovery dominate.`" in scenario_skill
    assert "preferred example: `Choose when stable recovery supports systematic progression.`" in scenario_skill
    assert "preferred example: `Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.`" in scenario_skill
    assert "preferred example: `May under-deliver if high load tolerance is available.`" in scenario_skill
    assert "preferred example: `Less forgiving than A if continuity break or recovery slip appears.`" in scenario_skill
    assert "preferred example: `Too aggressive if fatigue risk or travel disruption appears.`" in scenario_skill
    assert "Field completion contract:" in scenario_skill
    assert "`scenario_guidance.recovery_margin` = explicit recovery stance as a non-empty string" in scenario_skill
    assert "`scenario_guidance.fatigue_exposure` = explicit fatigue posture as a non-empty string" in scenario_skill
    assert "`scenario_guidance.specificity_density` = explicit specificity posture as a non-empty string" in scenario_skill
    assert "`core_idea` = one-sentence scenario promise" in scenario_skill
    assert "`event_alignment_notes` = future-only active event logic" in scenario_skill
    assert "`data.notes` = global scenario-layer clarifications" in scenario_skill
    assert "Use `none` by default." in scenario_skill
    assert "Do not claim that the scenario layer resolved or replaced the objective/event hierarchy." in scenario_skill
    assert "front-loaded source of operational posture" in scenario_skill
    assert "self-contained for operational posture" in scenario_skill
    assert "Emit `recovery_margin`, `fatigue_exposure`, and `specificity_density` directly in `scenario_guidance`" in scenario_skill
    assert "The active scenario-generation layer is the front-loaded source of operational posture." in prompt
    assert "The active scenario-generation layer must be self-contained for operational posture" in prompt


def test_season_scenario_vo2_rule_is_canonical_and_frontloaded() -> None:
    prompt = _read("prompts/agents/season_scenario.md")
    task_config = _read("config/crewai/tasks.yaml")
    scenario_skill = _read("skills/season/scenario-generation/SKILL.md")
    canonical_rule = (
        "Scenario C VO2MAX hard rule: Scenario C may include `VO2MAX` only when it is explicitly justified as "
        "`sparse ceiling-support`, `fresh-only`, `not primary identity`, and ambition sourced from "
        "`specificity-under-fatigue`, `density`, `event simulation`, or `load posture`."
    )
    canonical_omission = (
        "If that rationale cannot be stated explicitly in `decision_notes` and/or `kpi_guardrail_notes`, "
        "omit `VO2MAX` from Scenario C `allowed_domains`."
    )
    canonical_sentence = (
        "VO2MAX remains sparse ceiling-support only when fresh-only, not primary identity; "
        "the scenario ambition comes from specificity-under-fatigue, density, and event simulation."
    )

    normalized = [" ".join(content.split()) for content in (prompt, task_config, scenario_skill)]

    for content in normalized:
        assert canonical_rule in content
        assert canonical_omission in content
        assert canonical_sentence in content

    normalized_prompt = " ".join(prompt.split())
    normalized_task = " ".join(task_config.split())

    assert normalized_prompt.index(canonical_rule) < normalized_prompt.index("For Scenario A, make `best_suited_if`")
    assert normalized_task.index(canonical_rule) < normalized_task.index("For Scenario A, make")
    assert scenario_skill.index(canonical_rule) < scenario_skill.index("- Scenarios B and C may legitimately share identical `allowed_domains`")


def test_season_scenario_cadence_rule_is_canonical_and_frontloaded() -> None:
    prompt = _read("prompts/agents/season_scenario.md")
    task_config = _read("config/crewai/tasks.yaml")
    scenario_skill = _read("skills/season/scenario-generation/SKILL.md")
    canonical_rule = (
        "Recommendation-default cadence hard rule: deterministic recommendation cadence is advisory for one scenario, "
        "not the default cadence for all scenarios."
    )
    canonical_shared = (
        "A/B/C must not all mirror the recommendation-default cadence unless the stored scenario fields explicitly justify "
        "that cadence is intentionally shared."
    )
    canonical_diff = (
        "When cadence is intentionally shared, the stored scenario fields must explicitly say that differentiation instead "
        "comes from `load philosophy`, `specificity-under-fatigue`, `recovery margin` and/or `recovery tolerance`, "
        "`intensity permissions`, or `risk posture`."
    )
    canonical_omission = (
        "If that rationale cannot be stated explicitly in `decision_notes`, `risk_flags`, `event_alignment_notes`, and/or "
        "`kpi_guardrail_notes`, at least one scenario must use a different `deload_cadence`."
    )

    normalized = [" ".join(content.split()) for content in (prompt, task_config, scenario_skill)]
    for content in normalized:
        assert canonical_rule in content
        assert canonical_shared in content
        assert canonical_diff in content
        assert canonical_omission in content

    normalized_prompt = " ".join(prompt.split())
    normalized_task = " ".join(task_config.split())
    normalized_skill = " ".join(scenario_skill.split())
    assert normalized_prompt.index(canonical_rule) < normalized_prompt.index("Scenario C VO2MAX hard rule:")
    assert normalized_task.index(canonical_rule) < normalized_task.index("Scenario C VO2MAX hard rule:")
    assert normalized_skill.index(canonical_rule) < normalized_skill.index("Scenario C VO2MAX hard rule:")


def test_season_macrocycle_guidance_supports_multi_a_event_conflict_resolution() -> None:
    macrocycle = _read("skills/season/macrocycle-architecture/SKILL.md")
    audit = _read("skills/season/audit/SKILL.md")

    assert "one or more priority `A` event anchors" in macrocycle
    assert "equal-priority `A` events" in macrocycle
    assert "do not force a second independent macrocycle" in macrocycle
    assert "each target macrocycle ends in either one `A` event or one explicit `A`-event peak cluster" in audit
    assert "multi-`A` spacing requires a peak cluster or downgrade" in audit
