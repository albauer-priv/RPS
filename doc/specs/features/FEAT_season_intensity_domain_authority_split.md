---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-19
Owner: Planning Runtime
---
# FEAT: Season Intensity-Domain Authority Split

* **ID:** FEAT_season_intensity_domain_authority_split
* **Status:** Implemented
* **Owner/Area:** Planning Runtime
* **Last-Updated:** 2026-05-19
* **Related:** FEAT_season_plan_semantic_hardening

---

## 1) Context / Problem

**Current behavior**

* `SEASON_PLAN` generation can collapse to `allowed_intensity_domains: ["ENDURANCE"]` across all phases even when the selected `SEASON_SCENARIOS` scenario permits additional domains.
* The store path for season-plan contract validation also failed on one code path because `build_selected_scenario_structure_block()` was called with the wrong keyword argument.
* The current examples in `mandatory_output_season_plan.md` and `mandatory_output_phase_guardrails.md` imply different domain breadth without clearly explaining that Season and Phase operate at different authority levels.

**Problem**

* Season-level domain authority was not carried deterministically from the selected scenario into the season load-capacity and season phase-load context.
* The deterministic path therefore used a silent `ENDURANCE` fallback in season planning.
* Phase-level semantics are allowed to be narrower than season semantics, but they must not retroactively become the season source of truth.

**Constraints**

* No schema change unless strictly required.
* `LoadEstimationSpec` remains binding for deterministic load capacity and S5 calculations.
* Season, Phase, and Week validation must remain compatible with existing store and CrewAI guardrails.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Carry selected-scenario intensity-domain authority deterministically into season planning.
* [x] Remove the season-path silent fallback to `["ENDURANCE"]` when scenario authority is available or required.
* [x] Allow Phase/Week to stay narrower than Season without letting Phase guardrails overwrite Season semantics.
* [x] Harden validation so a season-wide collapse to `ENDURANCE only` is blocked when the selected scenario allows broader domains.
* [x] Align season skills/tasks and legacy example docs with the authority split.

**Non-Goals**

* [x] No change to JSON schema enums or field shapes.
* [x] No attempt to make all phases carry the full scenario domain set.
* [x] No workout-prescription or week-level density redesign in this feature.

---

## 3) Proposed Behavior

**User/System behavior**

* `SEASON_SCENARIOS` plus `SEASON_SCENARIO_SELECTION` define season-level intensity-domain authority.
* `SEASON_PLAN` and deterministic season load context consume that authority directly.
* `PHASE_GUARDRAILS` may narrow domains for a specific phase, and Week/Workout planning may narrow further operationally.
* Validation blocks a season artifact when all phases collapse to `ENDURANCE only` despite broader selected-scenario authority.

**UI impact**

* UI affected: No direct UI flow change.

**Non-UI behavior**

