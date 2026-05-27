---
Version: 1.1
Status: Implemented
Last-Updated: 2026-05-27
Owner: Skills
---
# FEAT: Curated Durability Reference Tables

* **ID:** FEAT_durability_reference_tables
* **Status:** Implemented
* **Owner/Area:** Skills / Shared durability-methodology
* **Last-Updated:** 2026-05-27
* **Related:** FEAT_active_prompt_policy_migration_completion, FEAT_workout_policy_skill_completion

---

## Historical Position

This document remains useful as the **initial table/library migration step**, but
it is no longer the sole canonical description of the evidence runtime.

Read the following as the current canonical follow-on docs:

- `doc/specs/features/FEAT_repo_wide_evidence_library_and_refresh.md`
- `doc/specs/features/FEAT_evidence_curation_pipeline.md`

This file should now be interpreted as:
- the step that separated `core` and `applied` evidence tables
- the step that decommissioned mixed bibliography files as operative inputs
- not the final description of evidence discovery, curation, gating, or activation

---

## 1) Context / Problem

**Current behavior**

* The repo now carries a canonical local evidence library plus generated reference tables, while older bibliography files remain only as decommission markers.
* Earlier broad bibliographies mixed peer-reviewed studies, books, podcasts, blogs, and practitioner media in one long thematic list.

**Problem**

* Active skills do not get a clean distinction between high-authority research references and practice/media references.
* Agents can over-read mixed bibliography entries as if they were equally authoritative.
* The existing bibliography is a useful historical seed but not an acceptable operational lookup table.

**Constraints**

* No web-dependent rebuild for this pass.
* Use existing local bibliography sources as the primary seed.
* Fully decommission old bibliography files as operative inputs while preserving compatibility markers where needed.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Add a curated core reference table for peer-reviewed / DOI / PubMed-near sources.
* [x] Add a separate applied reference table for practitioner/media sources.
* [x] Give both tables one consistent schema for agent lookup.
* [x] Repoint the shared durability skill to the canonical local evidence library and generated tables as primary references.
* [x] Decommission the old bibliography as an operative source.

**Non-Goals**

* [ ] Exhaustively normalize every evidence-oriented document in the repo.
* [ ] Add live-verified DOI/PMID coverage for every legacy bibliography entry.

---

## 3) Proposed Behavior

**User/System behavior**

* Shared durability/planning skills should consult a compact core reference table first.
* If the skill needs implementation/practice framing, it should consult a separate applied table.
* Decommissioned bibliography files remain only as compatibility/history markers and are no longer operative references.

**UI impact**

* UI affected: No

**Non-UI behavior**

* Components involved:
  * `skills/shared/durability-methodology/SKILL.md`
  * `skills/shared/durability-methodology/references/*`
* `skills/shared/durability-methodology/references/evidence_library_manifest.md`

* Contracts touched:
  * local skill reference conventions only

---

## 4) Implementation Analysis

**Components / Modules**

* Shared durability skill: update evidence-use boundary and reference priority.
* Shared references: add a structured local library plus generated markdown tables.
* Legacy bibliography: replace with a decommission note.

**Data flow**

* Inputs: existing local durability bibliography entries and curated verified locator data
* Processing: normalize into canonical core/applied library data with authority limits and generated views
* Outputs: canonical library plus agent-usable generated reference tables

**Schema / Artefacts**

* New artefacts:
* `library/core_studies.yaml`
* `library/applied_sources.yaml`
* `durability_reference_table_core.md`
* `durability_reference_table_applied.md`
* Changed artefacts:
  * `skills/shared/durability-methodology/SKILL.md`
* decommissioned bibliography/manifest markers

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: None in runtime contracts
* Fallback behavior: decommissioned files remain as compatibility markers, but not active lookup inputs

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
* Keeps historical context while removing it from the operative path

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
* [x] The shared durability skill explicitly prioritizes the canonical local evidence library and generated tables
* [x] Active prompts and adjacent skills that explain durability-first decisions use the same reference priority
* [x] `factual_evidence` injects the evidence manifest and generated tables only
* [x] Runtime coach guidance and runtime tests align with the curated reference priority
* [x] Direct operative spec examples no longer point at decommissioned bibliography files
* [x] The old bibliography is marked as decommissioned rather than primary operative lookup
* [x] Validation passes: syntax, lint, typecheck, relevant smoke run

---

## 8) Migration / Rollout

**Migration strategy**

* No schema migration required
* Reference-first rollout; legacy bibliography files remain only as decommission markers

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert reference-file and skill-text changes

---

## 9) Risks & Failure Modes

* Failure mode: mixed-authority sources still used as if equal
  * Detection: skill text still points to decommissioned bibliography files or free-web lookup
  * Safe behavior: canonical library remains the first declared authority
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
* [x] decommissioned bibliography/manifest markers updated
* [x] `CHANGELOG.md` — note the new curated reference tables

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* Skills source audit: `doc/architecture/skills_source_migration_audit.md`
* Shared durability skill: `skills/shared/durability-methodology/SKILL.md`
