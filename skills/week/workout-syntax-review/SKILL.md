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
5. Forbidden shorthand, zones, HR, pace, absolute watts, unsupported time formats, and distance durations are absent.
6. Loop usage stays within the single-level project subset.
7. Comments, if present, remain on their own line and do not break loop/section structure.

Hard rejection cases:
- any nested loop
- any `@` shorthand
- any HR/pace/zone/absolute-watt target
- missing cadence on any step line
- `MM:SS` or `HH:MM:SS` used inside step lines
