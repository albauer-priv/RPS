---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-19
Owner: Agents/Runtime
---
# FEAT: Phase/Week Review Subject And Runtime Hardening

* **ID:** FEAT_phase_week_review_subject_and_runtime_hardening
* **Status:** Implemented
* **Owner/Area:** CrewAI runtime / planning review flows
* **Last-Updated:** 2026-05-19
* **Related:** FEAT_season_review_candidate_bundle_authority, FEAT_macrocycle_task_runtime_semantics

## 1) Context / Problem

**Current behavior**

* Phase and week reviews run through the shared review runner.
* The shared review runner still injected a season-specific review subject block (`Candidate Season Bundle`) for every review crew.
* Several bounded phase/week specialists still had native reasoning enabled although they now run in contract-bound, sequential specialist-first crews.

**Problem**

* Phase/week review steps can receive the wrong review-subject framing and may attempt to reason about the wrong synthetic artefact shape.
* Bounded phase/week specialists can still trigger foreign observer/replan behavior that adds cost and unstable meta-planning.

**Constraints**

* Review flows must stay sequential specialist-first.
* Candidate bundles should be treated as injected review subjects, not synthetic workspace artefacts.
* Changes must remain backward compatible with existing review decision schemas.

## 2) Goals & Non-Goals

**Goals**

* [x] Make phase/week review subject authority explicit and bundle-type correct.
* [x] Disable native reasoning on bounded phase/week specialists where deterministic/tool-bounded execution is sufficient.
* [x] Preserve existing review flow outputs and tests.

**Non-Goals**

* [ ] Redesign review decision schemas.
* [ ] Introduce new persisted candidate artefacts for phase or week review.

## 3) Proposed Behavior

**User/System behavior**

* `phase_review` evaluates the injected candidate phase bundle directly.
* `week_review` evaluates the injected candidate week bundle directly.
* Neither review path expects a synthetic persisted candidate artefact.
* Bounded phase/week specialists run without native reasoning-agent observer mode unless they are true manager/integration roles.

**UI impact**

* UI affected: No

**Non-UI behavior**

* Components involved:
  * `config/crewai/runtime_profiles.yaml`
  * `config/crewai/tasks.yaml`
  * `src/rps/agents/crewai_backend.py`
  * review manager prompts and tests
* Contracts touched:
  * injected planning bundle review-subject semantics

## 4) Implementation Analysis

**Components / Modules**

* `crewai_backend.py`: make review-subject injection generic by crew name.
* `tasks.yaml`: align phase/week review task descriptions with injected candidate-bundle authority.
* `runtime_profiles.yaml`: disable reasoning for bounded phase/week specialists/auditors/reviewers.
* prompts/tests: keep wording and assertions aligned.

**Data flow**

* Inputs: injected candidate planning bundle + deterministic contracts + prior specialist outputs
* Processing: sequential review specialists evaluate the injected bundle directly
* Outputs: review decision artefacts only

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: None at schema boundary
* Fallback behavior: existing deterministic contracts and injected bundle still drive review

**Impacted areas**

* Pipeline/data: review-step authority handling
* Validation/tooling: runtime config and CrewAI tests

**Required refactoring**

* Replace season-specific review-subject injection with generic per-crew mapping.
* Normalize bounded phase/week runtime profiles away from native reasoning.

## 6) Options & Recommendation

### Option A — Generic injected review-subject authority (recommended)

**Pros**

* Keeps review source-of-truth in one place.
* Avoids synthetic artefact lookups.
* Matches the sequential specialist-first execution model.

**Cons**

* Requires task/prompt wording discipline.

### Option B — Persist synthetic candidate phase/week artefacts

**Pros**

* Explicit workspace handoff point.

**Cons**

* Adds artefact churn and another contract surface.
* Unnecessary for current in-memory planning/review flow.

## 7) Acceptance Criteria (DoD)

* `phase_review` and `week_review` receive bundle-type-correct injected review-subject instructions.
* Phase/week review tasks do not reference synthetic persisted candidate artefacts.
* Bounded phase/week specialists identified in this feature have `reasoning.enabled = false`.
* `tests/test_crewai_runtime.py` passes.

## 8) Migration / Rollout

* No migration needed.
* Runtime-only hardening applies on next deploy.

## 9) Risks & Failure Modes

* If a truly integrative phase/week specialist was over-constrained, quality could drop.
* Detection: review smoke logs will show missing synthesis or incorrect blocked decisions.

## 10) Observability / Logging

* Conversation logs should stop showing season-specific candidate-bundle wording inside phase/week review paths.
* Fewer phase/week bounded specialist runs should surface foreign reasoning/observer prompts.

## 11) Documentation Updates

* Update `CHANGELOG.md`
* Keep review prompts/tasks/tests aligned

## 12) Link Map

* [CHANGELOG.md](/Users/alexander/RPS/CHANGELOG.md)
* [config/crewai/tasks.yaml](/Users/alexander/RPS/config/crewai/tasks.yaml)
* [config/crewai/runtime_profiles.yaml](/Users/alexander/RPS/config/crewai/runtime_profiles.yaml)
* [src/rps/agents/crewai_backend.py](/Users/alexander/RPS/src/rps/agents/crewai_backend.py)
