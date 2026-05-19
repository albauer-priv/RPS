---
Version: 1.0
Status: Approved
Last-Updated: 2026-05-19
Owner: Season Planning
---
# FEAT: Season Plan Semantic Hardening

* **ID:** FEAT_season_plan_semantic_hardening
* **Status:** Approved
* **Owner/Area:** Season Planning
* **Last-Updated:** 2026-05-19
* **Related:** [skills/season/macrocycle-architecture/SKILL.md](/skills/season/macrocycle-architecture/SKILL.md), [skills/season/load-governance/SKILL.md](/skills/season/load-governance/SKILL.md)

---

## 1) Context / Problem

**Current behavior**

* Season Plan generation receives selected scenario structure, deterministic phase slots, availability load capacity, athlete context, events, logistics, and KPI guidance.
* The selected Season Scenario owns cadence and phase math (`deload_cadence`, `phase_length_weeks`, `phase_count_expected`, shortened phase summary).
* The Season Plan should interpret the selected scenario and serialize a schema-valid `SEASON_PLAN`.

**Problem**

* Generated plans can flatten scenario cadence semantics, e.g. treating `2:1:1` as a generic deload label instead of `2 load + mini-reset + reload`.
* Plans can copy availability capacity as phase corridors without enough phase-role, progression, and taper interpretation.
* Phase weekly S5 bands can be numerically flat because week role and phase role are not applied as deterministic Progressive Overload overlays.
* Durability-first semantics can degrade into intensity-free planning, losing the old method distinction between dominant endurance and targeted, recovery-compatible quality.
* Writer-produced metadata and trace versions must remain runtime-owned and schema-valid.

**Constraints**

* No persisted schema change for `SeasonPlanInterface`.
* No new dependencies.
* Scenario selection remains the authority for cadence choice; Season Plan must not select or infer a new cadence.
* Superseded planning/spec documents are migration evidence, not canonical runtime authority.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Treat selected scenario cadence and phase math as binding Season Plan input.
* [x] Add deterministic, scenario-derived cadence week roles to Season planning context.
* [x] Harden internal Season bundle output so review/writer stages preserve phase-level semantics.
* [x] Strengthen Season skills and review gates for taper, B-event handling, durability-first intensity semantics, and load-corridor realism.
* [x] Make Season phase corridors availability-bounded and phase-role aware before Phase Guardrails run.
* [x] Make Phase weekly S5 bands week-role aware while preserving S5 as the final numeric gatekeeper.
* [x] Add tests that prevent `2:1:1` from becoming a default or free constant.

**Non-Goals**

* [x] Manually persist a replacement production Season Plan.
* [x] Add new Season Plan schema fields.
* [x] Change Scenario generation ownership of cadence choice.

---

## 3) Proposed Behavior

**User/System behavior**

* After a Season Scenario is selected, Season Plan generation inherits the selected scenario structure exactly.
* The deterministic phase-slot prompt block includes cadence week roles derived from the selected scenario's cadence.
* Season planning and review must reject or replan outputs that contradict selected scenario cadence, omit A-event taper semantics, imply a full B-event taper, or collapse durability-first into intensity-free planning.

**UI impact**

* UI affected: No.

**Non-UI behavior**

