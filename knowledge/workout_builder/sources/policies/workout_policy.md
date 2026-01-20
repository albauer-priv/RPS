---
Type: Specification
Specification-For: WORKOUT_POLICY
Specification-ID: WorkoutPolicy
Version: 1.2

Scope: Shared
Authority: Binding

Normative-Role: Guardrails
Decision-Authority: GuardrailOnly

Applies-To:
  - Micro-Planner
  - Workout-Builder

Explicitly-Not-For:
  - Macro-Planner
  - Meso-Architect

Dependencies:
  - Specification-ID: AgendaEnumSpec
    Version: 1.2
  - Specification-ID: IntervalsWorkoutEBNF
    Version: 1.0
  - Specification-ID: WorkoutSyntaxAndValidation
    Version: 1.0


Notes: >
  Single source of truth for workout construction, progression rules, and canonical
  EBNF-compatible examples. This specification constrains workout design only;
  it does not decide scheduling, frequency, or load distribution.
  v1.2: structured Warmup/Cooldown rules and QUALITY intent lookup guidance.
---

# WORKOUT_POLICY


## 1. Purpose

This document defines the **canonical workout construction policy** for the system.
It consolidates:
- workout construction rules
- progression logic
- validation guardrails

It is the **single source of truth** for how workouts are designed once they are permitted by:
- Macro intent
- Meso block governance
- Weekly agenda permissions

This document does **not** decide *when* or *how often* workouts are scheduled.

---

## 2. Normative Role

- **Normative-Role:** Guardrails
- **Decision-Authority:** GuardrailOnly

This policy constrains workout design. It never decides scheduling or load distribution.

---

## 3. Agenda & Intensity Mapping (Binding)

Every workout MUST map to exactly one agenda configuration.

| Workout Intent | Day Role | Intensity Domain | Load Modality |
|---------------|---------|------------------|---------------|
| Endurance | ENDURANCE | ENDURANCE | NONE |
| Recovery | RECOVERY | RECOVERY | NONE |
| Tempo | QUALITY | TEMPO | NONE |
| Sweet Spot | QUALITY | SST | NONE |
| Threshold | QUALITY | THRESHOLD | NONE |
| VO2max | QUALITY | VO2MAX | NONE |
| K3 (strength endurance) | QUALITY | ENDURANCE | K3 |

Violations are invalid.

---

## 4. General Workout Design Principles (Integrated)

### 4.1 Structural Clarity

Every workout MUST follow a clear, explicit structure. Sections are ordered and optionality is strictly defined.

**Canonical Order**
1. Warmup
2. Activation (optional but mandatory for specific workout types)
3. Main Work Block(s)
4. Optional Add-On
5. Cooldown

---

#### Activation (Priming / Neuromuscular & VO₂ Kinetics)

**Purpose**

- Activate VO₂ kinetics
- Recruit fast-twitch fibers
- Prepare cardiovascular system for rapid oxygen uptake

**Placement**

- Directly after Warmup
- Separated by a blank line

**Typical Parameters**

- Duration: 2–4 minutes total
- Repetitions: 2–3
- Intensity: 110–125 % FTP
- Recovery: 55–65 % FTP

**Canonical Example (EBNF-compatible)**

```
#### Activation

3x
- 20s 120% 95rpm
- 40s 60% 85rpm

```

Activation is **mandatory** for VO2max, Threshold and SST workouts, optional for Tempo.

Clarifications:
- Activation MUST NOT be used to compensate for illegal Warmup design.
- Activation represents the transition from prepared state to focused work.

---

#### Add-On (Aerobic Extension Block)

**Purpose**

- Increase aerobic load without neuromuscular stress
- Improve fat oxidation and fatigue resistance
- Fine-tune weekly load (kJ-first)

**Rules**

- Optional but recommended when weekly load allows
- Executed after Main Set(s)
- Never increases intensity classification of the workout

**Typical Parameters**

- Intensity range: 65–80 % FTP
- Format: short ramps or alternating steady blocks
- Cadence: 85–95 rpm

**Canonical Example (EBNF-compatible)**

