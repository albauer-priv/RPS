---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-26
Owner: Skills
---
# FEAT: Curated Durability Reference Tables

* **ID:** FEAT_durability_reference_tables
* **Status:** Implemented
* **Owner/Area:** Skills / Shared durability-methodology
* **Last-Updated:** 2026-05-26
* **Related:** FEAT_active_prompt_policy_migration_completion, FEAT_workout_policy_skill_completion

---

## 1) Context / Problem

**Current behavior**

* The repo already contains broad durability bibliographies under `specs/knowledge/_shared/sources/evidence/` and `skills/shared/durability-methodology/references/`.
* Those bibliographies mix peer-reviewed studies, books, podcasts, blogs, and practitioner media in one long thematic list.

**Problem**

* Active skills do not get a clean distinction between high-authority research references and practice/media references.
* Agents can over-read mixed bibliography entries as if they were equally authoritative.
* The existing bibliography is a good seed source but not a strong operational lookup table.

**Constraints**

* No web-dependent rebuild for this pass.
* Use existing local bibliography sources as the primary seed.
* Keep the old bibliography as archive/seed rather than deleting it.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Add a curated core reference table for peer-reviewed / DOI / PubMed-near sources.
* [x] Add a separate applied reference table for practitioner/media sources.
* [x] Give both tables one consistent schema for agent lookup.
* [x] Repoint the shared durability skill to the new tables as primary references.
* [x] Keep the old bibliography as archive/seed only.

**Non-Goals**

* [ ] Exhaustively normalize every evidence-oriented document in the repo.
* [ ] Add live-verified DOI/PMID coverage for every legacy bibliography entry.

---

## 3) Proposed Behavior

**User/System behavior**

* Shared durability/planning skills should consult a compact core reference table first.
* If the skill needs implementation/practice framing, it should consult a separate applied table.
* The old bibliography remains available for expansion, but is no longer the primary operative reference.

**UI impact**

* UI affected: No

**Non-UI behavior**

* Components involved:
  * `skills/shared/durability-methodology/SKILL.md`
  * `skills/shared/durability-methodology/references/*`
  * `specs/knowledge/_shared/sources/evidence/durability_bibliography.md`

* Contracts touched:
  * local skill reference conventions only

---

## 4) Implementation Analysis

**Components / Modules**

* Shared durability skill: update evidence-use boundary and reference priority.
* Shared references: add two new markdown tables with a fixed schema.
* Legacy bibliography: add a short archival/seed note.

**Data flow**

* Inputs: existing local durability bibliography entries
* Processing: curate into core vs applied tables with authority limits
* Outputs: two new agent-usable reference tables

**Schema / Artefacts**

* New artefacts:
  * `durability_reference_table_core.md`
  * `durability_reference_table_applied.md`
* Changed artefacts:
  * `skills/shared/durability-methodology/SKILL.md`
  * old bibliography headers

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: None in runtime contracts
* Fallback behavior: old bibliography remains available as archive/seed

**Conflicts with ADRs / Principles**

* No ADR conflict identified

**Impacted areas**

* UI: none
* Pipeline/data: none
* Renderer: none
* Workspace/run-store: none
* Validation/tooling: none
* Deployment/config: none

**Required refactoring**

* none beyond reference/skill text changes

---

## 6) Options & Recommendation

### Option A — Two-tier curated tables

**Summary**

* Separate high-authority and practice/media sources while preserving a shared schema.

**Pros**

* Clearer agent authority boundaries
* Better reuse in planning/coaching skills
* Keeps the old bibliography as a seed source

**Cons**

* Requires curation effort
* Does not fully normalize every repo bibliography copy

### Option B — Keep one mixed bibliography

**Summary**

* Leave the current list as-is and add usage notes only.

**Pros**

* Minimal editing

**Cons**

* Still mixes source authority
* Weak lookup behavior for agents

### Recommendation

* Choose: Option A
* Rationale: it gives agents a usable operational lookup without losing the breadth of the seed bibliography.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] A core reference table exists under `skills/shared/durability-methodology/references/`
* [x] An applied reference table exists under the same folder
* [x] Both tables use the same fixed columns
* [x] The shared durability skill explicitly prioritizes core -> applied -> old bibliography
* [x] Active prompts and adjacent skills that explain durability-first decisions use the same reference priority
* [x] `factual_evidence` injects the curated tables ahead of the archive bibliography
* [x] Runtime coach guidance and runtime tests align with the curated reference priority
* [x] Direct operative spec examples no longer point at the archive bibliography when a curated lookup table is available
* [x] The old bibliography is marked as archive/seed rather than primary operative lookup
* [x] Validation passes: syntax, lint, typecheck, relevant smoke run

---

## 8) Migration / Rollout

**Migration strategy**

* No schema migration required
* Reference-first rollout; old bibliography remains in place

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert reference-file and skill-text changes

---

## 9) Risks & Failure Modes

* Failure mode: mixed-authority sources still used as if equal
  * Detection: skill text still points to old bibliography first
  * Safe behavior: core table remains the first declared authority
  * Recovery: tighten skill guidance further

* Failure mode: missing locator values in table rows
  * Detection: static review of required columns
  * Safe behavior: use `none` explicitly
  * Recovery: fill missing identifiers later from vetted sources

---

## 10) Observability / Logging

**New/changed events**

* none

**Diagnostics**

* inspect the shared skill and the new reference tables directly

---

## 11) Documentation Updates

* [x] `skills/shared/durability-methodology/SKILL.md` — reference priority and usage boundary
* [x] `skills/conversation/guarded-operations/SKILL.md` — aligned evidence priority
* [x] `skills/week/recommendation-and-adjustment/SKILL.md` — aligned evidence priority
* [x] `prompts/agents/week_recommendation_specialist.md` — aligned evidence priority
* [x] `prompts/agents/coach.md` — aligned evidence priority
* [x] `config/crewai/knowledge_sources.yaml` — curated tables injected in `factual_evidence`
* [x] `src/rps/crewai_runtime/coach_chat.py` — runtime coach evidence priority aligned
* [x] `tests/test_crewai_runtime.py` — evidence reference tests aligned
* [x] `specs/knowledge/_shared/sources/specs/mandatory_output_season_plan.md` — example citation target moved off archive bibliography
* [x] `doc/architecture/agents.md` — factual evidence bundle description updated
* [x] `skills/shared/durability-methodology/references/durability_bibliography.md` — archive/seed note
* [x] `specs/knowledge/_shared/sources/evidence/durability_bibliography.md` — archive/seed note
* [x] `CHANGELOG.md` — note the new curated reference tables

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* Skills source audit: `doc/architecture/skills_source_migration_audit.md`
* Shared durability skill: `skills/shared/durability-methodology/SKILL.md`
