---
name: preview-synthesis
description: Derive a preview narrative from approved phase logic without adding new decisions.
metadata:
  author: rps
  version: "1.0"
---
Summarize the phase candidate as a derived preview only.

Rules:
- summarize existing planning decisions only
- summarize existing guardrail content only
- preview must remain traceable to the existing bundle
- `weekly_agenda_preview` must stay inside stored `PHASE_STRUCTURE` authority
- use only weeks from the exact phase range
- use only allowed day roles, intensity domains, and load modalities from structure
- fixed non-training days must remain non-training with `NONE` / `NONE`
- do not exceed the structure quality-day cap in any preview week

Output format:
- Return the task expected_output as a structured review contribution.
- Include approved findings, blocking issues, warnings, and required adjustments in separate fields or clearly separated sections.
- Tie each issue to the relevant context, policy, phase/week range, load band, or artifact field.
