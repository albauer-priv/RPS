---
Type: Specification
Specification-For: PLANNING_PRINCIPLES
Specification-ID: DurabilityFirstPrinciples
Version: 1.2

Scope: Shared
Authority: Binding

Normative-Role: Guardrails
Decision-Authority: GuardrailOnly

Applies-To:
  - Macro-Planner
  - Meso-Architect
  - Micro-Planner

Related-Evidence:
  - Specification-ID: DurabilityEvidenceLayer
    Version: 1.0

Notes: >
  Defines time-stable, durability-first planning principles for ultra-distance
  and brevet cycling. The document constrains how planning decisions are made
  but defines no numeric thresholds, gates, or prescriptions. All concrete
  decision logic resides in KPI profiles and governance artefacts.
---




# Principles Paper
## Durability-First Annual Training Planning for Ultra-Distance and Brevet Cycling

**Version:** v1.2 - 2026

---

## HARD CONSTRAINT
This document MUST NOT be used to:
- justify micro-level decisions
- override governance artefacts
- replace KPI profiles or contracts


---

## 1. Purpose and Performance Model

This document defines the **time-stable principles** for planning an Annual Training Plan (ATP) for ultra, marathon, and brevet distances (200-600 km). It is **not** a training plan, but a **decision and thinking framework** for coaches, athletes, and planning agents.

### 1.1 Central performance goal: durability
Durability describes the ability to **maintain submaximal performance over long durations with minimal physiological, biomechanical, and mental decay**.

What matters is not fresh peak performance (FTP, VO2max), but:
- onset timing of fatigue
- magnitude of performance and efficiency loss under preload
- stability of pacing, heart rate, and RPE over many hours

Durability is treated as an **independent performance dimension** on par with VO2max, threshold, and economy.

---

## 2. Load and Energetics - kJ-first System

### 2.1 Principle
For ultra and brevet distances, **mechanical work (kilojoules, kJ)** is the **primary steering and comparison metric**.

> **kJ connects training load, energetics, fueling, and long-term durability.**
> **Terminology:** "Weekly kJ" means **mechanical** kJ (sum of session kJ),
> not stress-weighted load.

### 2.2 Hierarchy of steering metrics
1. **Primary:** kJ (per session, week, block, year)
2. **Secondary:** CTL, ATL, TSB (tolerance and trend)
3. **Tertiary:** IF, intensity distribution (characterization)

CTL/TSB are deliberately **not** used as leading metrics because they do not represent fatigue resistance.

### 2.3 kJ and durability
Durability metrics are **only valid** when they:
- are measured after a **defined energetic preload**, and
- are interpreted relative to the work performed.

Performance stability without preload is **not meaningful** for ultra performance.

### 2.4 Coupling training and fueling
Fueling is **not planned separately**; it is derived from energetic load:
- carbohydrate intake aligns with the **hourly kJ rate**
- the goal is performance stability, not short-term frugality

Concrete calculations and thresholds are **outside this document** in the KPI/DES system.

---

## 3. Macro Periodization and Annual Logic

### 3.1 Base structure
The annual plan follows a classic, robust sequence:

1. **Base:** aerobic foundation, volume, structural robustness
2. **Build:** durability stimuli plus dosed intensity
3. **Specificity:** event simulation, pacing, fueling
4. **Taper:** fatigue reduction while maintaining sharpness

### 3.2 Backplanning and event prioritization (Agent-Executable Planning Cookbook)

This cookbook defines how planning agents must reason (Macro / Meso / Micro). It governs
annual structure, event prioritization, peak logic, and conflict resolution. It does not define
workouts, numeric load targets, or intensity prescriptions.

#### 3.2.1 Agent roles and responsibilities

**Macro Planner (Season Architect)**
- Authority: highest-level planner; owns annual structure and event logic.
- Responsibilities: interpret Season Brief; classify events (A/B/C); define macrocycles; determine peak windows; enforce priority hierarchy.
- Prohibitions: must not create workouts; must not optimize short-term performance at the expense of macro logic.

**Meso Architect (Block Designer)**
- Authority: subordinate to Macro Planner; owns block-level structure.
- Responsibilities: translate macro phases into blocks; assign blocks to calendar ranges; respect taper and recovery constraints; integrate B/C events per macro rules.
- Prohibitions: must not redefine event priority; must not introduce additional peaks.

