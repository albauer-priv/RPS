---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-12
Owner: Runtime / Planning
---
# FEAT: Hierarchical CrewAI Execution for Season and Phase

* **ID:** FEAT_hierarchical_crewai_execution
* **Status:** Implemented
* **Owner/Area:** Runtime / Planning
* **Last-Updated:** 2026-05-12
* **Related:** ADR-036

---

## 1) Context / Problem

**Current behavior**

* The hard CrewAI cutover moved persisted planning/advisory execution onto CrewAI.
* Season and Phase had a refined internal specialist foundation in YAML/models, but runtime execution still behaved like a single persisted task.
* Phase bundle semantics existed only as architecture intent.

**Problem**

* Runtime execution did not yet use the internal Season/Phase specialist split.
* The new CrewAI role taxonomy was not reflected in actual planner behavior.
* Phase-specialist work and bundle finalization could not be exercised end-to-end.

**Constraints**

* Existing external artefact schemas must stay unchanged.
* `WEEK_PLAN`, `DES_ANALYSIS_REPORT`, and workout export must remain stable.
* Hierarchical execution must remain compatible with the current local test strategy, where CrewAI is monkeypatched.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Execute `SEASON_PLAN` through internal Season specialist subtasks plus manager finalization.
* [x] Execute `PHASE_GUARDRAILS` / `PHASE_STRUCTURE` / `PHASE_PREVIEW` through internal Phase specialist subtasks plus `PhaseBundle` finalization.
* [x] Keep external persisted artefact contracts unchanged.
* [x] Preserve current behavior for Week, Report, and feed-forward tasks that are not part of the Season/Phase hierarchical path.

**Non-Goals**

* [ ] Replace outer orchestrators with CrewAI Flows in this change.
* [ ] Introduce a new persisted `PhaseBundle` artefact.
* [ ] Change Plan Hub phase-step isolation semantics.

---

## 3) Proposed Behavior

**User/System behavior**

* `SEASON_PLAN` runs now execute internal CrewAI specialist subtasks first, then a Season manager task emits the persisted final envelope.
* `PHASE_GUARDRAILS`, `PHASE_STRUCTURE`, and `PHASE_PREVIEW` now execute internal Phase specialist subtasks and audits, then a manager task emits an internal `PhaseBundle` with nested phase documents.
* The backend deterministically selects the requested nested phase document from the bundle and persists only the requested public artefact.

**UI impact**

* UI affected: No direct layout change
* If Yes: n/a

**Non-UI behavior**

* Components involved:
  * `src/rps/agents/crewai_backend.py`
  * `config/crewai/agents.yaml`
  * `config/crewai/tasks.yaml`
  * `src/rps/crewai_runtime/models.py`
  * `src/rps/crewai_runtime/bindings.py`
* Contracts touched:
  * season and phase ownership/authority contracts only indirectly; persisted external artefacts stay the same

---

## 4) Implementation Analysis

**Components / Modules**

* CrewAI backend now orchestrates internal specialist tasks for Season and Phase before final persistence.
* CrewAI YAML adds prompt-agent mapping and manager delegation metadata.
* Internal typed models are used as real runtime outputs, not just placeholders.

**Data flow**

* Inputs: existing user input plus planner/advisory context.
* Processing:
  * Season: specialist task outputs are serialized into manager context, then manager emits final `SEASON_PLAN`.
  * Phase: specialist task outputs are serialized into manager context, manager emits `PhaseBundle`, backend extracts the requested nested phase artefact envelope.
* Outputs: unchanged public artefacts; internal specialist outputs remain runtime-only.

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: the final persisted document still goes through existing normalization and guarded validation.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none in public artefact shape
* Fallback behavior: non-Season/Phase tasks continue using the direct single-task CrewAI execution path

**Conflicts with ADRs / Principles**

* Potential conflicts: none; this is the runtime realization of the already accepted CrewAI architecture direction.
* Resolution: captured in ADR-036.

**Impacted areas**

* UI: none directly
* Pipeline/data: none
* Renderer: none
* Workspace/run-store: none beyond persisted outputs already produced today
* Validation/tooling: new Season/Phase hierarchical execution tests
* Deployment/config: CrewAI agent/task YAML semantics expanded

**Required refactoring**

* Add specialist-task execution helpers in the CrewAI backend.
* Extend test doubles to support internal typed models and `PhaseBundle` splitting.

---

## 6) Options & Recommendation

### Option A — Hierarchical internal execution with unchanged public artefacts

**Summary**

* Run internal specialist CrewAI tasks for Season and Phase, then keep public persistence unchanged.

**Pros**

* Gives immediate value from the specialist split.
* Avoids public schema churn.
* Keeps orchestrators stable.

**Cons**

* Outer orchestration is still not Flow-owned.

**Risk**

* Internal specialist prompts still reuse top-level prompt files, so role separation is partly config-driven rather than prompt-file-driven.

### Option B — Wait for outer Flow migration first

**Summary**

* Defer specialist execution until Flow refactors are complete.

**Pros**

* Cleaner sequencing on paper.

**Cons**

* Leaves the specialist foundation unused.

### Recommendation

* Choose: Option A
* Rationale: it unlocks the Season/Phase crew split now without forcing a full orchestration rewrite.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `SEASON_PLAN` execution runs through internal specialist subtasks before final persistence.
* [x] `PHASE_GUARDRAILS`/`PHASE_STRUCTURE`/`PHASE_PREVIEW` execution runs through specialist subtasks and a final `PhaseBundle` task.
* [x] `PhaseBundle` stays internal and is not persisted directly.
* [x] Persisted outputs remain schema-compatible envelopes.
* [x] Validation passes: `py_compile`, targeted pytest, lint, typecheck.

---

## 8) Migration / Rollout

**Migration strategy**

* No artefact migration required.
* Existing artefact readers and validators remain valid.

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert the hierarchical execution path to the previous direct-task path in `crewai_backend.py`

---

## 9) Risks & Failure Modes

* Failure mode: internal specialist task does not return typed output.
  * Detection: backend returns a typed-output error before persistence.
  * Safe behavior: no artefact is stored.
  * Recovery: inspect task config/model mapping and prompt context.

* Failure mode: `PhaseBundle` lacks the requested nested phase document.
  * Detection: backend raises split-selection failure.
  * Safe behavior: no phase artefact is stored.
  * Recovery: inspect manager output and bundle prompt expectations.

---

## 10) Observability / Logging

**New/changed events**

* No new log families.
* Backend error surfaces now include internal-task or bundle-selection failures when relevant.

**Diagnostics**

* Check CrewAI task output typing in tests.
* Check stored phase artefact owner/shape after bundle split.

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] `/CHANGELOG.md` — record hierarchical Season/Phase execution
* [x] `/doc/overview/feature_backlog.md` — move hierarchical execution from deferred to implemented
* [x] `/doc/architecture/agents.md` — specialist roles remain internal, public ownership unchanged
