---
Version: 1.1
Status: Implemented
Last-Updated: 2026-07-07
Owner: Agent Runtime
---
# FEAT: CrewAI Backend Module Split

* **ID:** FEAT_crewai_backend_module_split
* **Status:** Implemented
* **Owner/Area:** Agent Runtime
* **Last-Updated:** 2026-07-07
* **Related:** `doc/adr/ADR-059-crewai-backend-module-split.md`, `src/rps/agents/crewai_backend.py`, `src/rps/agents/crewai_output_extraction.py`, `src/rps/agents/crewai_validation.py`, `src/rps/agents/crewai_builders.py`, `src/rps/agents/crewai_bundle_normalization.py`, `tests/test_crewai_runtime.py`

---

## 1) Context / Problem

**Current behavior**

* `src/rps/agents/crewai_backend.py` is 4357 lines and 87 top-level functions, mixing bundle normalization, CrewAI agent/crew/LLM construction, task execution orchestration, structured-output extraction, and artifact persistence/validation in one file.
* It is the single most-changed file in the repo over the last 90 days.

**Problem**

* Low cohesion causes unrelated changes to land in the same file/diff, increasing review difficulty and regression risk.
* Structural audit (see ADR-059) found 7 functional groups with varying extraction risk; some are safely separable now, others require design work first.

**Constraints**