```
#### Add-On – short alternating ramps (70–80%)

- 3m ramp 70%-75% 85-90rpm
- 3m ramp 75%-80% 85-90rpm
- 3m ramp 80%-72% 85-90rpm
- 3m ramp 72%-78% 85-90rpm
- 3m ramp 78%-70% 85-90rpm
- 4m ramp 75%-60% 85rpm

```

---

#### DEFAULT DESIGN RULES (Binding unless forbidden by governance):

- WarmupBlock REQUIRED (see WarmupBlock rules)
- CooldownBlock REQUIRED (see CooldownBlock rules)
- SST / Threshold / VO2max:
  - Activation block REQUIRED unless explicitly forbidden


#### WarmupBlock (Binding)

Definition:
A WarmupBlock is a structured preparatory sequence executed before Activation or Main Set,
intended to prepare the athlete without introducing training stimulus.

Structural rules:
- A WarmupBlock MUST exist in every workout.
- A WarmupBlock MUST consist of 1-4 step lines.
- Total WarmupBlock duration MUST NOT exceed 10 minutes.
- WarmupBlock steps MUST appear before Activation (if present) or Main Set (if no Activation).

Allowed step types (WarmupBlock):
1) Steady steps
   - Intensity <= ENDURANCE domain
2) Ramp steps
   - Intensity <= ENDURANCE domain
3) Short activation spikes
   - Duration <= 30 seconds per spike
   - Intensity <= TEMPO domain
   - Recovery between spikes >= equal duration at <= ENDURANCE

Forbidden content (WarmupBlock):
- Sustained work (> 60s) in SST, Threshold, or VO2max
- Loops or repeats that include sustained work
- Load modalities (e.g., K3)
- Freeride / unstructured steps
- Hidden progression beyond ENDURANCE + short spikes
- Total WarmupBlock duration > 10 minutes

Violation of any rule invalidates the workout.


#### CooldownBlock (Binding)

Definition:
A CooldownBlock is a structured recovery sequence executed after the Main Set (and optional Add-On),
intended to facilitate physiological down-regulation.

Structural rules:
- A CooldownBlock MUST exist in every workout.
- A CooldownBlock MUST consist of 1-3 step lines.
- Total CooldownBlock duration MUST NOT exceed 8 minutes.
- All CooldownBlock steps MUST appear after the Main Set (and optional Add-On).

Allowed step types (CooldownBlock):
- Steady steps or ramp steps
- For ramp steps, the range MUST be descending (e.g., 60%-45%)
- Intensity MUST be monotonically descending
- Maximum intensity <= ENDURANCE domain

Forbidden content (CooldownBlock):
- Intensity spikes
- Ramps that increase intensity
- Loops or repeats
- Load modalities
- Freeride / unstructured steps
- Any step > ENDURANCE

Violation of any rule invalidates the workout.


#### Backward Compatibility (Binding)

- Workouts compliant with WorkoutPolicy v1.1 remain valid.
- A single ramp step <= 10 minutes automatically satisfies WarmupBlock rules.
- A single ramp step <= 8 minutes automatically satisfies CooldownBlock rules.


#### Warmup/Cooldown Validator Checklist (Informative)

A validator SHOULD be able to verify Warmup/Cooldown legality by checking:
- step count
- summed duration
- maximum intensity domain
- presence of forbidden constructs
- monotonicity (Cooldown)


#### Design Intent (Non-Normative)

This extension exists to:
- allow natural warmup and cooldown patterns
- preserve intent separation (Warmup != Training, Activation != Warmup)
- maintain deterministic validation without heuristics

It does not permit:
- additional training stimulus
- hidden progression
- increased intensity density


---

### 4.2 Workout-Type Principles (Binding)

Each workout type follows a primary design principle. These principles are normative and MUST be respected when designing, progressing, or modifying workouts.

