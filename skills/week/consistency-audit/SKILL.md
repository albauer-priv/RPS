---
name: consistency-audit
description: Audit candidate week coherence across role, duration, load, and workout structure.
metadata:
  author: rps
  version: "1.0"
---
Audit the candidate week before it is written.

Checklist:
1. Day roles remain coherent with phase intent.
2. Planned load and duration reconcile without hidden inflation.
3. Recovery days stay protected.
4. Workout structures match their declared intent and keep intensity explicit.
5. Candidate edits remain bounded to the requested scope.

Return blocking issues, warnings, and what may remain unchanged during replan.

Output format:
- Return the task expected_output as a structured review contribution.
- Include approved findings, blocking issues, warnings, and required adjustments in separate fields or clearly separated sections.
- Tie each issue to the relevant context, policy, phase/week range, load band, or artifact field.
