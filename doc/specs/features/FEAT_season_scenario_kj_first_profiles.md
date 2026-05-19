---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-19
Owner: Season Planning
---
# FEAT: Season Scenario kJ-First Profiles

* **ID:** FEAT_season_scenario_kj_first_profiles
* **Status:** Implemented
* **Owner/Area:** Season Planning
* **Last-Updated:** 2026-05-19
* **Related:** FEAT_season_intensity_domain_authority_split

---

## 1) Context / Problem

**Current behavior**

* The active `season_scenario` runtime mainly distinguishes A/B/C through cadence language, risk phrasing, and allowed intensity domains.
* The active skill requires `intensity_guidance`, but it does not make `kJ-envelope`, `fatigue exposure`, `specificity`, and `risk contract` the primary scenario identity.

**Problem**

* In a kJ-first ultra/brevet system, scenarios must be distinguished first by load philosophy and durability-specific exposure, not by domain labels.
* Without explicit runtime guidance, the scenario step can drift toward shallow patterns like `A = lower kJ`, `B = medium kJ`, `C = more kJ`, or worse, `A/B/C` separated mostly by domain breadth.

**Constraints**

* `_shared` documents may be used as source material, but active authority must live in runtime skill/task/guardrail files.
* The scenario step remains advisory; it must not become a fully deterministic code-owned planner.
* Existing schema shape for `SEASON_SCENARIOS` stays unchanged.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Make `season_scenario` explicitly kJ-first.
* [x] Define A/B/C as distinct risk/exposure profiles rather than only low/mid/high kJ.
* [x] Keep intensity domains as permissions rather than primary scenario identity.
* [x] Add light runtime checks for obviously weak or contradictory scenario outputs.

**Non-Goals**

* [x] No schema change for `SEASON_SCENARIOS`.
* [x] No full code-owned computation of scenario domain sets.
* [x] No week- or workout-level decision logic in the scenario step.

---

## 3) Proposed Behavior

**User/System behavior**

* Scenario A is framed as robust completion-first with lower feasible exposure, higher recovery margin, and minimal intensity allowance.
* Scenario B is the durability-forward target plan with realistic target exposure, systematic long-ride progression, and selected tempo/SST economy work.
* Scenario C is the ambitious long build with upper plausible exposure, more specificity under fatigue, and optional threshold/VO2 only when justified.
* Two scenarios may share the same `allowed_domains` when their exposure/risk/specificity profiles are meaningfully different.

**Non-UI behavior**

* Components involved: `skills/season/scenario-generation`, `prompts/agents/season_scenario.md`, `config/crewai/tasks.yaml`, season-scenario runtime guardrails.
* Contracts touched: `SEASON_SCENARIOS` advisory output quality and runtime review semantics.

---

## 4) Implementation Analysis

**Components / Modules**

* `skills/season/scenario-generation/SKILL.md`: primary active methodology and A/B/C target profiles.
* `prompts/agents/season_scenario.md`: compact prompt reinforcement so the agent does not default to domain-first distinction.
* `config/crewai/tasks.yaml`: task description updated to match the kJ-first runtime method.
* `src/rps/crewai_runtime/guardrails.py`: add a persisted-artifact guardrail for grossly weak `SEASON_SCENARIOS` differentiation.
* `config/crewai/task_policies.yaml`: activate the new scenario guardrail for the `season_scenarios` task.

**Data flow**

* Inputs: athlete context, planning events, availability, logistics, KPI context, deterministic horizon and cadence option blocks.
* Processing: skill guides the agent to create scenario identity via exposure/risk/specificity first, then intensity-domain permissions second.
* Outputs: more coherent `SEASON_SCENARIOS` narratives and a runtime warning/block for shallow or contradictory scenario sets.

**Schema / Artefacts**

