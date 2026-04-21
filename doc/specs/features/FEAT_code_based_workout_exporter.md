---
Version: 1.0
Status: Implemented
Last-Updated: 2026-04-21
Owner: Planning Pipeline
---
# FEAT: Code-Based Workout Exporter

* **ID:** FEAT_code_based_workout_exporter
* **Status:** Implemented
* **Owner/Area:** Planning / Workout Export
* **Last-Updated:** 2026-04-21
* **Related:** `src/rps/orchestrator/workout_export.py`, `src/rps/workouts/exporter.py`

---

## 1) Context / Problem

**Current behavior**

* `plan_week(...)` delegated Intervals export generation to the `workout_builder` LLM agent.
* The agent is instructed to do deterministic conversion only: validate `WEEK_PLAN.workout_text`, map it into `INTERVALS_WORKOUTS`, and store the export.

**Problem**

* The former builder could false-stop on valid `workout_text`, because validation was model-judged instead of deterministically enforced in code.
* The output contract is simple enough that an LLM adds failure surface without adding useful decision quality.

**Constraints**

* No new dependencies.
* Existing artefact schemas and filenames must remain unchanged.
* Existing `INTERVALS_WORKOUTS` store path and versioning must remain week-scoped.
* Validation must respect:
  * `intervals_workout_ebnf.md` as the formal grammar baseline
  * `workout_syntax_and_validation.md` as the cycling-specific subset restriction
  * `workout_json_spec.md` as the export mapping

---

## 2) Goals & Non-Goals

**Goals**

* [x] Replace the LLM-based export step with deterministic code.
* [x] Enforce `WEEK_PLAN` -> `INTERVALS_WORKOUTS` transformation in code using schema + workout-text validation.
* [x] Preserve current orchestrator behavior, artefact type, storage path, and posting integration.

**Non-Goals**

* [ ] Replacing `week_planner` workout generation.
* [ ] Implementing a full generic EBNF parser beyond the project-relevant workout subset.

---

## 3) Proposed Behavior

**User/System behavior**

* `plan_week(...)` still generates `WEEK_PLAN` first.
* The subsequent export step no longer calls the `workout_builder` LLM.
* A local exporter loads `WEEK_PLAN`, validates it, validates each `workout_text` against the project workout subset, maps workouts to the Intervals JSON array, validates the output schema, and stores `INTERVALS_WORKOUTS`.

**UI impact**

* UI affected: No

**Non-UI behavior**

* Components involved:
  * `src/rps/orchestrator/workout_export.py`
  * new `src/rps/workouts/*`
* Contracts touched:
  * `week__builder_contract.md`
  * `workout_json_spec.md`
  * `intervals_workout_ebnf.md`
  * `workout_syntax_and_validation.md`

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/workouts/validator.py`: local workout-text validation and agenda consistency checks.
* `src/rps/workouts/exporter.py`: deterministic `WEEK_PLAN` -> `INTERVALS_WORKOUTS` mapping.
* `src/rps/orchestrator/workout_export.py`: swap agent execution for local exporter/store path.

**Data flow**

* Inputs: `WEEK_PLAN` artefact for one ISO week.
* Processing:
  * validate input schema
  * validate workout references and `workout_text`
  * map to export JSON array
  * validate output schema
  * store `INTERVALS_WORKOUTS`
* Outputs: `INTERVALS_WORKOUTS` artefact with the same week-scoped versioning as before.

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications:
  * `week_plan.schema.json` must pass before conversion
  * `workouts.schema.json` must pass before storage

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: the `workout_builder` agent and prompt are no longer used on the export path
* Fallback behavior: export fails with explicit deterministic validation errors instead of model STOP text

**Conflicts with ADRs / Principles**

* Potential conflicts: none identified
* Resolution: aligns with “UI delegates orchestration” and deterministic pipeline boundaries

**Impacted areas**

* UI: none
* Pipeline/data: export step becomes code-based
* Renderer: none
* Workspace/run-store: same artefact write path, same versioning
* Validation/tooling: new local validator added
* Deployment/config: none

**Required refactoring**

* Remove agent dependency from `workout_export.py`
* Introduce explicit validator/exporter modules

---

## 6) Options & Recommendation

### Option A — Code-based exporter

**Summary**

* Replace the LLM export step with local validation and mapping code.

**Pros**

* Deterministic
* No false model stops
* Easier to test
* Faster and cheaper

**Cons**

* Requires maintaining local validation logic

**Risk**

* Under-validating the intended grammar if the subset rules drift from specs

### Option B — Keep LLM builder, only tighten prompt

**Summary**

* Keep the agent and improve prompt instructions.

**Pros**

* Lower immediate code change

**Cons**

* Still non-deterministic
* False positives remain possible

### Recommendation

* Choose: Option A
* Rationale: the export step is purely technical transformation and should not depend on model judgment

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `create_intervals_workouts_export(...)` no longer calls the `workout_builder` LLM path.
* [x] Valid `WEEK_PLAN` workout texts convert to schema-valid `INTERVALS_WORKOUTS`.
* [x] Invalid workout text yields deterministic validation errors.
* [x] Validation passes: `py_compile`, `ruff`, `mypy`, targeted pytest
* [x] No regressions in `INTERVALS_WORKOUTS` storage path or version resolution
* [x] Performance guardrail: no additional network/model call for export generation

---

## 8) Migration / Rollout

**Migration strategy**

* No artefact migration required.

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert `workout_export.py` to the prior agent-based path

---

## 9) Risks & Failure Modes

* Failure mode: local validator rejects valid planner output
  * Detection: deterministic error message in planning log
  * Safe behavior: do not write `INTERVALS_WORKOUTS`
  * Recovery: adjust validator/test/spec alignment

* Failure mode: output mapping produces schema-invalid JSON
  * Detection: output schema validation fails before store
  * Safe behavior: stop and log validation error
  * Recovery: fix exporter mapping

---

## 10) Observability / Logging

**New/changed events**

* `Running local workout export for ISO week ...` is emitted by the local exporter path.
* deterministic validation failures include explicit invalid workout ids / lines.

**Diagnostics**

* `rps.log`
* stored `WEEK_PLAN`
* stored `INTERVALS_WORKOUTS`

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] `doc/specs/features/FEAT_code_based_workout_exporter.md` — feature record
* [x] `CHANGELOG.md` — note the code-based exporter replacement

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* Workspace: `doc/architecture/workspace.md`
* Validation / runbooks: `doc/runbooks/validation.md`
* Logging policy: `doc/specs/contracts/logging_policy.md`
* Specs:
  * `specs/knowledge/_shared/sources/specs/workouts/intervals_workout_ebnf.md`
  * `specs/knowledge/_shared/sources/specs/workouts/workout_syntax_and_validation.md`
  * `specs/knowledge/_shared/sources/specs/workouts/workout_json_spec.md`
  * `specs/knowledge/_shared/sources/contracts/week__builder_contract.md`

---

## Open Questions

* none

---

## Out of Scope / Deferred

* Full generic EBNF parser generation from spec text
* Auto-repair of malformed planner workout text
