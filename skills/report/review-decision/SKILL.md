---
name: review-decision
description: Integrate DES review findings into approve, reject, or bounded rework decisions.
metadata:
  author: rps
  version: "1.0"
---
Decide whether the diagnostic bundle is fit for writing.

Rules:
- reject action leakage beyond diagnostic authority
- require evidence-based warnings where confidence is limited
- bound any rework request to diagnostic interpretation, not planning redesign
- do not ask coworkers to rediscover report-week evidence, readiness context, or diagnostic-only boundaries during review


Output format:
- Return the task expected_output with a clear decision status: `approved`, `replan_required`, or `rejected`.
- Include blocking issues, warnings, replan instructions, and writer-ready summary when applicable.
- State the concrete change needed before approval when the decision is not approved.
