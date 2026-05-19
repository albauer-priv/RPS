---
Version: 1.0
Status: Draft
Last-Updated: 2026-05-19
Owner: Planning
---
# FEAT: Planning Chain Contract Hardening

* **ID:** FEAT_planning_chain_contract_hardening
* **Status:** Draft
* **Owner/Area:** Planning
* **Last-Updated:** 2026-05-19
* **Related:** ADR-028, ADR-046

---

## 1) Context / Problem

**Current behavior**

* Planning flows already inject deterministic context for scenario slots, phase/week roles, load bands, availability, and snapshot memory.
* Some downstream checks still rely on prompt compliance, narrative notes, or writer discipline.

**Problem**

* Season, Phase, Week, and Workout artifacts can drift from code-owned contracts if a model rewrites structure, cadence, load bands, or calendar details.
* Snapshot memory freshness is not consistently treated as a planning contract.

**Constraints**

* No persisted schema change in v1.
* No new dependencies.
* Existing CrewAI memory remains assistive and non-binding.

---

## 2) Goals & Non-Goals

**Goals**

* [ ] Make deterministic contracts the structural authority for Scenario → Season → Phase → Week → Workouts.
* [ ] Validate writer outputs against deterministic context and approved internal blueprints.
* [ ] Treat fresh snapshot memory as code-owned derived context and stale snapshots as blockers when used authoritatively.
* [ ] Keep LLMs responsible for narrative and controlled wording, not structural decisions.

**Non-Goals**

* [ ] Persist new schema fields in Season/Phase/Week artifacts.
* [ ] Replace CrewAI memory with a new memory backend.

---

## 3) Proposed Behavior

**User/System behavior**

* Planner runs stop with actionable blockers when required contracts or fresh snapshots are missing.
* Review and writer stages reject artifacts that change phase slots, cadence roles, load corridors, weekly bands, availability constraints, or workout export rules.

**UI impact**

* UI affected: No direct layout change.

**Non-UI behavior**

* Components involved: orchestrators, deterministic context builders, CrewAI guardrails, guarded store, skills/prompts.
* Contracts touched: scenario slot contract, season phase load context, phase execution context, week calendar context, snapshot memory freshness.

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/planning/contracts.py`: shared deterministic contract validators.
* `src/rps/planning/deterministic_context.py`: phase execution must consume slot contracts rather than prose.
* `src/rps/crewai_runtime/guardrails.py`: contract guardrails for Season/Phase/Week writer outputs.
* `src/rps/orchestrator/season_flow.py` and `src/rps/orchestrator/plan_week.py`: fail fast on missing critical context and bind context into guardrails.

**Data flow**

* Inputs: selected scenario, scenario selection, season plan, phase guardrails/structure, availability, planning events, zone model, snapshot artifacts.
* Processing: build contracts in code, inject prompt blocks, validate agent outputs against runtime context.
* Outputs: unchanged persisted artifacts plus clearer runtime blocker diagnostics.

**Schema / Artefacts**

* New artefacts: none.
* Changed artefacts: none.
* Validator implications: stronger semantic guardrails before persistence.

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible: Yes for stored schema shape.
* Breaking changes: previously tolerated drift can now block planning runs.
* Fallback behavior: non-binding advisory memory may be stale; authoritative snapshots may not.

**Conflicts with ADRs / Principles**

* Aligned with ADR-028 snapshot-based planner memory.
* Aligned with ADR-046 separation of state, memory, knowledge, and guardrails.

**Impacted areas**

* UI: no direct change.
* Pipeline/data: no change.
* Renderer: no change.
* Workspace/run-store: stronger guarded-store checks where upstream context is available.
* Validation/tooling: new contract validators and tests.
* Deployment/config: no new config.

**Required refactoring**

* Remove prose-based phase cadence inference.
* Add direct S5/context comparisons instead of notes regex authority.
* Add snapshot freshness checks.

---

## 6) Options & Recommendation

### Option A — Code-owned contracts with existing schemas

**Summary**

* Keep schemas unchanged and enforce semantics through deterministic context, internal blueprints, guardrails, and store checks.

**Pros**

* Low migration cost.
* Preserves current artifacts.
* Moves fragile behavior from prompts to code.

**Cons**

* Some contract values remain internal rather than persisted.

### Option B — Persist contract fields

**Summary**

* Add explicit contract fields to artifact schemas.

**Pros**

* Easier downstream inspection.

**Cons**

* Requires schema migration and broader renderer/UI updates.

### Recommendation

* Choose: Option A.
* Rationale: the immediate problem is semantic drift, not missing persisted fields.

---

## 7) Acceptance Criteria

* [ ] Season Plan is rejected when phases do not match selected scenario slots.
* [ ] Phase artifacts are rejected when week roles or S5 bands do not match phase execution context.
* [ ] Week Plan is rejected when agenda, load band, availability, quality cap, or workout syntax violates active week context.
* [ ] Fresh authoritative snapshots are required before Season/Phase/Week authoritative planning.
* [ ] Validation passes: syntax check, lint, typecheck, targeted pytest.

---

## 8) Migration / Rollout

**Migration strategy**

* No schema migration.

**Rollout / gating**

* No feature flag. Guardrails apply when context is available.
* Safe rollback: remove new guardrails from task policy and disable fail-fast checks.

---

## 9) Risks & Failure Modes

* Failure mode: strict contracts block runs that previously completed with drift.
  * Detection: guardrail/runtime error messages.
  * Safe behavior: stop planning rather than persist invalid artifacts.
  * Recovery: regenerate upstream scenario/phase/week artifacts with fresh context.

* Failure mode: missing snapshot source versions.
  * Detection: snapshot freshness issue.
  * Safe behavior: rebuild snapshot or block authoritative injection.

---

## 10) Observability / Logging

**New/changed events**

* Existing guardrail telemetry records contract guardrail failures.

**Diagnostics**

* Workspace context artifacts in `runtime/athletes/<athlete_id>/data/context/`.
* Runtime logs in `runtime/athletes/<athlete_id>/runs/`.

---

## 11) Documentation Updates

* [ ] `doc/runbooks/crewai_memory.md` — clarify snapshot freshness vs CrewAI memory.
* [ ] `doc/architecture/crewai_flows.md` — clarify contract guardrail stage.
* [ ] Skills under `skills/shared`, `skills/season`, `skills/phase`, and `skills/week` — add contract consumption boundaries.

---

## 12) Link Map

* [ADR-028 Snapshot-Based Planner Memory](../../adr/ADR-028-snapshot-based-planner-memory.md)
* [ADR-046 CrewAI State, Memory, Knowledge, and Guardrail Separation](../../adr/ADR-046-crewai-state-memory-knowledge-guardrails.md)
* [CrewAI Memory Runbook](../../runbooks/crewai_memory.md)
