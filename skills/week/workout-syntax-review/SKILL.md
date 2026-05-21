---
name: workout-syntax-review
description: Review workout text against the project subset, grammar restrictions, and export-safe constraints.
metadata:
  author: rps
  version: "3.0"
---
Review candidate workout text as syntax, export policy, and workout-policy semantic compliance.

Runtime source boundary:
- This skill is the active runtime method for week workout syntax and semantics review.
- Do not depend on legacy workout prose under `specs/knowledge/_shared/sources/...` at runtime.
- Use local `references/validation_checklist.md` for the compact blocking checklist.

Review authority order:
1. `PHASE_GUARDRAILS` legality
2. active week contract context
3. project workout subset and exportability
4. inherited canonical phase-semantics fit (`phase_type`, `phase_intent`, `build_subtype`)

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
10. The candidate maps cleanly to one agenda/intensity configuration and one canonical workout family.
11. Targets stay inside the declared/intended intensity domain and inside the canonical workout-family ranges.
12. QUALITY intent placement, when explicit upstream, stays subordinate to Phase Guardrails and Phase Structure and does not redefine the legal domain.
13. Progression claims do not silently increase multiple dimensions at once.
14. K3 stays low-cadence and seated in character; over-under stays rhythmic; short VO2max stays 2:1; long VO2max stays 4-6 minute central intervals.
15. Warmup/Cooldown legality holds: no hidden sustained high-intensity warmup, no non-descending cooldown, no loops or spikes in cooldown.
16. No advanced EBNF-only tokens leak into the project subset unless explicitly permitted by the skill rules.
17. Workout family and target placement remain coherent with inherited canonical phase semantics, not only with day role and domain legality.
18. The candidate would pass the same strict export subset enforced by the runtime validator; prose serialization is a blocker, not a warning.
19. Canonical declared workout family/domain and final workout text remain mutually consistent; if they disagree, block approval.

Canonical family checks:
- `Recovery`: no hidden quality or activation
- `Endurance`: steady low-intensity aerobic work; no disguised threshold content
- `Tempo`: controlled tempo inside the legal domain; not threshold by stealth
- `Tempo / Over-Under`: recognizable under/over alternation around threshold
- `Sweet Spot`: long sustained intervals with controlled discomfort and legal TiZ/intensity
- `Threshold`: threshold-range sustained intervals with short recoveries
- `VO2max` short dense: `20-40s` work, `2:1` ratio, active recovery `45-60%`
- `VO2max` long: `4-6 min` work, active recovery `2-3 min @ 50-60%`
- `K3`: `85-90%`, `50-60 rpm`, no intensity spikes

Blocking syntax cases:
- nested loop
- `@` shorthand
- HR/pace/zone/absolute-watt target
- distance duration
- prose section serialization such as `Warmup:` / `Main Set:` / `Cooldown:`
- missing duration on any step line
- missing cadence on any step line
- missing Warmup or Cooldown
- missing required Activation for VO2max, Threshold, or Sweet Spot
- section order violation
- `MM:SS` or `HH:MM:SS` inside step lines
- ramp basis suffix like `FTP`, `HR`, `LTHR`, `Pace`, or `MMP`
- `press lap`, `power=...`, `hr=...`, `hidepower`, `freeride`, or similar advanced export token
- workout cannot be classified into a canonical family
- target values violate workout-family parameter ranges without explicit upstream justification
- QUALITY intent is used to push targets outside the legal domain
- multiple progression dimensions are advanced at once in the claimed workout evolution
- the workout is syntactically valid but semantically wrong for inherited canonical phase semantics
- a recovery-like workout uses `RECOVERY` when the active phase guardrails forbid `RECOVERY`
- a threshold-like workout uses `THRESHOLD` when the active phase guardrails forbid `THRESHOLD`
- the candidate bundle declares a legal family/domain but the actual workout text still signals a forbidden family/domain

Approval rule:
- do not approve a candidate week bundle that would fail `collect_week_plan_export_issues(...)`
- if syntax/export validity and week semantics disagree, return a blocker and bounded replan, not `approved`

Output format:
- Return the task expected_output as a structured review contribution.
- Include approved findings, blocking issues, warnings, and required adjustments in separate fields or clearly separated sections.
- Tie each issue to the relevant context, policy, phase/week range, load band, or artifact field.
