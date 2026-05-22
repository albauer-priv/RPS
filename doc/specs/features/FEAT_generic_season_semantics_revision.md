---
Version: 1.0
Status: Approved
Last-Updated: 2026-05-22
Owner: Season Planning
---
# FEAT: Generic Season Semantics Revision

* **ID:** FEAT_generic_season_semantics_revision
* **Status:** Approved
* **Owner/Area:** Season Planning
* **Last-Updated:** 2026-05-22
* **Related:** [FEAT_season_plan_semantic_hardening](/doc/specs/features/FEAT_season_plan_semantic_hardening.md), [FEAT_phase_intent_semantic_backbone](/doc/specs/features/FEAT_phase_intent_semantic_backbone.md), [ADR-053](/doc/adr/ADR-053-canonical-phase-taxonomy-and-build-subtypes.md)

---

## 1) Context / Problem

**Current behavior**

* Season planning already uses canonical `phase_type`, `phase_intent`, and `build_subtype`.
* Deterministic phase load context already computes role-week load bands and event taper traces.
* Final `SEASON_PLAN` artifacts still drift semantically in four places:
  * `RECOVERY` is not treated consistently as a legal active-recovery domain.
  * `allowed_load_modalities` can collapse to `["K3"]`, making K3 look mandatory.
  * `events_constraints` can contain synthetic “no event” placeholders instead of real events only.
  * role-week guardrails are structurally present upstream but not always made visible in the final season artifact.

**Problem**

* Downstream Phase/Week planning can receive semantically misleading season authority.
* Human auditability is weaker than the deterministic context that already exists.
* Objective vs A-event mismatches need to be surfaced without blocking planning, because the user owns the correction.

**Constraints**

* No structural schema-field change for `SeasonPlanInterface` in this pass.
* Canonical semantics must be generic and must not depend on one concrete season instance.
* Objective/A-event mismatch detection is downstream-visible but must not block finalization.
* Structured deterministic role-week bands remain the validation source of truth; text rendering is secondary.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Open `RECOVERY` as a canonical non-quality domain across the full phase taxonomy unless explicitly overridden.
* [x] Derive `allowed_load_modalities` from canonical phase semantics instead of prompt drift.
* [x] Serialize only real planning events in `season_plan.data.phases[].events_constraints`.
* [x] Materialize deterministic role-week guardrails visibly in `SEASON_PLAN` without turning them into week prescriptions.
* [x] Add objective/A-event mismatch detection as a visible warning in the plan, not as a blocker.
* [x] Ensure taper validation distinguishes pre-event training load from event-week total load.

**Non-Goals**

* [x] Automatically rewrite user objectives to match the A event.
* [x] Introduce new season-plan schema fields for warnings or role-week bands.
* [x] Make role-week text rendering the new parser/validator source of truth.

---

## 3) Proposed Behavior

**User/System behavior**

* Canonical phase semantics own both legal intensity domains and legal load modalities.
* `RECOVERY` is legal as an active-recovery execution domain across canonical phase intents unless a hard override prohibits it.
* `allowed_load_modalities` follow a canonical matrix:
  * `TRANSITION`, `PEAK`, `TAPER`, `RACE`: `["NONE"]`
  * `BASE`, `BUILD`: `["NONE", "K3"]`
  * `PREPARATION`: `["NONE"]` by default
* `events_constraints` contain only real A/B/C events and use an interface-valid event window representation.
* `SEASON_PLAN` visibly exposes inherited role-week load bands inside existing narrative fields as season-level guardrails.
* A material mismatch between the primary season objective and the highest in-horizon A event is surfaced as a warning in the final plan and in deterministic validation, but the plan still writes successfully.

**UI impact**

* UI affected: No direct page-logic change.
* Existing season-plan rendering will show the new warning and cleaner event/guardrail content through the artifact data it already renders.

**Non-UI behavior (if applicable)**

