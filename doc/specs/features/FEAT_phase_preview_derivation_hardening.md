---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-20
Owner: Workspace
---
# FEAT: Phase Preview Derivation Hardening

* **ID:** FEAT_phase_preview_derivation_hardening
* **Status:** Implemented
* **Owner/Area:** Workspace / Validation
* **Related:** `src/rps/workspace/guarded_store.py`, `skills/phase/preview-synthesis/SKILL.md`, `skills/phase/preview-review/SKILL.md`

---

## 1) Context / Problem

**Current behavior**

* `PHASE_PREVIEW` is intended to remain derived and informational.
* Prompt/skill guidance already says the preview must add no new planning decisions.
* Guarded-store validation only enforced `traceability.derived_from` against the stored `PHASE_STRUCTURE`.

**Problem**

* This leaves a gap between intent and enforcement.
* A preview could remain traceable while still drifting away from `PHASE_STRUCTURE` and `PHASE_GUARDRAILS` in structured fields such as week coverage, agenda day roles, intensity domains, modalities, fixed non-training days, or quality-day caps.

**Constraints**

* No schema version bump.
* `PHASE_PREVIEW` remains optional and informational.
* `PHASE_PREVIEW` must remain useful as a readable derived layer, not be reduced to a duplicate of `PHASE_STRUCTURE`.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Enforce that `PHASE_PREVIEW.weekly_agenda_preview` stays inside the stored `PHASE_STRUCTURE` authority.
* [x] Ensure preview weeks cover the same phase range as the stored structure.
* [x] Ensure preview agenda respects allowed day roles, intensity domains, load modalities, fixed non-training days, and quality-day caps.
* [x] Keep preview synthesis/review skills aligned with the new guarded-store invariants.

**Non-Goals**

* [ ] No change to `PHASE_PREVIEW` schema.
* [ ] No attempt to hard-validate free-form narrative wording such as `dominant_theme` or `what_is_flexible`.
* [ ] No change to Week planning authority; `PHASE_PREVIEW` remains informational there.

---

## 3) Proposed Behavior

**User/System behavior**

* `PHASE_PREVIEW` still exists and still serves as the informative explanatory layer.
* Store-time validation now rejects previews whose structured agenda contradicts the stored structure.
* Narrative flexibility remains, but structured preview content must stay inside phase authority.

**UI impact**

* UI affected: No

**Non-UI behavior**

* Components involved:
  * `GuardedValidatedStore`
  * phase preview synthesis/review skills
* Contracts touched:
  * `PHASE_PREVIEW`
  * `PHASE_STRUCTURE`

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/workspace/guarded_store.py`
  * extend preview validation beyond traceability
* `skills/phase/preview-synthesis/SKILL.md`
  * make derivation rules explicit for agenda fields
* `skills/phase/preview-review/SKILL.md`
  * review against the same structured invariants
* `tests/test_guarded_store.py`
  * add regression coverage

**Data flow**

* Inputs:
  * candidate `PHASE_PREVIEW`
  * stored exact-range `PHASE_STRUCTURE`
* Processing:
  * validate traceability
  * compare preview agenda weeks and day semantics against structure authority
* Outputs:
  * accepted preview save or schema-validation failure

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications:
  * preview validation becomes stricter on structured semantic derivation

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes at schema level; behavior is stricter.
* Breaking changes: previously accepted but semantically drifting previews may now fail to store.
* Fallback behavior: review/replan should correct the preview to match structure.

**Conflicts with ADRs / Principles**

* Potential conflicts: none
* Resolution: reinforces the existing authority split rather than changing it

**Impacted areas**

* UI: none
* Pipeline/data: phase preview store validation
* Renderer: none
* Workspace/run-store: guarded preview save path
* Validation/tooling: stricter preview validation
* Deployment/config: none

**Required refactoring**

* Replace traceability-only preview validation with structure-aware validation.

---

## 6) Options & Recommendation

### Option A — Guarded-store structured derivation checks

**Summary**

* Enforce only structured invariants at store time and leave free-form narrative text to review skills.

**Pros**

* Strong protection where drift is most harmful.
* Avoids brittle NLP-style narrative matching.
* Preserves preview usefulness.

**Cons**

* Some semantic drift can still exist in narrative prose.

**Risk**

* Mild risk of rejecting previews that were previously tolerated but structurally contradictory.

### Option B — Traceability-only plus stronger prompt text

**Summary**

* Keep validation light and rely on skills/review only.

**Pros**

* Lowest code change.

**Cons**

* Leaves the current gap in hard enforcement.

### Recommendation

* Choose: Option A
* Rationale: it closes the real authority gap without overfitting narrative text.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `PHASE_PREVIEW` must reference the stored `PHASE_STRUCTURE` filename.
* [x] `weekly_agenda_preview` weeks must match the phase range / structure coverage.
* [x] Agenda day roles, intensity domains, and load modalities must stay inside structure authority.
* [x] Fixed non-training days must remain non-training in preview agenda.
* [x] Preview weekly `QUALITY` count must not exceed the structure cap.
* [x] Validation passes: `python3 -m py_compile`, `./scripts/run_lint.sh`, `./scripts/run_typecheck.sh`, targeted pytest.

---

## 8) Migration / Rollout

**Migration strategy**

* No data migration.
* Existing previews remain readable; only future writes are stricter.

**Rollout / gating**

* No feature flag.
* Safe rollback: revert the guarded-store checks and skill wording.

---

## 9) Risks & Failure Modes

* Failure mode: a preview draft is rejected although it is narratively acceptable.
  * Detection: guarded-store validation error on `PHASE_PREVIEW`
  * Safe behavior: stop persistence and surface the mismatch
  * Recovery: adjust the preview draft or review guidance

* Failure mode: narrative still drifts while structured agenda passes.
  * Detection: preview review output
  * Safe behavior: review can still reject
  * Recovery: tighten preview-review guidance further if needed

---

## 10) Observability / Logging

**New/changed events**

* No new log events; existing guarded-store schema-validation failures now cover more preview mismatches.

**Diagnostics**

* `rps.log`
* guarded-store exception text
* phase review outputs

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] [doc/specs/contracts/validation/phase_preview_validation.md](/Users/alexander/RPS/doc/specs/contracts/validation/phase_preview_validation.md) — add structured derivation checks
* [x] [CHANGELOG.md](/Users/alexander/RPS/CHANGELOG.md) — record preview hardening

---

## 12) Link Map

* Workspace: [doc/architecture/workspace.md](/Users/alexander/RPS/doc/architecture/workspace.md)
* Validation runbook: [doc/runbooks/validation.md](/Users/alexander/RPS/doc/runbooks/validation.md)
* Phase contract: [season__phase_contract.md](/Users/alexander/RPS/specs/knowledge/_shared/sources/contracts/season__phase_contract.md)