* New artefacts: none.
* Changed artefacts: none structurally; output semantics are tightened.
* Validator implications: season-scenario persisted-artifact guardrails now include content-quality checks beyond schema shape.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes at schema level.
* Breaking changes: scenario outputs that are schema-valid but materially shallow may now be rejected by guardrails.
* Fallback behavior: none beyond existing schema/normalization path.

**Conflicts with ADRs / Principles**

* No known ADR conflict.
* The feature aligns scenario generation with the repository's kJ-first and durability-first direction.

**Impacted areas**

* UI: indirect only through better scenario outputs on the Season page.
* Pipeline/data: only the `SEASON_SCENARIOS` generation/review path.
* Validation/tooling: new content-quality guardrail and tests.

**Required refactoring**

* Move kJ-first scenario differentiation from implicit intent into explicit active runtime instructions.
* Add minimal runtime checks that permit same-domain scenarios when exposure/risk profiles differ.

---

## 6) Options & Recommendation

### Option A — Skill-first kJ-profile hardening with light guardrails

**Summary**

* Put the real methodology in the active skill and add a small guardrail for obvious failures.

**Pros**

* Fastest path to active runtime improvement.
* Preserves agent flexibility while constraining bad outputs.
* Matches current architecture.

**Cons**

* Still depends on model reasoning quality.

### Option B — Full deterministic scenario construction

**Summary**

* Compute A/B/C load and domain profiles in code.

**Pros**

* Stronger reproducibility.

**Cons**

* Much heavier change and more policy decisions than currently needed.

### Recommendation

* Choose: Option A
* Rationale: the user asked for a better skill, and the current architecture already supports skill-led runtime behavior with targeted guardrails.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] The active scenario skill explicitly describes A/B/C with kJ-first exposure/risk profiles.
* [x] The skill states that scenarios must not be only low/mid/high weekly-kJ variants.
* [x] The skill states that domains are permissions, not primary identity.
* [x] The runtime accepts identical domain sets for B/C when risk/specificity differ materially.
* [x] The runtime rejects or warns on obviously weak cases such as Scenario C with only `ENDURANCE`.
* [x] Tests cover the new skill language and guardrail behavior.

---

## 8) Migration / Rollout

**Migration strategy**

* No schema migration.
* Existing saved scenarios remain readable; new generation runs use the updated method and guardrails.

**Rollout / gating**

* No feature flag.
* Safe rollback: revert the skill/task/guardrail bundle together.

---

## 9) Risks & Failure Modes

* Failure mode: guardrail is too strict and rejects acceptable same-domain B/C scenarios.
  * Detection: failing runtime/test cases for B/C with distinct risk/specificity but shared domains.
  * Safe behavior: allow same domains when narrative and exposure profiles differ.
  * Recovery: relax the guardrail without weakening the skill.

* Failure mode: scenario outputs still collapse into simple low/mid/high-kJ language.
  * Detection: skill-content tests and scenario-output review.
  * Safe behavior: block the weakest cases and keep task descriptions aligned.
  * Recovery: strengthen the skill wording rather than normalizing outputs blindly.

---

## 10) Observability / Logging

**New/changed events**

* No new event family required.
* Existing guardrail failure telemetry will carry the new season-scenario guardrail name when it triggers.

**Diagnostics**

* `events.jsonl`
* `rps.log`
* guardrail failure messages on season-scenario task runs

---

## 11) Documentation Updates

* [x] [skills/season/scenario-generation/SKILL.md](/Users/alexander/RPS/skills/season/scenario-generation/SKILL.md) — active kJ-first methodology and explicit A/B/C profiles.
* [x] [prompts/agents/season_scenario.md](/Users/alexander/RPS/prompts/agents/season_scenario.md) — compact prompt reinforcement.
* [x] [config/crewai/tasks.yaml](/Users/alexander/RPS/config/crewai/tasks.yaml) — task description aligned with active methodology.

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* Artefact flow: `doc/overview/artefact_flow.md`
* Validation runbook: `doc/runbooks/validation.md`
* Logging policy: `doc/specs/contracts/logging_policy.md`