| Workout-Type | Primary Principle | Normative Interpretation |
|--------------|------------------|--------------------------|
| VO₂max | Progressive | Density and stimulus increase over blocks; intensity may rise only after structural progression |
| Sweet Spot | Stable | Intensity held constant; progression via TiZ only |
| K3 / strength endurance | Neuromuscular | Constant tension, low cadence, no intensity spikes |
| Endurance / Z2 | Loose–Variable | Low intensity with optional variability (ramps) |
| Tempo / Over-Under | Rhythmic | Structured oscillation around threshold |

---

### 4.3 Progressive Overload (Binding)

All workout progressions follow the principle of **progressive overload**.

Rules:
- Only **one progression dimension** may be increased per micro-cycle:
  - intensity
  - volume (TiZ)
  - repetitions
- Never increase multiple dimensions simultaneously.

Workout-type specific focus:
- **VO₂max:** repetitions → blocks → interval length → intensity
- **Sweet Spot & K3:** increase TiZ before intensity
- **Endurance:** increase duration by 5–10%, later allow back-to-back days

---

### 4.4 QUALITY Intent -> Intensity Target Band (Binding, Micro-Planner)

Normative status:
- Authority: Binding (Micro-Planner responsibility)
- Decision Authority: GuardrailOnly
- Binding Effect: Required when explicit QUALITY intent is declared upstream

Validation note:
- This rule is enforced by the Micro-Planner and is not required to be validated by the Workout-Builder.

This section provides a lookup heuristic for Micro-Planners to parameterize workouts
within already permitted intensity domains, based on the QUALITY intent declared via:
- `block_governance_*`
- `block_execution_arch_*`

This guidance:
- does not redefine zones,
- does not introduce new limits,
- does not create progression rules.

All workouts MUST still comply with:
- Zone Model (min/max % FTP)
- Workout-Type parameter ranges defined in this policy

#### 4.4.1 Purpose

Within the allowed %FTP ranges of each intensity domain, the QUALITY intent
defines a preferred target band to align workout feel and stress level with block intent.

QUALITY intent answers:
Where inside the allowed window should this workout sit?

#### 4.4.2 Input Signals (Required)

The Micro-Planner MUST apply this lookup if:
- an explicit QUALITY intent is present in block governance or execution architecture
- the corresponding intensity domain is allowed for the day

If no QUALITY intent is specified, the Micro-Planner MUST target the mid-range default of the domain
or apply conservative placement within the allowed domain range.

#### 4.4.3 Lookup Table - Preferred % FTP Target Bands

All values are percent of base FTP and MUST remain within Zone Model boundaries.

A) Stabilization (Maintenance / Hold)

Intent:
Maintain existing capacity with minimal metabolic escalation.

| Intensity Domain | Preferred Target Band (% FTP) |
| ---------------- | ------------------------------ |
| TEMPO (Z3)       | 76-83 %                        |
| SST (Sweet Spot) | 84-90 %                        |
| Threshold        | 91-96 % (only if explicitly allowed) |

B) Build (Development)

Intent:
Elicit controlled adaptation within the allowed domain.
Progression MAY occur, but is not required.

| Intensity Domain | Preferred Target Band (% FTP) |
| ---------------- | ------------------------------ |
| TEMPO (Z3)       | 83-90 %                        |
| SST (Sweet Spot) | 90-95 %                        |
| Threshold        | 96-102 %                       |

C) Overload (Block-Specific, Explicit Only)

Intent:
Temporary stress concentration with accepted fatigue.
Requires explicit macro or block-level authorization.

| Intensity Domain | Preferred Target Band (% FTP) |
| ---------------- | ------------------------------ |
| TEMPO (Z3)       | 88-90 %                        |
| SST (Sweet Spot) | 93-97 %                        |
| Threshold        | 100-105 %                      |

#### 4.4.4 Interpretation Rules (Critical)

- QUALITY intent selects position within a range, not the range itself.
- QUALITY intent MUST NOT:
  - shift zone boundaries,
  - introduce new intensity limits,
  - imply automatic progression.
- Progression logic remains governed exclusively by Section 4.3 (Progressive Overload).

If multiple signals conflict:
- Block Governance > Execution Architecture > This lookup.

#### 4.4.5 Default Behavior (No Intent Provided)

If no QUALITY intent is declared upstream:
- Micro-Planner MUST target the midpoint of the allowed domain range
- or apply conservative placement based on athlete context.

