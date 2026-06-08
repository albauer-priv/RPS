---
Version: 1.0
Status: Implemented
Last-Updated: 2026-06-08
Owner: Planning Pipeline
---
# FEAT: Phase Bundle Nested Intent Normalization

* **ID:** FEAT_phase_bundle_nested_intent_normalization
* **Status:** Implemented
* **Owner/Area:** Planning Pipeline
* **Last-Updated:** 2026-06-08
* **Related:** [FEAT_phase_authority_realignment_and_shared_week_skeleton](/Users/alexander/RPS/doc/specs/features/FEAT_phase_authority_realignment_and_shared_week_skeleton.md)

## 1) Context / Problem

`phase_bundle_finalize` can emit a `PhaseDraftBundle` whose top-level `phase_intent` is canonical while nested payloads still carry free-text narrative `phase_intent` strings. `phase_bundle_review_readiness` correctly blocks that drift with `phase_bundle_nested_intent_mismatch`, but the repair belongs in deterministic bundle normalization before review guardrails run.

## 2) Goals & Non-Goals

**Goals**

* [x] Normalize nested internal `phase_intent` fields to the canonical top-level bundle intent.
* [x] Fail closed during bundle normalization if canonical phase intent is unavailable.
* [x] Keep review-readiness validation-only.

**Non-Goals**

* [x] No public schema change.
* [x] No Pydantic narrowing of nested `phase_intent` fields in this fix.
* [x] No writer/store/latest cleanup changes.

## 3) Proposed Behavior

`normalize_phase_draft_bundle(...)` now:

* requires deterministic canonical phase intent from `phase_execution_context`
* projects canonical `phase_intent` into:
  * `guardrails.phase_intent`
  * `structure.phase_intent`
  * `preview.phase_intent`
* raises immediately if canonical phase intent is missing or unresolvable

The active phase finalizer instructions explicitly treat nested `phase_intent` fields as canonical taxonomy tokens only.

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/agents/crewai_backend.py`: deterministic bundle normalization and fail-closed normalization-stage error
* `config/crewai/tasks.yaml`: active `phase_bundle_finalize` task wording
* `prompts/agents/phase_bundle_manager.md`: active manager prompt wording
* `skills/phase/bundle-synthesis/SKILL.md`: active synthesis skill wording
* `tests/test_crewai_runtime.py`: regression coverage

**Validator implications**

* `validate_phase_bundle_review_readiness(...)` remains unchanged in ownership
* it now receives a repaired normalized bundle for this failure class

## 5) Impact Analysis

* Backward compatible: Yes
* Breaking changes: none for persisted artifacts
* Pipeline effect: Phase bundle failures for missing canonical intent move decisively to normalization-stage failure

## 6) Acceptance Criteria

* [x] Nested `phase_intent` drift is normalized before review-readiness validation.
* [x] Missing canonical phase intent fails through `PHASE_BUNDLE_NORMALIZATION_FAILED`.
* [x] The real failing bundle shape with narrative `guardrails.phase_intent` is covered by regression tests.

## 7) Link Map

* [CHANGELOG.md](/Users/alexander/RPS/CHANGELOG.md)
* [feature_backlog.md](/Users/alexander/RPS/doc/overview/feature_backlog.md)
* [phase_bundle_manager.md](/Users/alexander/RPS/prompts/agents/phase_bundle_manager.md)
* [bundle-synthesis/SKILL.md](/Users/alexander/RPS/skills/phase/bundle-synthesis/SKILL.md)
