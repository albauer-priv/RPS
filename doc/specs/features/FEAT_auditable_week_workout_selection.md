---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-20
Owner: Planning / Week Selection
---
# FEAT: Auditable Week Workout Selection

* **ID:** FEAT_auditable_week_workout_selection
* **Status:** Implemented
* **Owner/Area:** Week Planning / Workout Selection
* **Last-Updated:** 2026-05-20
* **Related:** [FEAT_workout_protocol_generation_rules.md](/Users/alexander/RPS/doc/specs/features/FEAT_workout_protocol_generation_rules.md), [FEAT_week_protocol_diversification_and_reentry_shaping.md](/Users/alexander/RPS/doc/specs/features/FEAT_week_protocol_diversification_and_reentry_shaping.md), [ADR-052-protocol-driven-week-workout-generation.md](/Users/alexander/RPS/doc/adr/ADR-052-protocol-driven-week-workout-generation.md)

---

## 1) Context / Problem

**Current behavior**

* Week planning already uses a deterministic protocol registry and a deterministic protocol solver.
* Selection of weekly workout combinations was still mainly based on ordered candidate lists plus a few targeted shaping rules.
* The system already emits `selection_reason`, warnings, and progression metadata, but not a complete candidate-by-candidate audit trail.

**Problem**

* External reviewers could not fully reconstruct why one legal workout candidate was selected over another.
* Week-level logic such as duplicate-workout avoidance, anti-monotony shaping, preview alignment, and modality mismatch handling was only partially visible in configuration.
* Quality assurance needed one canonical, flat, exportable audit surface that could be inspected without reading Python control flow.

**Constraints**

* The selector must stay deterministic.
* The selector must remain downstream of existing season/phase artefacts.
* The existing protocol solver and Intervals export layer stay in place.
* `freeride` remains unsupported.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Add a deterministic week-level selector above the protocol solver.
* [x] Keep selection policy reviewable in a flat config table.
* [x] Persist one audit artefact per generated `WEEK_PLAN`.
* [x] Export the same audit rows as CSV for external review.
* [x] Make duplicate-workout avoidance, monotony penalties, preview alignment, and modality strictness externally visible.

**Non-Goals**

* [x] No LLM-based selection logic.
* [x] No replacement of the protocol solver.
* [x] No persisted `WEEK_PLAN` schema break.

---

## 3) Proposed Behavior

**User/System behavior**

* Week planning first selects suitable workout protocol variants for each training day.
* The selector uses season/phase intent, week role, day role, legal domains/modalities, prior progression state, preview hints, and already-selected weekly stimuli.
* The selector records every evaluated candidate in a structured audit artefact and a CSV sidecar.
* The protocol solver then turns only the selected protocol variants into concrete workouts.

**UI impact**

* UI affected: No direct page flow change in this feature.
* The resulting `WEEK_PLAN` and audit artefacts are available for downstream inspection and future UI surfacing.

**Non-UI behavior**

* Components involved:
  * `config/planning/week_workout_protocols.yaml`
  * `config/planning/week_workout_selection_rules.yaml`
  * `rps.planning.week_selector`
  * `rps.planning.week_engine`
  * `rps.workouts.protocol_solver`
* Contracts touched:
  * internal week workout blueprint metadata
  * new audit artefact contract
  * new flat selector-rule registry contract

---

## 4) Implementation Analysis

**Components / Modules**

* `week_workout_selection_rules.yaml`: canonical flat selector-policy registry.
* `week_selection_rules.py`: typed loader and matcher for selector rows.
* `week_selector.py`: deterministic candidate evaluation, scoring, and audit row generation.
* `week_engine.py`: integrates selector, persists audit artefact, keeps solver layering intact.
* `models.py`: extends workout blueprint metadata with selector-facing fields.

**Data flow**

* Inputs:
  * `SEASON_PLAN`
  * `PHASE_GUARDRAILS`
  * `PHASE_STRUCTURE`
  * `PHASE_PREVIEW`
  * previous `WEEK_PLAN`
  * protocol registry
  * selector-rule registry
* Processing:
  * build candidate pool
  * evaluate legal/illegal status
  * resolve best matching selector rule row
  * score candidates deterministically
  * pick final weekly combination with stable tie-breakers
  * persist audit rows + CSV
  * pass selected protocols to the solver
* Outputs:
  * `WEEK_PLAN`
  * `WEEK_WORKOUT_SELECTION_AUDIT`
  * CSV sidecar for the audit rows

**Schema / Artefacts**

* New artefact: `WEEK_WORKOUT_SELECTION_AUDIT` (`week_workout_selection_audit.schema.json`)
* Changed internal semantics:
  * `WeekWorkoutBlueprintModel.stimulus_class`
  * `WeekWorkoutBlueprintModel.monotony_group`
  * `WeekWorkoutBlueprintModel.selection_score`
  * `WeekWorkoutBlueprintModel.selection_rule_row_ids`

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes.
* Breaking changes: none in persisted `WEEK_PLAN`.
* Fallback behavior:
  * if no selector rule matches a candidate, the candidate is filtered with `no_selection_rule`
  * if no prior progression signature exists, progression fit bonus is zero