#### 4.4.6 Non-Normative Clarification

This lookup exists to:
- improve coherence between block intent and workout feel,
- reduce accidental over- or under-shooting of intended stress,
- support consistent micro-level execution.

It does not:
- encode training strategy,
- evaluate adaptation,
- trigger progression or deload decisions.

---

## 5. Canonical Workout Types & Policies

> The following sections include **canonical EBNF-compatible workout examples** derived from the original planner examples and guidelines. These examples are normative references and may be parameterized, but not structurally altered.

### 5.1 VO₂max — Tabata / Rønnestad Intervals (2:1)

**Intent**  
Maximize time ≥90% VO₂max using short, dense work intervals with incomplete recovery.

This workout type is explicitly aligned with **Tabata- and Rønnestad-style intervals** using a strict **2:1 work:recovery ratio**.

---

**Design Rules (Binding)**
- Work : Recovery ratio MUST be **2:1**
- Typical formats:
  - 20s / 10s
  - 30s / 15s
  - 40s / 20s
- Recovery is always active (≥ 45–60 % FTP)
- Breathing stress and oxygen kinetics are prioritized over peak power

---

**Parameter Ranges**
- Work intensity: **110–120 % FTP**
- Recovery intensity: **45–60 % FTP**
- Interval duration (work): **20–40 s**
- Target TiZ (work): **18 → 40 min** >90% VO₂max

---

**Progression Rules (Binding)**
Progression MUST follow this order:
1. Increase repetitions per block
2. Increase number of blocks
3. Increase work interval duration (20 → 30 → 40 s)
4. Increase intensity (last)

Only **one dimension** may be progressed per micro-cycle.

---

**Canonical Example — Rønnestad 30/15 (EBNF-compatible)**

```
Warmup
- 10m ramp 50%-75% 85-90rpm

#### Activation

3x
- 20s 120% 95rpm
- 40s 60% 85rpm

Main Set
13x
- 30s 115% 92-95rpm
- 15s 50% 85rpm

- 3m 55% 85rpm

13x
- 30s 115% 92-95rpm
- 15s 50% 85rpm

- 3m 55% 85rpm

13x
- 30s 115% 92-95rpm
- 15s 50% 85rpm

- 3m 55% 85rpm


#### Add-On
- 3m ramp 70%-75% 85-90rpm
- 3m ramp 75%-80% 85-90rpm
- 3m ramp 80%-72% 85-90rpm
- 3m ramp 72%-78% 85-90rpm
- 3m ramp 78%-70% 85-90rpm
- 4m ramp 75%-60% 85rpm

Cooldown
- 8m ramp 60%-45% 80-85rpm
```

---

### 5.2 Sweet Spot (SST)

**Intent**  
Increase sustainable power and fatigue resistance.

**Design Rules**
- Continuous or long intervals
- Controlled discomfort

**Parameter Ranges**
- Intensity: 90–93 % FTP
- Interval length: 8–20 min
- TiZ target: 40 → 60 min

**Progression**
- Extend interval length
- Increase total TiZ
- Small intensity step (+1%) only after volume stabilization

**Canonical Example (EBNF-compatible)**

```
Warmup
- 10m ramp 50%-75% 85rpm

Main Set
4x
- 12m 90% 85-90rpm
- 3m 60% 85rpm

Cooldown
- 8m ramp 60%-45% 80rpm
```

---

### 5.3 Threshold

**Intent**  
Improve lactate clearance and race-pace durability.

**Parameter Ranges**
- Intensity: 95–100 % FTP
- Interval length: 6–15 min

**Progression**
- Increase total time at intensity
- Keep recovery short

**Canonical Example (EBNF-compatible)**

```
Warmup
- 8m ramp 50%-75% 85rpm

Main Set
3x
- 10m 95% 85-90rpm
- 3m 60% 85rpm

Cooldown
- 10m ramp 60%-45% 80rpm
```

---

### 5.4 Tempo / Over-Under

**Intent**  
Develop aerobic durability and lactate clearance through rhythmic oscillation around threshold.

