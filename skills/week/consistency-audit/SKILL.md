---
name: consistency-audit
description: Audit candidate week coherence across role, duration, load, and workout structure.
metadata:
  author: rps
  version: "2.0"
---
Audit the candidate week before it is written.

Checklist:
1. Day roles remain coherent with phase intent and active phase week role.
2. Agenda covers exactly Mon..Sun of the target ISO week and matches deterministic dates.
3. Planned load and duration reconcile against the active Phase/S5 band without hidden inflation.
4. Fixed rest days, zero-availability days, and recovery days stay protected.
5. Quality-day count and workout domains remain inside phase guardrails.
6. Workout structures match declared intent and keep intensity explicit.
7. Candidate edits remain bounded to the requested scope.
8. Workout-family choice, QUALITY-intent placement, and warmup/cooldown legality remain coherent with the approved week semantics.

Block approval when:
- `weekly_load_corridor_kj` is not the active Phase/S5 band
- a `DELOAD`, `MINI_RESET`, or `SHORTENED_MINI_RESET` week carries build-style quality
- a day exceeds deterministic availability
- a workout cannot be exported safely
- a workout is syntactically exportable but semantically drifts from the approved workout family, legal domain placement, or warmup/cooldown rules

Return blocking issues, warnings, and what may remain unchanged during replan.

Output format:
- Return the task expected_output as a structured review contribution.
- Include approved findings, blocking issues, warnings, and required adjustments in separate fields or clearly separated sections.
- Tie each issue to the relevant context, policy, phase/week range, load band, or artifact field.
