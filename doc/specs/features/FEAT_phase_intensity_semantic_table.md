---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-19
Owner: Season and Phase Planning
---
# FEAT: Phase Intensity Semantic Table

* **ID:** FEAT_phase_intensity_semantic_table
* **Status:** Implemented
* **Owner/Area:** Season and Phase Planning
* **Last-Updated:** 2026-05-19
* **Related:** [skills/season/plan-synthesis/SKILL.md](/skills/season/plan-synthesis/SKILL.md), [skills/phase/intensity-distribution/SKILL.md](/skills/phase/intensity-distribution/SKILL.md)

---

## 1) Context / Problem

**Current behavior**

* Season and Phase skills already encode durability-first intensity logic in prose.
* The repo uses schema-valid cycles `Base`, `Build`, `Peak`, and `Transition`, while finer phase semantics are expressed through phase role, phase intent, and season phase role.

**Problem**

* The active skills do not contain one compact, repo-aligned table that maps cycle/phase intent to allowed domains, optional domains, avoid domains, and modality notes.
* Without an explicit table in the `SKILL.md` bodies, planners can drift toward ad hoc interpretations of `Transition`, late `Build`, `Peak`, rehearsal, and taper semantics.

**Constraints**

* No schema changes.
* No new dependencies.
* The table must use active repo terminology and must live in `SKILL.md`, not only in detached references.
* `K3` remains a load modality, not an intensity-domain enum.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Add a repo-compatible phase-intensity table directly to the active Season and Phase skills.
* [x] Keep the table aligned with schema-valid cycles and existing season-phase role semantics.
* [x] Make the authority flow explicit: scenario domains -> phase domains -> week execution domains.

**Non-Goals**

* [x] Introduce new schema cycle enums such as `Specificity` or `Taper`.
* [x] Add new persisted artifact fields for phase semantics.

---

## 3) Proposed Behavior

**User/System behavior**

* `season_planner` and `phase_architect` consume a shared semantic table embedded directly in their active skills.
* The table uses existing cycles plus repo-aligned phase intent labels such as `shortened_re_entry`, `transition_consolidation`, `b_event_rehearsal`, `peak_preparation`, and `a_event_peak_taper`.
* The table distinguishes:
  * allowed intensity domains
  * optional/conditional domains
  * default avoid domains
  * allowed load modalities
  * semantic notes

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved: Season skill text, Phase skill text, tests
* Contracts touched: runtime planning-skill contract only

---

## 4) Implementation Analysis

**Components / Modules**

* `skills/season/plan-synthesis/SKILL.md`: embed the table as season-level phase-intent guidance.
* `skills/phase/intensity-distribution/SKILL.md`: embed the same table as phase-level intensity-shaping guidance.
* `tests/test_season_semantic_hardening.py`: assert that the table and its key guardrails remain present.

**Data flow**

* Inputs: selected scenario, deterministic season context, phase role, event timing, recovery state
* Processing: skills interpret allowed/narrowed semantics through the embedded table
* Outputs: more stable season and phase narrative/blueprint intensity semantics

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: skill-content regression checks only

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none
* Fallback behavior: existing skill prose still applies if a downstream consumer ignores the new table

**Conflicts with ADRs / Principles**

* Potential conflicts: none known
* Resolution: table reinforces existing durability-first and schema-valid cycle rules

**Impacted areas**

* UI: none
* Pipeline/data: none
* Renderer: none
* Workspace/run-store: none
* Validation/tooling: adds a regression assertion for active skill semantics
* Deployment/config: none

**Required refactoring**

* Normalize the phase taxonomy to active repo terms inside the skills.

---

## 6) Options & Recommendation

### Option A — Embed the table directly in both active skills

**Summary**

* Put the same repo-aligned phase-intensity table into the Season and Phase `SKILL.md` bodies.

**Pros**

* Matches runtime skill loading rules exactly
* Keeps the operational rule next to the instructions the agent actually receives
* Avoids hidden reference indirection

**Cons**

* Duplicates a compact table across two skills

**Risk**

* Future edits could drift if one skill is changed without the other

### Option B — Keep the table only in references

**Summary**

* Put the table into a local `references/` file and mention it briefly in the skill body.

**Pros**

* Less duplication

**Cons**

* Weaker guarantee that the skill really "has" the rule during runtime
* Conflicts with the repo requirement that the essential rule must be present in `SKILL.md`

### Recommendation

* Choose: Option A
* Rationale: this is operational guidance, so it belongs directly in the active skill text.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `skills/season/plan-synthesis/SKILL.md` contains a repo-aligned phase-intensity table.
* [x] `skills/phase/intensity-distribution/SKILL.md` contains the same repo-aligned phase-intensity table.
* [x] The table uses only schema-valid cycles and repo-aligned phase-intent semantics.
* [x] The table keeps `K3` only under load modalities.
* [x] Tests assert the new table/authority wording remains present.
* [x] Validation passes: py_compile, lint, typecheck, targeted pytest, relevant smoke run.

---

## 8) Migration / Rollout

**Migration strategy**

* None

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert the skill-table additions and test

---

## 9) Risks & Failure Modes

* Failure mode: Season and Phase skills drift to different table semantics
  * Detection: regression test and code review
  * Safe behavior: runtime still has at least one table, but planning may become inconsistent
  * Recovery: resync the two skill tables

* Failure mode: the table introduces non-repo phase labels as if they were schema enums
  * Detection: skill review and planning-output audit
  * Safe behavior: no schema break, but semantics become ambiguous
  * Recovery: keep labels explicitly framed as phase intent inside schema-valid cycles

---

## 10) Observability / Logging

**New/changed events**

* None

**Diagnostics**

* Use `tests/test_season_semantic_hardening.py` as the primary regression check for this skill content.

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] This feature spec
* [x] `CHANGELOG.md` — add a note about the embedded phase-intensity table

---

## 12) Link Map (no duplication; links only)

* [System architecture](/doc/architecture/system_architecture.md)
* [Artefact flow](/doc/overview/artefact_flow.md)
* [Season plan semantic hardening](/doc/specs/features/FEAT_season_plan_semantic_hardening.md)
* [Season scenario kJ-first profiles](/doc/specs/features/FEAT_season_scenario_kj_first_profiles.md)
