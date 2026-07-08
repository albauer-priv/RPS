---
Version: 1.0
Status: Implemented
Last-Updated: 2026-07-08
Owner: Planning Runtime
---
# FEAT: Finalize Manager Synthesis Boundary

* **ID:** FEAT_finalize_manager_synthesis_boundary
* **Status:** Implemented
* **Owner/Area:** Planning Runtime
* **Last-Updated:** 2026-07-08
* **Related:** `season_plan_finalize`, `phase_bundle_finalize`, `SeasonPlanManagerSynthesisModel`, `PhaseBundleManagerSynthesisModel`, `WeekPlanningNoteModel`, supersedes `FEAT_season_finalize_raw_bundle_boundary`

---

## 1) Context / Problem

**Current behavior**

* `season_plan_finalize`'s task description instructed the manager LLM to "preserve and consolidate" `constraints[]`, `load_governance[]`, and `phase_blueprints` — three fields already produced, in an already-typed shape, by name-matched sibling tasks earlier in the same crew (`season_constraint_review`/`season_historical_context_review`/`season_kpi_guidance_review`; `season_load_corridor_draft`/`season_progression_review`; `season_phase_blueprint_draft`).
* `phase_bundle_finalize` had the identical pattern for `guardrails`/`structure`/`preview`, produced first by `phase_guardrail_band_draft`/`phase_structure_draft`/`phase_preview_draft`.
* Asking an LLM to faithfully retype already-typed, already-correct structures adds a failure-prone LLM round-trip with zero semantic value. A production incident showed this directly: `season_plan_finalize` failed after 3 wasted LLM calls with `season_bundle_audit_slot_integrity` rejecting `constraints[]` because a canonically-shaped audit item had drifted into row-shaped form during reproduction.
* `FEAT_season_finalize_raw_bundle_boundary` (2026-06-10) patched a symptom of this same defect: `season_plan_finalize` used `output_mode: pydantic` originally, but CrewAI's strict binding rejected correctly-shaped-but-misplaced audit items (a constraint item shaped like governance, or vice versa), so the task was moved to `output_mode: json` with a narrow post-hoc reclassification coercion (`coerce_season_plan_draft_bundle_slots`). That patch worked around the reproduction problem instead of removing it.
* `phase_bundle_finalize` had the same underlying defect but a different failure surface: it already used `output_mode: pydantic`, so CrewAI's own strict binding intercepted malformed reproduction immediately via its guardrail-retry mechanism (`guardrail_max_retries: 2`) — same wasted-LLM-call cost, just not visible as a distinct logged failure the way Season's `json`-mode path was.
* Week's finalizer (`week_plan_finalize`) does not share this pattern: its upstream draft tasks (`week_load_target_draft`/`week_revision_draft`/`week_workout_text_draft`) produce untyped narrative (`PlanningDraftModel`), with no type match to the day/workout blueprints `week_plan_finalize` produces — genuine synthesis, not reproduction. Week's only related gap was that `WeekPlanBundleModel.constraint_summary`/`load_target_summary`/`revision_summary` were untyped `list[str]`.

**Problem**

* A finalize/manager CrewAI task was being asked to reproduce data that sibling tasks in the same crew had already produced, in an already-typed shape — an architecturally wasteful, failure-prone LLM round-trip.

**Constraints**

