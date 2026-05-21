---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-21
Owner: Planning Runtime
---
# FEAT: Season and Phase Draft-to-Normalized Contract Refactor

* **ID:** FEAT_season_phase_draft_normalized_contract_refactor
* **Status:** Implemented
* **Owner/Area:** Planning Runtime
* **Last-Updated:** 2026-05-21
* **Related:** ADR-053

---

## 1) Context / Problem

**Current behavior**

* `season_plan_finalize` and `phase_bundle_finalize` return internal bundles that are immediately treated as authoritative.
* Season had already started validating code-owned semantics at the finalize task boundary.
* Deterministic enrichment of season semantics happened only after the finalize task completed.

**Problem**

* The runtime validated raw LLM output as if it were already canonical.
* Season failed when the model emitted illegal `phase_type` / `phase_intent` combinations or over-broad domains.
* Phase still used the same architectural pattern even though it had not yet hit the same runtime failure.

**Constraints**

* Persisted `SEASON_PLAN`, `PHASE_GUARDRAILS`, `PHASE_STRUCTURE`, and `PHASE_PREVIEW` schemas must remain unchanged.
* A season must support a variable number of phases and repeated macrocycles; no fixed 5-phase assumption is allowed.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Split Season and Phase internal bundle handling into draft vs normalized states.
* [x] Make Python the owner of canonical semantics and deterministic writer handoff fields.
* [x] Run hard semantic validation only after normalization.

**Non-Goals**

* [x] No persisted artifact schema redesign.
* [x] No planner-logic redesign for event strategy or macrocycle structure.

---

## 3) Proposed Behavior

**User/System behavior**

* Season and Phase finalizer tasks now emit draft bundles.
* Python normalizes draft bundles into writer-safe canonical bundles before review and writing.
* Raw finalizer output is no longer treated as canonical semantics.

**UI impact**

* UI affected: No

**Non-UI behavior**

* Components involved: CrewAI runtime bindings, guardrails, planning backend, internal output models.
* Contracts touched: internal Season/Phase planning bundle contracts and runtime telemetry.

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/crewai_runtime/models.py`: add draft bundle models.
* `src/rps/crewai_runtime/bindings.py`: register draft output kinds.
* `src/rps/agents/crewai_backend.py`: normalize draft bundles before review/writer and emit stage-aware runtime events.
* `src/rps/crewai_runtime/guardrails.py`: narrow finalize-stage guardrails and keep normalized-bundle validation reusable.

**Data flow**

* Inputs: CrewAI finalizer draft bundle + deterministic season/phase contract context.
* Processing: finalize draft -> Python normalization -> normalized-bundle validation -> review -> writer.
* Outputs: unchanged persisted artifacts, plus clearer runtime events for normalization-stage failures.

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none persisted
* Validator implications: finalize-stage guardrails now validate draft shape, while normalized-bundle validation runs in backend before review.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes, for persisted artifacts.
* Breaking changes: internal CrewAI output-kind names for finalizer tasks changed to draft bundle kinds.
* Fallback behavior: draft models still accept legacy semantic hints where needed; normalization overwrites them.

**Conflicts with ADRs / Principles**

* Potential conflicts: none
* Resolution: aligns ADR-053 with explicit draft-vs-normalized ownership boundaries.

**Impacted areas**

* UI: none
* Pipeline/data: Season and Phase planning pipeline sequencing
* Renderer: none
* Workspace/run-store: additional normalization-stage runtime events
* Validation/tooling: output-model registry, guardrail sequencing, tests
* Deployment/config: task output kinds and task policies

**Required refactoring**

* Separate draft and normalized internal bundle models.
* Move normalized-bundle validation out of finalize task guardrails into backend-controlled post-processing.

---

## 6) Options & Recommendation

### Option A — draft-to-normalized split

**Summary**

* Keep raw finalizer output lightweight and normalize deterministically in Python.

**Pros**

* Clear ownership boundary
* Stable review/writer handoff
* Supports variable season phase counts and repeated cycles

**Cons**

* More internal models and pipeline steps

**Risk**

* Requires touching both runtime config and backend sequencing together

### Option B — keep single bundle model and relax guardrails

**Summary**

* Continue using one bundle model and only weaken finalize validation.

**Pros**

* Smaller code change

**Cons**

* Preserves ambiguous ownership
* Leaves the same failure mode available elsewhere

### Recommendation

* Choose: Option A
* Rationale: it fixes the ownership boundary instead of hiding the symptom.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Season finalizer outputs a draft bundle kind.
* [x] Phase finalizer outputs a draft bundle kind.
* [x] Draft bundles are normalized before review.
* [x] Normalized Season semantics are validated after normalization, not on raw finalize output.
* [x] Validation passes: syntax, lint, typecheck, targeted tests, CLI smoke.
* [x] No regressions in persisted Season/Phase artifact schemas.

---

## 8) Migration / Rollout

**Migration strategy**

* No persisted artifact migration.
* Internal output-kind and model migration only.

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert to previous output kinds and finalize-stage guardrail wiring.

---

## 9) Risks & Failure Modes

* Failure mode: draft bundle missing structural fields
  * Detection: draft integrity guardrail
  * Safe behavior: fail before review
  * Recovery: fix finalizer prompt/schema or upstream specialist output

* Failure mode: normalized bundle violates deterministic semantics
  * Detection: post-normalization validation event + exception
  * Safe behavior: fail before review/writer
  * Recovery: fix normalizer or deterministic contract inputs

---

## 10) Observability / Logging

**New/changed events**

* `SEASON_BUNDLE_NORMALIZATION_FAILED`
* `SEASON_BUNDLE_NORMALIZED_CONTRACT_FAILED`
* `PHASE_BUNDLE_NORMALIZATION_FAILED`
* `PHASE_BUNDLE_NORMALIZED_CONTRACT_FAILED`

**Diagnostics**

* Runtime log
* per-run `events.jsonl`

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] `doc/adr/ADR-053-canonical-phase-taxonomy-and-build-subtypes.md` — add draft-vs-normalized planning ownership rule
* [x] `CHANGELOG.md` — summarize internal contract refactor

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* Artefact flow: `doc/overview/artefact_flow.md`
* Planning flow: `doc/overview/how_to_plan.md`
* Logging/runtime diagnostics: `doc/architecture/system_architecture.md`
* ADR: `doc/adr/ADR-053-canonical-phase-taxonomy-and-build-subtypes.md`