**Micro Planner (Execution Layer)**
- Authority: lowest level; implements sessions.
- Responsibilities: execute block intent; manage day-to-day load; respect fatigue and recovery signals.
- Prohibitions: must not compensate missed sessions; must not override block intent.

#### 3.2.2 Core planning principle (Hard rule)
ALL plans MUST be built via backplanning from the highest-priority event (A event). Forward-only
planning without reference to the A event is invalid.

#### 3.2.3 Event classification logic

**A event**
- Definition: primary performance objective; receives a dedicated taper; defines macrocycle structure.
- Rules: only one A event per macrocycle; a macrocycle = Base -> Build -> Peak -> Transition (recovery).

**B event**
- Definition: secondary event supporting the A event.
- Allowed purposes: specificity rehearsal, durability testing, pacing/fueling validation.
- Rules: no full taper; may receive short load reduction only; must not disrupt macro progression.

**C event**
- Definition: low-priority event treated as training.
- Rules: no taper; no structural changes; no recovery debt carried forward.

#### 3.2.4 Backplanning algorithm (Macro level)

**Inputs**
- Season Brief
- Events calendar
- Athlete constraints

**Process**
1. Identify candidate events.
2. Select A event(s) based on objectives.
3. Assign each A event to a macrocycle.
4. Place taper directly before each A event.
5. Build phases backward: Specificity -> Build -> Base.
6. Assign B and C events into the existing structure.

**Outputs**
- Macrocycle map
- Event priority table
- Peak windows

#### 3.2.5 Multiple A events (Allowed models only)

**Model 1: Multiple macrocycles (A1/A2)**
- Conditions: at least 8-12 weeks between A events; full recovery possible between cycles.
- Rules: each A event gets its own macrocycle; no carry-over of peak fatigue; Transition (recovery) phase is mandatory.

**Model 2: A-event cluster (Peak window)**
- Conditions: events within ~2-6 weeks; similar performance demands; durability prioritized over sharpness.
- Rules: single build; single peak window; no repeated tapers; recovery only after the cluster.

**Explicitly forbidden**
- Multiple independent tapers within short intervals
- Rebuilding fitness between clustered events
- Overlapping macrocycles

#### 3.2.6 Priority hierarchy (Conflict resolution)
When constraints collide, resolve conflicts in this order:
1. A event integrity
2. Macrocycle structure
3. Recovery and fatigue tolerance
4. B events
5. C events

Lower-priority items are modified or removed first.

#### 3.2.7 Taper rules (Global)
- Taper exists only for A events.
- B events may receive minor load adjustment.
- C events receive none.
- Taper duration and depth scale with event duration, accumulated fatigue, and athlete age/resilience.

#### 3.2.8 Load and consistency guardrails
- Missed sessions are not made up.
- Consistency outweighs intensity.
- Fatigue management is a performance variable.
- Deloads are planned, non-negotiable, and active components of adaptation.

#### 3.2.9 Naming and state management
Use unambiguous labels: `A1`, `A2`, `A_block`, `Peak_Window_1`, `B_support_event`, `C_training_event`.
Avoid ambiguous terms like "important race" or "key event" without a priority class.

#### 3.2.10 Validation checklist (Agent self-test)
Before finalizing a plan, verify:
- Exactly one A event per macrocycle.
- Every taper serves an A event.
- B and C events fit without breaking structure.
- Recovery is explicitly planned.
- Peak logic is consistent with event spacing.

If any answer is "no", the plan is invalid.

**Execution summary:** Agents must optimize for long-term performance integrity, not short-term event satisfaction.

### 3.3 3:1 cycles
Load typically follows **3:1 cycles**:
- 2-3 progressive load weeks
- 1 deliberate deload/consolidation week

Masters athletes use more conservative progressions and larger deloads.

### 3.4 Permitted macro archetype: "Kinzlbauer macro template" (ultra / brevet)

**Status:** permitted macro-level pattern.
**Scope:** macro architecture only (phase sequencing, emphasis, and intent).
**Non-scope:** no workout prescriptions, no session-level structure, no numeric progression rules. Concrete dosing and guardrails remain owned by KPI profiles and governance artefacts.

This archetype is useful when the season objective prioritizes long-distance performance (marathon -> ultracycling) and the athlete's constraints require a time-efficient weekday structure with weekend volume expansion, while maintaining a coherent progression that first develops the aerobic ceiling (VO2max) and then improves long-duration economy (VLamax lowering + volume stabilization).

