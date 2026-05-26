---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-26
Owner: Planning Runtime
---
# FEAT: Active Prompt + Policy Migration Completion

* **ID:** FEAT_active_prompt_policy_migration_completion
* **Status:** Implemented
* **Owner/Area:** Planning Runtime
* **Last-Updated:** 2026-05-26
* **Related:** `doc/architecture/skills_source_migration_audit.md`, `doc/architecture/crewai_migration_audit.md`, `doc/specs/features/FEAT_upstream_first_planning_pipeline.md`

---

## 1) Context / Problem

**Current behavior**

* Policies and principles were already migrated materially into active skills and deterministic runtime helpers.
* Several active prompt roles in the Season/Phase/Week runtime still remained too thin, especially legacy root prompts and selected specialist prompts.
* Earlier migration audits were too optimistic about prompt completeness and prompt/skill/code authority separation.

**Problem**

* Active prompts could still act as thin wrappers rather than self-contained role-authority definitions.
* Review and writer stages still risked becoming semantic cleanup fallback points when planner/finalizer prompts were under-specified.
* The repo lacked one combined audit that showed legacy policy/principle/prompt sources against active code/skill/prompt/task ownership.

**Constraints**

* Keep deterministic numeric and structural authority in code-owned runtime context where already established.
* Do not duplicate code-owned or skill-owned operational logic unnecessarily in prompts.
* Preserve the current CrewAI agent wiring in `config/crewai/agents.yaml`.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Extend the existing migration audit to cover legacy prompt sources and all active prompt roles.
* [x] Harden active root, manager, specialist, and selected secondary prompts to explicit role-authority prompts.
* [x] Make prompt ownership explicitly upstream-first: planner/finalizer before review, review before writer, writer as serialization only.
* [x] Align active prompts with the new self-contained standard: definitions, injected authority, scope, hard rules, and output discipline.

**Non-Goals**

* [x] No schema changes.
* [x] No change to deterministic numeric ownership in `src/rps/planning/*`.
* [x] No change to objective-mismatch ownership; it remains input-owned and warning-only.

---

## 3) Proposed Behavior

**User/System behavior**

* Planning prompts now declare explicit authority boundaries instead of relying on thin legacy placeholders.
* Active Season/Phase/Week prompt roles now state injected deterministic authority, self-check boundaries, and no-review/no-writer-healing rules directly.
* The central migration audit now records both policy/principle migration and prompt migration in one place.

**UI impact**

* UI affected: No.

**Non-UI behavior**

* Components involved: `prompts/agents/*.md`, `doc/architecture/skills_source_migration_audit.md`, `AGENTS.md`, `config/crewai/agents.yaml`
* Contracts touched: prompt-authority conventions only; no schema/version changes.

---

## 4) Implementation Analysis

**Components / Modules**

* `doc/architecture/skills_source_migration_audit.md`: combined source-to-active audit for legacy policy/principle/prompt sources and active prompt roles.
* `prompts/agents/*.md`: active prompt hardening for root, manager, specialist, and secondary roles.
* `AGENTS.md`: stricter repository rule for active self-contained planning layers and variable authority.

**Data flow**

* Inputs: active prompt files, active agent wiring, existing legacy policy/principle sources, existing deterministic context ownership.
* Processing: classify active roles, assign authority layer, harden prompts, document remaining gaps.
* Outputs: updated audit doc and active prompts; no new runtime artifact.

**Schema / Artefacts**

* New artefacts: none.
* Changed artefacts: prompt docs and architecture docs only.
* Validator implications: no schema validator changes; runtime prompt behavior becomes more explicit.

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible: Yes.
* Breaking changes: none intended at artifact/schema level.
* Fallback behavior: unchanged runtime tools and deterministic context remain authoritative when prompts do not own numeric logic.

**Conflicts with ADRs / Principles**

* No ADR conflict identified.
* This reinforces the existing upstream-first and skills-first runtime direction.