**Primary Principle**  
Rhythmic: structured alternation between under- and over-threshold intensity.

**Parameter Ranges**
- Under: 90–95 % FTP
- Over: 100–105 % FTP
- Oscillation block: 3–6 min

**Progression Rules**
- Increase number of oscillations
- Increase total TiZ
- Intensity remains stable until rhythm is mastered

**Canonical Example (EBNF-compatible)**

```
Warmup
- 8m ramp 50%-75% 85rpm

Main Set
4x
- 3m 95% 85-90rpm
- 1m 105% 90rpm

Cooldown
- 10m ramp 60%-45% 80rpm
```

---

### 5.5 K3 (strength endurance)

**Intent**  
Improve force endurance at sub-threshold intensity.

**Design Rules**
- Low cadence, seated

**Parameter Ranges**
- Intensity: 85–90 % FTP
- Cadence: 50–60 rpm
- Interval length: 6–10 min

**Progression**
- Extend interval duration first
- Add intervals second
- No intensity spikes

**Canonical Example (EBNF-compatible)**

```
Warmup
- 10m ramp 50%-75% 85rpm

Main Set
4x
- 8m 88% 55rpm
- 3m 55% 85rpm

Cooldown
- 8m ramp 60%-45% 80rpm
```

---

### 5.6 Endurance / Z2

**Intent**  
Aerobic base and fatigue resistance.

**Parameter Ranges**
- Intensity: 65–75 % FTP
- Duration: 60 min → multi-hour

**Progression**
- Increase duration by 5–10%
- Back-to-back days allowed

**Canonical Example (EBNF-compatible)**

```
Main Set
- 2h 68-72% 85-90rpm
```

---

### 5.7 VO₂max — Long Intervals (Seiler-Type)

**Intent**  
Central VO₂max stimulus (stroke volume, VO₂ slow component) with low neuromuscular escalation.

**Agenda Mapping (Binding)**
- Workout Intent: VO₂max
- Day Role: QUALITY
- Intensity Domain: VO2MAX
- Load Modality: NONE

**Design Rules (Binding)**
- Interval duration **4–6 minutes**
- Intensity **108–112 % FTP**
- Active recovery **2–3 minutes @ 50–60 % FTP**
- Target metric is **time ≥90 % VO₂max**, not peak power

**Parameter Ranges**
- Repetitions: 4–6
- Target TiZ (work): 16–30 min

**Progression Rules (Binding)**
Progression MUST follow this order:
1. Repetitions
2. Interval length
3. Intensity (last)

**Canonical Example (EBNF-compatible)**
```
Warmup
- 8m ramp 50%-75% 85rpm

#### Activation
3x
- 20s 120% 95rpm
- 40s 60% 85rpm

Main Set
5x
- 5m 110% 92-95rpm
- 2m 55% 85rpm

Cooldown
- 10m ramp 60%-45% 80rpm
```

---

### 5.8 VO₂max — Ramp Intervals (Slow-Burn)

**Intent**  
VO₂ kinetics optimization with gradual load increase, especially suitable for masters.

**Agenda Mapping (Binding)**
- Workout Intent: VO₂max
- Day Role: QUALITY
- Intensity Domain: VO2MAX
- Load Modality: NONE

**Design Rules (Binding)**
- Ramp intervals **6–8 minutes**
- Start ≤95 % FTP -> End **110–115 % FTP**
- No power spikes >115 % FTP

**Parameter Ranges**
- Repetitions: 3–5
- Target TiZ (≥105 % FTP): 12–25 min

**Progression Rules (Binding)**
- Repetitions first
- Then ramp duration
- Intensity end point last

**Canonical Example (EBNF-compatible)**
```
Main Set
4x
- 7m ramp 95%-112% 90-95rpm
- 3m 55% 85rpm
```

---

### 5.9 Sweet Spot — Extensive / Low-Stress

**Intent**  
VLamax reduction and threshold durability with low metabolic escalation.

**Agenda Mapping (Binding)**
- Workout Intent: Sweet Spot
- Day Role: QUALITY
- Intensity Domain: SST
- Load Modality: NONE

