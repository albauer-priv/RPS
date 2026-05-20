---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-20
Owner: Planning / Week Engine
---
# FEAT: Week Protocol Diversification and Re-Entry Shaping

* **ID:** FEAT_week_protocol_diversification_and_reentry_shaping
* **Status:** Implemented
* **Owner/Area:** Week Planning / Workout Selection
* **Last-Updated:** 2026-05-20
* **Related:** [FEAT_workout_protocol_generation_rules.md](/Users/alexander/RPS/doc/specs/features/FEAT_workout_protocol_generation_rules.md)

---

## 1) Context / Problem

**Current behavior**

* The deterministic week engine selects legal workout protocols and the solver renders them deterministically.
* The resulting week can be contract-valid while still being too monotonous within a recovery-sensitive phase.

**Problem**

* In `shortened_re_entry` weeks the engine could select the same upper-tempo quality session twice, which is formally legal but methodically too coarse.
* `PHASE_GUARDRAILS` and `PHASE_STRUCTURE` can disagree on allowed load modalities, especially around `K3`.
* `PHASE_PREVIEW` provides useful week-shape hints, but the week engine did not expose drift from those hints.

**Constraints**

* The fix must stay deterministic.
* The Intervals export surface must remain unchanged.
* `PHASE_PREVIEW` remains non-binding; it can guide and warn, but not override binding contracts.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Reduce protocol monotony across quality days in recovery-sensitive shortened weeks.
* [x] Damp the second repeated tempo-quality stimulus in `shortened_re_entry` instead of repeating the same upper-tempo dose.
* [x] Enforce the stricter effective load-modality set when `PHASE_GUARDRAILS` and `PHASE_STRUCTURE` disagree.
* [x] Surface preview-alignment and modality-consistency warnings.

**Non-Goals**

* [x] No hard binding of `PHASE_PREVIEW`.
* [x] No new persisted artefact types.
* [x] No completed-session logic.

---

## 3) Proposed Behavior

* For `shortened_*` phase intents, week-level quality protocol selection should avoid duplicate quality protocol variants when a legal alternative exists.
* If the second quality day still resolves to the same tempo-classic protocol in a `shortened_re_entry` week, the engine should damp it:
  * reduce the target range
  * reduce the TiZ target
  * keep the session legal and deterministic
* Effective allowed load modalities are the intersection of:
  * `PHASE_GUARDRAILS.allowed_load_modalities`
  * `PHASE_STRUCTURE.execution_principles.load_intensity_handling.load_modality_constraints`
  when both are present.
* If `PHASE_PREVIEW` hints differ from the generated week shape, emit warnings into the planning bundle and final `WEEK_PLAN`.

---

## 4) Implementation Analysis

* `week_engine.py`
  * compute effective modalities
  * track selected quality variants within the week
  * apply shortened re-entry shaping to repeated tempo sessions
  * collect preview-alignment warnings
* `workout_generation_guide.md`
  * explain why re-entry weeks should not stack the same upper-tempo session twice
* `FEAT_workout_protocol_generation_rules.md`
  * capture diversification and dampening as week-level rules above the solver

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible for persisted artefacts.

**Impacted areas**

* Week planning behavior
* Bundle warnings
* Final `WEEK_PLAN` warning text

---

## 6) Options & Recommendation

### Option A — Shape repeated quality sessions in the week engine

**Pros**

* Keeps solver focused on protocol progression.
* Handles phase-sensitive week-shape logic where it belongs.

**Cons**

* Adds some selection logic above the solver.

### Recommendation

* Choose Option A.

---

## 7) Acceptance Criteria

* [x] `shortened_re_entry` weeks no longer emit two identical upper-tempo quality sessions without warning or dampening.
* [x] If `K3` is allowed in guardrails but blocked in phase structure, the week engine uses the stricter effective modality set.
* [x] Preview drift is surfaced as warnings, not silent behavior.
* [x] Tests cover repeated-tempo dampening and modality-consistency handling.

---

## 8) Migration / Rollout

* No migration required.

---

## 9) Risks & Failure Modes

* Failure mode: preview warnings become noisy
  * Safe behavior: warning only; no blocking
* Failure mode: effective modality intersection becomes empty
  * Safe behavior: fall back to guardrails set and emit warning

---

## 10) Observability / Logging

* Week bundle warnings now carry:
  * modality mismatch
  * preview alignment drift
  * re-entry dampening markers

---

## 11) Documentation Updates

* [x] [doc/specs/features/FEAT_week_protocol_diversification_and_reentry_shaping.md](/Users/alexander/RPS/doc/specs/features/FEAT_week_protocol_diversification_and_reentry_shaping.md)
* [x] [doc/specs/features/FEAT_workout_protocol_generation_rules.md](/Users/alexander/RPS/doc/specs/features/FEAT_workout_protocol_generation_rules.md)
* [x] [doc/overview/workout_generation_guide.md](/Users/alexander/RPS/doc/overview/workout_generation_guide.md)

---

## 12) Link Map

* [doc/overview/how_to_plan.md](/Users/alexander/RPS/doc/overview/how_to_plan.md)
* [doc/overview/artefact_flow.md](/Users/alexander/RPS/doc/overview/artefact_flow.md)
* [specs/knowledge/_shared/sources/policies/workout_policy.md](/Users/alexander/RPS/specs/knowledge/_shared/sources/policies/workout_policy.md)
* [specs/knowledge/_shared/sources/principles/principles_durability_first_cycling.md](/Users/alexander/RPS/specs/knowledge/_shared/sources/principles/principles_durability_first_cycling.md)
