---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-17
Owner: CrewAI Runtime
---
# FEAT: Native CrewAI Skill Activation

* **ID:** FEAT_native_crewai_skill_activation
* **Status:** Implemented
* **Owner/Area:** CrewAI Runtime
* **Last-Updated:** 2026-05-17
* **Related:** `doc/architecture/crewai_skills_attachment.md`, `config/crewai/skills.yaml`

---

## 1) Context / Problem

**Current behavior**

* RPS passes repo-local skill directories to CrewAI through `skills=[...]`.
* Some runtime paths also manually rendered the same `SKILL.md` bodies into agent goals, backstories, or task descriptions.
* A few `SKILL.md` files referenced `references/` files in other skill directories.

**Problem**

* Native CrewAI activation already injects the full `SKILL.md` body.
* Manual prompt rendering in parallel can duplicate instructions and makes RPS diverge from CrewAI's skill model.
* Cross-skill reference paths break the self-contained skill-package expectation.

**Constraints**

* Binding methodology remains in `SKILL.md`.
* `references/` are local supplemental files on the owning skill path and are not treated as automatic prompt context.
* No artifact schema changes.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Use native CrewAI `skills=[...]` as the only skill activation path.
* [x] Remove manual `SKILL.md` body rendering from active runtime prompts.
* [x] Ensure `SKILL.md` reference paths are local to their own skill directory.
* [x] Add tests that prevent cross-skill references and manual skill injection from returning.

**Non-Goals**

* [x] No fallback prompt-rendered skill path.
* [x] No change to CrewAI knowledge-source retrieval.
* [x] No new tools.

---

## 3) Proposed Behavior

**User/System behavior**

* Agents receive skills via CrewAI's native skill activation.
* RPS does not duplicate `SKILL.md` bodies into `goal`, `backstory`, or task descriptions.
* Skill references are self-contained and local.

**UI impact**

* UI affected: No.

**Non-UI behavior**

* Components involved: `src/rps/crewai_runtime/skills.py`, `src/rps/agents/crewai_backend.py`, `src/rps/crewai_runtime/coach_chat.py`, skill packages, architecture docs, tests.
* Contracts touched: none.

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/crewai_runtime/skills.py`: native skill kwargs only.
* `src/rps/agents/crewai_backend.py`: no manual skill prompt append.
* `src/rps/crewai_runtime/coach_chat.py`: no manual skill prompt append.
* `skills/**/references`: local copies for referenced material.
* `tests/test_skill_references.py`: self-contained skill package validation.

**Data flow**

* Inputs: `config/crewai/skills.yaml`.
* Processing: resolve skill directories and pass absolute paths to CrewAI.
* Outputs: CrewAI agents/tasks with native skill activation.

**Schema / Artefacts**

* New artefacts: none.
* Changed artefacts: none.
* Validator implications: skill reference test added.

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible: Yes for persisted artifacts.
* Breaking changes: prompt construction no longer contains duplicated rendered skill bodies.
* Fallback behavior: none; native CrewAI skill activation is required.

**Conflicts with ADRs / Principles**

* Potential conflicts: older feature docs described compatibility prompt rendering.
* Resolution: updated docs to make native CrewAI skill activation the target.

**Impacted areas**

* UI: none.
* Pipeline/data: none.
* Renderer: none.
* Workspace/run-store: none.
* Validation/tooling: new skill self-containment tests.
* Deployment/config: requires CrewAI skill support.

**Required refactoring**

* Remove manual skill prompt block rendering calls.
* Repair cross-skill reference paths.

---

## 6) Options & Recommendation

### Option A (recommended) — Native Skill Activation Only

**Summary**

* Pass skill directories to CrewAI and remove manual prompt rendering.

**Pros**

* Aligns with CrewAI documentation.
* Avoids duplicate instructions.
* Keeps skill packages self-contained.

**Cons**

* Requires native CrewAI skill behavior to be available in runtime.

**Risk**

* If CrewAI skill activation changes upstream, RPS relies on that native behavior.

### Option B — Native Plus Fallback Prompt Rendering

**Summary**

* Keep manual skill body rendering as a compatibility path.

**Pros**

* More tolerant of partial CrewAI compatibility.

**Cons**

* Duplicates instructions and diverges from CrewAI's skill-first model.

### Recommendation

* Choose: Option A.
* Rationale: RPS should use CrewAI features directly where available and avoid maintaining a parallel skill-injection layer.

---

## 7) Acceptance Criteria

* [x] No active runtime call to `render_skill_prompt_block`.
* [x] No cross-skill `SKILL.md` reference paths.
* [x] All `references/...` paths in `SKILL.md` files are local and exist.
* [x] Tests cover skill directory/name matching and local references.
* [x] Validation passes: syntax, lint, typecheck, tests, smoke.

---

## 8) Migration / Rollout

**Migration strategy**

* No data migration.

**Rollout / gating**

* No feature flag. Native CrewAI skill activation is the runtime contract.

---

## 9) Risks & Failure Modes

* Failure mode: CrewAI does not activate provided skills.
  * Detection: skill behavior absent in planning output or runtime tests against CrewAI object kwargs.
  * Safe behavior: fail tests; do not reintroduce manual prompt injection.
  * Recovery: fix CrewAI skill configuration or upstream integration.

* Failure mode: a skill refers to missing local reference material.
  * Detection: `tests/test_skill_references.py`.
  * Safe behavior: block merge.
  * Recovery: copy the reference locally or remove the pointer.

---

## 10) Observability / Logging

**New/changed events**

* None.

**Diagnostics**

* Inspect CrewAI agent kwargs for `skills`.
* Use tests to verify no manual prompt-rendered skill blocks are present.

---

## 11) Documentation Updates

* [x] `doc/architecture/crewai_skills_attachment.md` — document native-only activation and local references.
* [x] `doc/specs/features/FEAT_crewai_skills_unified_planning_cutover.md` — remove compatibility-rendering language.
* [x] `CHANGELOG.md` — record runtime cleanup.

---

## 12) Link Map

* `config/crewai/skills.yaml`
* `src/rps/crewai_runtime/skills.py`
* `src/rps/agents/crewai_backend.py`
* `src/rps/crewai_runtime/coach_chat.py`
* `doc/architecture/crewai_skills_attachment.md`