* Components involved: deterministic planning context, CrewAI internal output models, Season and Phase skills/prompts, tests.
* Contracts touched: internal structured outputs only; persisted `SeasonPlanInterface` remains unchanged.

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/planning/season_structure.py`: derive and render `cadence_week_roles` from selected scenario cadence.
* `src/rps/planning/load_bands.py`: derive availability-bounded Season phase load context and role-aware weekly S5 progression overlays.
* `src/rps/crewai_runtime/models.py`: add internal season phase and phase week blueprint fields.
* `skills/season/*`, `skills/phase/*`, and artifact-writer prompts: preserve inherited cadence, phase role, week role, availability, and progressive-overload semantics.

**Data flow**

* Inputs: `SEASON_SCENARIOS`, `SEASON_SCENARIO_SELECTION`, planning horizon, availability, logistics, events, KPI guidance.
* Processing: selected scenario structure builds deterministic phase slots and derived cadence roles; deterministic load context bounds phase corridors by phase role and availability; Phase planning applies role-aware S5 bands.
* Outputs: schema-valid `SEASON_PLAN` data, with runtime-owned metadata.

**Schema / Artefacts**

* New artefacts: none.
* Changed artefacts: none.
* Validator implications: existing JSON Schema validation must still pass.

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible: Yes.
* Breaking changes: none for persisted artifacts.
* Fallback behavior: invalid or inconsistent selected scenario structure is surfaced as a blocking planning issue, not silently repaired by Season Plan.

**Conflicts with ADRs / Principles**

* Potential conflicts: none known.
* Resolution: preserves code-owned deterministic context and runtime-owned metadata boundaries.

**Impacted areas**

* UI: none.
* Pipeline/data: none.
* Renderer: none.
* Workspace/run-store: metadata behavior remains code-owned.
* Validation/tooling: tests cover deterministic context and structured models.
* Deployment/config: none.

**Required refactoring**

* Add internal phase blueprint model.
* Tighten Season skills and prompt wording.

---

## 6) Options & Recommendation

### Option A — Internal hardening without schema change

**Summary**

* Preserve existing `SeasonPlanInterface`; carry richer semantics through deterministic context, internal blueprints, and review gates.

**Pros**

* Backward compatible.
* Focuses the fix on generator behavior.
* Avoids schema migration while still preventing semantic drift.

**Cons**

* Cadence roles are not queryable from persisted Season Plan except through narrative/rationale fields.

**Risk**

* Writer prompts must reliably preserve reviewed blueprints.

### Option B — Persist cadence roles in Season Plan

**Summary**

* Add new schema fields for cadence week roles.

**Pros**

* Stronger persisted auditability.

**Cons**

* Requires schema bump, renderer updates, and migration handling.

### Recommendation

* Choose: Option A.
* Rationale: The issue is generator semantic drift, not a missing persisted contract.

---

## 7) Acceptance Criteria (Definition of Done)

* [ ] Selected scenario cadence is the only cadence authority during Season Plan generation.
* [ ] Phase slots include derived cadence week roles in deterministic prompt context.
* [ ] `SeasonPlanBundleModel` validates phase blueprints.
* [ ] Season skills block cadence mismatch, missing A-event taper, full B-event taper, availability-capacity copy-through, and phase corridors above feasible availability.
* [ ] Phase skills block weekly bands that contradict phase role, inherited week role, or S5 trace.
* [ ] Golden tests cover i150546/KW21 semantic expectations.
* [ ] Validation passes: py_compile, lint, typecheck, targeted pytest.

---

## 8) Migration / Rollout

**Migration strategy**

* None for persisted artifacts.

**Rollout / gating**

* No feature flag.
* Safe rollback: revert deterministic context/model/skill changes; no data migration required.

---

## 9) Risks & Failure Modes

* Failure mode: selected scenario structure is incomplete.
  * Detection: deterministic context lacks slots or marks inconsistent coverage.
  * Safe behavior: planning review requires replan/repair instead of guessing.
  * Recovery: regenerate scenarios/selection.
* Failure mode: writer loses reviewed semantics.
  * Detection: golden semantic test or audit gate fails.
  * Safe behavior: writer stops or review returns `replan_required`.
  * Recovery: rerun Season Plan after generator fix.

---

## 10) Observability / Logging

**New/changed events**

* None required.

**Diagnostics**

* Inspect Plan Hub run events for deterministic context injection and guardrail failures.
* Inspect `runtime/athletes/<athlete_id>/runs/<run_id>/events.jsonl` for Season planning/review/writer stages.

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] This feature spec.
* [ ] `CHANGELOG.md` — summarize generator hardening.

---

## 12) Link Map

* [Durability methodology skill](/skills/shared/durability-methodology/SKILL.md)
* [Season macrocycle architecture skill](/skills/season/macrocycle-architecture/SKILL.md)
* [Season load governance skill](/skills/season/load-governance/SKILL.md)
* [Season audit skill](/skills/season/audit/SKILL.md)
* [Load estimation core skill](/skills/shared/load-estimation-core/SKILL.md)
* [Legacy durability principles migration evidence](/specs/knowledge/_shared/sources/principles/principles_durability_first_cycling.md)
* [Legacy load estimation migration evidence](/specs/knowledge/_shared/sources/specs/load_estimation_spec.md)
