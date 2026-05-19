---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-19
Owner: Planning Runtime
---
# FEAT: Season Review Candidate Bundle Authority

* **ID:** FEAT_season_review_candidate_bundle_authority
* **Status:** Implemented
* **Owner/Area:** Planning Runtime
* **Last-Updated:** 2026-05-19

## 1) Context / Problem

Season review tasks receive the candidate planning bundle in task context, but runtime conversation logs showed review specialists trying to reload a synthetic `candidate_season_bundle` artifact from workspace and blocking when it was not found. That split the source of truth between an injected in-memory review subject and a non-existent persisted intermediate artifact.

## 2) Goals & Non-Goals

**Goals**

* [x] Make the injected candidate season bundle the explicit review subject.
* [x] Prevent review specialists from expecting a synthetic `candidate_season_bundle` workspace artifact.
* [x] Keep deterministic contract tools available for contract checks only.

**Non-Goals**

* [ ] Introduce a persisted `CANDIDATE_SEASON_BUNDLE` artifact type.
* [ ] Change the final public `SEASON_PLAN` writing contract.

## 3) Proposed Behavior

Season review specialists and the season review manager should review the injected candidate bundle directly. Workspace retrieval is still allowed for athlete-managed inputs or deterministic contract values, but not for reloading a synthetic review candidate artifact that is already present in task context.

## 4) Implementation Analysis

* Label the injected planning bundle explicitly as the candidate review subject.
* Add a review-subject rule in the season review contract-context injection.
* Tighten season review task descriptions, skill text, and review-manager prompt so they do not attempt synthetic candidate-bundle retrieval.

## 5) Impact Analysis

Backward compatible. No artifact schema changes. Runtime behavior becomes more deterministic and avoids false blocked review states caused by missing synthetic intermediate artifacts.

## 6) Recommendation

Use the injected candidate bundle as the sole review subject and reserve tools for deterministic contract reloads and athlete-managed inputs only.

## 7) Acceptance Criteria

* [x] Season review tasks explicitly reference the injected candidate bundle as the review subject.
* [x] Runtime review input labels the bundle as `Candidate Season Bundle`.
* [x] Season review contract-context blocks include a no-synthetic-retrieval rule.
* [x] Tests cover the new review-subject labeling/rule behavior.

## 8) Migration / Rollout

No migration required.

## 9) Risks & Failure Modes

If review tasks still block, the next likely issue is that a specific deterministic fact is not present in either the injected candidate bundle or the deterministic contract tools.

## 10) Observability / Logging

Inspect season review conversation logs for attempts to retrieve `candidate_season_bundle`. After this change, those lookups should disappear.

## 11) Documentation Updates

* [x] [CHANGELOG.md](/Users/alexander/RPS/CHANGELOG.md)