#### 3.4.1 Intent and sequencing (macro-only)

The template follows a two-step progression logic:

1. **Aerobic ceiling first (VO2 foundation -> VO2 block):** establish or reinforce VO2max as a system-wide "ceiling" before large volume ramps.
2. **Economy and durability next (VLamax lowering + volume raise):** shift emphasis toward metabolic efficiency and fatigue-resilience while stabilizing the aerobic ceiling.

A typical high-level sequence (illustrative, scenario-level instantiation defines exact block lengths) is:

- **Phase A - VO2 foundation (short build):** build tolerance and repeatability of high-intensity exposure without compromising low-intensity volume.
- **Phase B - VO2-focused block:** concentrated VO2 emphasis with protected recovery; low-intensity remains the dominant volume.
- **Phase C - Transition coupling:** maintain VO2 exposure while introducing VLamax-lowering emphasis (still macro-level: "domains allowed/forbidden", not sessions).
- **Phase D - VLamax reduction + VO2 stabilization + volume raise:** longer consolidation period where volume becomes the primary overload axis and metabolic efficiency is the dominant focus.
- **Repeatable cycle option:** the VLamax-focused cycle can be repeated once more to time a peak later in the season, if the planning horizon and recovery capacity support it.

#### 3.4.2 Allowed macro characteristics (what makes it "Kinzlbauer-like")

At macro level, the following characteristics define compliance with this archetype:

- **Progression order:** intensification precedes major volume escalation (first "intensity tolerance", then "volume stability").
- **Weekday time-crunch compatibility:** structure assumes most athletes have limited weekday time; weekend rides are the primary lever for long-duration exposure.
- **Volume expansion is conditional:** athletes already adapted to higher volume may add additional low-intensity volume, but only when it does not violate KPI guardrails (fatigue stability, recovery protection, fueling stability).
- **Durability is explicit:** long-duration exposure and late-ride quality are progressively emphasized as the plan moves from VO2 emphasis toward economy/durability.

#### 3.4.3 How this maps into Macro Overview artefacts

When this archetype is used, it must be expressed via macro artefacts only:

- **Phase naming and cycle labels:** Base/Build/Peak/Transition remain valid; the archetype influences phase intent and allowed/forbidden domains.
- **Weekly load corridors:** kJ-first corridors are derived from the athlete's historical activities_trend baselines and constrained by the chosen KPI profile; the archetype does not override governance guardrails.
- **Intensity semantics:** define allowed/forbidden intensity domains per phase (e.g., VO2 exposure emphasized early; later phases emphasize VLamax-lowering domains and long-duration durability), without specifying workouts.

#### 3.4.4 Traceability anchors (internal bibliography)

Use the following items as traceability anchors in justification.citations when instantiating this archetype:

