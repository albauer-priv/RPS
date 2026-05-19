---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-19
Owner: Season Planning
---
# FEAT: Season Scenario UX Fields

* **ID:** FEAT_season_scenario_ux_fields
* **Status:** Implemented
* **Owner/Area:** Season Planning / UI / Contracts
* **Last-Updated:** 2026-05-19
* **Related:** [skills/season/scenario-generation/SKILL.md](/skills/season/scenario-generation/SKILL.md), [specs/schemas/season_scenarios.schema.json](/specs/schemas/season_scenarios.schema.json)

---

## 1) Context / Problem

**Current behavior**

* `SEASON_SCENARIOS` already differentiates A/B/C through kJ-first planning logic, cadence, risk profile, and intensity-domain permissions.
* The Season page renders these scenarios mostly through `core_idea`, `load_philosophy`, `risk_profile`, `key_differences`, and `best_suited_if`.

**Problem**

* As user-facing text, the scenarios are still not sharp enough.
* They read as coherent prose, but not yet as immediately graspable choices.
* Users need short practical cues for:
  * what a typical week feels like
  * what they gain
  * what they give up
  * what gets prioritized
  * what gets de-emphasized

**Constraints**

* This is a real artifact-contract change, not only a prompt tweak.
* The new fields must be added to the active schema, normalization path, generated schema-backed Pydantic models, and UI rendering.
* No new dependencies.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Add five user-facing scenario differentiation fields to `SEASON_SCENARIOS`.
* [x] Make these fields required and schema-backed.
* [x] Render them on the Season page so scenario choices become more legible.
* [x] Keep the scenario step kJ-first while improving selection UX.

**Non-Goals**

* [x] Redesign scenario selection flow.
* [x] Change the scenario count or scenario-id contract.

---

## 3) Proposed Behavior

**User/System behavior**

Each scenario now includes five additional required fields:

* `typical_week_feel`
* `main_payoff`
* `main_cost`
* `what_gets_prioritized`
* `what_gets_de_emphasized`

These fields sit on the scenario object itself and are intended for direct user reading on the Season page.

**UI impact**

* UI affected: Yes
* Season page scenario rendering shows the five new user-facing scenario differentiators.

**Non-UI behavior**

* Components involved: schema, normalization, generated artifact models, scenario skill/task guidance, UI rendering, tests
* Contracts touched: `SeasonScenariosInterface`

---

## 4) Implementation Analysis

**Components / Modules**

* `specs/schemas/season_scenarios.schema.json`: add the five required fields.
* `src/rps/agents/output_normalization.py`: preserve and normalize the five fields.
* `skills/season/scenario-generation/SKILL.md`: require the five fields explicitly.
* `config/crewai/tasks.yaml`: sharpen `season_scenarios` task description toward the five user-facing distinctions.
* `src/rps/ui/pages/plan/season.py`: render the five fields.
* `scripts/bundle_schemas.py` + generated models: regenerate bundled schema and schema-backed Pydantic models.

**Data flow**

* Inputs: season-scenario generation output
* Processing: normalization, schema validation, generated model binding, UI rendering
* Outputs: persisted `SEASON_SCENARIOS` payload and clearer scenario UX on the Season page

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: `SEASON_SCENARIOS` schema contract only
* Validator implications: scenario payloads must include all five fields

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: No, contract becomes stricter for newly generated payloads
* Breaking changes: older raw `SEASON_SCENARIOS` payloads without the five fields need normalization defaults to remain valid when re-validated
* Fallback behavior: normalization fills missing fields with safe text defaults

**Conflicts with ADRs / Principles**

* Potential conflicts: none known
* Resolution: the change improves scenario explainability without moving ownership away from the existing scenario step

**Impacted areas**

* UI: Season scenario rendering
* Pipeline/data: season-scenario normalization and schema validation
* Renderer: none beyond Season page markdown block
* Workspace/run-store: persisted scenario documents gain new required fields
* Validation/tooling: schema bundling, generated artifact models, tests
* Deployment/config: none

**Required refactoring**

* Tighten normalization and tests around scenario string fields.

---

## 6) Options & Recommendation

### Option A — Add required UX fields to the scenario contract

**Summary**

* Add the fields to the schema and carry them through runtime and UI.

**Pros**

* User-facing clarity becomes part of the artifact contract
* No prompt-only drift
* UI can rely on the fields

**Cons**

* Makes the contract stricter

**Risk**

* Old payloads need normalization defaults

### Option B — Keep fields only in prompt/UI formatting

**Summary**

* Derive the extra UX labels ad hoc from existing prose.

**Pros**

* No schema change

**Cons**

* Weak and inconsistent
* UI has to infer fields from prose

### Recommendation

* Choose: Option A
* Rationale: these are now part of the product contract, not just writing style.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `season_scenarios.schema.json` requires the five new fields.
* [x] Normalization preserves or backfills the five fields.
* [x] `SeasonScenariosModel` is regenerated from the updated schema.
* [x] Season scenario skill and task mention the five fields explicitly.
* [x] Season page renders the five fields.
* [x] Validation passes: py_compile, lint, typecheck, targeted pytest, schema bundle/model generation.

---

## 8) Migration / Rollout

**Migration strategy**

* No data migration file needed.
* Runtime normalization backfills missing fields for older payloads.

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert schema + normalization + UI change and regenerate models

---

## 9) Risks & Failure Modes

* Failure mode: schema and generated models drift
  * Detection: schema/model tests fail
  * Safe behavior: persisted validation fails before bad writes
  * Recovery: rerun bundling/model-generation and commit regenerated files

* Failure mode: UI still renders only old prose fields
  * Detection: manual Season page smoke or UI tests
  * Safe behavior: artifact remains valid but user benefit is reduced
  * Recovery: update Season page template

---

## 10) Observability / Logging

**New/changed events**

* None

**Diagnostics**

* Use scenario normalization tests, generated-model tests, and Season page rendering inspection.

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] This feature spec
* [x] `CHANGELOG.md` — summarize the new scenario UX fields

---

## 12) Link Map (no duplication; links only)

* [Season scenario kJ-first profiles](/doc/specs/features/FEAT_season_scenario_kj_first_profiles.md)
* [Season intensity authority split](/doc/specs/features/FEAT_season_intensity_domain_authority_split.md)
* [System architecture](/doc/architecture/system_architecture.md)
