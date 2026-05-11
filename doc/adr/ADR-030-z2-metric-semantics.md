---
Version: 1.0
Status: Accepted
Last-Updated: 2026-05-11
Owner: ADR
---
# ADR-030: Z2 metric semantics

**Status:** Accepted  
**Date:** 2026-05-11  

## Context

RPS exposes several aerobic distribution metrics across `activities_actual`,
`activities_trend`, report rendering, and planner context. A semantic mismatch
appeared in the pipeline:

* fields named `Z2 Share` were interpreted by policy and reports as pure Z2,
* but one activity-level formula used `(Z1 + Z2) / total` under the label
  `Power TiZ Share Z2 (%)`.

This created inconsistent values and caused `Flag Z2 Share >= 60%/70%` to be
derived from a mislabeled low-intensity share.

## Decision

RPS defines aerobic distribution metrics as follows:

* `Z2 Share` means **pure Z2 share**:
  * `Power TiZ Z2 / sum(Power TiZ Z1..Z7) * 100`
* `Z1 + Z2 Time (%)` means **combined low-intensity share**:
  * `(Power TiZ Z1 + Power TiZ Z2) / sum(Power TiZ Z1..Z7) * 100`
* `Weekly Z2 Share (%)` remains a weekly moving-time share:
  * `weekly_z2_time_total_min / weekly_moving_time_total_min * 100`

All fields, labels, flags, and policy references named `Z2 Share` must follow
the pure-Z2 definition.

## Consequences

- Policy, report interpretation, and planner context stay aligned.
- Activity-level `power_tiz_share_z2` and derived flags may drop after
  regeneration because they now exclude Z1 time.
- `Z1+Z2` remains available explicitly and is not removed.
- Future additions must distinguish pure-Z2 metrics from broader
  low-intensity-share metrics by name.

## Exceptions

None.
