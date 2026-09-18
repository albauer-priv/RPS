---
name: ultra-endurance-methodology
description: Scientific methodology for ultra-distance cycling and brevet planning — durability as the primary performance dimension, kJ-first load progression, ENDURANCE-domain dominance (below VT1), and Kinzlbauer metabolic conditioning sequence.
metadata:
  author: rps
  version: "1.1"
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

## Zone model and RPS domain mapping

**Important**: research literature (Seiler, Spragg/Leo) uses a **3-zone physiological model**
anchored at VT1 (first ventilatory/lactate threshold) and VT2 (second threshold). The RPS
system uses an **8-zone intervals.icu / Coggan-derived model** (Z1, Z2, Z3, SS, Z4, Z5, Z6, Z7),
which is NOT the same as the research 3-zone model. The mapping is:

| Research (3-zone) | Physiological boundary | intervals.icu zones | RPS domain | Approx. % FTP |
|---|---|---|---|---|
| Below VT1 (research "low") | Below first lactate/ventilatory threshold | Z1 + Z2 | `RECOVERY` + `ENDURANCE` | 0–75% FTP |
| VT1–VT2 (research "moderate") | Between first and second threshold | Z3 + SS + Z4 | `TEMPO` + `SWEET_SPOT` + `THRESHOLD` | 75–105% FTP |
| Above VT2 / CP (research "high") | Above second threshold / critical power | Z5 + Z6 + Z7 | `VO2MAX` + anaerobic/neuro | > 105% FTP |

**Critical clarification**:
- When research says "70–80% of training time below VT1" it means Z1 + Z2 combined — not just Z1
  (Active Recovery). The primary aerobic base zone is **Z2 (Endurance, 55–75% FTP)**.
- The intervals.icu Z2 = "Aerobic base / fat oxidation" is the main durability-building zone.
- Z1 (Active Recovery, < 55% FTP) alone is not a productive training stimulus — it is used only
  for recovery rides and warmup.

**When this skill says "below VT1" it means `RECOVERY + ENDURANCE` combined** — but in practice
the productive training time is in `ENDURANCE` (Z2). `RECOVERY` (Z1) is circulation only.

RPS agents must use intensity domain names (`ENDURANCE`, `TEMPO`, `THRESHOLD`, `VO2MAX`) in
planning output, never zone numbers. Zone numbers Z1–Z7 + SS are used in workout encoding
only, not in planning-level decisions. The 3-zone research boundaries are used here as
evidence-level framing to explain WHY the `ENDURANCE` domain is dominant.

## The kJ-differentiation principle

**Not all kJ are equal.** Accumulated work above the critical power (CP) causes a
disproportionate decrement in subsequent performance — more than work-matched effort below CP.

Evidence (`ult_core_002`, Mateo-March, Leo et al. 2024): in professional male cyclists,
accumulated work **above CP** impairs short-duration performance significantly more than
equivalent kJ below CP. The implication for planning:

- The majority of weekly kJ must be accumulated **below VT1** (= `RECOVERY + ENDURANCE`
  domains in RPS terminology)
- Every unnecessary session above CP (= `THRESHOLD` / `VO2MAX` domains) reduces the
  durability-building value of the training week
- kJ in `ENDURANCE` accumulate aerobic adaptations without the recovery debt that
  `THRESHOLD` / `VO2MAX` sessions carry

This is the scientific foundation for the kJ-first / volume-first approach used throughout RPS.

## Training distribution for ultra/brevet

Target distribution for athletes building toward ultra/brevet events (evidence: `ult_core_001`,
`dur_core_010`, `dur_core_011`). Research zones are from the 3-zone model; see mapping above.

| Research boundary | intervals.icu zones | RPS domain | % of training time | Purpose |
|---|---|---|---|---|
| Below VT1 | Z1 + Z2 | `RECOVERY` + `ENDURANCE` | 70–80% | Primary durability stimulus; fat oxidation; aerobic base |
| VT1–VT2 | Z3 + SS + Z4 | `TEMPO` + `SWEET_SPOT` + `THRESHOLD` | 10–15% | Submaximal economy; not a primary driver for ultra |
| Above VT2 / CP | Z5 + Z6 + Z7 | `VO2MAX` | 5–15% | Bounded purpose only; raises VO2max ceiling when needed |

In practice: the productive training time below VT1 is predominantly **`ENDURANCE` (Z2)**. Active
recovery rides (Z1) are not counted toward durability stimulus.

**Polarized distribution** (`ENDURANCE` dominant + bounded `VO2MAX`, minimal `TEMPO`/`SWEET_SPOT`/`THRESHOLD`)
associates with durability improvements in professional cyclists (`ult_core_001`). For ultra/brevet,
polarized is preferred over threshold-heavy distribution — `THRESHOLD`/`SWEET_SPOT` accumulation
without `ENDURANCE` foundation risks high CarbOx at race pace.

**The key rule**: training time in `ENDURANCE` (Z2) is the single best proxy for durability
development. Weeks where `ENDURANCE` + `RECOVERY` combined time falls below 60% of total
training time should be flagged — not as a strict blocker, but as a durability-building risk.

## Phase sequencing for ultra/brevet

The canonical ultra/brevet season sequence follows the Kinzlbauer archetype (see
`skills/season/macrocycle-architecture/references/kinzlbauer_season_template.md`):

**VO2max ceiling first → VLamax/economy → specific durability**

This ordering is intentional: a higher VO2max makes every subsequent training stimulus more
productive (the same `ENDURANCE` pace sits at a lower %VO2max → stronger fat-oxidation signal),
and high-intensity tolerance built in the ceiling phase reduces the VLamax load of later aerobic work.

