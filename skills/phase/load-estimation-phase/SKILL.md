---
name: load-estimation-phase
description: Phase-level load estimation rules for exact-range guardrail and structure authoring.
metadata:
  author: rps
  version: "2.0"
---
Apply phase-range load estimation as exact-range governance-band logic.

Definitions:
- `planned_kj`: mechanical workout/day work estimate; never the phase band compliance metric
- `planned_weekly_load_kj`: governance week-load metric used for exact-range band semantics
- `weekly_kj_bands[w]`: exact-range governance-load band for ISO week `w`
- `phase_role`: deterministic role of the exact phase range
- `week_role`: deterministic inherited cadence role for ISO week `w`
- `S5`: deterministic weekly band derivation and fallback ladder already computed for the exact range
- `BL_kJ`: baseline weekly governance-load anchor when exact-range overload interpretation needs it
- `DL_kJ`, `RE_kJ`, `MR_kJ`: exact-range reset targets used to interpret week-role meaning

Authority / injected sources:
- `phase_role`, `week_role`, exact ISO-week range, and S5 band traces come from deterministic phase execution context
- load-estimation math and `IF_ref_load` semantics come from `skills/shared/load-estimation-core/SKILL.md`
- this layer derives exact-range band meaning and fallback semantics; it must not compute workout-level segment math

Use this skill together with:
- `skills/shared/load-estimation-core/SKILL.md`
- `skills/phase/guardrails-authoring/SKILL.md`
- `skills/phase/cadence-recovery/SKILL.md`

Phase load-estimation scope:
- derive exact-range `weekly_kj_bands` in `planned_weekly_load_kj`
- preserve the distinction between:
  - workout/day `planned_kj` = mechanical work
  - week `planned_weekly_load_kj` = governance load
- keep S5 and active corridor semantics exact; no ad hoc reinterpretation

Operational method:
1. Start from deterministic phase execution context, inherited week roles, exact ISO-week range, and S5 bands.
2. Apply the shared load-estimation core invariants unchanged.
3. Copy code-owned S5 bands exactly into the phase range and explain how they are used.
4. Keep exact-range semantics visible:
   - build weeks progress
   - deload weeks reduce
   - mini-reset weeks reduce less than full deload
   - reload weeks return near prior build load
   - re-entry weeks are baseline-anchored after fatigue or true deload

Progression axes:
- duration / total governance work
- frequency only where inherited structure permits it
- density / complexity
- intensity last

Exact-range rules:
- emitted week keys must match the required phase weeks exactly
- no weekly band may exceed availability feasibility without explicit STOP/replan pressure
- use phase role plus inherited week role to interpret the band, not prose alone
- if season corridor is infeasible for this exact range, preserve fallback trace rather than pushing overload downstream

Progressive-overload translation:
- `3:1`, `2:1`, and `2:1:1` must be visible in weekly band meaning
- if `2:1:1` falls back:
  - mini-reset may become true deload
  - reload must become re-entry
- preserve conservative Build entry after shortened/base/re-entry context

Durability-first translation:
- do not compress missed or infeasible load into protected recovery days
- prefer slightly under target with traceable rationale over structurally incoherent exact hit
- phase bands should remain repeatable and survivable under small execution variance

Output expectation:
- return exact-range band derivation, fallback pressure, and risk notes in a form guardrails and structure can copy directly
