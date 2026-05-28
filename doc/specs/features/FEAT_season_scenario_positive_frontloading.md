---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-28
Owner: Planning
---
# FEAT: Season Scenario Positive Frontloading

* **ID:** FEAT_season_scenario_positive_frontloading
* **Status:** Implemented
* **Owner/Area:** Planning / CrewAI season scenarios
* **Last-Updated:** 2026-05-28
* **Related:** [FEAT_season_scenario_vo2max_explanation_hardening](/Users/alexander/RPS/doc/specs/features/FEAT_season_scenario_vo2max_explanation_hardening.md), [FEAT_active_prompt_policy_migration_completion](/Users/alexander/RPS/doc/specs/features/FEAT_active_prompt_policy_migration_completion.md)

---

## 1) Context / Problem

**Current behavior**

* `season_scenarios` already had semantic guardrails for weak selection gates, vague caution markers, and under-specified Scenario C `VO2MAX` rationale.
* The active task, prompt, and skill had been hardened incrementally after repeated guardrail failures.

**Problem**

* Repeated failures showed that active generation guidance still leaned too much on defensive constraints instead of giving the model a clear positive target for each stored field.
* That caused the model to drift into vague wording for `best_suited_if`, `risk_flags`, and Scenario C rationale, then rely on downstream guardrail retries to repair the output.
* The current error family is therefore upstream shaping, not missing acceptance logic.

**Constraints**

* No schema change.
* Guardrails remain the semantic acceptance backstop.
* Existing season-scenario rules remain intact for:
  * future-only event logic
  * eligibility-not-authorization semantics for `allowed_domains`
  * objective-mismatch warning-only semantics
  * Scenario C `VO2MAX` exception handling
  * `season_archetype` exception handling

---

## 2) Goals & Non-Goals

**Goals**

* [x] Make prompt/skill/task text primarily show what good `SEASON_SCENARIOS` output should sound like.
* [x] Convert critical fields to explicit positive field contracts with preferred formulations.
* [x] Keep Scenario C `VO2MAX` wording aligned to the real guardrail markers without broadening the acceptance contract.
* [x] Add a compact positive self-check block in the active generation layer.
* [x] Capture the source-first / guardrail-second pattern as a reusable documented template for later planner rollout.

**Non-Goals**

* [ ] No repo-wide rollout of this pattern in the same change.
* [ ] No weakening or broadening of the runtime guardrail.
* [ ] No planner schema, workspace, or orchestration refactor.

---

## 3) Proposed Behavior

**User/System behavior**

* The active `season_scenarios` generation layer now leads with preferred field formulations and short example sentences instead of mainly negative rule lists.
* The model is told explicitly how strong `best_suited_if`, `risk_flags`, `decision_notes`, `kpi_guardrail_notes`, `event_alignment_notes`, `load_philosophy`, `risk_profile`, and `key_differences` should read.
* Scenario A/B/C each receive preferred wording examples for selection and caution logic.
* If Scenario C includes `VO2MAX`, the active files expose one normative sentence that already satisfies the acceptance contract:
  * `VO2MAX remains sparse ceiling-support only when fresh-only, not primary identity; the scenario ambition comes from specificity-under-fatigue, density, and event simulation.`
* The prompt and skill now include a short positive “before finalizing” quality check instead of relying on guardrail retries to reveal weak wording.

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved:
  * `prompts/agents/season_scenario.md`
  * `skills/season/scenario-generation/SKILL.md`
  * `config/crewai/tasks.yaml`
  * `tests/test_season_semantic_hardening.py`
  * `tests/test_crewai_runtime.py`
* Contracts touched:
  * `SEASON_SCENARIOS`
  * `season_scenarios_profile_quality` acceptance semantics remain stable

---

## 4) Implementation Analysis

**Components / Modules**

* `prompts/agents/season_scenario.md`
  * compress repetitive defensive prose
  * promote preferred field formulations and examples
  * add positive self-check block
* `skills/season/scenario-generation/SKILL.md`
  * mirror the prompt-side positive field contracts
  * keep local operative rules self-contained
  * include preferred Scenario C `VO2MAX` sentence
* `config/crewai/tasks.yaml`
  * make task-level field targets explicit and copyable
* `tests/test_season_semantic_hardening.py`
  * assert presence of positive contracts, example sentences, and self-check language
* `tests/test_crewai_runtime.py`
  * assert the existing guardrail still rejects weak stored wording and incomplete Scenario C rationale

**Data flow**

* Inputs: unchanged season-scenario context from the orchestrator
* Processing:
  * model receives clearer field-shape guidance
  * guardrail remains the deterministic acceptance gate
* Outputs: unchanged `SEASON_SCENARIOS` artefact schema with higher-probability compliant phrasing

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: existing guardrail tests remain authoritative

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none
* Fallback behavior: guardrail continues to reject weak outputs if positive frontloading still fails

