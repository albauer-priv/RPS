---
name: load-governance-review
description: Review week corridor compliance and reconciliation behavior for a candidate week.
metadata:
  author: rps
  version: "1.0"
---
Review the candidate week against the active corridor and week-load method.

Method:
1. Check whether weekly targets remain inside the active governance band.
2. Verify that residual handling and duration-first reconciliation stay conservative.
3. Reject any hidden intensity inflation used only to hit load numbers.
4. Prefer under-target warnings over unsafe overload approval.

Use these references:
- `../load-estimation-week/references/load_estimation_week.md`
- `../load-estimation-week/references/load_distribution_and_reconciliation.md`