* Components involved: canonical phase semantics, season bundle normalization, season writer guardrails, deterministic planning contracts, season prompts/skills, renderers.
* Contracts touched: `SeasonPlanInterface` semantics, deterministic season bundle semantics, season review / writer expectations.

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/workspace/phase_intents.py`: canonical recovery legality and modality matrix.
* `src/rps/agents/crewai_backend.py`: season bundle normalization, event constraint projection, role-week materialization, warning projection.
* `src/rps/planning/contracts.py`: non-blocking objective mismatch warning, event and taper checks.
* `src/rps/crewai_runtime/guardrails.py`: writer exact-copy repair for code-owned season semantics.
* `prompts/agents/season_artifact_writer.md`: preserve new deterministic season semantics.
* `skills/season/artifact-writing/SKILL.md`, `skills/season/plan-synthesis/SKILL.md`: align methodology wording and writer obligations.

**Data flow**

* Inputs: selected scenario, deterministic phase slots, season phase load context, planning events, season objective, reviewed planning bundle.
* Processing:
  * canonicalize phase semantics and load modalities,
  * project real events into phase-local `events_constraints`,
  * materialize role-week guardrails into audit-visible text,
  * derive non-blocking objective mismatch warnings,
  * validate final season artifact against deterministic context.
* Outputs: schema-valid `SEASON_PLAN` with code-owned semantics, real event constraints, visible guardrails, and non-blocking warnings.

**Schema / Artefacts**

* New artefacts: none.
* Changed artefacts: no structural schema change; semantic content of existing fields changes.
* Validator implications:
  * canonical modality expectations become deterministic,
  * season plan may emit warning issues without blocking,
  * `events_constraints.window` must be confirmed to accept exact event dates under the current interface.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes for schema and readers.
* Breaking changes:
  * new writes will emit broader legal `RECOVERY` semantics,
  * new writes will stop emitting phantom event placeholders,
  * season validation becomes stricter for modality/event/narrative consistency.
* Fallback behavior:
  * if exact event dates are not interface-valid, keep a schema-valid window string while still validating against the true event date.

**Conflicts with ADRs / Principles**

* Potential conflicts:
  * ADR-053 code-owned semantics and taxonomy propagation
  * planning rule forbidding week plans inside `SEASON_PLAN`
* Resolution:
  * role-week bands are rendered only as inherited season-level guardrails, not as prescriptive week authoring.

**Impacted areas**

* UI: rendered season-plan content becomes cleaner and more auditable.
* Pipeline/data: season normalization and writer guardrails become more deterministic.
* Renderer: existing template consumes improved data without structural changes.
* Workspace/run-store: no storage-engine changes; warning detection may enrich final artifact text.
* Validation/tooling: tests and contract validators expand.
* Deployment/config: none.

**Required refactoring**

* Add canonical modality helpers to the phase-semantic backbone.
* Rebuild season event constraints from real event data instead of writer prose.
* Split taper validation into training-load semantics vs event-week total-load semantics.

---

## 6) Options & Recommendation

### Option A — Code-owned season semantic normalization (recommended)

**Summary**

* Keep schema stable and fix semantics in the canonical backbone plus normalization/validation layers.

**Pros**

* Generic across all season instances.
* Preserves deterministic authority.
* Avoids schema migration while improving auditability.

**Cons**

* Touches several cross-cutting planning layers together.

**Risk**

* Writer/validator/test updates must stay aligned.

### Option B — Prompt-only repair

**Summary**

* Tighten prompts and reviews without changing code-owned normalization semantics.

**Pros**

* Smaller code diff.

**Cons**

* Does not reliably stop drift in events, modalities, and warning projection.

### Recommendation

* Choose: Option A.
* Rationale: these are contract-semantic failures, not prompt-style failures.

---

## 7) Acceptance Criteria (Definition of Done)

* [ ] `RECOVERY` is legal across the canonical phase taxonomy unless explicitly overridden.
* [ ] Canonical `allowed_load_modalities` are derived from phase semantics rather than copied from model prose.
* [ ] `SEASON_PLAN.events_constraints` contains only real events and no synthetic “no event” placeholders.
* [ ] Structured deterministic role-week bands remain the validation source of truth.
* [ ] Final `SEASON_PLAN` visibly materializes role-week guardrails in existing text fields.
* [ ] Taper validation distinguishes pre-event training load from total event-week load.
* [ ] Objective/A-event mismatch produces a warning in the final plan and contract checks, but does not block writing.
* [ ] Validation passes: `py_compile`, lint, typecheck, targeted pytest, and one relevant smoke run.

---

## 8) Migration / Rollout

**Migration strategy**

* No schema migration.
* Existing artifacts remain readable.
* New writes adopt canonical recovery/modality/event semantics immediately.

**Rollout / gating**

* No feature flag.
* Safe rollback: revert semantic normalization / validation changes; no stored-data migration required.

---

## 9) Risks & Failure Modes

* Failure mode: `events_constraints.window` exact-date representation is not compatible with the existing interface.
  * Detection: schema validation or targeted contract test fails.
  * Safe behavior: retain schema-valid window representation while keeping real-event matching deterministic.
  * Recovery: document and implement the compatible representation path.

* Failure mode: role-week bands appear in text but drift from the structured deterministic source.
  * Detection: normalization/rendering tests compare text materialization against structured bands.
  * Safe behavior: treat structured data as authoritative and regenerate text.
  * Recovery: fix normalization helper.

* Failure mode: objective mismatch gets escalated to blocker behavior.
  * Detection: contract tests or finalization flow fail on warning-only scenarios.
  * Safe behavior: downgrade to warning and continue finalization.
  * Recovery: fix severity handling in validator/writer path.

---

## 10) Observability / Logging

**New/changed events**

* No new telemetry family required.
* Existing season-bundle / season-plan failures should include:
  * canonical phase intent,
  * modality expectation,
  * event constraint mismatch detail,
  * whether objective mismatch was warning-only.

**Diagnostics**

* `runtime/athletes/<athlete_id>/runs/<run_id>/events.jsonl`
* persisted `SEASON_PLAN` artifact and rendered Markdown
* deterministic season phase load context inside guardrail/runtime context

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] [doc/specs/features/FEAT_generic_season_semantics_revision.md](/doc/specs/features/FEAT_generic_season_semantics_revision.md) — feature source of truth
* [ ] [doc/adr/ADR-055-season-semantic-recovery-and-guardrail-serialization.md](/doc/adr/ADR-055-season-semantic-recovery-and-guardrail-serialization.md) — architectural decision
* [ ] [specs/knowledge/_shared/sources/specs/mandatory_output_season_plan.md](/specs/knowledge/_shared/sources/specs/mandatory_output_season_plan.md) — season output semantics
* [ ] [CHANGELOG.md](/CHANGELOG.md) — summarize semantic revision

---

## 12) Link Map (no duplication; links only)

* [Season plan semantic hardening](/doc/specs/features/FEAT_season_plan_semantic_hardening.md)
* [Canonical phase taxonomy ADR](/doc/adr/ADR-053-canonical-phase-taxonomy-and-build-subtypes.md)
* [Season artifact writer prompt](/prompts/agents/season_artifact_writer.md)
* [Season artifact writing skill](/skills/season/artifact-writing/SKILL.md)
* [Season plan synthesis skill](/skills/season/plan-synthesis/SKILL.md)
* [Mandatory season-plan output spec](/specs/knowledge/_shared/sources/specs/mandatory_output_season_plan.md)

