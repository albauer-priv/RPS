---
name: workout-syntax-review
description: Review workout text against the project subset, grammar restrictions, and export-safe constraints.
metadata:
  author: rps
  version: "2.0"
---
Review candidate workout text purely as syntax and export policy.

Checklist:
1. Top-level document uses only allowed blocks and at most one `Category:` line.
2. Section order stays inside the project convention.
3. Every step line contains duration, power target, and cadence.
4. Only allowed target forms are used.
5. The text uses the supported workout syntax subset for shorthand, targets, time formats, and durations.
6. Loop usage stays within the single-level project subset.
7. Comments, if present, remain on their own line and preserve loop/section structure.
8. Every workout includes `Warmup`, `Main Set`, and `Cooldown`.
9. `Activation` is present for VO2max, Threshold, and Sweet Spot workouts.

Blocking syntax cases:
- nested loop
- `@` shorthand
- HR/pace/zone/absolute-watt target
- missing duration on any step line
- missing cadence on any step line
- missing Warmup or Cooldown
- missing required Activation for VO2max, Threshold, or Sweet Spot
- section order violation
- `MM:SS` or `HH:MM:SS` inside step lines

Output format:
- Return the task expected_output as a structured review contribution.
- Include approved findings, blocking issues, warnings, and required adjustments in separate fields or clearly separated sections.
- Tie each issue to the relevant context, policy, phase/week range, load band, or artifact field.
