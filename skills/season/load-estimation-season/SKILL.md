---
name: load-estimation-season
description: Season-level load estimation rules for corridor derivation.
metadata:
  author: rps
  version: "2.0"
---
Apply season-level load-estimation rules as binding corridor logic, not as a loose reference.

Use this skill together with:
- `skills/shared/load-estimation-core/SKILL.md`
- `skills/season/load-governance/SKILL.md`

Season load-estimation scope:
- derive season phase corridors in `planned_weekly_load_kj/week`
- preserve the distinction between:
  - `planned_kj` = mechanical work
  - `planned_weekly_load_kj` = governance load
- keep `weekly_kj_bands` / `weekly_load_corridor_kj` semantics aligned with governance load, never raw work

Operational method:
1. Start from deterministic `availability_load_capacity_kj`, phase role, inherited cadence week roles, baseline, and progression trace.
2. Use the shared load-estimation core math and invariants unchanged:
   - IF applied exactly once
   - `IF_ref_load` resolved deterministically
   - mechanical work and governance load never merged
3. Express season corridors as sustainable repeatable governance load, not as availability capacity copies.
4. Keep corridor meaning phase-specific:
   - Base = stabilization / repeatability
   - Build = progression with risk control
   - Peak/Taper = load reduction with execution clarity
   - Transition/Preparation = re-entry / consolidation

Season-specific rules:
- a season corridor must fit deterministic availability and phase-role feasibility
- do not set all phases equal to capacity min/typical/max just because capacity exists
- if a corridor is below capacity, explain whether that is due to:
  - re-entry
  - deload / mini-reset
  - taper / peak
  - B-event rehearsal or event proximity
- if a corridor would need hidden intensity inflation to be met, lower the corridor or mark review pressure
- if a corridor is infeasible under deterministic context, stop or escalate; do not normalize the problem away

Progressive-overload translation:
- choose cadence-family interpretation from upstream scenario authority
- keep ramp class explicit
- use conservative baseline updates
- preserve Build-entry readiness gates
- distinguish:
  - deload
  - mini-reset
  - reload
  - re-entry

Durability-first translation:
- prefer repeatability over cosmetic corridor centering
- increase load mainly through durable work/kJ expansion, not intensity stacking
- no catch-up logic after misses or compressed windows
- when compressed, reduce lower-priority stress before weakening recovery structure

Output expectation:
- return season corridor logic that downstream Phase can inherit deterministically
- include explicit trace cues for:
  - baseline source
  - corridor rationale
  - cadence interpretation
  - fallback / replan pressure
