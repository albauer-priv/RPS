---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-26
Owner: Planning Runtime
---
# FEAT: Season Scenario Guardrail Alignment

* **ID:** FEAT_season_scenario_guardrail_alignment
* **Status:** Implemented
* **Owner/Area:** Planning Runtime
* **Last-Updated:** 2026-05-26
* **Related:** `prompts/agents/season_scenario.md`, `config/crewai/tasks.yaml`, `skills/season/scenario-generation/SKILL.md`, `src/rps/crewai_runtime/guardrails.py`

---

## 1) Context / Problem

**Current behavior**

* The `season_scenarios` task is guarded by `season_scenarios_profile_quality`.
* Scenario C may include `VO2MAX` only when the stored scenario fields explicitly explain that it is sparse ceiling-support work and not the primary scenario identity.

**Problem**

* The active prompt `prompts/agents/season_scenario.md` was too thin relative to the stricter task, skill, and guardrail contract.
* This allowed the model to emit Scenario C with `VO2MAX` but without the required explicit explanation in `decision_notes` or `kpi_guardrail_notes`, causing repeated guardrail retries and final task failure.

**Constraints**

* The fix must stay in the active planning layer, not in review or writer.
* No schema change is needed.
* The solution should remain narrowly scoped and testable.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Align the active `season_scenario` prompt with the existing task/skill/guardrail rule for Scenario C and `VO2MAX`.
* [x] Add a regression test that fails if the active prompt loses this local operative rule again.
* [x] Check nearby active prompts for the same class of missing local guardrail rule.

**Non-Goals**

* [x] Change the Scenario C schema or guardrail semantics.
* [x] Introduce a generic prompt-audit framework in this pass.

---

## 3) Proposed Behavior

**User/System behavior**

* `season_scenarios` should stop failing on avoidable Scenario C `VO2MAX` justification omissions.
* The active prompt must locally state:
  * Scenario C is not defined by `VO2MAX`
  * if `VO2MAX` is included, the explanation must live in `decision_notes` and/or `kpi_guardrail_notes`
  * otherwise omit `VO2MAX`

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved: active prompt, prompt-content regression test
* Contracts touched: active prompt authority contract for `season_scenarios`

---

## 4) Implementation Analysis

**Components / Modules**

* `prompts/agents/season_scenario.md`: add the missing explicit local rule
* `tests/test_season_semantic_hardening.py`: add a regression test for prompt/task/skill alignment

**Data flow**

* Inputs: task description, skill guidance, active prompt
* Processing: model emits Scenario C under the aligned local rule
* Outputs: fewer guardrail retry failures for `season_scenarios`

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: existing guardrail remains unchanged and should pass more reliably

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none
* Fallback behavior: guardrail still blocks invalid Scenario C outputs

**Conflicts with ADRs / Principles**

* Potential conflicts: none
* Resolution: aligns with active-layer authority rules in `AGENTS.md`

**Impacted areas**

* UI: none
* Pipeline/data: `season_scenarios` task reliability improves
* Renderer: none
* Workspace/run-store: none
* Validation/tooling: targeted prompt regression test added
* Deployment/config: none

**Required refactoring**

* none beyond prompt hardening and test coverage

---

## 6) Options & Recommendation

### Option A — Harden the active prompt directly

**Summary**

* Put the missing operational rule into `prompts/agents/season_scenario.md`.

**Pros**

* Fixes the error at the right layer
* Keeps task/skill/guardrail symmetry
* Small and low-risk

**Cons**

* Does not create a generic detector for every future prompt drift

**Risk**

* Low

### Option B — Relax the guardrail

**Summary**

* Make the guardrail more forgiving.

**Pros**

* Fewer immediate failures

**Cons**

* Lowers contract quality
* Leaves the active prompt underspecified

### Recommendation

* Choose: Option A
* Rationale: the missing rule belongs in the active prompt layer and the existing guardrail is doing the right job.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `prompts/agents/season_scenario.md` explicitly carries the Scenario C `VO2MAX` rule.
* [x] A regression test fails if the prompt loses the local `VO2MAX` justification rule.
* [x] Repo check confirms no similarly obvious missing local rule in nearby active Season/Phase/Week prompts for this issue class.
* [x] Validation passes: syntax, lint, type check, targeted tests.
* [x] No regressions in Season runtime/task config wiring.

---

## 8) Migration / Rollout

**Migration strategy**

* None

**Rollout / gating**

* No feature flag
* Safe rollback: revert prompt/test patch

---

## 9) Risks & Failure Modes

* Failure mode: prompt drifts again and loses the local rule
  * Detection: regression test failure or repeated `CREW_TASK_GUARDRAIL_FAILED` for Scenario C `VO2MAX`
  * Safe behavior: runtime keeps blocking invalid output
  * Recovery: restore local prompt rule

---

## 10) Observability / Logging

**New/changed events**

* none

**Diagnostics**

* Runtime logs: `CREW_TASK_GUARDRAIL_FAILED` for `season_scenarios`
* Tests: `tests/test_season_semantic_hardening.py`

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] [CHANGELOG.md](/Users/alexander/RPS/CHANGELOG.md) — record the prompt/guardrail alignment fix
* [x] This feature doc — capture the cause and local-layer fix

## 12) Link Map

* [AGENTS.md](/Users/alexander/RPS/AGENTS.md)
* [season_scenario.md](/Users/alexander/RPS/prompts/agents/season_scenario.md)
* [tasks.yaml](/Users/alexander/RPS/config/crewai/tasks.yaml)
* [scenario-generation/SKILL.md](/Users/alexander/RPS/skills/season/scenario-generation/SKILL.md)
* [guardrails.py](/Users/alexander/RPS/src/rps/crewai_runtime/guardrails.py)
