---
Version: 1.0
Status: Implemented
Last-Updated: 2026-06-09
Owner: Planning Runtime
---
# FEAT: Active Prompt, Skill, and Doc Debt Cleanup

* **ID:** FEAT_active_prompt_skill_doc_debt_cleanup
* **Status:** Implemented
* **Owner/Area:** Planning Runtime / Documentation
* **Last-Updated:** 2026-06-09
* **Related:** [FEAT_active_prompt_policy_migration_completion](/Users/alexander/RPS/doc/specs/features/FEAT_active_prompt_policy_migration_completion.md), [FEAT_full_typecheck_and_test_harness_closure](/Users/alexander/RPS/doc/specs/features/FEAT_full_typecheck_and_test_harness_closure.md), [ADR-056-upstream-first-planning-pipeline](/Users/alexander/RPS/doc/adr/ADR-056-upstream-first-planning-pipeline.md)

---

## 1) Context / Problem

**Current behavior**

* The active Season/Phase/Week planning chain is materially more self-contained than before.
* The prompt/skill migration audit already documents that most active prompts are no longer thin wrappers.
* A small number of active skill files still carry residual implementation debt:
  * variable-like terms remain in operative text without local definition or explicit injected-source mapping
  * one shared active skill is still thinner than the repo's current self-contained standard
  * the migration audit still describes these as open follow-up gaps

**Problem**

* These leftovers are exactly the class of ambiguity that causes planners to lean back on historical understanding instead of active local authority.
* The repo now has clear rules in `AGENTS.md` for active planning layers:
  * every variable-like term must be locally defined, explicitly mapped to injected authority, or forbidden
  * active files must be self-contained enough to operate without reconstructing logic from audit or legacy prose
* The remaining drift is small, but it is now the highest-value prompt/skill/doc cleanup still open.

**Constraints**

* No schema changes.
* No authority-model redesign.
* No broad prompt rewrite just for stylistic consistency.
* Keep code-owned deterministic authority unchanged.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Remove remaining variable-definition gaps in active Season/Phase planning skills.
* [x] Upgrade the shared durability skill to the current self-contained active-skill standard.
* [x] Update the migration audit so it reflects the cleaned active-state reality rather than stale residual gaps.
* [x] Make active planner/finalizer guidance explicitly reject historical migration docs and superseded prose as operative runtime sources.

**Non-Goals**

* [ ] No new planner feature behavior.
* [ ] No schema or persisted artifact changes.
* [ ] No repo-wide documentation rewrite outside the active migration/audit surfaces.

---

## 3) Proposed Behavior

**User/System behavior**

* Planning behavior stays functionally the same.
* Active Season/Phase/Week skills become more explicit and less dependent on institutional memory.
* The migration audit becomes decision-complete for the currently active prompt/skill runtime layer.

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved:
  * `skills/season/load-governance/SKILL.md`
  * `skills/phase/cadence-recovery/SKILL.md`
  * `skills/shared/durability-methodology/SKILL.md`
  * selected active task/prompt files where explicit no-historical-doc guidance should be frontloaded
  * `doc/architecture/skills_source_migration_audit.md`
* Contracts touched:
  * active prompt/skill/doc authority conventions only

---

## 4) Implementation Analysis

**Components / Modules**

* Active skills:
  * define or map residual variable terms such as `LR_share` and `CH_kJ`
  * add missing self-contained structure to the shared durability skill
* Active planning task/prompt files:
  * add compact explicit wording that historical migration docs and superseded prose are not operative runtime sources
* Audit doc:
  * remove stale "next cleanup" findings once the targeted active files are corrected
  * record the completion state of the active-layer migration

**Data flow**

* Inputs: current active prompt/skill/doc files and the migration audit
* Processing: tighten active file definitions, authority blocks, and non-scope wording
* Outputs: cleaner active planning guidance and an updated audit baseline

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: prompt/skill/doc files only
* Validator implications: no schema validator changes

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none expected
* Fallback behavior: existing code-owned deterministic context remains authoritative

**Conflicts with ADRs / Principles**

* Potential conflicts: none expected
* Resolution: this reinforces ADR-056 and current AGENTS rules rather than changing them

**Impacted areas**

* UI: none
* Pipeline/data: none
* Renderer: none
* Workspace/run-store: none
* Validation/tooling: documentation and active-skill clarity improve
* Deployment/config: none

**Required refactoring**

* tighten active skill definitions and authority blocks
* update migration audit conclusions to match repo reality

---

## 6) Options & Recommendation