### Metabolic conditioning sequence (across seasons / multi-phase macro)

1. **Raise the aerobic ceiling** (GPP → VO2 foundation → VO2-focused phase): bounded
   `THRESHOLD` / `VO2MAX` blocks → VO2max ↑ → same absolute event pace = lower %VO2max →
   better fat oxidation signal for subsequent phases. Short-interval protocols (30/15 s →
   40/20 s → longer threshold) progress within interval family before escalating.
2. **Lower VLamax / build economy** (economy/durability phase): shift to high `ENDURANCE`
   volume as primary overload axis; sub-threshold (`TEMPO`, `SWEET_SPOT`) and low-cadence work
   increase; carbohydrate oxidation at submaximal intensity falls; VT1 power rises.
3. **Train specific durability** (specific durability phase): event-specific kJ/kg preload
   exposure under accumulated fatigue; standardized fatigued-state quality checks (normal
   performance after ≥ 30 kJ/kg preload) become primary quality metrics.

### Mapping to schema-valid phases

| Schema cycle | Kinzlbauer sub-phase | Primary work | Intensity domains |
|---|---|---|---|
| `Base` — GPP | General preparation | Structural robustness, aerobic continuity | `ENDURANCE`; minimal `TEMPO` |
| `Base` — VO2 foundation | **VO2max ceiling starts here** | Short VO2 intervals on top of Z2 base | `ENDURANCE` + bounded `VO2MAX` |
| `Build` | VO2-focused peak | Concentrated VO2 peak (longer intervals) | `ENDURANCE` + `VO2MAX` + `THRESHOLD` support |
| `Build` | Economy / VLamax lowering | VLamax ↓, FatOx ↑ | `ENDURANCE` dominant; `TEMPO` / `SWEET_SPOT` |
| `Build` | Specific durability | kJ/kg preload; fatigued-state checks | `ENDURANCE` B2B; `TEMPO`/`SWEET_SPOT` hard-late |
| `Peak` | Taper | Volume −41–60%, intensity maintained | `ENDURANCE` + short openers |

Only `Base`, `Build`, `Peak`, `Transition` are valid schema cycle values.

### Phase content rules

**Base phase (ultra context) — two mandatory sub-phases**

The Base cycle contains two structurally distinct sub-phases. Agents must read `build_subtype`
and phase intent to distinguish them; both map to the schema cycle `Base`.

*Sub-phase 1: GPP (General Preparation)*
- Primary goal: structural robustness, musculoskeletal readiness, aerobic continuity
- Intensity: `ENDURANCE` dominant; no `THRESHOLD` / `VO2MAX`; very light `TEMPO` only if
  continuity is stable and recovery is established
- Cadence: `2:1:1` or `2:1` depending on athlete recovery profile
- Duration: 4–6 weeks minimum
- This sub-phase is NOT the whole Base — it is the foundation before the VO2 ceiling work begins

*Sub-phase 2: VO2 Foundation (still within the Base cycle)*
- Primary goal: **VO2max ceiling tolerance — this is where the major ceiling-raising work happens**
  (per Kinzlbauer: the ceiling must be raised BEFORE shifting to VLamax/economy work)
- Intensity: introduce `VO2MAX` (Z5, 105–120% FTP) via short-interval protocols; Z2 `ENDURANCE`
  volume remains protected — ceiling work is added on top of base volume, not instead of it
- Interval progression within the VO2 foundation: 30/15 s protocols from reduced set/rep count
  to full protocol over 2–4 weeks, before progressing to longer intervals (40/20 s)
- Do NOT proceed to economy/VLamax phase before meaningful VO2max adaptation is established

**Why VO2max ceiling work belongs in Base, not only in Build:**
A higher VO2max lowers the relative intensity of subsequent aerobic base training — the same
Z2 watts sit at a lower %VO2max → the fat-oxidation signal is stronger, VLamax falls more
effectively. Building the ceiling first makes every subsequent `ENDURANCE`-dominant week
more metabolically productive. This is the core Kinzlbauer sequencing rationale.

**Build phase — VO2 ceiling peak segment**
- Primary goal: concentrated VO2max emphasis; peak ceiling tolerance
- Intensity: progress to longer VO2max intervals (40/20 s → 3–5 min efforts); `THRESHOLD`
  for clearance support; `ENDURANCE` volume remains protected
- Follows VO2 foundation within Base; represents the concentrated VO2 peak before transitioning
  to economy work

**Build phase — economy/durability segment**
- Primary goal: VLamax lowering; metabolic efficiency at ultra pace; demonstrated durability
- Load character: `ENDURANCE` volume becomes primary overload axis; `THRESHOLD`/`VO2MAX`
  bounded; introduce B2B long rides, preload + hard-later sessions
- Sub-threshold (`TEMPO`, `SWEET_SPOT`) and low-cadence (`K3`) increase → VLamax ↓, CarbOx ↓
- kJ/kg milestones (indicative): 20–25 kJ/kg early → 28–32 kJ/kg mid → 35–40 kJ/kg late
- Hard-late sessions: planned effort in the final hours of a long ride — trains the durability
  adaptation directly (`ult_core_002`, `dur_core_003`)

**Build phase — specific durability segment**
- Primary goal: event-specific kJ/kg preload exposure under accumulated fatigue
- Standardized fatigued-state quality checks: normal performance after ≥ 30 kJ/kg preload
  becomes the primary quality metric
- B2B long rides that simulate the metabolic fatigue pattern of the target event

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