* No change to the persisted `SEASON_PLAN` / `PHASE_GUARDRAILS` / `PHASE_STRUCTURE` / `PHASE_PREVIEW` / `WEEK_PLAN` artifact schemas.
* No change to ADR-035 authority boundaries.
* Guardrails remain fail-closed; removing a guardrail from CrewAI's retry chain is only valid when the same check still runs as a plain post-assembly function.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Narrow `season_plan_finalize`'s and `phase_bundle_finalize`'s own LLM output contracts to exclude any field 100% derivable from already-completed same-crew sibling tasks.
* [x] Assemble the full bundle deterministically in repo code from the manager's narrow synthesis plus the sibling tasks' already-typed outputs, after `crew.kickoff()`.
* [x] Restore `output_mode: pydantic` for `season_plan_finalize` (CrewAI's own strict binding now works natively, since the manager no longer produces the ambiguous audit-slot fields).
* [x] Relocate guardrails that depended on the removed pass-through fields from CrewAI's guardrail/retry chain to plain post-assembly Python checks.
* [x] Add a typed `WeekPlanningNoteModel` for Week's three previously-untyped narrative-note fields.
* [x] Retire `coerce_season_plan_draft_bundle_slots` / `_classify_season_audit_item` / `_freeze_season_bundle_audit_slots` (superseded, no longer reachable).

**Non-Goals**

* [x] No change to Week's finalize architecture beyond the typed-note fix (Week does not share the reproduction defect).
* [x] No change to `constraint_audit`/`load_governance_audit` ownership on `phase_bundle_finalize` — those are genuinely LLM-originated (the matching `phase_constraint_audit`/`phase_governance_review` tasks run in a separate, later review crew, not as upstream siblings within the same crew).

---

## 3) Proposed Behavior

**User/System behavior**

* `season_plan_finalize` now produces `SeasonPlanManagerSynthesisModel` (event priority, macrocycle, season load envelope, season semantic notes, decision/candidate summaries, warnings/blocking issues) — no `constraints[]`, `load_governance[]`, or `phase_blueprints`.
* `phase_bundle_finalize` now produces `PhaseBundleManagerSynthesisModel` (phase identity fields, `week_blueprints`, `constraint_audit`, `load_governance_audit`, decision summary) — no `guardrails`, `structure`, or `preview`.
* Immediately after `crew.kickoff()`, `_assemble_season_plan_draft_bundle` / `_assemble_phase_draft_bundle` (`src/rps/agents/crewai_output_extraction.py`) merge the manager's narrow synthesis with the already-typed sibling task outputs (read via `task.output.pydantic`) into the full `SeasonPlanDraftBundleModel` / `PhaseDraftBundleModel` — unchanged full contracts, now assembled rather than LLM-authored end-to-end.
* Guardrails whose checks depend on the removed pass-through fields (`season_bundle_integrity`, `season_bundle_audit_slot_integrity`, `season_phase_load_feasibility`, `season_bundle_review_readiness` for Season; `phase_bundle_integrity`, `phase_bundle_review_readiness` for Phase) run as plain Python function calls against the assembled bundle in `_run_season_plan_document` / `_run_phase_bundle_document`, raising `RuntimeError` (with a `SEASON_BUNDLE_RAW_VALIDATION_FAILED` / `PHASE_BUNDLE_RAW_VALIDATION_FAILED` runtime event) on failure — same fail-closed behavior, just invoked directly instead of through CrewAI's guardrail/retry wrapper (retrying the LLM cannot fix a code-assembly issue).
* `phase_week_role_load_coherence` is unaffected (only needs `week_blueprints`, which stays LLM-authored) and remains a CrewAI-attached guardrail.
* `WeekPlanBundleModel.constraint_summary` / `.load_target_summary` / `.revision_summary` are now `list[WeekPlanningNoteModel]` instead of `list[str]`; `week_engine.py`'s deterministic construction wraps each note in `WeekPlanningNoteModel(text=...)`.

**UI impact**

* UI affected: No — internal CrewAI execution contract only.

**Non-UI behavior**

* Components involved: `config/crewai/tasks.yaml`, `config/crewai/task_policies.yaml`, `src/rps/crewai_runtime/models.py`, `src/rps/crewai_runtime/bindings.py`, `src/rps/agents/crewai_output_extraction.py`, `src/rps/agents/crewai_task_execution.py`, `src/rps/planning/week_engine.py`.
* Contracts touched: internal CrewAI output contracts for `season_plan_finalize` and `phase_bundle_finalize`; `WeekPlanBundleModel`'s three narrative-note fields. No persisted artifact schema changes.

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/crewai_runtime/models.py`: `SeasonPlanManagerSynthesisModel`, `PhaseBundleManagerSynthesisModel`, `WeekPlanningNoteModel` (new); `SeasonPlanDraftBundleModel` / `PhaseDraftBundleModel` unchanged as the full assembled contracts.
* `src/rps/crewai_runtime/bindings.py`: registers `season_plan_manager_synthesis` and `phase_bundle_manager_synthesis` output kinds.
* `config/crewai/tasks.yaml`: `season_plan_finalize.output` / `phase_bundle_finalize.output` point at the new narrower kinds; task descriptions rewritten to state the pass-through fields are not part of this task's output and are assembled deterministically after synthesis. `season_phase_blueprint_draft`'s description updated to match (no longer says the finalizer "must preserve and consolidate" its output).
* `config/crewai/task_policies.yaml`: `season_plan_finalize.output_mode: pydantic` (was `json`); guardrail lists trimmed on both `season_plan_finalize` and `phase_bundle_finalize` to only the guardrails that remain valid against the narrower raw LLM output.
* `src/rps/agents/crewai_output_extraction.py`: `_assemble_season_plan_draft_bundle`, `_assemble_phase_draft_bundle`, `_collect_typed` (shared sibling-output collector); replaces `_freeze_season_bundle_audit_slots` / `coerce_season_plan_draft_bundle_slots` / `_classify_season_audit_item` (removed).
* `src/rps/agents/crewai_task_execution.py`: `_execute_crewai_multiagent_crew` calls the new assembly functions for `season_plan_finalize` / `phase_bundle_finalize`; `_run_season_plan_document` / `_run_phase_bundle_document` run the relocated post-assembly guardrail checks.
* `src/rps/planning/week_engine.py`: deterministic bundle construction wraps `constraint_summary`/`load_target_summary`/`revision_summary` entries in `WeekPlanningNoteModel`.
* Prompt/skill content updated for consistency wherever a prompt or skill instructed reproduction of a now-removed field: `prompts/agents/season_plan_manager.md`, `prompts/agents/phase_bundle_manager.md`, `prompts/agents/season_phase_blueprint_specialist.md`, `prompts/agents/guardrails_specialist.md`, `prompts/agents/structure_specialist.md`, `skills/season/plan-synthesis/SKILL.md`, `skills/phase/bundle-synthesis/SKILL.md`, `skills/phase/guardrails-authoring/SKILL.md`, `skills/phase/structure-authoring/SKILL.md`. Notably, the `inherited_scenario_contract` "freeze exactly, do not paraphrase nested fields" discipline moved from the Phase manager (which no longer sees the field) to `guardrails_specialist` / `structure_specialist` (the actual point of authorship now that there is no reproduction step to re-freeze it at).

**Data flow**

* Unchanged from the caller's perspective: `_run_season_plan_document` / `_run_phase_bundle_document` still return a fully-populated `JsonMap` matching `SeasonPlanDraftBundleModel` / `PhaseDraftBundleModel`. The change is entirely inside `_execute_crewai_multiagent_crew`'s post-`kickoff()` handling.

**Required refactoring**

* None outstanding; `coerce_season_plan_draft_bundle_slots` and friends confirmed to have no other callers before removal.

---

## 5) Recommendation

* Generalize this as the "manager synthesis vs. deterministic assembly" pattern: any future finalize/manager task whose output schema type-matches an already-completed same-crew sibling task's output should exclude that field from its own contract and have repo code assemble it post-`kickoff()`, rather than asking the LLM to reproduce it.

---

## 6) Acceptance Criteria

* [x] `season_plan_finalize` and `phase_bundle_finalize` no longer include pass-through fields in their own LLM output contracts.
* [x] `_assemble_season_plan_draft_bundle` / `_assemble_phase_draft_bundle` produce a `SeasonPlanDraftBundleModel` / `PhaseDraftBundleModel` matching the pre-existing full contract.
* [x] Guardrails that depend on removed pass-through fields run as post-assembly checks, not CrewAI-attached guardrails, and still fail closed.
* [x] `season_plan_finalize` uses `output_mode: pydantic` again.
* [x] `WeekPlanBundleModel`'s three narrative-note fields are typed (`WeekPlanningNoteModel`), matching the pattern used elsewhere in the runtime model layer.
* [x] Dead reclassification/coercion code removed; no remaining callers.
* [x] Full test suite, lint, and typecheck pass.

---

## 7) Migration / Rollout

**Migration strategy**

* None; internal execution-path and CrewAI output-contract change only. No persisted data migration.

**Rollout / gating**

* No feature flag.
* Rollback: revert this change set; `FEAT_season_finalize_raw_bundle_boundary`'s coercion path is retained in git history if a revert is ever needed, though the root-cause fix here is preferred over reverting to the coercion workaround.

---

## 8) Risks & Failure Modes

* Failure mode: a sibling task the assembly function depends on did not run or produced no typed output (e.g. crew wiring changes upstream).
  * Detection: `_assemble_season_plan_draft_bundle` / `_assemble_phase_draft_bundle` raise `RuntimeError` immediately (no silent empty-list fallback).
  * Safe behavior: finalize execution aborts before any guardrail or persistence step.
  * Recovery: fix the crew task wiring; this is a code defect, not an LLM-content issue, so retrying the LLM will not help.
* Failure mode: CrewAI isn't installed in the local dev environment, so no real `crew.kickoff()` could be smoke-tested during implementation.
  * Detection: N/A locally; only unit tests with mocked `Task`/`Crew` objects could be run.
  * Mitigation: mock fixtures were upgraded to set `.output` on every task in a crew (not just the final one), matching real CrewAI's sequential execution semantics, so the assembly path is exercised the same way in tests as it will be at runtime.

---

## 9) Observability / Logging

**Diagnostics**

* `SEASON_BUNDLE_RAW_VALIDATION_FAILED` / `PHASE_BUNDLE_RAW_VALIDATION_FAILED` runtime events fire when a post-assembly guardrail check fails, carrying the guardrail's failure reason.
* CrewAI's own `CREW_TASK_GUARDRAIL_FAILED` events remain the signal for `typed_output_present` / `phase_week_role_load_coherence` failures against the narrower raw LLM output.

---

## 10) Documentation Updates

* [x] `doc/specs/features/FEAT_finalize_manager_synthesis_boundary.md` — this record.
* [x] `doc/specs/features/FEAT_season_finalize_raw_bundle_boundary.md` — marked Superseded.
* [x] `CHANGELOG.md` — behavior change summary.
