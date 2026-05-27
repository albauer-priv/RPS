---
Version: 1.0
Status: Approved
Last-Updated: 2026-05-27
Owner: Planning Runtime
---
# FEAT: Cadence-Aware and Future-Scoped Season Scenario Generation

* **ID:** FEAT_season_scenario_cadence_awareness
* **Status:** Approved
* **Owner/Area:** Planning Runtime
* **Last-Updated:** 2026-05-27
* **Related:** [FEAT_season_scenario_recommendation](/doc/specs/features/FEAT_season_scenario_recommendation.md), [FEAT_season_scenario_guardrail_alignment](/doc/specs/features/FEAT_season_scenario_guardrail_alignment.md), [FEAT_season_scenarios_deterministic_horizon](/doc/specs/features/FEAT_season_scenarios_deterministic_horizon.md)

---

## 1) Context / Problem

**Current behavior**

* `season_scenarios` emits `scenario_guidance.deload_cadence`.
* Downstream season structure correctly consumes the selected scenario cadence.
* Current scenario generation guidance under-specifies cadence as a scenario differentiator.
* In the active runtime, all three generated scenarios can collapse to the same cadence, especially when recommendation context prefers one cadence.
* Scenario generation has also been exposed to historical/pre-horizon events in prompt-facing context, which can confuse event-alignment language and produce invalid rehearsal/cluster semantics.
* The scenario layer does not yet consistently require selection-gate language, eligibility-not-authorization wording for intensity domains, or strict exception semantics for `season_archetype` and `VO2MAX`.

**Problem**

* Cadence is currently treated too much like copied structure metadata instead of part of scenario identity.
* Recommendation context can bias the model toward mirroring the recommended cadence across all scenarios without explicit rationale.
* Historical/pre-horizon event injection can lead to scenario text that treats past events as active rehearsal or cluster logic.
* The existing `season_scenarios_profile_quality` guardrail does not yet enforce selection-gate semantics, event-horizon discipline, or bounded exception logic for `season_archetype` / `VO2MAX`.

**Constraints**

* No downstream changes to season structure derivation or phase-slot math.
* No schema expansion or schema version bump in this pass.
* Shared cadence across scenarios remains legal when explicitly justified.
* Scenario B must not be hard-wired to `3:1`.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Make cadence a first-class scenario dimension in `season_scenarios`.
* [x] Keep recommendation context advisory instead of defaulting all scenarios to the recommended cadence.
* [x] Extend the existing `season_scenarios_profile_quality` guardrail to reject unexplained cadence collapse.
* [x] Restrict scenario-agent event injection to future / in-horizon events only.
* [x] Require explicit scenario selection gates in existing schema fields.
* [x] Treat `allowed_domains` as eligibility-only semantics in the scenario layer.
* [x] Default `season_archetype` to `none` and `VO2MAX` to exception-only semantics unless explicitly justified.
* [x] Keep downstream Season planning behavior unchanged.

**Non-Goals**

* [x] Do not redesign deterministic cadence math.
* [x] Do not force any scenario, including B, to a fixed default cadence.
* [x] Do not expand the `SEASON_SCENARIOS` schema.
* [x] Do not move binding phase/kJ/taper authority into the scenario layer.

---

## 3) Proposed Behavior

**User/System behavior**

* A/B/C scenarios must each emit a coherent cadence recommendation as part of the overall scenario story.
* Cadence may be shared across scenarios only when the stored scenario rationale clearly explains why differentiation comes from other axes such as load philosophy, specificity-under-fatigue, recovery margin, and risk posture.
* Recommendation context may support one scenario, but must not silently flatten all scenarios to the recommended cadence.
* The scenario agent receives only future / in-horizon event context; historical or pre-horizon events are not injected into prompt-facing scenario logic.
* `best_suited_if` and `risk_flags` become the required positive/negative selection-gate carriers using existing schema fields.
* `allowed_domains` are explicitly framed as eligibility for later assignment, not phase-wide authorization.
* `season_archetype = ceiling_first_durability` and Scenario C `VO2MAX` permission become strict exception paths that require explicit stored rationale.
* Objective/event mismatch remains warning-only and input-owned in the scenario layer.

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved: season scenario task contract, prompt, skill, orchestrator event-context preparation, orchestrator guardrail context, and existing scenario-quality guardrail.
* Contracts touched: `SEASON_SCENARIOS` generation contract only.

---

## 4) Implementation Analysis

**Components / Modules**

* `config/crewai/tasks.yaml`: require future-only event logic, explicit selection gates, eligibility-only domain wording, and bounded archetype/VO2 semantics.
* `prompts/agents/season_scenario.md`: make cadence, event-horizon, selection-gate, and exception semantics locally operational.
* `skills/season/scenario-generation/SKILL.md`: make cadence an explicit scenario identity dimension, preserve future-only event logic, and block recommendation-driven collapse plus unsafe archetype/VO2 drift.
* `src/rps/orchestrator/season_flow.py`: filter planning events to a future-only scenario-facing payload and bind event context into guardrail runtime context.
* `src/rps/planning/scenario_recommendation.py`: expose reusable future-only planning-event filtering for deterministic recommendation context.
* `src/rps/crewai_runtime/guardrails.py`: extend `season_scenarios_profile_quality(...)`.
* `tests/test_crewai_runtime.py`: add guardrail regression coverage.
* `tests/test_season_semantic_hardening.py`: add contract-text regression coverage.
* `tests/test_scenario_recommendation.py`: add future-only event-filter coverage.

