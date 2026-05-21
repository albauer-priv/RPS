---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-21
Owner: Planning Runtime
---
# FEAT: Multi-A-Event Reverse Planning Guidance

* **ID:** FEAT_multi_a_event_reverse_planning_guidance
* **Status:** Implemented
* **Owner/Area:** Planning Runtime
* **Last-Updated:** 2026-05-21
* **Related:** ADR-053

---

## 1) Context / Problem

**Current behavior**

* Season planning guidance strongly implies one dominant reverse-planning anchor.
* Multi-event language exists, but it does not clearly define when multiple `A` events form separate macrocycles versus one clustered peak window.

**Problem**

* The planner can collapse all season logic into the final `A` event.
* Close `A` events can be treated as separate rebuild targets even when the calendar only supports one shared peak cluster.

**Constraints**

* No persisted schema changes in this pass.
* No new canonical `phase_type`, `phase_intent`, or `build_subtype`.
* The new logic must sit above phases as Season-level planning guidance.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Teach the Season planner that a season may contain one or more target macrocycles.
* [x] Add explicit rules for `A-event peak cluster` vs separate `target macrocycle`.
* [x] Make A-event classification visible in season justification without schema changes.

**Non-Goals**

* [x] No schema fields such as `target_macrocycle_id` or `target_event_id` in this pass.
* [x] No deterministic runtime or validator redesign.

---

## 3) Proposed Behavior

**User/System behavior**

* Season planning may backplan from multiple `A` anchors when spacing supports it.
* Closely spaced `A` events are grouped into one shared peak cluster instead of forcing multiple overlapping tapers/builds.
* Post-`A` planning must re-enter through `TRANSITION` or `PREPARATION` before a new Build unless events remain inside one cluster.

**UI impact**

* UI affected: No

**Non-UI behavior**

* Components involved: season prompts, season task descriptions, season skills, string-level tests
* Contracts touched: planner guidance only

---

## 4) Implementation Analysis

**Components / Modules**

* `prompts/agents/macrocycle_architect.md`
* `prompts/agents/season_plan_manager.md`
* `skills/season/plan-synthesis/SKILL.md`
* `skills/season/macrocycle-architecture/SKILL.md`
* `config/crewai/tasks.yaml`

**Data flow**

* Inputs: planning events, selected-scenario structure, deterministic phase-slot and phase-load context
* Processing: reverse-plan one or more target macrocycles, classify `A` events, map resulting structure onto legal phase sequences
* Outputs: unchanged Season draft bundle and persisted `SEASON_PLAN`, but with clearer multi-`A` guidance and justification expectations

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: none; string-level guidance only

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none in schemas or runtime interfaces
* Fallback behavior: single-`A` seasons continue to plan as before

**Conflicts with ADRs / Principles**

* Potential conflicts: none
* Resolution: remains compatible with canonical phase taxonomy by keeping macrocycle semantics above phases

**Impacted areas**

* UI: none
* Pipeline/data: Season planner guidance only
* Renderer: none
* Workspace/run-store: none
* Validation/tooling: prompt/skill text tests
* Deployment/config: task descriptions only

**Required refactoring**

* Replace single-anchor wording with multi-anchor / cluster-aware wording
* Add explicit conflict and post-`A` recovery rules to season guidance

---

## 6) Options & Recommendation

### Option A — guidance-only multi-A behavior

**Summary**

* Add prompt/task/skill rules without changing schemas.

**Pros**

* Low risk
* Keeps taxonomy stable
* Immediately improves planner behavior

**Cons**

* Macrocycle identity remains implicit rather than machine-readable

### Option B — add explicit macrocycle fields now

**Summary**

* Introduce `target_macrocycle_id`, `target_event_id`, and related schema fields immediately.

**Pros**

* Stronger machine-readable structure

**Cons**

* Larger contract change
* Not needed for this guidance pass

### Recommendation

* Choose: Option A
* Rationale: fixes planner behavior without reopening artifact or runtime contracts.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Macrocycle prompt allows one or more target macrocycles.
* [x] Season synthesis guidance distinguishes separate macrocycles from peak clusters.
* [x] Conflict-resolution and A-priority rules are stated explicitly.
* [x] Guidance requires A-event classification to appear in season justification.
* [x] Validation passes: syntax, targeted tests, lint, typecheck, CLI smoke.

---

## 8) Migration / Rollout

**Migration strategy**

* No migration required.

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert prompt/task/skill wording only

---

## 9) Risks & Failure Modes

* Failure mode: planner still collapses to one final A-event
  * Detection: season justification lacks per-A classification; generated season shows one terminal-only taper arc
  * Safe behavior: review/replan catches contradictory macrocycle logic
  * Recovery: tighten planner/audit guidance further

* Failure mode: planner creates overlapping rebuild/taper demands
  * Detection: macrocycle rationale contradicts spacing rules
  * Safe behavior: review rejects the candidate season bundle
  * Recovery: enforce stronger audit language

---

## 10) Observability / Logging

**New/changed events**

* none

**Diagnostics**

* inspect generated season justification, event constraints, and transition guardrails

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] `CHANGELOG.md` — summarize multi-A-event reverse-planning guidance
* [x] `doc/architecture/agents.md` — note multi-macrocycle season guidance at season planning level

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* Agent architecture: `doc/architecture/agents.md`
* Artefact flow: `doc/overview/artefact_flow.md`
* Planning flow: `doc/overview/how_to_plan.md`
* ADR: `doc/adr/ADR-053-canonical-phase-taxonomy-and-build-subtypes.md`
