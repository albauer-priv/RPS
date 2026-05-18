---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-18
Owner: Planning
---
# FEAT: Merge Endurance Intensity Domains

* **ID:** FEAT_merge_endurance_intensity_domains
* **Status:** Implemented
* **Owner/Area:** Planning / Schemas / Skills
* **Last-Updated:** 2026-05-18
* **Related:** `specs/schemas/agenda_enum.schema.json`, `skills/shared/load-estimation-core/SKILL.md`

---

## 1) Context / Problem

**Current behavior**

* Intensity domains previously distinguished low and high endurance variants.
* Load estimation assigns different defaults to those two domains.

**Problem**

* The two endurance domains create avoidable prompt/schema complexity for planning and workout authoring.

**Constraints**

* Existing day role `ENDURANCE` remains unchanged.
* No new dependencies.
* Bundled schemas and generated artifact models must be regenerated.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Replace the split endurance intensity variants with one canonical intensity domain: `ENDURANCE`.
* [x] Set the new `ENDURANCE` load-estimation IF default to the former high-endurance value `0.70`.
* [x] Update schemas, skills, specs, tests, and bundled schema outputs.

**Non-Goals**

* [x] No change to day-role semantics.
* [x] No change to non-endurance domains such as `TEMPO`, `SWEET_SPOT`, `THRESHOLD`, or `VO2MAX`.

---

## 3) Proposed Behavior

**User/System behavior**

* Planning and workout artefacts use `ENDURANCE` as the only endurance intensity domain.
* Legacy split endurance-domain input is normalized to `ENDURANCE` at runtime where normalization exists.

**UI impact**

* UI affected: No

**Non-UI behavior**

* Components involved: schemas, schema bundles, load estimation, workout-load estimation, skills, tests.
* Contracts touched: agenda intensity-domain enum and all schemas that reference it.

---

## 4) Implementation Analysis

**Components / Modules**

* `specs/schemas/agenda_enum.schema.json`: remove split endurance domains.
* `src/rps/planning/load_bands.py`: set `ENDURANCE=0.70`.
* `src/rps/workspace/intensity_domains.py`: normalize split legacy labels to `ENDURANCE`.
* Skills/specs/templates/tests: update domain labels.

**Schema / Artefacts**

* New artefacts: none.
* Changed artefacts: schemas accept `ENDURANCE` only for endurance intensity.
* Validator implications: existing old artefacts with split endurance labels need normalization before new writes.

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible: Partially.
* Breaking changes: raw old artefacts containing split endurance-domain labels no longer validate unless normalized.
* Fallback behavior: runtime normalization maps both legacy split labels to `ENDURANCE`.

**Impacted areas**

* Validation/tooling: schema bundle and generated models regenerated.
* Planning/data: deterministic load defaults use `ENDURANCE=0.70`.

---

## 6) Options & Recommendation

### Option A — Merge to `ENDURANCE`

**Summary**

* Collapse both endurance domains into one canonical enum.

**Pros**

* Simpler schema, prompts, skills, and planner decisions.

**Cons**

* Requires migration/normalization for old artefacts.

### Recommendation

* Choose: Option A
* Rationale: User explicitly wants one endurance domain and the former high value as the default.

---

## 7) Acceptance Criteria

* [x] No split endurance-domain labels remain in active source, schema, skill, prompt, or test files except the explicit legacy alias map.
* [x] `ENDURANCE` IF default is `0.70`.
* [x] Schema bundle and generated artifact models are regenerated.
* [x] Validation passes: schema checks, syntax, lint, typecheck, pytest, CLI smoke.

---

## 8) Migration / Rollout

**Migration strategy**

* Runtime normalization treats old split endurance domain labels as `ENDURANCE`.

**Rollout / gating**

* Feature flag / config: none.
* Safe rollback: restore split enum and IF defaults.

---

## 9) Risks & Failure Modes

* Failure mode: old persisted artefacts fail direct schema validation.
  * Detection: schema validation errors mentioning legacy split endurance-domain labels.
  * Safe behavior: normalize through runtime write/load paths before persistence.

---

## 10) Observability / Logging

**New/changed events**

* None.

**Diagnostics**

* Schema validation output and guarded-store failure reason.

---

## 11) Documentation Updates

* [x] Update relevant skills/specs/templates containing split endurance domains.