* No behavior change: same functions, same runtime behavior, only import paths for internal-only names move.
* Orchestration boundaries (ADR-037), authority boundaries (ADR-035), and telemetry event shapes (ADR-040) must not change.
* No re-export shim left behind (per this repo's convention against compatibility-hack layers) — external callers update their imports directly.
* Staged, incremental delivery — one low-risk group per phase, matching this repo's established refactor discipline (`deterministic_context.py`, the `_load_latest_payload` consolidation series).

---

## 2) Goals & Non-Goals

**Goals**

* [x] Phase 1: extract structured-output extraction/parsing (Group C, ~231 lines / 10 functions) into `src/rps/agents/crewai_output_extraction.py`.
* [x] Phase 2: extract the bundle/artifact validation group (~77 lines / 7 functions) into `src/rps/agents/crewai_validation.py`.
* [x] Phase 3: extract CrewAI agent/crew/LLM construction (Group B, 14 functions — a fresh audit found 14, not the originally estimated 11) into `src/rps/agents/crewai_builders.py`.
* [x] Phase 4: extract season/phase bundle normalization (Group A, 25 functions plus `_as_int`/`_as_list` and 4 exclusive constants) into `src/rps/agents/crewai_bundle_normalization.py`. This was the final phase — all Goals in this spec are now done.

**Non-Goals**

* [ ] Extracting contract/context-block building (Group D) — tightly coupled to mutable guardrail runtime context; needs separate design work.
* [ ] Extracting task execution orchestration (Group E) — the closure-based planning/review/writer callback core; the riskiest, least mechanical piece. Not attempted by this spec.
* [ ] Any change to Season/Phase/Week/Report authority boundaries, persisted artifact schemas, or orchestration/Flow wiring.
* [ ] Splitting `tests/test_crewai_runtime.py` itself (tracked separately in `doc/overview/feature_backlog.md`).

---

## 3) Proposed Behavior

**User/System behavior**

* No end-user or runtime behavior change. This is a pure internal code-organization refactor.

**UI impact**

* UI affected: No.

**Non-UI behavior**

* Components involved: `src/rps/agents/crewai_backend.py`, new `src/rps/agents/crewai_output_extraction.py` (Phase 1), `tests/test_crewai_runtime.py`.
* Contracts touched: internal Python import paths only; no artifact schema, orchestration, or telemetry contract changes.

---

## 4) Implementation Analysis

**Components / Modules**

* `crewai_backend.py`: loses the 10 Group C functions (Phase 1); imports them back by name for internal use by execution orchestration (Group E).
* `crewai_output_extraction.py` (new): owns `_extract_raw_output_text`, `_parse_json_document`, `_coerce_artifact_envelope`, `_extract_typed_output`, `_extract_json_output`, `_extract_structured_output`, `_freeze_season_bundle_audit_slots`, `_classify_season_audit_item`, `coerce_season_plan_draft_bundle_slots`, `_output_model_for_task`, plus the two Group-C-exclusive constants `_SEASON_CONSTRAINT_AUDIT_TASKS`/`_SEASON_LOAD_GOVERNANCE_TASKS` and its own local `_as_map` helper (the shared `_as_map` in `crewai_backend.py` has 73 call sites and stays there; duplicating this trivial one-line coercion helper matches the existing pattern already used across `advisory_actions.py`/`coach.py`/`feed_forward.py` in this repo).
* `tests/test_crewai_runtime.py`: its large `from rps.agents.crewai_backend import (...)` block splits — the 5 externally-imported Group C names (`_coerce_artifact_envelope`, `_extract_structured_output`, `_freeze_season_bundle_audit_slots`, `_classify_season_audit_item`, `coerce_season_plan_draft_bundle_slots`) move to a new `from rps.agents.crewai_output_extraction import (...)` block.

**Data flow**

* No data-flow change. Function call graphs are identical; only which module owns which function body changes.

**Schema / Artefacts**

* None. No artifact, schema, or contract changes in any phase.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes for production code (no production module imports Group C names by the old path — see ADR-059's external-consumer audit).
* Breaking changes: none for production. `tests/test_crewai_runtime.py` needs its import block updated in the same commit as Phase 1 (see Implementation Analysis).
* Fallback behavior: n/a.

**Conflicts with ADRs / Principles**

* None. Governed directly by ADR-059.

**Impacted areas**

* UI: none.
* Pipeline/data: none.
* Renderer: none.
* Workspace/run-store: none.
* Validation/tooling: `tests/test_crewai_runtime.py` import block only.
* Deployment/config: none.

**Required refactoring**

* Phase 1 only for this implementation pass: move Group C, update `crewai_backend.py`'s internal imports, update the one test file's import block.

---

## 6) Options & Recommendation

### Option A (recommended) — Staged extraction, safest group first

**Summary:** Extract Group C now; track Groups B/A/Validation as separate future phases; leave Groups D/E in place indefinitely.

**Pros:** Matches this repo's proven staged-refactor discipline; each phase is independently reviewable and revertible; lowest-risk group moves first, building confidence before larger groups.

**Cons:** The full split takes multiple sessions; `crewai_backend.py` stays large until all phases land.

**Risk:** Low per phase.

### Option B — Big-bang full split in one pass

**Summary:** Extract all 7 groups (including D and E) in one commit.

**Pros:** File reaches its final target size immediately.

**Cons:** Groups D and E have real coupling (mutable guardrail context, closure-based callback wiring) that isn't safe to move without first redesigning that coupling; a single large diff touching orchestration/authority-adjacent code is exactly the kind of change this repo's own rules require extra scrutiny for.

**Risk:** High — could silently change execution ordering or guardrail context visibility.

### Recommendation

* Choose: Option A.
* Rationale: proven pattern in this repo, keeps each change independently verifiable, and defers the two genuinely risky groups (D, E) until their coupling is understood well enough to design a safe extraction — which this spec does not attempt to do.

---

## 6a) Implementation Readiness Review

* [x] Scope completeness: Phase 1's affected modules (`crewai_backend.py`, new `crewai_output_extraction.py`, `tests/test_crewai_runtime.py`) are named, including the two easy-to-miss dependencies (`_as_map`, the two Group-C-exclusive task-name constants).
* [x] Decision completeness: ADR-059 already made the phase-ordering and Group D/E exclusion decisions explicitly.
* [x] Architecture conformity: confirmed against ADR-035/ADR-037/ADR-040 — no orchestration/authority/telemetry change.
* [x] Execution readiness: exact function names, line numbers, and import statements were traced before this spec was written (see ADR-059's audit).

---

## 7) Acceptance Criteria (Definition of Done, Phase 1)

* [ ] `src/rps/agents/crewai_output_extraction.py` exists with the 10 Group C functions plus their exclusive constants/helper, moved verbatim.
* [ ] `crewai_backend.py` no longer defines those 10 functions; imports the ones Group E still calls.
* [ ] `tests/test_crewai_runtime.py` imports the 5 externally-used names from the new module path.
* [ ] Validation passes: `py_compile`, `run_lint.sh`, `run_typecheck.sh` (curated + `--full`), `tests/test_crewai_runtime.py`, full `pytest tests/`.
* [ ] No regressions in: CrewAI task execution, structured-output parsing, Season audit-slot coercion.

---

## 8) Migration / Rollout

**Migration strategy:** None — internal Python import path change only, no data migration.

**Rollout / gating:** None — no feature flag; ships as a normal internal refactor commit.

---

## 9) Risks & Failure Modes

* Failure mode: a monkeypatch string in `tests/test_crewai_runtime.py` still targets `"rps.agents.crewai_backend.<moved_name>"` after the move.

  * Detection: that test fails immediately (`AttributeError` on `monkeypatch.setattr`) since the attribute no longer exists on the old module.
  * Safe behavior: test suite run before considering the phase complete.
  * Recovery: update the monkeypatch string to the new module path.

---

## 10) Observability / Logging

* No new/changed events. Telemetry emission functions (`emit_runtime_event`, etc.) are Group E/imports, untouched by Phase 1.

---

## 11) Documentation Updates

* [x] `doc/adr/ADR-059-crewai-backend-module-split.md` — created.
* [x] `doc/adr/README.md` — index entry added.
* [x] `doc/overview/feature_backlog.md` — updated to reference this spec and record Phase 1 status.
* [ ] `doc/architecture/agents.md` — "Crew definition source" note (currently points to `crewai_backend.py` for task tuples) can stay as-is for Phase 1 since the task-tuple constants (`_SEASON_PLANNING_TASKS` etc.) are not moving; revisit if a later phase moves them.

---

## 11a) Post-Implementation Audit

* [x] Spec implemented fully (Phases 1-4 done — all Goals complete).
* [x] Acceptance criteria verified (Phases 1-4).
* [x] Verification commands/tests recorded.
* [x] Residual gaps/deferred items recorded.
* [x] Recommended next step recorded.

**Implementation report**

* Implemented scope: Phase 1 (Group C extraction), Phase 2 (Validation group extraction), Phase 3 (Group B extraction), Phase 4 (Group A extraction). All four active phases of this spec are complete.
* Verification performed: see Acceptance Criteria. Phase 2 additionally confirmed the two pre-existing string-based monkeypatches in `tests/test_crewai_runtime.py` (`_validate_normalized_season_bundle`, `_validate_normalized_phase_bundle`) kept working unmodified, since `crewai_backend.py` re-imports those names by value. Phase 3's own dependency audit corrected two errors in an earlier automated pass (`resolve_agent_memory_profile` and `CrewAIConfigBundle` turned out to be Group-B-exclusive, not shared with Group E), confirmed by direct grep before trimming imports. Phase 4's audit corrected three further discrepancies the same way, plus identified that `_as_int` (defined physically outside Group A's line range, in Group D's territory) was nonetheless Group-A-exclusive and needed to move with it to avoid a circular import; `_as_map` was the opposite case (57 of 72 uses in Group A, but 15 remain in Group D) and was duplicated rather than moved, per the established convention.
* Remaining gaps/risks: none active. Groups D/E (context-block building, task execution orchestration) are excluded indefinitely per ADR-059's Exceptions — no further phases are planned under this spec.
* Recommended next step: none for this spec. Unrelated backlog items remain: splitting the two oversized test files, and the separately-tracked `test_evidence_library.py` test-hygiene fix.

---

## 12) Link Map

* ADR: [doc/adr/ADR-059-crewai-backend-module-split.md](/doc/adr/ADR-059-crewai-backend-module-split.md)
* Architecture: [doc/architecture/agents.md](/doc/architecture/agents.md)
* Backlog: [doc/overview/feature_backlog.md](/doc/overview/feature_backlog.md)

---

## Out of Scope / Deferred

* Phases 2-4 (Validation group, Group B, Group A) — tracked in Goals above, not implemented in this pass.
* Groups D and E — excluded indefinitely per ADR-059 Exceptions.