**Design Rules (Binding)**
- Intensity **88–90 % FTP**
- Very long intervals with short recoveries
- Do not exceed 90 % FTP

**Parameter Ranges**
- Interval length: 20–35 min
- TiZ target: 50–90 min

**Progression Rules (Binding)**
- TiZ before intensity
- Intensity only after volume stabilization

**Canonical Example (EBNF-compatible)**
```
Main Set
2x
- 30m 88% 85-90rpm
- 3m 60% 85rpm
```

---

### 5.10 Tempo — Steady State (Brevet-Pace)

**Intent**  
Direct preparation for brevet race pacing (0.80–0.85 IF) with HR drift control.

**Agenda Mapping (Binding)**
- Workout Intent: Tempo
- Day Role: QUALITY
- Intensity Domain: TEMPO
- Load Modality: NONE

**Design Rules (Binding)**
- Intensity **80–85 % FTP**
- Long, uninterrupted blocks
- HR drift target ≤5 %

**Parameter Ranges**
- Duration: 45–120 min

**Progression Rules (Binding)**
- Duration before intensity
- Intensity remains constant

**Canonical Example (EBNF-compatible)**
```
Main Set
- 90m 82-85% 88-92rpm
```

---

### 5.11 Endurance — Fatigue Finish

**Intent**  
Durability development: maintain power under prior fatigue.

**Agenda Mapping (Binding)**
- Workout Intent: Endurance
- Day Role: ENDURANCE
- Intensity Domain: ENDURANCE
- Load Modality: NONE

**Design Rules (Binding)**
- Z2 preload **≥120 minutes** required
- Subsequent finish block **tempo or SST**

**Parameter Ranges**
- Preload: 65–72 % FTP
- Finish: 80–88 % FTP
- Finish duration: 20–60 min

**Progression Rules (Binding)**
- Preload duration before finish duration
- Finish intensity remains constant

**Canonical Example (EBNF-compatible)**
```
Main Set
- 2h30m 68-72% 85-90rpm
- 40m 82% 88rpm
```

---

### 5.12 Endurance — Back-to-Back Load (Day-Type)

**Intent**  
Multi-day tolerance and energetic robustness (brevet-specific).

**Agenda Mapping (Binding)**
- Workout Intent: Endurance
- Day Role: ENDURANCE
- Intensity Domain: ENDURANCE
- Load Modality: NONE

**Design Rules (Binding)**
- Valid only as a **day-type definition**
- Individual workout remains Z2-conform

**Parameter Ranges**
- Day load: 35–45 kJ/kg (Day 1)
- Following day: 25–35 kJ/kg + optional tempo finish

**Progression Rules (Binding)**
- kJ increase ≤10 %

---

## 6. KPI Traceability Notes (Non-Decision, Informational)

> **Purpose**  
> These traceability notes are solely for **transparency**:  
> Which **workout type typically provides data/stimuli** that are relevant to **DES KPIs**.
>
> ❗ **None of these mappings creates gate, progression, or deload decisions.**  
> KPI evaluation and decisions remain **exclusively** in the KPI profile / macro-governance layer.

---

### 6.1 VO₂max — Long Intervals (Seiler-Type)

**Primary KPIs addressed**
- VO₂ TiZ / week (supportive KPI)
- FIR (5′/20′) *fresh*

**Secondary effects**
- Central VO₂ adaptation -> long-term FTP stability

**Non-target metrics**
- Durability Index (DI)
- Pa:Hr under fatigue

**Interpretation note**  
FIR changes are **indicative**, not diagnostically dominant.

---

### 6.2 VO₂max — Ramp Intervals (Slow-Burn)

**Primary KPIs addressed**
- VO₂ TiZ / week
- FIR (5′/20′) *fresh to lightly fatigued*

**Secondary effects**
- Reduced neuromuscular fatigue -> higher block tolerance (masters)

**Non-target metrics**
- BBR
- DI

---

### 6.3 Sweet Spot — Extensive / Low-Stress

**Primary KPIs addressed**
- FTP durability (3 h @ 0.80–0.85 IF, indirect)
- EF trend (flat / rising)

