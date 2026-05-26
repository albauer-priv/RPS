---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-26
Owner: Planning / Runtime
---
# FEAT: Season Plan Traceability and Guardrail Closure

* **ID:** FEAT_season_plan_traceability_and_guardrail_closure
* **Status:** Implemented
* **Owner/Area:** Planning / Season runtime
* **Last-Updated:** 2026-05-26
* **Related:** FEAT_active_prompt_policy_migration_completion, FEAT_durability_reference_tables

---

## 1) Context / Problem

**Current behavior**

* `SEASON_PLAN` generation is now semantically much more stable.
* The final artifact still had three system-owned gaps:
  * incomplete `trace_data` / `trace_events` for a binding artifact
  * incorrect PubMed links in `principles_scientific_foundation`
  * season-level readiness/taper guardrails not explicit enough in the persisted output and downstream selection layer

**Problem**

* A `Binding` season artifact with `HIGH` confidence must expose the actual authoritative inputs it used.
* Bibliographic errors in the persisted scientific foundation block make evidence-backed documentation unreliable.
* The first Build entry after base/re-entry and taper-week selector semantics must be explicit enough that downstream phases/weeks cannot silently drift into the wrong intent.

**Constraints**

* Objective mismatch remains input-owned and must not be silently healed in planner/review/writer.
* Traceability should be filled from already loaded runtime context, not by guessing later.
* Week selector changes must preserve existing taper-freshening protocol intent and only hard-block the unsafe edge.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Add deterministic season-plan trace enrichment from active runtime input payloads.
* [x] Correct season scientific-foundation PubMed links deterministically.
* [x] Add explicit season-level readiness/taper guardrail language to the final normalized `SEASON_PLAN`.
* [x] Add a hard week-selector block against `SWEET_SPOT_EXTENSIVE` in `taper_freshening`.
* [x] Add targeted tests for the normalization behavior.

**Non-Goals**

* [ ] Rewrite user-owned season objectives automatically.
* [ ] Redesign the full planning-events horizon model in this pass.
* [ ] Rework all historical evidence/principles documents.

---

## 3) Proposed Behavior

**User/System behavior**

* Final `SEASON_PLAN.meta.trace_data` and `trace_events` include the actual season inputs when present:
  * `ATHLETE_PROFILE`
  * `KPI_PROFILE`
  * `AVAILABILITY`
  * `LOGISTICS`
  * `ZONE_MODEL`
  * `PLANNING_EVENTS`
  * while preserving existing historical activity traces when already present
* Season scientific-foundation publication links are corrected deterministically for known canonical references.
* `SEASON_PLAN` explicitly states:
  * first Build entry after shortened/base/re-entry context is readiness-gated
  * taper `LOAD_1` / `LOAD_2` / `RELOAD` are load-band labels only
  * final taper `RELOAD` means event-contained load, not training reload
* Week selector contains an explicit no-selection rule for `SWEET_SPOT_EXTENSIVE` in `taper_freshening`.

**UI impact**

* UI affected: No direct UI change

**Non-UI behavior**

* Components involved:
  * `src/rps/orchestrator/season_flow.py`
  * `src/rps/agents/crewai_backend.py`
  * `config/planning/week_workout_selection_rules.yaml`
  * `tests/test_crewai_runtime.py`
* Contracts touched:
  * final `SEASON_PLAN` meta/data completeness
  * week selector legality in taper context

---

## 4) Implementation Analysis

**Components / Modules**

* Season flow runtime context now binds the season input payloads alongside deterministic season context.
* Final season normalization enriches trace references, canonicalizes publication links, and appends explicit guardrail language.
* Week selector config adds one explicit taper exclusion row.

**Data flow**

* Inputs: latest season input artifacts already loaded in `season_flow`
* Processing:
  * bind payloads into guardrail runtime context
  * merge deterministic trace references into final `SEASON_PLAN.meta`
  * canonicalize scientific-foundation URLs by title
  * append readiness/taper guardrail text
  * hard-block one taper-incompatible protocol variant
* Outputs:
  * more auditable `SEASON_PLAN`
  * stricter taper selector behavior

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts:
  * `SEASON_PLAN` content only, schema unchanged
* Validator implications:
  * same season schema
  * same repo validation commands

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: No schema break
* Fallback behavior:
  * if an input payload is unavailable, existing traces remain and confidence can be reduced conservatively

**Conflicts with ADRs / Principles**

* No ADR conflict identified
* Aligned with upstream-first and binding-artifact traceability rules

**Impacted areas**

* UI: none direct
* Pipeline/data: season runtime context and season artifact normalization
* Renderer: season artifact will render more explicit guardrail text
* Workspace/run-store: no storage format change
* Validation/tooling: targeted tests updated
* Deployment/config: week selector config updated

**Required refactoring**

* no subsystem split
* localized normalization helpers and context binding only

---

## 6) Options & Recommendation

### Option A — Deterministic post-draft closure

**Summary**

* Close traceability, bibliography, and guardrail gaps in deterministic runtime normalization after planner/review output.

**Pros**

* keeps user-owned objective untouched
* uses already loaded authoritative runtime inputs
* avoids re-expanding prompt burden

**Cons**

* season finalizer still emits some content that Python then tightens

### Option B — Push all closure back into prompts

**Summary**

* Require planner/review/writer prompts to fully emit the corrected trace/publication/guardrail details.

**Pros**

* less deterministic post-processing

**Cons**

* weaker auditability
* more prompt fragility
* violates the code-owned authority boundary for trace and canonical references

### Recommendation

* Choose: Option A
* Rationale: traceability and canonical references are system-owned and should close in code.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Final `SEASON_PLAN` trace includes core authoritative season inputs when available.
* [x] Known wrong season-plan publication links are corrected deterministically.
* [x] Final `SEASON_PLAN` carries explicit Build-entry readiness and taper label semantics.
* [x] `SWEET_SPOT_EXTENSIVE` is explicitly blocked in `taper_freshening` selection rules.
* [x] Targeted tests cover normalization and selector guardrails.
* [x] Validation passes: syntax, lint, typecheck, smoke, targeted tests.

---

## 8) Migration / Rollout

**Migration strategy**

* No schema migration required.
* Existing stored season plans remain as historical artifacts; new writes get the stricter normalization.

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert runtime normalization and selector rule changes

---

## 9) Risks & Failure Modes

* Failure mode: missing input payloads still leave traces incomplete
  * Detection: final season artifact lacks expected trace references
  * Safe behavior: keep existing trace references and reduce confidence conservatively if needed
  * Recovery: inspect season-flow input loading and guardrail context binding

* Failure mode: over-broad taper block removes too many legal options
  * Detection: week selector tests or taper week generation drift
  * Safe behavior: explicit block applies only to `SWEET_SPOT_EXTENSIVE`
  * Recovery: narrow/adjust the selector row

---

## 10) Observability / Logging

**New/changed events**

* none required

**Diagnostics**

* inspect final `SEASON_PLAN` trace/publications/guardrails
* inspect targeted test output

---

## 11) Documentation Updates

* [x] `CHANGELOG.md` — add season traceability/guardrail closure note
* [x] `specs/knowledge/_shared/sources/specs/mandatory_output_season_plan.md` — already aligned previously on season-plan references; no schema change required in this pass

---

## 12) Link Map (no duplication; links only)

* `doc/architecture/system_architecture.md`
* `doc/architecture/skills_source_migration_audit.md`
* `doc/specs/features/FEAT_upstream_first_planning_pipeline.md`
* `specs/knowledge/_shared/sources/specs/mandatory_output_season_plan.md`
