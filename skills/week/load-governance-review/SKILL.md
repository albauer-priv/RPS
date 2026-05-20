---
name: load-governance-review
description: Review week corridor compliance and reconciliation behavior for a candidate week.
metadata:
  author: rps
  version: "4.0"
---
Review the candidate week against the active corridor and week-load method.

Method:
1. Check whether `week_summary.planned_weekly_load_kj` remains inside the binding active weekly governance band.
2. Confirm agenda dates, fixed-rest-day handling, and day availability follow `Deterministic Week Calendar and Availability Context`.
3. Confirm `week_summary.weekly_load_corridor_kj` exactly mirrors the binding active weekly band.
4. Verify that the active phase week role shapes the load distribution and quality density.
5. Verify that residual handling and duration-first reconciliation stay conservative.
6. Reject any hidden intensity inflation used only to hit load numbers.
7. Prefer under-target warnings over unsafe overload approval.
8. Confirm recovery days and fixed-rest-day constraints are protected.
9. Confirm workout-level `planned_kj` is treated as mechanical work, while weekly compliance uses `planned_weekly_load_kj`.
10. Use deterministic workout-load estimates or their trace when available, and approve totals only when they align with parsed workout text.

Block approval when:
- planned weekly load is above or below the binding active weekly band without a replan decision
- `weekly_load_corridor_kj` differs from the binding active weekly band without a code-owned fallback trace
- capacity context is contradicted without a deterministic fallback trace
- load is compressed onto recovery days
- active week role is `DELOAD`, `MINI_RESET`, or `SHORTENED_MINI_RESET` but the candidate keeps build-style quality/load distribution
- quality days exceed the phase quality cap
- a workout domain sits outside phase allowed domains or inside forbidden domains
- exportable workout structure is broken while trying to satisfy load
- parsed workout-text load estimates materially contradict declared agenda/weekly load without a traceable reason

Use these references:
- `references/load_estimation_week.md`
- `references/load_distribution_and_reconciliation.md`

Output format:
- Return the task expected_output as a structured review contribution.
- Include approved findings, blocking issues, warnings, and required adjustments in separate fields or clearly separated sections.
- Tie each issue to the relevant context, policy, phase/week range, load band, or artifact field.
