---
Status: Implemented
Version: 1.0
Last-Updated: 2026-09-16
---
# FEAT_vo2_scenario_activation

## Problem

The Season Scenarios agent generates three scenarios (A/B/C) that all forbid `VO2MAX` for the
entire season, even when the athlete profile explicitly lists VO2max development as a secondary
objective and training priority.

Root causes:
1. The scenario-generation skill treated VO2max development in `athlete_profile.objectives` as an
   *objective mismatch* (collision with durability event type) and surfaced it as a warning-only
   note rather than acting on it.
2. The `ceiling_first_durability` season archetype existed in code (`CANONICAL_SEASON_ARCHETYPES`)
   and documentation (`kinzlbauer_season_template.md`) but had no trigger rule — no skill said
   "when the athlete profile has this goal AND runway is sufficient, activate the archetype."
3. The macrocycle-architecture skill referenced the Kinzlbauer template but only activated it
   when the selected scenario already permitted `VO2MAX`. Since no scenario ever did, the template
   was never used.
4. Result: the season plan forbids VO2MAX in all 13 phases, directly contradicting the athlete's
   stated development goal.

## Goal

1. When `athlete_profile.objectives` contains explicit VO2max development language AND planning
   runway is ≥ 20 weeks, the scenario-generation layer MUST produce at least one scenario with
   `season_archetype: "ceiling_first_durability"` and `VO2MAX` in `allowed_intensity_domains`.
2. When the selected scenario uses `ceiling_first_durability`, the macrocycle-architecture task
   MUST map the first one or two phases to `vo2_build` intent and suppress `VO2MAX` from phase 3
   onward.
3. The `ceiling_first_durability` archetype follows the Kinzlbauer ultra/brevet template: aerobic
   ceiling first (VO2max foundation), then economy + durability + specificity.

## Non-Goals

- No change to the three-scenario (A/B/C) structure.
- No change to `phase_intents.py` (the `vo2_build` intent and `ceiling_first_durability` archetype
  were already declared; this feature activates them).
- No change to governance, load corridors, or deterministic kJ bands.

## Skill Changes

### `skills/season/scenario-generation/SKILL.md`
- New section **"Athlete VO2max development objectives"**: when VO2max is an explicit athlete
  objective and runway ≥ 20 weeks, MUST produce one ceiling_first scenario with `VO2MAX` in
  `allowed_domains`.
- **"Objective mismatch semantics"**: added EXCEPTION — VO2max development objective is NOT an
  objective mismatch; treat it as a binding planning directive.
- **Scenario C VO2MAX hard rule**: clarified that `ceiling_first_durability` framing (deliberate
  early-phase build) overrides the "sparse ceiling-support / not primary identity" framing.
- Added preferred copyable sentence for the ceiling_first_durability VO2MAX framing.

### `skills/season/macrocycle-architecture/SKILL.md`
- New section **"Ceiling-first archetype activation (mandatory when scenario uses it)"**: when
  the selected scenario has `season_archetype: "ceiling_first_durability"`, the macrocycle MUST
  map P01–P02 to `vo2_build` intent; from P03 onward transitions to `durability_build`. This
  activation is mandatory (not optional) once the scenario selects the archetype.

## Follows

- `kinzlbauer_season_template.md` — permitted archetype, already documented.
- `CANONICAL_SEASON_ARCHETYPES` in `phase_intents.py` — `ceiling_first_durability` already declared.
- `PHASE_SEMANTIC_PROFILES["vo2_build"]` in `phase_intents.py` — already defined.