**Conflicts with ADRs / Principles**

* No conflict with ADR-052.
* This feature strengthens the existing code-owned deterministic planning direction.

**Impacted areas**

* UI: no immediate page changes.
* Pipeline/data: new audit artefact and CSV sidecar.
* Renderer: unchanged for workouts; no new rendered workout syntax.
* Workspace/run-store: new artefact type, schema mapping, path mapping.
* Validation/tooling: new schema validation and selector-row tests.
* Deployment/config: new flat selector-rule config.

**Required refactoring**

* Replace first-legal-candidate selection with scored deterministic selection.
* Move week-shape semantics out of opaque branches into flat selector rows wherever possible.
* Keep re-entry shaping as a lower-layer safety net, not the main weekly selection strategy.

---

## 6) Options & Recommendation

### Option A — Flat rule table + runtime audit artefact

**Summary**

* Keep selection policy in a denormalized flat rule registry and emit evaluated candidate rows per week.

**Pros**

* Externally auditable.
* Reviewable in Git.
* Easy to export as CSV.
* Deterministic and testable.

**Cons**

* More verbose config.
* Requires disciplined row maintenance.

### Option B — Code-scored selector with minimal config

**Summary**

* Keep only protocol registry in config and encode more selection logic in Python.

**Pros**

* Smaller config files.

**Cons**

* Harder for external reviewers to inspect.
* Worse auditability and weaker change review.

### Recommendation

* Choose: Option A
* Rationale: auditability is a first-class requirement here, and the flat rule table gives the cleanest external review surface.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] A flat selector-rule registry exists and loads deterministically.
* [x] The selector records all evaluated candidates in an audit artefact.
* [x] The audit artefact has a CSV sidecar with one row per evaluated candidate/day combination.
* [x] `shortened_re_entry` avoids two identical upper-tempo quality sessions when a legal differentiated candidate exists.
* [x] Modality mismatch between guardrails and phase structure is visible in warnings and reflected in candidate filtering.
* [x] `K3` counts as true quality and is blocked when effective modality constraints exclude it.
* [x] Existing protocol progression and Intervals export behavior remain valid.

---

## 8) Migration / Rollout

**Migration strategy**

* No migration needed for existing `WEEK_PLAN` artefacts.
* New audit artefacts begin on the next week-generation run.

**Rollout / gating**

* No feature flag.
* Safe rollback: revert selector registry, selector code, and audit artefact integration together.

---

## 9) Risks & Failure Modes

* Failure mode: no legal candidate survives selection for a planned workout day

  * Detection: selector raises with evaluated-candidate context
  * Safe behavior: week planning fails clearly instead of silently choosing an illegal fallback
  * Recovery: fix selector rows or phase constraints

* Failure mode: overlapping selector rows create ambiguity

  * Detection: multiple matching rows resolved by specificity + lexical row id
  * Safe behavior: deterministic resolution
  * Recovery: tighten the registry rows

* Failure mode: audit artefact diverges from actual selected workouts

  * Detection: tests compare selected rows and final workout blueprints
  * Safe behavior: fail tests / validation
  * Recovery: keep selector and audit generation in one code path

---

## 10) Observability / Logging

**New/changed events**

* `week_selector_candidates_evaluated`: candidate count, quality budget, phase intent, week role
* `week_selector_choice`: day, protocol variant, score, rule row ids
* `week_selector_audit_written`: JSON path and CSV path

**Diagnostics**

* Inspect `WEEK_WORKOUT_SELECTION_AUDIT`
* Inspect CSV sidecar
* Inspect `selection_reason`, warnings, and `progression_state` in `WEEK_PLAN`

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] [FEAT_workout_protocol_generation_rules.md](/Users/alexander/RPS/doc/specs/features/FEAT_workout_protocol_generation_rules.md) — mention week selector layering and auditability.
* [x] [workout_generation_guide.md](/Users/alexander/RPS/doc/overview/workout_generation_guide.md) — mention deterministic week-level selection and audit review.
* [x] [CHANGELOG.md](/Users/alexander/RPS/CHANGELOG.md) — note auditable deterministic selection and new artefact.

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* Artifact flow: `doc/overview/artefact_flow.md`
* Workout generation rules: [FEAT_workout_protocol_generation_rules.md](/Users/alexander/RPS/doc/specs/features/FEAT_workout_protocol_generation_rules.md)
* Re-entry shaping: [FEAT_week_protocol_diversification_and_reentry_shaping.md](/Users/alexander/RPS/doc/specs/features/FEAT_week_protocol_diversification_and_reentry_shaping.md)
* ADR: [ADR-052-protocol-driven-week-workout-generation.md](/Users/alexander/RPS/doc/adr/ADR-052-protocol-driven-week-workout-generation.md)
