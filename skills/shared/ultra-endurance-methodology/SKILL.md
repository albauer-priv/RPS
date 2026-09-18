---
name: ultra-endurance-methodology
description: Scientific methodology for ultra-distance cycling and brevet planning — durability as the primary performance dimension, kJ-first load progression, Z1/Z2 dominance, and metabolic conditioning sequence.
metadata:
  author: rps
  version: "1.0"
---
Plan ultra-distance cycling and brevet events through the lens of durability, aerobic efficiency, and systematic fatigue exposure — not peak power.

This skill defines the ultra-endurance-specific layer of planning methodology. It extends
`skills/shared/durability-methodology` and `skills/shared/periodization-methodology` with
ultra/brevet-specific prescriptions derived from peer-reviewed research (Spragg/Leo/Swart,
Mateo-March/Leo/Mujika) and from practitioner synthesis (Kinzlbauer, empirical ultra coaching).

## The ultra/brevet performance model

Ultra-distance events (≥ 200 km, typically > 8 hours) expose a performance dimension that
laboratory measures miss: **durability** — the ability to maintain submaximal performance
under large accumulated work.

Three determinants, ordered by importance for ultra/brevet:

1. **Durability** (`ΔCP` or `Δfatigued-power`): ability to attenuate the power decline after
   2000+ kJ accumulated work. This is the primary differentiator between finishers and DNFs in
   ultra events. Evidence: `ult_core_001` (Spragg/Leo 2023), `ult_core_002` (Mateo-March/Leo 2024).
2. **Aerobic efficiency** (`FatOx` at ultra pace): substrate oxidation at submaximal intensity —
   athletes with lower carbohydrate oxidation (higher fat oxidation) at event pace show better
   durability. Evidence: `dur_core_004` (Spragg/Leo/Swart 2023).
3. **Aerobic ceiling** (`VO2max`): the upper bound of sustainable aerobic power. For ultra events,
   athletes ride at 55–70% VO2max — so the ceiling matters less than the efficiency at sub-ceiling
   intensity; however, a higher ceiling allows the same absolute pace to feel less demanding.

What matters less for ultra/brevet (compared to road/crit racing):
- Peak sprint power, VLamax, W', maximal lactate
- Short-duration (1–5 min) power-to-weight ratio
- Training Stress Score (TSS) or CTL/ATL metrics — these do not capture durability

## The kJ-differentiation principle

**Not all kJ are equal.** Accumulated work above the critical power (CP) causes a
disproportionate decrement in subsequent performance — more than work-matched effort below CP.

Evidence (`ult_core_002`, Mateo-March, Leo et al. 2024): in professional male cyclists,
accumulated work **above CP** impairs short-duration performance significantly more than
equivalent kJ below CP. The implication for planning:

- The majority of weekly kJ must be accumulated **below the first lactate threshold (VT1)** —
  this is Z1/Z2 in a 3-zone or 5-zone model
- Every unnecessary session above CP reduces the durability-building value of the training week
- kJ at Z1/Z2 accumulate aerobic adaptations without the recovery debt that Z4/Z5 sessions carry

This is the scientific foundation for the kJ-first / volume-first approach used throughout RPS.

## Training distribution for ultra/brevet

Target distribution for athletes building toward ultra/brevet events (evidence: `ult_core_001`,
`dur_core_010`, `dur_core_011`):

| Zone | % of training time | Purpose |
|---|---|---|
| Z1 (< VT1, < LT1) | 70–80% | Primary durability stimulus; fat oxidation adaptation |
| Z2 (VT1–VT2, LT1–LT2) | 10–15% | Tempo capacity; not a primary adaptation driver for ultra |
| Z3–Z4 (> VT2, > CP) | 5–15% | Bounded purpose only; raises VO2max ceiling when needed |

**Polarized distribution** (Z1 + Z3/Z4, minimal Z2) associates with durability improvements
in professional cyclists (`ult_core_001`). For ultra/brevet, polarized is preferred over
threshold-heavy distribution — threshold accumulation without Z1 foundation risks high CarbOx
at race pace.

**The key rule**: training time below VT1 is the single best proxy for durability development.
Weeks where Z1 time falls below 60% should be flagged — not as a strict blocker, but as a
durability-building risk.

## Phase sequencing for ultra/brevet

The canonical ultra/brevet season sequence follows the Kinzlbauer archetype (see
`skills/season/macrocycle-architecture/references/kinzlbauer_season_template.md`):

**VO2max ceiling first → VLamax/economy → specific durability**

This ordering is intentional: a higher VO2max makes every subsequent training stimulus more
productive (the same Z1 pace sits at a lower %VO2max → stronger fat-oxidation signal), and
high-intensity tolerance built in the ceiling phase reduces the VLamax load of later aerobic work.

### Metabolic conditioning sequence (across seasons / multi-phase macro)