* Components involved: `season_structure`, `load_bands`, `contracts`, `guardrails`, `guarded_store`, season orchestration, season skills/tasks.
* Contracts touched: deterministic selected-scenario context, season phase-load context, season-plan contract validation, CrewAI season bundle contract checks.

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/planning/season_structure.py`: carry selected-scenario intensity guidance into deterministic selected-scenario context.
* `src/rps/planning/load_bands.py`: use season-domain authority in season load capacity and season phase-load context; remove silent season fallback.
* `src/rps/planning/contracts.py`: validate season-plan intensity semantics against season authority while allowing per-phase narrowing.
* `src/rps/crewai_runtime/guardrails.py`: pass phase-blueprint domain semantics into season bundle contract validation.
* `src/rps/orchestrator/season_flow.py`: inject selected-scenario domain authority into deterministic season planning contexts.
* `src/rps/workspace/guarded_store.py`: fix selected-scenario structure block call and reuse the new deterministic context path.

**Data flow**

* Inputs: `SEASON_SCENARIOS`, `SEASON_SCENARIO_SELECTION`, athlete/availability/logistics/kpi/zone/wellness inputs.
* Processing: selected-scenario intensity domains are normalized, rendered into deterministic season context, consumed by load estimation, and checked again during contract validation.
* Outputs: season deterministic context blocks, stricter season-plan validation, updated season skills/tasks/spec examples.

**Schema / Artefacts**

* New artefacts: none.
* Changed artefacts: none at schema level; runtime behavior changes for `SEASON_PLAN`.
* Validator implications: season-plan validation now checks global collapse and out-of-authority domains.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes, at schema level.
* Breaking changes: Season plans that previously passed with `ENDURANCE only` despite broader selected-scenario authority now fail deterministically.
* Fallback behavior: Missing season-domain authority no longer silently defaults to `ENDURANCE`; season deterministic context surfaces the missing-authority failure.

**Conflicts with ADRs / Principles**

* Potential conflicts: none identified.
* Resolution: aligns with durability-first principles, `LoadEstimationSpec`, and existing deterministic contract ownership.

**Impacted areas**

* UI: indirect only through improved season outputs.
* Pipeline/data: season deterministic context and store validation.
* Renderer: no code change required.
* Workspace/run-store: season store path enforces stricter contract checks.
* Validation/tooling: new contract checks and tests.
* Deployment/config: none.

**Required refactoring**

* Separate season vs phase domain authority in deterministic helpers.
* Extend contract validation to reason about season-domain breadth without forcing exact per-phase equality.
* Clarify legacy example docs so season and phase examples are no longer implicitly contradictory.

---

## 6) Options & Recommendation

### Option A — Deterministic authority split plus validation hardening

**Summary**

* Carry selected-scenario domains into season deterministic context and validate season outputs against that authority.

**Pros**

* Fixes the actual root cause.
* Keeps Phase/Week narrowing valid.
* Uses existing deterministic/guardrail infrastructure.

**Cons**

* Adds more contract logic to season validation.

**Risk**

* Overly strict validation could reject acceptable narrow early phases if the rule is written too broadly.

### Option B — Prompt-only correction

**Summary**

* Tell the season agents not to emit `ENDURANCE only`.

**Pros**

* Small implementation.

**Cons**

* Does not fix the deterministic load-estimation path.
* Still leaves store/guardrail paths vulnerable.

### Recommendation

* Choose: Option A
* Rationale: the bug originates in deterministic authority propagation, not only in prompt language.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Selected-scenario intensity guidance is present in deterministic selected-scenario structure context.
* [x] Season load capacity uses selected-scenario domains and does not silently fall back to `ENDURANCE`.
* [x] Season phase-load context exposes season-level domain authority for review/validation.
* [x] Season contract validation blocks a full-season collapse to `ENDURANCE only` when the selected scenario allows broader domains.
* [x] Phase-specific narrowing remains valid.
* [x] Store crash from the wrong selected-scenario kwarg is fixed.
* [x] Validation passes: syntax check, lint, typecheck, targeted pytest, and one relevant smoke command.

---

## 8) Migration / Rollout

**Migration strategy**

* No schema migration.
* Existing stored season plans remain readable; only new writes and guarded reviews use the stricter behavior.

**Rollout / gating**

* Feature flag / config: none.
* Safe rollback: revert deterministic authority split and validator additions together.

---

## 9) Risks & Failure Modes

* Failure mode: selected-scenario domains missing or malformed.
  * Detection: season deterministic load context lacks `availability_load_capacity_kj` and surfaces warnings/blocking issues.
  * Safe behavior: block season generation/review instead of inferring `ENDURANCE`.
  * Recovery: fix or regenerate `SEASON_SCENARIOS` / `SEASON_SCENARIO_SELECTION`.

* Failure mode: validation incorrectly rejects legitimate narrow phases.
  * Detection: season contract test failures or blocked season review despite at least one phase using scenario-permitted quality where appropriate.
  * Safe behavior: validation remains phase-narrowing-tolerant and only blocks full collapse or out-of-authority domains.
  * Recovery: refine validator conditions, not schema.

---

## 10) Observability / Logging

**New/changed events**

* No new event family required.
* Existing season deterministic-context and guarded-store failure messages now surface missing domain authority more clearly via existing errors.

**Diagnostics**

* `rps.log`
* guarded-store validation errors
* deterministic context blocks in season-planning prompt context

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] [mandatory_output_phase_guardrails.md](/Users/alexander/RPS/specs/knowledge/_shared/sources/specs/mandatory_output_phase_guardrails.md) — clarify example is a narrow phase-level example, not a season-level authority default.
* [x] [mandatory_output_season_plan.md](/Users/alexander/RPS/specs/knowledge/_shared/sources/specs/mandatory_output_season_plan.md) — clarify season/phase authority split in the example section.
* [x] season skills and task descriptions — reflect durability-first as `ENDURANCE` dominant, not `ENDURANCE only`, and prohibit backward reconstruction from Phase Guardrails.

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* Workspace: `doc/architecture/workspace.md`
* Artefact flow: `doc/overview/artefact_flow.md`
* Validation / runbooks: `doc/runbooks/validation.md`
* Logging policy: `doc/specs/contracts/logging_policy.md`