**Secondary effects**
- VLamax reduction (model-based, not directly measured)

**Non-target metrics**
- VO₂ TiZ

---

### 6.4 Tempo — Steady State (Brevet-Pace)

**Primary KPIs addressed**
- Pa:Hr (Z2/GA2-adjacent load)
- HR Drift @ Race Pace
- FTP-Durability

**Secondary effects**
- EF stability over long duration

**Non-target metrics**
- FIR

---

### 6.5 Endurance — Fatigue Finish

**Primary KPIs addressed**
- Durability Index (DI) **nach Preload**
- Sustained Power Drop (3h vs 1h)
- HR drift under fatigue

**Secondary effects**
- FTP durability under pre-fatigue

**Non-target metrics**
- VO₂ TiZ

**Interpretation note**  
DI is **diagnostically dominant**, but **decision-neutral**.

---

### 6.6 Endurance — Back-to-Back Load

**Primary KPIs addressed**
- Back-to-Back Ratio (BBR)
- FIR (5′/20′) *fatigued*

**Secondary effects**
- Tolerance for multi-day kJ load

**Non-target metrics**
- VO₂ TiZ

---

### 6.7 VO₂max — Tabata / Rønnestad (2:1)

**Primary KPIs addressed**
- VO₂ TiZ / week (supportive KPI)
- FIR (5′/20′) fresh

**Secondary effects**
- Improved VO₂ kinetics
- Short-term peak power capacity

**Non-target metrics**
- Durability Index (DI)
- Pa:Hr
- BBR

---

## 6.8 Sweet Spot — Standard (90–93 % FTP)

**Primary KPIs addressed**
- FTP durability (indirect)
- EF-Trend

**Secondary effects**
- Lactate clearance capacity
- Metabolic stabilization

**Non-target metrics**
- VO₂ TiZ
- FIR

---

### 6.9 Threshold

**Primary KPIs addressed**
- Sustained Power (20–40 min)
- FIR (5′/20′) fresh

**Secondary effects**
- Threshold stability under moderate fatigue

**Non-target metrics**
- Durability Index (DI)
- Back-to-Back Ratio (BBR)

---

### 6.10 Tempo / Over-Under

**Primary KPIs addressed**
- HR-Drift (sub-threshold)
- EF stability

**Secondary effects**
- Lactate shuttle efficiency
- Transition stability under load changes

**Non-target metrics**
- VO₂ TiZ
- FIR

---

### 6.11 K3 / Strength Endurance

**Primary KPIs addressed**
- Economy-adjacent power stability
- EF-Trend (kontextuell)

**Secondary effects**
- Neuromuscular fatigue resistance

**Non-target metrics**
- VO₂ TiZ
- FIR
- DI

---

### 6.12 Endurance / Z2 (Standard)

**Primary KPIs addressed**
- Pa:Hr (≤5 % target range)
- Durability Index (with sufficient duration)

**Secondary effects**
- EF trend
- Fat metabolism efficiency

**Non-target metrics**
- VO₂ TiZ
- FIR

---

### 6.13 Recovery

**Primary KPIs addressed**
- None (recovery)

**Secondary effects**
- Improved recovery capacity
- TSB stabilization (indirect)

**Non-target metrics**
- All performance KPIs

---

### 6.14 Cross-cutting Note (Normative Clarification)

- **Durability metrics are diagnostically dominant, but not decisive.**  
- **Governance actions (Progress, Hold, Deload)** remain with:
  - KPI-Profile
  - Macro-/Meso-Gates
- Workout types **provide data**; they **do not interpret them**.

---

## 7. Validation Rules

All workouts MUST:
- Conform to Intervals.icu EBNF
- Obey agenda mapping
- Stay within parameter ranges

Workout-Builder MUST reject invalid workouts.

---

## 8. Usage Matrix

| Agent | Usage |
|------|------|
| Micro-Planner | Design & parameterize workouts |
| Workout-Builder | Validate & convert |
| Meso-Architect | ❌ |
| Macro-Planner | ❌ |

---
