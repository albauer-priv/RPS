---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-20
Owner: Planning
---
# FEAT: Deterministic Recovery-Sensitive S5 Fallback Semantics

* **ID:** FEAT_phase_s5_recovery_fallback_semantics
* **Status:** Implemented
* **Owner/Area:** Planning / Load Governance
* **Last-Updated:** 2026-05-20
* **Related:** `FEAT_phase_intent_semantic_backbone`

---

## 1) Context / Problem

**Current behavior**

* `build_load_capacity_context(...)` derives per-week S5 bands by intersecting season corridor, feasibility, KPI band, and progression overlays.
* When the progression overlay conflicts with KPI lower bounds, `derive_phase_s5_band(...)` may fall back to `dropped_progression_overlay`.

**Problem**

* For recovery-sensitive phase intents and reset-like week roles, the fallback can erase required load reduction.
* This creates an internal contradiction: deterministic `week_role_by_iso_week` requires a reset, but the emitted S5 band re-inflates the week back to load-level.
* Phase guardrails correctly reject this contradiction, but the fallback hierarchy is wrong.

**Constraints**

* Fallback behavior must remain deterministic and code-owned.
* The fix must use normalized planning semantics (`phase_intent`, `week_role`) instead of prompt prose.
* Existing build-phase behavior should remain unchanged unless the week role / phase intent explicitly requires recovery-sensitive handling.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Protect reset-like and shortened recovery-sensitive weeks from KPI-lower-bound inflation.
* [x] Make the fallback decision deterministic from `week_role` and `phase_intent`.
* [x] Preserve existing non-recovery build behavior where KPI lower bounds remain active.

**Non-Goals**

* [x] No schema changes.
* [x] No changes to LLM prompts or guardrail severity in this pass.

---

## 3) Proposed Behavior

**User/System behavior**

* When a week is recovery-sensitive by `phase_intent` / `week_role`, KPI lower bounds no longer override required reset/reduction semantics.
* For those weeks, KPI remains an upper-cap input only; role-aware progression remains binding.
* The S5 trace explicitly records the deterministic fallback policy.

**UI impact**

* UI affected: No

**Non-UI behavior**

* Components involved:
  * `src/rps/planning/load_bands.py`
  * `tests/test_load_bands.py`
* Contracts touched:
  * deterministic S5 band trace semantics
  * phase guardrail compatibility for reset/recovery weeks

---

## 4) Implementation Analysis

**Components / Modules**

* `load_bands.py`: add deterministic S5 fallback policy derived from `week_role` + `phase_intent`.
* `test_load_bands.py`: add regression tests for shortened mini-reset protection and non-recovery KPI enforcement.

**Data flow**

* Inputs:
  * `season_plan_payload`
  * `week_role_by_week`
  * `phase_role_by_week`
  * normalized `phase_intent`
* Processing:
  * derive week-level fallback policy
  * convert KPI band to upper-only mode for protected weeks
  * prevent `dropped_progression_overlay` for protected weeks
* Outputs:
  * deterministic `s5_bands` with explicit policy trace

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: protected reset/recovery weeks should no longer fail `phase_week_role_load_coherence` due to deterministic fallback inflation

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none
* Fallback behavior:
  * protected weeks switch KPI lower-bound handling from hard lower-bound to upper-only

**Conflicts with ADRs / Principles**

* Potential conflicts: none
* Resolution: aligns deterministic contracts with existing recovery/reset semantics

**Impacted areas**

* UI: none directly
* Pipeline/data: deterministic phase/week load context
* Renderer: none
* Workspace/run-store: none
* Validation/tooling: phase guardrails now see coherent reset bands
* Deployment/config: none

**Required refactoring**

* Add one explicit S5 fallback-policy helper

---

## 6) Options & Recommendation

### Option A — deterministic week-role / phase-intent policy

**Summary**

* Use normalized planning semantics to decide when KPI lower bounds may be relaxed.

**Pros**

* Deterministic
* Explains behavior in traces
* Preserves guardrail strictness

**Cons**

* Adds another policy branch inside load-band derivation

**Risk**

* If scoped too broadly, KPI lower bounds may be weakened for weeks that should still enforce them

### Option B — weaken the guardrail

**Summary**

* Let reset weeks pass even if final bands are flat versus prior load weeks

**Pros**

* Minimal code

**Cons**

* Hides a real contradiction instead of fixing it

### Recommendation

* Choose: Option A
* Rationale: the contradiction originates in deterministic band construction, so the fix belongs there.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Recovery-sensitive shortened/reset weeks preserve material load reduction in deterministic S5 output.
* [x] Non-recovery build weeks still allow KPI-lower-bound-driven fallback when appropriate.
* [x] S5 traces expose the applied deterministic fallback policy.
* [x] Validation passes: targeted `pytest`, `py_compile`, lint, and typecheck.

---

## 8) Migration / Rollout

**Migration strategy**

* None

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert deterministic fallback-policy helper

---

## 9) Risks & Failure Modes

* Failure mode: recovery policy applied too broadly
  * Detection: build-week S5 traces show `upper_only` unexpectedly
  * Safe behavior: tests catch protected vs non-protected behavior split
  * Recovery: narrow the policy scope

---

## 10) Observability / Logging

**New/changed events**

* No new runtime event types

**Diagnostics**

* `s5_bands[].trace.s5_fallback_policy`
* phase guardrail failures in run `events.jsonl`

---

## 11) Documentation Updates

* [x] `CHANGELOG.md` — note deterministic recovery-sensitive S5 fallback fix
* [x] `doc/specs/features/FEAT_phase_s5_recovery_fallback_semantics.md` — canonical feature record

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* Validation / runbooks: `doc/runbooks/validation.md`
* ADRs: `doc/adr/README.md`
