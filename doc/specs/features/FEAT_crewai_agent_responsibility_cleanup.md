---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-12
Owner: Runtime / Planning
---
# FEAT: CrewAI Agent Responsibility Cleanup

* **ID:** FEAT_crewai_agent_responsibility_cleanup
* **Status:** Implemented
* **Owner/Area:** Runtime / Planning
* **Last-Updated:** 2026-05-12
* **Related:** ADR-035

---

## 1) Context / Problem

**Current behavior**

* The CrewAI cutover removed the legacy runtime, but internal agent ownership remained too coarse.
* Season/phase/feed-forward authority was still partly documented as if `Performance-Analyst` owned `SEASON_PHASE_FEED_FORWARD`.
* Phase responsibility wording did not cleanly separate season-level cadence choice from phase-level cadence application.

**Problem**

* Repo contracts, mandatory-output specs, and architecture docs disagreed on some authority boundaries.
* The CrewAI YAML foundation did not yet reflect the intended specialist split for season and phase.
* Internal typed models were missing for the richer season/phase specialist outputs discussed in the architecture work.

**Constraints**

* Persisted artefact schemas must stay unchanged.
* Runtime behavior for existing Season/Phase/Week/Report flows must stay stable.
* Cleanup must preserve the current CrewAI-only runtime and guarded-store semantics.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Make Season-Scenario advisory only and Season-Planner the first binding planning authority.
* [x] Make `SEASON_PHASE_FEED_FORWARD` explicitly season-owned and `PHASE_FEED_FORWARD` phase-owned.
* [x] Clarify that cadence selection is season authority and phase may only apply that cadence.
* [x] Add CrewAI foundation config and internal typed models for the refined Season/Phase specialist split.

**Non-Goals**

* [ ] Execute a full hierarchical multi-task CrewAI runtime for Season/Phase in this change.
* [ ] Change persisted external artefact contracts or schema versions.
* [ ] Split Week-Planner or Performance-Analyst into additional persisted-artifact authorities.

---

## 3) Proposed Behavior

**User/System behavior**

* `Season-Planner` remains the binding author for `SEASON_PLAN` and `SEASON_PHASE_FEED_FORWARD`.
* `Phase-Architect` remains the binding author for `PHASE_GUARDRAILS`, `PHASE_STRUCTURE`, `PHASE_PREVIEW`, and `PHASE_FEED_FORWARD`.
* `Performance-Analyst` remains diagnostic-only and writes `DES_ANALYSIS_REPORT` only.
* Phase cadence logic is described as application/integration of season cadence, not phase-owned cadence selection.

**UI impact**

* UI affected: No direct layout change
* If Yes: n/a

**Non-UI behavior**

* Components involved:
  * `config/crewai/agents.yaml`
  * `config/crewai/tasks.yaml`
  * `src/rps/crewai_runtime/models.py`
  * `src/rps/crewai_runtime/bindings.py`
  * `src/rps/agents/crewai_backend.py`
* Contracts touched:
  * scenario/season, season/phase, phase/week, DES evaluation policy

---

## 4) Implementation Analysis

**Components / Modules**

* CrewAI YAML config: adds internal Season/Phase specialist roles and task blueprints.
* CrewAI typed models: adds internal season audit/macrocycle/event-anchor models plus phase bundle/audit payload models.
* CrewAI backend normalization: enforces canonical persisted `owner_agent` values by artefact type.
* Architecture docs: corrected feed-forward ownership and phase cadence authority wording.

**Data flow**

* Inputs: existing season/phase/report orchestration inputs.
* Processing: typed CrewAI output still flows through normalization and guarded store; ownership metadata is canonicalized before persistence.
* Outputs: unchanged persisted artefacts, plus richer internal CrewAI model vocabulary.

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: owner-agent normalization for season/phase/report artefacts is strengthened pre-store.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none in persisted artefact shape
* Fallback behavior: existing runtime behavior remains intact; this is an ownership/architecture cleanup

**Conflicts with ADRs / Principles**

* Potential conflicts: none; the cleanup aligns runtime/docs to existing binding contracts and principles.
* Resolution: captured in ADR-035.

**Impacted areas**

* UI: none directly
* Pipeline/data: none
* Renderer: none
* Workspace/run-store: stronger owner canonicalization before store
* Validation/tooling: new CrewAI config/model tests
* Deployment/config: CrewAI YAML semantics refined

**Required refactoring**

* Correct feed-forward authority documentation.
* Re-map persisted task blueprints to season/phase manager roles.
* Add internal typed models for future hierarchical execution.

---

## 6) Options & Recommendation

### Option A — Responsibility cleanup with CrewAI foundation updates

**Summary**

* Correct authority boundaries now and add the internal Season/Phase specialist foundation without forcing a full hierarchical executor refactor in the same change.

**Pros**

* Fixes real contract/documentation/runtime inconsistencies.
* Keeps current production paths stable.
* Prepares the config/model layer for later richer Crew execution.

**Cons**

* Specialist tasks remain foundation-only until a fuller hierarchical executor is introduced.

**Risk**

* Partial implementation could be mistaken for full multi-agent execution if the docs are vague.

### Option B — Defer cleanup until full hierarchical Crew execution exists

**Summary**

* Leave current inconsistencies in place until the complete Season/Phase crew engine is implemented.

**Pros**

* Fewer interim artifacts.

**Cons**

* Leaves real authority confusion in docs and runtime metadata.

### Recommendation

* Choose: Option A
* Rationale: authority cleanup is independently valuable and reduces future implementation risk.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `SEASON_PHASE_FEED_FORWARD` is documented and normalized as Season-Planner-owned.
* [x] `PHASE_FEED_FORWARD` is documented as Phase-Architect-owned.
* [x] Phase cadence wording reflects application of season cadence, not local selection authority.
* [x] CrewAI YAML contains explicit internal Season/Phase specialist roles and task blueprints.
* [x] Internal typed output models exist for Season audit/macrocycle/event-anchor and Phase bundle/audits.
* [x] Validation passes: `py_compile`, targeted pytest, lint, typecheck.

---

## 8) Migration / Rollout

**Migration strategy**

* No artefact migration required.
* Existing runs and stored artefacts remain valid.

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert CrewAI YAML/model/backend/doc changes together

---

## 9) Risks & Failure Modes

* Failure mode: stale docs still imply Performance-Analyst owns season feed-forward.
  * Detection: grep docs/config/runtime for `season_phase_feed_forward` ownership.
  * Safe behavior: runtime owner normalization still persists the canonical owner.
  * Recovery: update remaining doc references.

* Failure mode: future hierarchical executor assumes missing internal model types.
  * Detection: CrewAI binding tests fail on unknown `output` kinds.
  * Safe behavior: current persisted task execution remains functional.
  * Recovery: add model registry entries before enabling new tasks.

---

## 10) Observability / Logging

**New/changed events**

* No new log event families.
* Persisted CrewAI artefacts now carry canonical owner metadata aligned with contracts.

**Diagnostics**

* Check persisted `meta.owner_agent` in workspace outputs.
* Check CrewAI runtime tests for task/agent blueprint ownership.

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] `/doc/architecture/agents.md` — correct ownership boundaries and role notes
* [x] `/doc/architecture/system_architecture.md` — correct authority sections
* [x] `/doc/overview/artefact_flow.md` — clarify feed-forward authorship
* [x] `/CHANGELOG.md` — record ownership cleanup
