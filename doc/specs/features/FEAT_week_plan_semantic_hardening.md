---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-19
Owner: Planning
---
# FEAT: Week Plan Semantic Hardening

* **ID:** FEAT_week_plan_semantic_hardening
* **Status:** Implemented
* **Owner/Area:** Planning
* **Last-Updated:** 2026-05-19
* **Related:** Season/Phase role-aware load hardening

---

## 1) Context / Problem

**Current behavior**

* Week planning receives phase artefacts, availability, workout-load guidance, and workout syntax instructions.
* Some critical semantics are prompt-owned only: active phase week role, active S5 band mirroring, day-level availability distribution, and workout structure constraints.

**Problem**

* A Week Plan can appear plausible while copying or drifting its own corridor, ignoring the phase week role, distributing load onto unavailable days, or producing syntactically incomplete Intervals workout text.
* The Week Plan must execute the active Phase Plan and Phase Guardrails, not introduce new progression, taper, deload, or workout-intensity logic.

**Constraints**

* No persisted `week_plan.schema.json` change in this step.
* No new dependencies.
* Runtime-owned metadata remains authoritative.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Inject deterministic Week Execution Context with phase role, phase week role, active S5 band, allowed semantics, quality cap, fixed rest days, and exact Mon-Sun matrix.
* [x] Validate that `week_summary.weekly_load_corridor_kj` mirrors the active Phase/S5 weekly band.
* [x] Validate daily agenda shape, fixed rest, zero availability, and day availability caps.
* [x] Validate role coherence between phase week role, agenda day roles, quality density, and workout domains.
* [x] Enforce workout structure and Intervals syntax requirements before persistence/export.
* [x] Add internal day/workout blueprints to Week Plan bundle output.

**Non-Goals**

* [x] No schema upgrade for persisted `WEEK_PLAN`.
* [x] No new workout authoring engine or external Intervals dependency.
* [x] No change to Season/Phase cadence authority.

---

## 3) Proposed Behavior

**User/System behavior**

* Week planning uses `PHASE_STRUCTURE.week_skeleton_logic.week_roles` as the active week-role authority.
* The active weekly load band comes from the phase S5 band. The Week Plan must mirror it and plan inside it.
* The agenda must be exactly the selected ISO week, Monday through Sunday.
* Load is distributed only within availability and recovery constraints.
* Workout text must be structurally complete and valid for the project Intervals subset.
* If the constraints cannot be reconciled, guardrails block the artefact or force review/replan.

**UI impact**

* UI affected: No direct layout change.
* Plan Hub and Week export benefit from stronger validation failures and clearer retry messages.

**Non-UI behavior**

* Components involved: deterministic context, CrewAI output models, task guardrails, week availability validator, workout validator, Week skills/prompts.
* Contracts touched: internal Week Plan bundle only; persisted `WEEK_PLAN` remains unchanged.

---

## 4) Implementation Analysis

**Components / Modules**

* Deterministic context: extend week calendar context with active phase week-role and active guardrail semantics.
* Guardrails: add active corridor, agenda calendar, role alignment, and workout structure checks.
* Validators: strengthen agenda/availability checks and Intervals workout-text structure checks.
* Models: add internal day/workout blueprints to the Week Plan bundle.
* Skills/prompts: make phase role, week role, availability distribution, S5 band, and workout syntax non-optional.

**Data flow**

* Inputs: Season Plan, Phase Guardrails, Phase Structure, Availability, Logistics, Planning Events, Zone Model, Load Capacity context.
* Processing: code resolves the active ISO week role, active S5 band, day matrix, availability caps, allowed semantics, and quality cap.
* Outputs: schema-valid `WEEK_PLAN` and exportable workout text, or deterministic guardrail failure.

**Schema / Artefacts**

* New artefacts: none.
* Changed artefacts: none.
* Validator implications: `WEEK_PLAN` must now pass additional runtime guardrails before persistence/export.

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible: Yes for schema shape.
* Breaking changes: invalid or semantically drifting Week Plans are rejected earlier.
* Fallback behavior: if deterministic active phase context is unavailable, guardrails skip only the context-dependent checks and keep schema/export checks active.

**Conflicts with ADRs / Principles**

* No conflicts. The change reinforces code-owned deterministic context and runtime-owned metadata.

**Impacted areas**

* UI: no layout change.
* Pipeline/data: stronger Week Plan validation.
* Renderer: no direct change.
* Workspace/run-store: guarded store rejects more invalid Week Plan artefacts.
* Validation/tooling: tests cover new Week/Workout guardrails.
* Deployment/config: no new config.

