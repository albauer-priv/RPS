---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-14
Owner: Planning Runtime
---
# FEAT: Single-Method Skill Model for CrewAI Planning

* **ID:** FEAT_skills_source_partition_single_method_skill_model
* **Status:** Implemented
* **Owner/Area:** CrewAI Runtime / Planning Knowledge
* **Last-Updated:** 2026-05-14
* **Related:** `ADR-049-single-method-skill-attachment.md`, `ADR-047-crewai-skills-unified-planning.md`, `ADR-048-skills-first-multi-crew-planning-runtime.md`

---

## 1) Context / Problem

**Current behavior**

* Agents receive multiple skill bundles, and bundles may expand to several skills.
* Important planning knowledge still lives mainly in `specs/knowledge/_shared/sources/` while many `SKILL.md` files remain thin wrappers.
* The runtime prompt compatibility layer injects `SKILL.md` content only, which weakens `references/` as an effective methodology source.

**Problem**

* The effective planning method per agent is ambiguous.
* Agents can mix cross-domain knowledge and multiple method packages.
* Real planning logic is still split between prompts, thin skills, and legacy prose specs.

**Constraints**

* CrewAI technically supports multiple skills on both agents and crews.
* RPS should adopt a stricter local rule for maintainability.
* No change should break current Season/Phase/Week/Coach/Report task routing.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Enforce exactly one method skill per agent.
* [x] Restrict crew-level skills to cross-cutting operational guidance only.
* [x] Move substantive planning methodology from legacy prose specs into skill packages and references.
* [x] Make the skill compatibility layer inject both `SKILL.md` and `references/` content.
* [x] Keep current planning/review/writer crew topology working with the stricter skill policy.

**Non-Goals**

* [ ] Full redesign of every planning task or output model.
* [ ] Removal of all legacy planning prose files in this change.

---

## 3) Proposed Behavior

**User/System behavior**

* Every agent now resolves to one canonical method skill package.
* Every crew may attach only operational cross-cutting skills.
* Methodology is owned by skills, not by broad bundle composition or prompt-local duplication.
* The runtime injects active skill summaries together with their local reference material into task prompts.

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved: CrewAI skill config, runtime config validation, runtime skill prompt rendering, planning skill packages.
* Contracts touched: `config/crewai/skills.yaml`, planning skill-package layout under `skills/`.

---

## 4) Implementation Analysis

**Components / Modules**

* `config/crewai/skills.yaml`: replace bundle-driven method composition with `crews.<crew>.skills` and `agents.<agent>.skill`.
* `src/rps/crewai_runtime/config.py`: validate one method skill per agent and crew-level operational allowlist.
* `src/rps/crewai_runtime/skills.py`: resolve crew-level operational skills plus one agent method skill; render references in compatibility prompts.
* `skills/**`: enrich existing method skills and add missing single-role packages.

**Data flow**

* Inputs: existing agent/task config, active crew name, active agent name, skill package files.
* Processing: validate config -> resolve operational crew skills -> append one agent method skill -> render `SKILL.md` plus `references/`.
* Outputs: deterministic active skill profile per agent, compatible prompt block, unchanged task outputs.

**Schema / Artefacts**

* No artifact schema change.
* Skill config shape changes.
* No workspace migration.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: No, for `config/crewai/skills.yaml` structure.
* Breaking changes: bundle-style multi-skill composition is removed from skills config.
* Fallback behavior: config load fails fast when an agent resolves to more than one method skill or when a crew attaches a non-operational skill.

**Conflicts with ADRs / Principles**

* Refines ADR-047 by tightening attachment semantics.
* Refines ADR-048 by making skills more executable and less bundle-driven.

**Impacted areas**

* UI: none directly.
* Pipeline/data: none directly.
* Renderer: none.
* Workspace/run-store: none.
* Validation/tooling: CrewAI config validation and runtime tests.
* Deployment/config: `skills.yaml` becomes stricter.

**Required refactoring**

* Replace bundle-based skill resolution.
* Add missing single-role skills for managers/reviewers/week syntax and constraint roles.
* Enrich thin skills with operational method content.

---

## 6) Options & Recommendation

### Option A — strict one-method-skill-per-agent

**Summary**

* Each agent gets one method skill, crews get operational skills only.

**Pros**

* Clear ownership.
* Easier debugging.
* Prevents quiet cross-domain drift.

**Cons**

* More skill packages.
* Some manager/review roles need dedicated synthesis/review skills.

**Risk**

* If skills stay thin, the stricter split alone would not help. This change therefore also deepens the method skills.

### Option B — keep multi-skill composition, just document it better

**Summary**

* Keep current bundles and rely on discipline.

**Pros**

* Less config churn.

**Cons**

* Preserves the current ambiguity.
* Does not solve the methodology fragmentation problem.

### Recommendation

* Choose: Option A
* Rationale: the repo already showed that multi-bundle composition hides where method authority actually lives.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `skills.yaml` resolves one method skill per agent.
* [x] Crew-level attachments are restricted to operational skills.
* [x] Runtime validation fails on multi-method or invalid crew-level attachments.
* [x] Key planning knowledge from durability, load-estimation, and workout syntax/policy specs is present in skills and references.
* [x] Compatibility prompt rendering includes both `SKILL.md` and local reference material.
* [x] Validation passes: `py_compile`, lint, typecheck, targeted CrewAI runtime tests, full pytest.

---

## 8) Migration / Rollout

**Migration strategy**

* Replace the old skills bundle structure in one cut.
* Keep legacy prose specs as source material for now, but they are no longer the intended runtime methodology source.

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert `skills.yaml`, runtime skill resolver, and new skill packages together.

---

## 9) Risks & Failure Modes

* Failure mode: method knowledge still too thin in a single skill.
  * Detection: weak planning outputs or runtime tests relying on skill prompt content fail.
  * Safe behavior: fail config/tests rather than silently allowing multi-skill fallback.
  * Recovery: enrich the affected skill package instead of reintroducing composition.

* Failure mode: crew-level method skills slip back in.
  * Detection: config validation error.
  * Safe behavior: startup/runtime construction fails fast.
  * Recovery: move method content into the owning agent skill.

---

## 10) Observability / Logging

**New/changed events**

* No new telemetry events.
* Skill prompt rendering now reflects richer active skill payloads in debug-visible task descriptions.

**Diagnostics**

* Primary diagnostics: CrewAI config validation failures and `tests/test_crewai_runtime.py`.

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] `doc/adr/ADR-049-single-method-skill-attachment.md` — local attachment rule.
* [x] `CHANGELOG.md` — summarize single-method skill cutover.
* [x] `config/crewai/skills.yaml` — canonical attachment model.
