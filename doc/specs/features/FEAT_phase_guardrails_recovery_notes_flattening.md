---
Version: 1.0
Status: Implemented
Last-Updated: 2026-04-13
Owner: Specs
---
# FEAT: Phase Guardrails Recovery Notes Flattening

* **ID:** FEAT_phase_guardrails_recovery_notes_flattening
* **Status:** Implemented
* **Owner/Area:** Phase-Architect / Specs
* **Last-Updated:** 2026-04-13
* **Related:** `specs/knowledge/_shared/sources/specs/mandatory_output_phase_guardrails.md`, `src/rps/agents/multi_output_runner.py`

---

## 1) Context / Problem

**Current behavior**

* `SEASON_PLAN` defines `data.global_constraints.recovery_protection.notes` as an array of strings.
* `PHASE_GUARDRAILS` defines `data.execution_non_negotiables.recovery_protection_rules` as a single required string.
* The Phase-Guardrails mandatory output chapter required the season-plan notes to appear "verbatim" in that single string field.

**Problem**

* The prompt/spec contract was internally unsatisfiable.
* The model correctly stopped instead of emitting an invalid artefact.
* This blocks Phase Guardrails creation and therefore blocks planning for the affected week.

**Constraints**

* `PHASE_GUARDRAILS` schema remains string-based for `recovery_protection_rules`.
* Season-plan recovery notes remain an array.
* The mapping must preserve every upstream note without weakening validation expectations.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Define one unambiguous mapping from season-plan recovery note arrays into the phase-guardrails string field.
* [x] Remove the impossible "array verbatim into string" wording from the mandatory output chapter.
* [x] Add runtime normalization so list-shaped model output can still be repaired before store validation.

**Non-Goals**

* [x] Changing the `SEASON_PLAN` schema shape.
* [x] Changing the `PHASE_GUARDRAILS` schema field from string to array.

---

## 3) Proposed Behavior

**User/System behavior**

* Every entry in `season_plan.data.global_constraints.recovery_protection.notes` must be preserved verbatim.
* `PHASE_GUARDRAILS.data.execution_non_negotiables.recovery_protection_rules` stores those entries as one string joined by ` | `.
* If a model emits a list for `recovery_protection_rules`, the runner normalizes it into that canonical joined string before validation/store.

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved: Phase-Architect mandatory-output knowledge and multi-output normalization
* Contracts touched: season-to-phase recovery-note propagation only

---

## 4) Implementation Analysis

**Components / Modules**

* `specs/knowledge/_shared/sources/specs/mandatory_output_phase_guardrails.md`: define canonical array-to-string flattening.
* `src/rps/agents/multi_output_runner.py`: normalize list output for `recovery_protection_rules`.
* `tests/test_multi_output_runner.py`: verify normalization behavior.

**Data flow**

* Inputs: `season_plan.data.global_constraints.recovery_protection.notes`
* Processing: preserve each entry verbatim, flatten with ` | ` delimiter
* Outputs: schema-valid `execution_non_negotiables.recovery_protection_rules` string

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: existing string schema remains valid; propagation becomes satisfiable

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none
* Fallback behavior: if only one note exists, the field remains a single string with that one note

**Conflicts with ADRs / Principles**

* Potential conflicts: none
* Resolution: preserves upstream constraints exactly while staying within the existing schema contract

**Impacted areas**

* UI: none
* Pipeline/data: phase planning unblocks
* Renderer: none
* Workspace/run-store: blocked phase runs can complete again
* Validation/tooling: normalization and tests added
* Deployment/config: none

**Required refactoring**

* None beyond prompt/spec clarification and runner normalization

---

## 6) Options & Recommendation

### Option A — Flatten notes into one canonical string

**Summary**

* Preserve each note verbatim and join with a stable delimiter.

**Pros**

* Minimal change surface.
* Keeps both current schemas intact.
* Removes the prompt contradiction.

**Cons**

* The list structure is not preserved in the phase artefact.

**Risk**

* Low; content fidelity is preserved.

### Option B — Change `PHASE_GUARDRAILS` schema to array

**Summary**

* Align the phase field to the season field shape.

**Pros**

* More structurally consistent.

**Cons**

* Wider schema and renderer impact than needed.
* Requires downstream changes.

### Recommendation

* Choose: Option A
* Rationale: the issue is a contract mismatch, not a need for a wider schema redesign.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Phase-Guardrails mandatory output no longer asks the model to place an array verbatim into a string field.
* [x] All season recovery notes are still required and preserved verbatim in the phase output.
* [x] Runner normalization converts list-shaped `recovery_protection_rules` into the canonical string form.
* [x] Validation passes: `python3 -m py_compile $(git ls-files '*.py')`
* [x] Validation passes: targeted runner tests

---

## 8) Migration / Rollout

**Migration strategy**

* None required.

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert the mandatory-output wording and runner normalization

---

## 9) Risks & Failure Modes

* Failure mode: models still STOP because stale knowledge text is injected elsewhere
  * Detection: logs still mention the old "verbatim array into string" conflict
  * Safe behavior: no invalid artefact is stored
  * Recovery: re-sync bundled knowledge/vector store and verify injected mandatory-output content

---

## 10) Observability / Logging

**New/changed events**

* No new log families

**Diagnostics**

* `rps.agents.multi_output_runner` no-tool-call STOP text
* Plan-week logs around `CREATE_PHASE_GUARDRAILS`

---

## 11) Documentation Updates

* [x] `doc/specs/features/FEAT_phase_guardrails_recovery_notes_flattening.md`
* [ ] `CHANGELOG.md`

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/agents.md`
* Artefact flow: `doc/overview/artefact_flow.md`
* Validation: `doc/specs/contracts/validation/phase_guardrails_validation.md`
* Contracts: `specs/knowledge/_shared/sources/contracts/season__phase_contract.md`