**Required refactoring**

* Replace heuristic week-role prompt context with Phase Structure derived context.
* Compare Week Plan corridors against runtime context, not only self-declared fields.

---

## 6) Options & Recommendation

### Option A — Runtime guardrails without schema migration

**Summary**

* Add deterministic context, internal blueprints, and guardrails while keeping `WEEK_PLAN` schema unchanged.

**Pros**

* Minimal persistence risk.
* Strong validation at generation and guarded-store boundaries.

**Cons**

* Some semantics remain internal/runtime rather than persisted as first-class fields.

**Risk**

* Existing weak plans may be rejected and require re-generation.

### Option B — Persist week role and workout domains

**Summary**

* Add persisted fields to `WEEK_PLAN` for phase week role, workout domain, and day allocation trace.

**Pros**

* Stronger auditability in stored artefacts.

**Cons**

* Requires schema migration and renderer/UI updates.

### Recommendation

* Choose: Option A.
* Rationale: it addresses the current semantic failure modes without a schema migration.

---

## 7) Acceptance Criteria

* [x] Week context includes active Phase Structure week role.
* [x] Week corridor mismatch against active S5 band is blocked when runtime context is available.
* [x] Agenda calendar shape is exactly seven Mon-Sun rows for the target week.
* [x] Fixed rest and unavailable days cannot carry load or workouts.
* [x] Quality density and deload/reset role violations are blocked.
* [x] Workout text requires Warmup, Cooldown, ordered sections, step durations, power target, cadence, and valid Intervals subset syntax.
* [x] Validation passes for targeted Week/Workout tests.

---

## 8) Migration / Rollout

**Migration strategy**

* No persisted schema migration.
* Existing artefacts remain readable; stricter checks apply when new or edited Week Plans are stored/exported.

**Rollout / gating**

* No feature flag.
* Rollback is reverting the feature commit.

---

## 9) Risks & Failure Modes

* Failure mode: Phase Structure lacks week roles.
  * Detection: deterministic context shows missing `phase_week_role`.
  * Safe behavior: context-dependent role checks skip or planner guardrails retry with explicit prompt context.
  * Recovery: regenerate Phase Structure.
* Failure mode: Availability cannot support the active S5 band.
  * Detection: Week load or availability guardrail failure.
  * Safe behavior: reject/replan rather than adding intensity.
  * Recovery: replan Phase/S5 band or adjust availability inputs.
* Failure mode: Workout syntax is invalid.
  * Detection: workout structure/export guardrails.
  * Safe behavior: reject before export.
  * Recovery: regenerate Workout text.

---

## 10) Observability / Logging

**New/changed events**

* Existing `CREW_TASK_GUARDRAIL_FAILED` telemetry records the new guardrail name and failure reason.

**Diagnostics**

* Planning run logs show Week Planner guardrail failures.
* Workspace guarded-store validation reports exportability issues for stored Week Plans.

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] `skills/week/plan-synthesis/SKILL.md` — active week-role and blueprint requirements.
* [x] `skills/week/load-estimation-week/SKILL.md` — load distribution against active S5 band and availability.
* [x] `skills/week/load-governance-review/SKILL.md` — active corridor and role-aware checks.
* [x] `skills/week/consistency-audit/SKILL.md` — agenda/workout/role coherence.
* [x] `skills/week/workout-construction/SKILL.md` — workout structure and Intervals subset.
* [x] `skills/week/workout-syntax-review/SKILL.md` — structural syntax checks.
* [x] `skills/week/artifact-writing/SKILL.md` — writer constraints.
* [x] `prompts/agents/week_artifact_writer.md` — no unapproved agenda/workout invention.

---

## 12) Link Map

* `specs/knowledge/_shared/sources/principles/principles_durability_first_cycling.md`
* `specs/knowledge/_shared/sources/policies/workout_policy.md`
* `specs/knowledge/_shared/sources/policies/load_distribution_policy.md`
* `specs/knowledge/_shared/sources/specs/load_estimation_spec.md`
* `specs/knowledge/_shared/sources/specs/phase__week_contract.md`
* `specs/knowledge/_shared/sources/specs/mandatory_output_week_plan.md`
* `specs/knowledge/_shared/sources/specs/agenda_enum_spec.md`
* `specs/knowledge/_shared/sources/specs/workouts/intervals_workout_ebnf.md`
* `specs/knowledge/_shared/sources/specs/workouts/workout_syntax_and_validation.md`
* `specs/knowledge/_shared/sources/specs/workouts/workout_json_spec.md`
