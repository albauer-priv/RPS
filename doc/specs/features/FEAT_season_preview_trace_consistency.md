---
Version: 1.0
Status: Implemented
Last-Updated: 2026-06-09
Owner: Planning Pipeline
---
# FEAT: Season Load Envelope and Preview/Trace Consistency

* **ID:** FEAT_season_preview_trace_consistency
* **Status:** Implemented
* **Owner/Area:** Planning Pipeline
* **Last-Updated:** 2026-06-09
* **Related:** [FEAT_phase_authority_realignment_and_shared_week_skeleton](/Users/alexander/RPS/doc/specs/features/FEAT_phase_authority_realignment_and_shared_week_skeleton.md), [FEAT_phase_preview_derivation_hardening](/Users/alexander/RPS/doc/specs/features/FEAT_phase_preview_derivation_hardening.md), [ADR-058-phase-authority-chain-and-shared-week-skeleton](/Users/alexander/RPS/doc/adr/ADR-058-phase-authority-chain-and-shared-week-skeleton.md)

---

## 1) Context / Problem

**Current behavior**

* Season plans persist authoritative `role_week_load_bands`.
* Preview and Week already share one deterministic skeleton source.
* Final Phase artifact normalization already repairs some lineage and authority fields.

**Problem**

* `season_load_envelope.expected_average_weekly_kj_range` was still derived from broad phase corridors instead of authoritative role-week bands.
* `PHASE_PREVIEW` could still be worded as if it were the binding week authority, despite remaining a derived artifact.
* `trace_upstream` on Phase artifacts could retain duplicate or lower-quality entries when better in-process references were available.

**Constraints**

* No authority-model redesign.
* No schema change.
* Keep Preview/Week alignment on the existing shared deterministic skeleton.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Derive season average weekly kJ envelope from authoritative role-week bands.
* [x] Keep Preview explicitly informational while preserving deterministic Preview/Week alignment.
* [x] Deduplicate and canonicalize immediate Phase `trace_upstream` lineage.

**Non-Goals**

* [x] No change to scenario-vs-phase legality ownership.
* [x] No change to structural-vs-operational `NONE` handling.

---

## 3) Proposed Behavior

**User/System behavior**

* Season envelope min/max now reflect the authoritative average implied by persisted role-week guardrails.
* Preview remains day-by-day visible, but is always framed as a derived informational view of the current phase skeleton.
* Phase trace metadata keeps the immediate formal upstream dependency exactly once and prefers the real in-process run id over synthetic fallback entries.

**UI impact**

* UI affected: Yes
* The Phase Preview renderer now uses softer language that reflects shared-skeleton alignment instead of immutable preview authority.

**Non-UI behavior**

* Components involved: planning contracts, output normalization, preview rendering, active preview guidance.
* Contracts touched: `SEASON_PLAN`, `PHASE_PREVIEW`, Phase artifact metadata.

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/planning/contracts.py`: authoritative season envelope derivation.
* `src/rps/agents/output_normalization.py`: preview authority/writing normalization and trace dedupe preference.
* `src/rps/rendering/templates/phase_preview.md.j2`: user-facing preview wording.
* active preview task/prompt/skill files: explicit informational-preview guidance.

**Schema / Artefacts**

* No new artefacts.
* No schema bump.
* Existing validators remain strict; only deterministic derivation inputs change.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none at schema level
* Fallback behavior: legacy role-week-band notes still parse when structured bands are absent

**Conflicts with ADRs / Principles**

* Potential conflicts: none
* Resolution: aligns more tightly with ADR-058 and upstream-first ownership

**Impacted areas**

* UI: preview wording
* Pipeline/data: season envelope derivation and phase trace normalization
* Renderer: preview narrative labels
* Validation/tooling: season envelope comparison now checks the role-week-band-based value

---

## 6) Options & Recommendation

### Option A — tighten existing deterministic sources

**Summary**

* Reuse current role-week and shared-skeleton sources; fix only derivation, wording, and lineage normalization.

### Recommendation

* Choose: Option A
* Rationale: fixes the reviewed defects without reopening already-correct authority layers.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `expected_average_weekly_kj_range` is derived from authoritative role-week bands.
* [x] `PHASE_PREVIEW` stores as `Informational` and stays aligned with Week via the shared skeleton.
* [x] Preview wording no longer implies immutable week authority.
* [x] Immediate Phase `trace_upstream` references are canonical and deduplicated.
* [x] Validation passes: `py_compile`, targeted pytest, lint, typecheck.

---

## 8) Migration / Rollout

**Migration strategy**

* No migration required.

**Rollout / gating**

* No feature flag.
* Safe rollback: revert the deterministic derivation/normalization changes.

---

## 9) Risks & Failure Modes

* Failure mode: legacy season plans without usable role-week-band data fail envelope derivation.
  * Detection: season validation mismatch or missing-envelope issue
  * Safe behavior: fail closed instead of silently falling back to corridor averages
  * Recovery: restore parseable legacy notes or structured role-week bands

---

## 10) Observability / Logging

**Diagnostics**

* Existing season validation and artifact store paths remain the detection points.
* No new telemetry contract is required.

---

## 11) Documentation Updates

* [x] [specs/knowledge/_shared/sources/specs/mandatory_output_season_plan.md](/Users/alexander/RPS/specs/knowledge/_shared/sources/specs/mandatory_output_season_plan.md) — clarify authoritative season envelope derivation
* [x] [CHANGELOG.md](/Users/alexander/RPS/CHANGELOG.md) — record the behavior change
* [x] [doc/overview/feature_backlog.md](/Users/alexander/RPS/doc/overview/feature_backlog.md) — record implemented feature