1. **Raise the aerobic ceiling** (GPP → VO2 foundation → VO2-focused phase): bounded Z3/Z4
   blocks → VO2max ↑ → same absolute event pace = lower %VO2max → better fat oxidation signal
   for subsequent phases. Short-interval protocols (30/15 s → 40/20 s → longer threshold)
   progress within interval family before escalating.
2. **Lower VLamax / build economy** (economy/durability phase): shift to high Z1/Z2 volume as
   primary overload axis; sub-threshold and low-cadence work increase; carbohydrate oxidation at
   submaximal intensity falls; VT1 power rises.
3. **Train specific durability** (specific durability phase): event-specific kJ/kg preload
   exposure under accumulated fatigue; standardized fatigued-state quality checks (normal
   performance after ≥ 30 kJ/kg preload) become primary quality metrics.

### Mapping to schema-valid phases

| Schema cycle | Kinzlbauer phase | Ultra emphasis |
|---|---|---|
| `Base` | GPP + VO2 foundation | Structural robustness; early ceiling work |
| `Build` | VO2-focused + economy/durability | Ceiling peak → transition to VLamax/economy |
| `Build` | Specific durability | kJ/kg preload; fatigued-state quality checks |
| `Peak` | Taper | Volume −41–60%, intensity maintained (see `periodization-methodology`) |

Only `Base`, `Build`, `Peak`, `Transition` are valid schema cycle values.

### Phase content rules

**Base phase (ultra context)**
- Primary goal: structural robustness + early aerobic base; no high-intensity unless explicitly
  permitted; cadence `2:1:1` or `2:1` depending on athlete recovery profile
- Duration: minimum 4–6 weeks before progressing to ceiling work

**Build phase — VO2 ceiling segment**
- Primary goal: VO2max ceiling tolerance and repeatability
- Load character: bounded Z3/Z4; short-interval protocols progress within family before escalating;
  Z1/Z2 remains protected — ceiling work does not replace base volume

**Build phase — economy/durability segment**
- Primary goal: VLamax lowering; metabolic efficiency at ultra pace; demonstrated durability
- Load character: volume becomes primary overload axis; Z3+ bounded; introduce B2B long rides,
  preload + hard-later sessions
- kJ/kg milestones (indicative): 20–25 kJ/kg early → 28–32 kJ/kg mid → 35–40 kJ/kg late
- Hard-late sessions: planned effort in the final hours of a long ride — trains the durability
  adaptation directly (`ult_core_002`, `dur_core_003`)

**Peak phase (ultra context)**
- Same taper rules as in `periodization-methodology`: volume −41–60%, intensity maintained
- Ultra-specific: 2–3 week taper; final long ride ≥ 2 weeks before A event; no new stimuli
  (new distances, new intensity domains) inside the taper window

## Kinzlbauer principle — the "prepared state"

Ultra cycling coach Max Kinzlbauer (coach of Christoph Strasser, Walter Ablinger, and elite
cyclists; practitioner source `ult_applied_001`) frames ultra preparation around a core question:
**"In welchem Zustand sollte man sich befinden, um für lange Strecken auf dem Rad gerüstet zu
sein?"** — "In what physiological state should an athlete be in to be prepared for long distances?"

The prepared state for ultra cycling has these hallmarks:
- **Metabolic efficiency**: able to ride at ultra pace (55–70% VO2max) primarily on fat,
  with low relative carbohydrate contribution → sustains effort for > 8 hours without bonking
- **Demonstrated durability**: can perform near-target pace after 3,000–5,000 kJ accumulated
  → proven in training, not just estimated from rested lab values
- **Repeatability**: consecutive training days at ultra volume do not require extended recovery →
  the athlete absorbs 5–7 days per week of volume without hidden recovery debt
- **Mental/logistical exposure**: has experienced multi-day fatigue in training (particularly
  for events > 24h: RAAM, Paris-Brest-Paris) — sleep deprivation, night riding, nutrition under fatigue

This "prepared state" cannot be inferred from FTP or VO2max alone — it requires the
systematic accumulation of training history in the durability and repeatability domains.

## What this skill does NOT define

- kJ-band numbers, progression ramp percentages: see `load-governance`
- Cadence (2:1/3:1/2:1:1) and deload targets: see `cadence-recovery`
- Phase structural content (week roles, taper weeks): see `periodization-methodology`
- General durability-first philosophy and evidence library: see `durability-methodology`

Reference files:
- `references/ultra_cycling_evidence.md` — verified evidence table for ultra/brevet-specific sources
- `references/fat_adaptation_and_substrate_oxidation.md` — detailed metabolic basis

Cross-references:
- `skills/season/macrocycle-architecture/references/kinzlbauer_season_template.md` — canonical
  ultra/brevet season archetype (phase sequence, kJ/kg milestones, fueling progression, HR markers)
- `skills/shared/durability-methodology/` — durability-first philosophy and full evidence library
- `skills/shared/periodization-methodology/` — phase structural rules, taper content, backward planning

Authority: This skill extends durability-methodology and periodization-methodology for the
ultra/brevet context. It does not override load-governance, availability constraints, or
schema-validated planning structure.