**Impacted areas**

* UI: none.
* Pipeline/data: none.
* Renderer: none.
* Workspace/run-store: none.
* Validation/tooling: prompt audit and human review improve.
* Deployment/config: no changes to provider/runtime profiles required.

**Required refactoring**

* Replace thin active prompt wrappers with explicit role-authority prompts.
* Consolidate migration evidence in the existing central audit rather than spreading it across multiple audit docs.

---

## 6) Options & Recommendation

### Option A — Combined audit + active prompt hardening

**Summary**

* Keep one central migration audit and update active prompts to the new authority template.

**Pros**

* Clear ownership.
* Easier to review.
* Reduces recurrence of partial migration.

**Cons**

* Touches many prompt files.

**Risk**

* Prompt wording drift if not kept consistent across roles.

### Option B — Audit only, defer prompt hardening

**Summary**

* Document gaps but do not fix prompts yet.

**Pros**

* Smaller immediate patch.

**Cons**

* Leaves active runtime prompts under-specified.
* Reintroduces the same migration risk later.

### Recommendation

* Choose: Option A.
* Rationale: the audit alone does not reduce runtime ambiguity; the active prompts must be hardened in the same pass.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `doc/architecture/skills_source_migration_audit.md` includes prompt-source and active-prompt migration coverage.
* [x] Active Season/Phase/Week root prompts are no longer 3-line wrappers.
* [x] Active manager/finalizer/review prompts state authority boundaries and no-review/no-writer-healing rules explicitly.
* [x] Prioritized specialist and secondary prompts are hardened where previously too thin.
* [x] Prompt ownership and code/skill/task/review/writer separation are documented consistently.
* [x] Validation passes: syntax, lint, typecheck, targeted tests, and one safe smoke run.

---

## 8) Migration / Rollout

**Migration strategy**

* No stored artifact migration.
* Prompt/runtime semantics update in place.

**Rollout / gating**

* No feature flag.
* Safe rollback: restore previous prompt bodies and audit doc.

---

## 9) Risks & Failure Modes

* Failure mode: prompt files become inconsistent across layers
  * Detection: audit matrix and prompt review
  * Safe behavior: review against `config/crewai/agents.yaml` and active role classes
  * Recovery: normalize prompts to the shared structure

* Failure mode: prompt starts duplicating code-owned math
  * Detection: review against deterministic authority sections
  * Safe behavior: keep numeric ownership in code/skills
  * Recovery: move duplicated rules back to code-owned or skill-owned layer

---

## 10) Observability / Logging

**New/changed events**

* none

**Diagnostics**

* inspect `doc/architecture/skills_source_migration_audit.md` for source-to-active status
* inspect `prompts/agents/*.md` for role-authority structure

---

## 11) Documentation Updates

* [x] [doc/architecture/skills_source_migration_audit.md](/Users/alexander/RPS/doc/architecture/skills_source_migration_audit.md) — combined policy/principle/prompt migration audit
* [x] [AGENTS.md](/Users/alexander/RPS/AGENTS.md) — upstream-first and self-contained active-layer rules
* [x] [CHANGELOG.md](/Users/alexander/RPS/CHANGELOG.md) — document prompt migration hardening

---

## 12) Link Map (no duplication; links only)

* Architecture: [doc/architecture/agents.md](/Users/alexander/RPS/doc/architecture/agents.md)
* Architecture: [doc/architecture/system_architecture.md](/Users/alexander/RPS/doc/architecture/system_architecture.md)
* Migration audit: [doc/architecture/crewai_migration_audit.md](/Users/alexander/RPS/doc/architecture/crewai_migration_audit.md)
* Workspace: `doc/architecture/workspace.md`
* ADRs: `doc/adr/ADR-048-skills-first-multi-crew-planning-runtime.md`, `doc/adr/ADR-049-single-method-skill-attachment.md`