### Option A — Targeted active-layer cleanup

**Summary**

* Fix only the remaining active prompt/skill/doc debt that still affects runtime reasoning quality.

**Pros**

* Small, reviewable patch
* Directly addresses the highest-value residual ambiguity
* Avoids reopening already-solved migration areas

**Cons**

* Does not attempt a broad doc-style normalization

**Risk**

* Minor risk of overclaiming migration completeness if the audit is not updated carefully

### Option B — Broad repo-wide prompt/doc sweep

**Summary**

* Reformat and restate many prompt/skill/doc files in one pass.

**Pros**

* More visually uniform

**Cons**

* Higher review cost
* Easier to mix real fixes with stylistic churn
* Increases regression risk in active planning language

### Recommendation

* Choose: Option A
* Rationale: Wave 4 should close real active-layer debt, not create a large text-only diff with weak signal.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Residual active variable gaps (`LR_share`, `CH_kJ`, or equivalent current leftovers) are locally defined or explicitly mapped.
* [x] `skills/shared/durability-methodology/SKILL.md` follows the current self-contained active-skill structure closely enough to operate without hidden audit/legacy dependencies.
* [x] Selected active tasks/prompts explicitly reject historical migration docs and superseded prose as operative runtime sources.
* [x] `doc/architecture/skills_source_migration_audit.md` is updated to reflect the closure of this residual active-layer debt.
* [x] Validation passes: `python3 -m py_compile $(git ls-files '*.py')`, `./scripts/run_lint.sh`, `./scripts/run_typecheck.sh`

---

## 8) Migration / Rollout

**Migration strategy**

* No data migration
* In-place update of active prompt/skill/doc assets

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert the touched prompt/skill/doc files

---

## 9) Risks & Failure Modes

* Failure mode: active guidance is tightened inconsistently across layers

  * Detection: targeted audit readback plus lint/typecheck gates
  * Safe behavior: runtime still uses deterministic code-owned authority
  * Recovery: normalize the affected prompt/skill wording in a follow-up patch

* Failure mode: audit overstates completeness

  * Detection: compare audit conclusions against active file contents directly
  * Safe behavior: keep residual gaps listed until the files are actually fixed
  * Recovery: amend the audit instead of hiding the gap

---

## 10) Observability / Logging

**New/changed events**

* none

**Diagnostics**

* inspect `doc/architecture/skills_source_migration_audit.md`
* inspect active touched `SKILL.md` and prompt/task files

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] [doc/architecture/skills_source_migration_audit.md](/Users/alexander/RPS/doc/architecture/skills_source_migration_audit.md) — close the residual active-layer findings and record the updated conclusion
* [x] [doc/overview/feature_backlog.md](/Users/alexander/RPS/doc/overview/feature_backlog.md) — record Wave-4 slice progress/completion
* [x] [CHANGELOG.md](/Users/alexander/RPS/CHANGELOG.md) — document the active prompt/skill/doc debt cleanup

---

## 12) Link Map (no duplication; links only)

* Architecture: [doc/architecture/system_architecture.md](/Users/alexander/RPS/doc/architecture/system_architecture.md)
* Migration audit: [doc/architecture/skills_source_migration_audit.md](/Users/alexander/RPS/doc/architecture/skills_source_migration_audit.md)
* Feature baseline: [FEAT_active_prompt_policy_migration_completion](/Users/alexander/RPS/doc/specs/features/FEAT_active_prompt_policy_migration_completion.md)
* ADR: [ADR-056-upstream-first-planning-pipeline](/Users/alexander/RPS/doc/adr/ADR-056-upstream-first-planning-pipeline.md)

---

## 13) Implementation Outcome

**Completed in this slice**

* Active Season/Phase planning skills no longer carry the audited undefined variable leftovers:
  * `LR_share` is now defined and source-bound in `skills/season/load-governance/SKILL.md`
  * `CH_kJ` is now defined and source-bound in `skills/phase/cadence-recovery/SKILL.md`
* `skills/shared/durability-methodology/SKILL.md` now carries explicit definitions, authority boundaries, scope, and output expectation.
* Active planner/finalizer/review surfaces now explicitly reject historical migration audits and superseded prose as operative runtime sources.
* `doc/architecture/skills_source_migration_audit.md` now records the closure of the residual active-layer migration gaps instead of leaving them as an open next-pass note.

**Validation completed**

* `python3 -m py_compile $(git ls-files '*.py')`
* `./scripts/run_lint.sh`
* `./scripts/run_typecheck.sh`
