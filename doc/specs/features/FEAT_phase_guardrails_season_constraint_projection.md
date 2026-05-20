---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-20
Owner: Planning Runtime
---
# FEAT: Phase Guardrails Season Constraint Projection

* **ID:** FEAT_phase_guardrails_season_constraint_projection
* **Status:** Implemented
* **Owner/Area:** Planning Runtime / Phase Guardrails
* **Last-Updated:** 2026-05-20
* **Related:** `src/rps/agents/output_normalization.py`, `src/rps/workspace/guarded_store.py`, `doc/specs/features/FEAT_guarded_store_constraint_matching.md`

---

## 1) Context / Problem

**Current behavior**

* `PHASE_GUARDRAILS` is authored by the phase bundle and then validated by `GuardedValidatedStore`.
* The guarded store requires exact propagation of selected `SEASON_PLAN.data.global_constraints` content:
  * `availability_assumptions`
  * `risk_constraints`
  * `planned_event_windows`
  * `recovery_protection.notes`

**Problem**

* The phase writer often paraphrases or compresses these constraints instead of repeating them verbatim.
* The phase run can therefore pass planning and review, but fail at persistence with `Required isolated phase artefacts missing`.
* This is wasteful because the missing content is already available deterministically in the runtime from `SEASON_PLAN`.

**Constraints**

* No schema bump.
* No relaxation of the guarded-store propagation rules.
* The solution must stay deterministic and runtime-owned.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Deterministically project required season constraints into `PHASE_GUARDRAILS` before store validation.
* [x] Preserve existing writer-authored content while appending missing binding season constraints.
* [x] Support both date-based planned-event strings and current free-text / ISO-week season event window markers.

**Non-Goals**

* [x] Changing `PHASE_GUARDRAILS` schema structure.
* [x] Weakening guarded-store propagation rules.
* [x] Moving season-constraint authority back into prompt-only behavior.

---

## 3) Proposed Behavior

**User/System behavior**

* Before persisting `PHASE_GUARDRAILS`, the runtime normalizer inspects the loaded `SEASON_PLAN`.
* Missing season constraints are appended into the phase guardrails deterministically:
  * availability assumptions into `phase_summary.non_negotiables`
  * risk constraints into `phase_summary.key_risks_warnings`
  * recovery notes into `execution_non_negotiables.recovery_protection_rules`
  * planned event windows:
    * date-based compact markers become structured `events_constraints.events[]`
    * non-date/free-text markers are preserved verbatim in the guardrails text payload

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved: CrewAI output normalization, guarded-store validation
* Contracts touched: `SEASON_PLAN -> PHASE_GUARDRAILS` propagation contract

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/agents/output_normalization.py`
  * extract loaded season-plan document from workspace tool results
  * deterministically project required season constraints into phase guardrails
* `src/rps/agents/crewai_backend.py`
  * pass loaded season-plan context into phase-guardrails normalization
* `tests/test_output_normalization.py`
  * regression coverage for verbatim constraint projection and planned-event repair

**Data flow**

* Inputs: `PHASE_GUARDRAILS` draft payload, loaded `SEASON_PLAN`
* Processing: append missing constraint strings / structured event markers
* Outputs: store-ready `PHASE_GUARDRAILS` envelope

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: guarded-store validation stays unchanged; normalized payload now satisfies it

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none
* Fallback behavior: if `SEASON_PLAN` is unavailable, normalization remains best-effort and leaves the payload untouched

**Conflicts with ADRs / Principles**

* Potential conflicts: none
* Resolution: preserves runtime-owned contract enforcement and reduces prompt brittleness

**Impacted areas**

* UI: none
* Pipeline/data: phase persistence becomes robust against paraphrased constraints
* Renderer: none
* Workspace/run-store: fewer false persistence failures for phase runs
* Validation/tooling: guarded-store remains strict; normalizer gets broader deterministic repair
* Deployment/config: none

**Required refactoring**

* Extend phase-guardrails normalization to accept loaded season-plan context

---

## 6) Options & Recommendation

### Option A — Deterministic pre-store projection

**Summary**

* Repair `PHASE_GUARDRAILS` using runtime-owned season-plan inputs before guarded-store validation.

**Pros**

* Deterministic
* Localized change
* Preserves strict validation

**Cons**

* Adds more normalization logic in runtime

**Risk**

* Low; projection rules are direct copies from the season plan

### Option B — Relax guarded-store propagation checks

**Summary**

* Accept paraphrased phase guardrails without projecting the exact season constraints.

**Pros**

* Smaller code change

**Cons**

* Weakens contract guarantees
* Leaves downstream artifacts less traceable

### Recommendation

* Choose: Option A
* Rationale: the source data is deterministic and already present in runtime, so repair belongs in code, not in another prompt retry.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `PHASE_GUARDRAILS` normalization appends missing season availability assumptions and risk constraints verbatim.
* [x] Recovery notes are preserved verbatim in `recovery_protection_rules`.
* [x] Date-based planned-event windows are materialized into structured `events_constraints.events[]`.
* [x] Free-text or ISO-week season event-window markers remain semantically present in the normalized guardrails payload.
* [x] Validation passes: `python3 -m py_compile $(git ls-files '*.py')`
* [x] Validation passes: `pytest -q tests/test_output_normalization.py tests/test_guarded_store.py`

---

## 8) Migration / Rollout

**Migration strategy**

* None

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert the projection helper and tests

---

## 9) Risks & Failure Modes

* Failure mode: season plan is not loaded by the workspace tool path
  * Detection: phase guardrails still fail guarded-store propagation checks
  * Safe behavior: store rejects the payload instead of persisting partial constraints
  * Recovery: load the season plan through the runtime tool path or add another deterministic lookup

---

## 10) Observability / Logging

**New/changed events**

* No new runtime event families

**Diagnostics**

* `rps.workspace.guarded_store` persistence errors
* normalized `PHASE_GUARDRAILS` payload in local regression tests

---

## 11) Documentation Updates

* [x] [doc/specs/features/FEAT_phase_guardrails_season_constraint_projection.md](/Users/alexander/RPS/doc/specs/features/FEAT_phase_guardrails_season_constraint_projection.md) — new feature spec
* [x] [CHANGELOG.md](/Users/alexander/RPS/CHANGELOG.md) — add unreleased fix entry

## 12) Link Map

* [doc/specs/features/FEAT_guarded_store_constraint_matching.md](/Users/alexander/RPS/doc/specs/features/FEAT_guarded_store_constraint_matching.md)
* [doc/architecture/workspace.md](/Users/alexander/RPS/doc/architecture/workspace.md)
* [doc/overview/artefact_flow.md](/Users/alexander/RPS/doc/overview/artefact_flow.md)