**Data flow**

* Inputs: deterministic cadence options, deterministic recommendation context, future-only scenario-facing event context, athlete/event context, generated `SEASON_SCENARIOS`.
* Processing: scenario generation emits cadence-aware future-scoped scenarios; guardrail validates cadence presence, selection gates, domain semantics, event-horizon discipline, exception rationale, and anti-collapse behavior.
* Outputs: unchanged `SEASON_SCENARIOS` schema with stricter semantics.

**Schema / Artefacts**

* New artefacts: none.
* Changed artefacts: none.
* Validator implications: existing guardrail becomes stricter for cadence collapse and unsupported cadence values.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes for schema, stricter for runtime validity.
* Breaking changes: weak scenario outputs that silently collapse cadence, omit real selection gates, misuse historical events, over-authorize domains, or use weak archetype/VO2 rationale will now fail guardrails.
* Fallback behavior: scenarios may still share cadence when explicitly justified in existing rationale fields.

**Conflicts with ADRs / Principles**

* Potential conflicts: none identified.
* Resolution: no ADR update required because architecture boundaries remain unchanged.

**Impacted areas**

* UI: indirect improvement only through better scenario outputs.
* Pipeline/data: stricter scenario-generation retries on weak cadence semantics.
* Renderer: none.
* Workspace/run-store: none beyond possible additional guardrail failures.
* Validation/tooling: new scenario-quality assertions.
* Deployment/config: task/prompt/skill text changes only.

**Required refactoring**

* Reuse the existing `season_scenarios_profile_quality(...)` guardrail instead of adding a second validation path.
* Bind recommendation context and future/all-event context into guardrail runtime context so bias-aware and horizon-aware validation can inspect code-owned evidence.

---

## 6) Options & Recommendation

### Option A — Tighten generation contract plus existing guardrail and future-only event injection

**Summary**

* Update the task, prompt, and skill; restrict scenario-facing event injection to future-only context; extend the existing scenario-quality guardrail; keep schema and downstream structure logic unchanged.

**Pros**

* Small blast radius.
* Fixes the actual failure mode.
* Preserves existing architecture and artifact contracts.

**Cons**

* Weak scenario outputs may retry more often until prompts settle.

**Risk**

* Over-strict wording could block legitimate shared-cadence scenarios if rationale detection is too narrow.

### Option B — Add a new cadence-specific schema field or separate validator

**Summary**

* Introduce new cadence-specific metadata or a second validation stage.

**Pros**

* More explicit machine-readable cadence reasoning.

**Cons**

* Higher migration cost.
* Unnecessary schema churn.
* Duplicates existing guardrail responsibility.

### Recommendation

* Choose: Option A
* Rationale: the failure is a contract/guardrail gap, not a schema or downstream planning problem.

---

## 7) Acceptance Criteria (Definition of Done)

* [ ] `season_scenarios` task, prompt, and skill explicitly require cadence-aware scenario differentiation.
* [ ] Scenario-agent event injection is future-only.
* [ ] Shared cadence across A/B/C is allowed only with explicit stored rationale.
* [ ] `best_suited_if` and `risk_flags` are treated as required selection-gate carriers.
* [ ] `allowed_domains` are framed as eligibility-only semantics.
* [ ] `season_scenarios_profile_quality(...)` rejects unexplained cadence collapse, historical-event active logic, weak selection gates, unsafe cluster wording, weak archetype rationale, and unsafe VO2 exception semantics.
* [ ] Recommendation-default cadence mirrored across all scenarios without rationale fails guardrail.
* [ ] Existing downstream season structure tests remain unchanged and pass.
* [ ] Validation passes: `python3 -m py_compile`, targeted pytest, lint, typecheck.

---

## 8) Migration / Rollout

**Migration strategy**

* No schema or artifact migration required.

**Rollout / gating**

* Feature flag / config: none.
* Safe rollback: revert task/prompt/skill and guardrail changes together.

---

## 9) Risks & Failure Modes

* Failure mode: guardrail rejects legitimate shared-cadence scenarios.

  * Detection: repeated `season_scenarios_profile_quality` failures with explicit rationale present.
  * Safe behavior: bounded retry, no invalid scenario artifact persisted.
  * Recovery: widen rationale detection to the documented existing fields only.

* Failure mode: recommendation-bias rule is too weak and collapse still passes.

  * Detection: regression tests or runtime output show all scenarios mirroring recommended cadence without scenario-specific rationale.
  * Safe behavior: guardrail failure blocks persistence.
  * Recovery: tighten rationale matching and context use.

---

## 10) Observability / Logging

**New/changed events**

* No new event types required.

**Diagnostics**

* Guardrail failure messages in `rps.log` and run-store telemetry must name cadence collapse or missing cadence rationale explicitly.

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] [CHANGELOG.md](/CHANGELOG.md) — note cadence-aware season scenario generation hardening.
* [x] [doc/specs/features/FEAT_season_scenario_cadence_awareness.md](/doc/specs/features/FEAT_season_scenario_cadence_awareness.md) — canonical feature spec for this fix.

---

## 12) Link Map (no duplication; links only)

* Architecture: `/doc/architecture/system_architecture.md`
* Artefact flow: `/doc/overview/artefact_flow.md`
* Validation / runtime guardrails: `/src/rps/crewai_runtime/guardrails.py`
* Scenario generation skill: `/skills/season/scenario-generation/SKILL.md`
* Scenario prompt: `/prompts/agents/season_scenario.md`
* Scenario task config: `/config/crewai/tasks.yaml`