**Conflicts with ADRs / Principles**

* Potential conflicts:
  * active planning-layer ownership rules could be violated if review/writer became the repair layer
* Resolution:
  * this feature reinforces the existing project rule: planner/finalizer first, review second, writer serialization only

**Impacted areas**

* UI: none
* Pipeline/data: season-scenario generation wording quality
* Renderer: none
* Workspace/run-store: none
* Validation/tooling: stronger prompt contract assertions, explicit runtime regressions
* Deployment/config: task/prompt/skill text only

**Required refactoring**

* Rebalance active generation text toward positive contracts instead of further additive “must not” growth.
* Extract the reusable template pattern into one feature doc and backlog the broader rollout instead of applying it immediately elsewhere.

---

## 6) Options & Recommendation

### Option A — keep tightening guardrails

**Summary**

* Continue addressing repeated failures mostly by adding acceptance logic and rejection branches.

**Pros**

* Deterministic and bounded
* Easy to reason about per failure

**Cons**

* Treats the symptom late instead of shaping output early
* Risks turning the guardrail into a second planner
* Does not reduce the model’s freedom where the drift starts

**Risk**

* Repeated retry loops and brittle wording repairs continue

### Option B — positive frontloading with stable guardrails

**Summary**

* Keep the guardrail contract stable, but make the active generation layer state the preferred wording clearly and locally.

**Pros**

* Fixes the source of the repeated failure family
* Keeps acceptance logic narrow and deterministic
* Creates a reusable template for later planner families

**Cons**

* Requires more careful prompt/skill/task maintenance than one-off guardrail edits

### Recommendation

* Choose: Option B
* Rationale: the repeated failures are generation-shape defects. They should be fixed where the text is produced, while guardrails remain the bounded acceptance gate.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Prompt, task, and skill contain positive preferred formulations for Scenario A/B/C.
* [x] Prompt, task, and skill describe critical scenario fields as explicit positive field contracts.
* [x] The normative Scenario C `VO2MAX` sentence is present in the active generation layer.
* [x] Prompt and skill contain a positive self-check block.
* [x] Runtime tests verify:
  * valid Scenario C `VO2MAX` rationale passes
  * missing `not primary identity` fails
  * missing specificity source fails
  * weak `best_suited_if` fails
  * weak `risk_flags` fails
* [x] Validation passes:
  * `python3 -m py_compile $(git ls-files '*.py')`
  * `./scripts/run_lint.sh`
  * `./scripts/run_typecheck.sh`
  * `PYTHONPATH=src pytest -q tests/test_season_semantic_hardening.py tests/test_crewai_runtime.py -k 'season_scenarios_profile_quality or season_scenario_prompt_carries_local_vo2_guardrail_rule'`

---

## 8) Migration / Rollout

**Migration strategy**

* No schema or data migration.

**Rollout / gating**

* No feature flag.
* Safe rollback: revert task/prompt/skill changes and associated tests.
* Broader rollout to other planner families is deferred and tracked in backlog.

---

## 9) Risks & Failure Modes

* Failure mode: prompt/skill/task still leave too much freedom and a new wording gap appears.
  * Detection: existing season-scenario guardrail failures and runtime tests
  * Safe behavior: output is rejected before persistence
  * Recovery: refine active field contracts first; only change guardrail if the semantic acceptance contract itself is wrong

* Failure mode: future planner work copies the pattern inconsistently.
  * Detection: drift between active files and the reusable template
  * Safe behavior: limited to local planner family
  * Recovery: use this feature doc as the template source before rollout

---

## 10) Observability / Logging

**New/changed events**

* No new telemetry events.

**Diagnostics**

* `events.jsonl`
* `rps.log`
* guardrail failure reasons on `season_scenarios`

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] [CHANGELOG.md](/Users/alexander/RPS/CHANGELOG.md) — record the positive-frontloading change
* [x] [doc/overview/feature_backlog.md](/Users/alexander/RPS/doc/overview/feature_backlog.md) — add broader planner rollout follow-up

---

## 12) Link Map

* Active planner ownership rules: [AGENTS.md](/Users/alexander/RPS/AGENTS.md)
* Guardrail contract: [guardrails.py](/Users/alexander/RPS/src/rps/crewai_runtime/guardrails.py)
* Existing Scenario C hardening: [FEAT_season_scenario_vo2max_explanation_hardening](/Users/alexander/RPS/doc/specs/features/FEAT_season_scenario_vo2max_explanation_hardening.md)
* Prompt policy migration direction: [FEAT_active_prompt_policy_migration_completion](/Users/alexander/RPS/doc/specs/features/FEAT_active_prompt_policy_migration_completion.md)