- **Kinzlbauer (Science2Performance):** "Metabolic efficiency for brevets: FatMax and fueling" (Durability Bibliography #38).
- **Sitzfleisch Podcast (Kinzlbauer):**
  - Ep. 154 "Ultracycling-Training mit Coach Max Kinzlbauer" (Bibliography #61/#62).
  - Ep. 218 "Richtig regenerieren und smart trainieren mit Max Kinzlbauer" (Bibliography #63).
  - Optional supporting context: Ep. 39 (K3 practice) (Bibliography #60), Ep. 272 (training camps) (Bibliography #64).

### 3.5 3:1 default pattern and alternatives

**Default: 3:1 (most athletes)**

**Load weeks (2-3 weeks):**
- Progress via **one axis** only (kJ/duration **or** frequency **or** density/complexity).
- Intensity stays a later lever: prioritize "consistently long" over "too often hard".

**Deload/consolidation week (1 week):**
- Goal: **secure adaptation + reduce fatigue** without breaking rhythm.
- Practical implementation:
  - **Volume/kJ clearly down** (noticeably lower, not just marginal).
  - **Frequency can stay**, but sessions are shorter and truly easy.
  - **No durability density** (no back-to-back, no hard-late, no overload).
  - **Optional: one very small quality touch**, only if intensity is required
    (short, clean, non-fatiguing).

**When 3:1 is not the best default**

**2:1 (more conservative)** is often better when:
- Masters/older athletes, high life stress, unstable sleep.
- Volume/frequency is being ramped up from a lower base.
- Week 3 regularly collapses (HR/RPE drift, heavy legs, motivation drop).

**4:1 (more aggressive)** can work when:
- Very high training stability, good sleep/stress buffer.
- Base phase with high LIT and low complexity/intensity.
- Athlete history shows 3:1 deloads are too early.

**Decision rule (simple and reliable)**
- If week 3 regularly tips: switch to **2:1** (or make week 3 half-load, then deload).
- If week 3 is stable but deload feels under-dosed: keep **3:1**, but make deload a
  **consolidation** (hold frequency, reduce volume/density).
- If 3:1 is stable and base is very quiet: test **4:1** only with clear early-warning
  signals and strict countermeasures.

---

## 4. Training Content Taxonomy (What trains what?)

This chapter describes training content **independent of the calendar**.

### 4.1 Z2 / GA1-GA2 (low intensity)
- foundation of durability
- improves mitochondrial density and fat metabolism
- trains passive structures

### 4.2 VO2max / high intensity
- raises the aerobic ceiling
- improves load tolerance
- use: **rarely, deliberately, when recovered**

### 4.3 Sweet Spot / threshold
- economy near race pace
- stabilizes sustained power
- moderate effect on VLamax

### 4.4 K3 / low cadence
- torque tolerance
- passive structures (tendons, joints)
- pedaling economy under load

### 4.5 Durability-specific stimuli
- hard-late intervals
- back-to-back load
- pre-fatigue protocols
- long Z2 sessions with stable output

These sessions are **not hard**, but **long and consistent**.

---

## 4.6 Intensity Distribution - polarized vs pyramidal (and what to follow)

**Goal of this section**
Intensity distribution describes how weekly work is distributed across intensities. In a durability-first context it is a characterization and quality parameter, but not the primary steering lever (kJ stays primary).

### 4.6.1 Terms (precise and practical)

- **Polarized:** very high low intensity (Z1/Z2), little moderate work, and a small, targeted share of high intensity (VO2 and above threshold).
- **Pyramidal:** high low intensity, a larger share of moderate work (Tempo/SST/Threshold), little high intensity.

Both models rely on high LIT proportions; the difference is **how much middle** (Tempo/SST/Threshold) is used.

### 4.6.2 Which is more appropriate - polarized or pyramidal?

In an ultra/brevet durability-first system, the default answer is:

- **Base/General build:** more **pyramidal-leaning** (high LIT, dosed Tempo/SST as an economical race-adjacent stimulus, little HI).
- **Build/Performance sharpening:** more **polarized** (LIT stays high, moderate density is capped, 1-2 high-quality HI sessions when recovered).

Rationale (system logic and evidence alignment):

- Durability depends on **LIT dominance** and the ability to keep quality stable under preload; too much moderate work raises overall fatigue and blurs intensity separation.
- HIIT is effective for ceiling/VO2, but in ultra contexts it is only a support capacity and must remain recovery-compatible.
- Moderate contents (Tempo/SST) can improve economy near brevet pace, but must not compromise long, stable work.

### 4.6.3 What must be followed - decision rules (policy)

**Rule 1: Primacy of durability work**
Regardless of polarized or pyramidal, the weekly architecture must ensure long, stable Z2 work (and/or B2B/hard-late stimuli) remains repeatable. If intensity distribution threatens that, it is wrong.

**Rule 2: Choose the model based on the limiting factor**

- If the limiting factor is **aerobic ceiling/VO2** and Z2 base is stable - **polarized**.
- If the limiting factor is **economy/race pace comfort** (long steady efforts feel costly) - **pyramidal-leaning** with dosed Tempo/SST.
- If the limiting factor is **recovery/stress/masters recovery** - **more polarized in the sense of more easy, less middle**, and HI rarely or in very small doses.

**Rule 3: The middle is a budget, not a default**
Moderate intensity (Tempo/SST/Threshold) is treated as a budget:

- used when it has a clear purpose (economy, longer steady stability, event-specific pace)
- reduced once it degrades HI quality or LIT consistency

**Rule 4: HI only if it is truly HI (and recovered)**
A HI stimulus is only useful if it:

- is performed with adequate freshness
- holds the target quality (clean repeats, stable power)
- is not stacked on top of an already maximized kJ week

**Rule 5: Specificity rises near the A event**
Closer to the A event, the relevance of the following increases:

- event-like duration, pace stability, fueling stability, B2B/hard-late

This typically means **less random moderate work** and more targeted specificity.

### 4.6.4 Practical default (no numbers)

- **Default:** LIT-dominant, moderately dosed (pyramidal-leaning), HI rarely.
- **Build/sharpen:** LIT stays dominant, moderate density decreases, HI quality rises (polarized).
- **High fatigue:** LIT yes, but less density/complexity; pause HI; use deload actively.

---

## 5. Progressive Overload - Durability-First Logic

**Goal of this section**
Progressive overload in a durability-first system is not more intensity; it is **more robust, repeatable work** with stable execution. The purpose is to enable later fatigue and lower drift (HR/RPE/economy) under energetic preload.

### 5.1 Definition (for this system)

Progressive overload means a **planned, stepwise increase** in training stimulus over weeks/blocks **without** compromising consistency.

In a brevet/ultra context:

- Primary stimulus: mechanical work (kJ) plus duration
- Secondary: frequency and repeatability
- Tertiary: complexity/density
- Intensity: last lever (sparingly, dosed, recovered)

### 5.2 Allowed overload axes (hierarchy)

1. **Time / kJ (primary)**
   - longer Z2 sessions, longer steady segments, more total weekly kJ
2. **Frequency (secondary)**
   - additional short Z2 stack sessions, better distribution vs single monster days
3. **Density / complexity (tertiary)**
   - same weekly kJ, but harder: back-to-back, hard-late, pre-fatigue protocols
4. **Intensity (quaternary)**
   - VO2/high intensity only when quality is high and the LIT base is protected

### 5.3 Concrete progression rules (guardrails, no numbers)

These rules are principle-based by design (numbers belong in KPI/DES).

**A. One variable per step**
Per week/progression step, increase **at most one axis** (e.g., only kJ **or** only frequency). This reduces attribution noise and protects consistency.

**B. Stability first - progress only with stable execution**
Overload is only allowed when the prior week(s) were stable:

- pacing/output in Z2/steady without disproportionate drift
- RPE remains expected
- no accumulation of red flags (sleep, mood, motivation, pain)

Rationale: Durability is defined by **stability under load**, not fresh peak values.

**C. Deload is part of the overload system (not optional)**
Deload/consolidation is an active component to secure adaptation and enable the next progression. "More" without consolidation just moves fatigue forward.

**D. Protect intensity by reducing other levers**
If a week contains true quality (VO2/high intensity), overload is **not** maximized via kJ/density at the same time. Goal: hard stays hard, long stays long - without gray mixed fatigue.

### 5.4 Durability-specific overload patterns (examples as patterns, not plans)

- **Extensify pattern:** Z2 duration/kJ increases over 2-3 weeks, then deload
- **Repeatability pattern:** same weekly kJ, but more sessions (better frequency)
- **Complexify pattern:** same weekly kJ, but 1-2 targeted durability sessions (back-to-back or hard-late)

### 5.5 Common errors (and why they are costly in ultra contexts)

- **Intensity too early as overload lever:** raises fatigue density and reduces the ability to consistently reproduce Z2/kJ work.
- **Missed sessions are made up:** violates failure-tolerance principles; leads to load spikes instead of robustness.
- **Moderate gray work as default:** can make short-term fitness feel higher, but undermines long-term stability and freshness.

---

## 6. Decision Gates and Failure Tolerance

### 6.1 Principles
- consistency beats perfection
- missed sessions are **not made up**
- fatigue management is performance management

### 6.2 Deloads
Deloads are **active training components**, not weakness:
- reduce volume or intensity
- consolidate adaptations

### 6.3 Masters logic
- larger recovery windows
- lower intensity density
- priority on quality and consistency

---

## 7. Mental and Event Specifics

Durability is also mental:
- monotony
- sleep deprivation
- cold, rain, night rides

Simulation is **dosed**, not maximal.

---

## 8. Boundary to Other Documents

This principles paper contains:
- **no** season dates
- **no** KPI thresholds
- **no** weekly plans

It explicitly references:
- *Season Brief* (athlete and goals)
- *KPI / DES system* (measurement and decisions)

---

## 9. Closing Remark

A good ultra plan does not maximize short-term fitness, but:

> **the ability to reproduce performance under fatigue.**
