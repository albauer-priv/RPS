---
name: preview-review
description: Review phase preview text for derivation-only behavior.
metadata:
  author: rps
  version: "1.0"
---
Check whether the preview remains descriptive and derivative.

Reject if the preview adds:
- new constraints
- new targets
- new structural decisions

Reject if the preview agenda:
- covers weeks outside the stored phase range
- uses day roles, intensity domains, or load modalities outside stored `PHASE_STRUCTURE`
- violates fixed non-training days
- exceeds the stored quality-day cap

Output format:
- Return the task expected_output as a structured review contribution.
- Include approved findings, blocking issues, warnings, and required adjustments in separate fields or clearly separated sections.
- Tie each issue to the relevant context, policy, phase/week range, load band, or artifact field.
