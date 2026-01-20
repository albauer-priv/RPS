---
Type: Specification
Specification-For: LOAD_ESTIMATION
Specification-ID: LoadEstimationSpec
Version: 1.0

Scope: Shared
Authority: Binding

Applies-To:
  - Macro-Planner
  - Meso-Architect
  - Micro-Planner
  - Workout-Builder

Dependencies:
  - Interface-ID: ZoneModelInterface
    Version: 1.0

Notes: >
  Defines binding rules and formulas for estimating training load.
  kJ is the primary planning and governance metric; TSS is secondary
  and used for explanatory cross-checking only.
---

# load_estimation_spec (kJ-first)

This specification defines **how to estimate training load** for planning and governance in RPS.
Primary steering metric is **kJ**. **TSS is secondary** and used for cross-checking.

**Key idea:**  
- **kJ** approximates total mechanical work / fueling demand proxy (planning priority).  
- **TSS** approximates intensity-weighted stress (supporting metric).
> **Terminology note:** When templates or corridors say “Weekly kJ”, they mean
> **mechanical** `planned_kJ_week` (sum of session kJ), not stress-weighted load.
> Stress-weighted load is captured as `planned_Load_kJ_week` and used for
> governance checks.

This spec is **binding** for all planning agents.

---

## Schema Reference (Normative)

Field locations and structural definitions are defined in the relevant JSON
schemas (e.g., `workouts_plan.schema.json`, `block_governance.schema.json`).
This spec defines calculations and decision rules only. If there is any
structure mismatch, the schema prevails.

## 1) Definitions

### 1.1 Inputs (minimum)
- `FTP_W` : Functional Threshold Power in watts.
- `ZoneModelVersion` : exact version string of the zone model used.
- Planned session structure as a list of segments:
  - `segment_minutes`
  - `segment_domain` (ENDURANCE / TEMPO / SST / VO2MAX / RECOVERY / etc.)
  - `segment_IF` (optional; if omitted, use defaults from zone model)

### 1.2 planned_Load_kJ (Stress-Weighted Load Metric)

`planned_Load_kJ` is the stress-weighted load metric for
- weekly governance
- progression decisions
- overload / deload gating

Mechanical `planned_kJ` remains the primary **planning corridor** metric.

### 1.3 Outputs
Per session:
- `planned_kJ`
- `planned_Load_kJ`   # stress-weighted kJ (stress metric)
- `planned_TSS`
- `planned_IF_adj`
- `kJ_confidence` (HIGH/MED/LOW)
- `TSS_confidence` (HIGH/MED/LOW)

Per week / block:
- sums and bands (`planned_kJ_week`, `planned_Load_kJ_week`, `planned_TSS_week`)
  and compliance flags vs guardrails.

---

## 2) Priority Rule (kJ-first)

1) All governance bands **must exist in kJ** (weekly and/or per key session).
2) If TSS band conflicts with kJ band, **kJ wins**. TSS is used to explain *why* (e.g., “more quality at same kJ”).
3) Agents MUST NOT “fix” kJ by inflating intensity; kJ is corrected primarily via **duration/volume** adjustments.


Primary planning target is `planned_kJ_week`.
`planned_Load_kJ_week` is the governing stress metric.
When a template or corridor says “Weekly kJ”, interpret it as `planned_kJ_week`.

TSS MUST NOT be used to:
- define weekly targets
- drive progression
- justify volume reduction

---

## 3) kJ Estimation (primary)

Primary planning input is target_kJ_per_session
(or derived from target_duration × domain power).

Intensity (IF) is used only to shape how kJ is accumulated,
not to define kJ.


Estimate AvgPower from:
- target duration
- typical power for the domain (from zone model)

IF is derived secondarily as:
IF = AvgPower / FTP


### 3.1 Ground truth (if AvgPower is known)
If you already have/assume an average power:
- `kJ = AvgPower_W × duration_seconds / 1000`

### 3.2 Fallback estimation (IF-based, kJ-unknown)

This method MUST ONLY be used if no target_kJ
or target_duration is available.

We estimate average power from planned intensity:

1) Estimate segment normalized power proxy:
- `NP_i ≈ IF_i × FTP_W`

2) Convert to segment average power proxy:
- `Avg_i ≈ NP_i × r_i`

Where `r_i` is a variability/structure factor (Avg-to-NP ratio).

3) Segment kJ:
- `kJ_i = Avg_i × (segment_minutes × 60) / 1000`

4) Session kJ:
- `planned_kJ = Σ kJ_i`

---

## 4) TSS Estimation (secondary)


TSS is a secondary explanatory metric.
It MUST NOT be used as an optimization target.
Its sole purpose is interpretability and cross-checking.


### 4.1 Single-intensity approximation
For steady sessions approximated by one IF:
- `TSS ≈ hours × IF² × 100`

### 4.2 Mixed-intensity / interval sessions (IF_adj)
For sessions with multiple segments:
- `IF_adj = sqrt( Σ(IF_i^4 × t_i) / Σ(t_i) )`
- `TSS = total_hours × IF_adj² × 100`

These formulas are aligned with the zone model dependency.

---

## 5) kJ-based Load Estimation (primary)

planned_Load_kJ is computed as:

planned_Load_kJ = planned_kJ × IF^α
IF = planned_IF_adj (session-level intensity factor)


Where:
- α defaults to 1.3
- α may be adjusted per sport or athlete profile
- α MUST be constant within a block


Weekly progression, overload and deload decisions
MUST be based on planned_Load_kJ_week,
not on planned_TSS_week.


---

## 6) Default IF values (from zone model)

Agents should pull default typical IF values from the active zone model.
If the zone model provides typical IFs such as:
- ENDURANCE: 0.68
- TEMPO: 0.83
- SST: 0.92
- VO2MAX: 1.12
(illustrative; use the file as source of truth)

Then for a segment with only a domain label:
- `IF_i = IF_typical(domain)`

---

## 7) Default variability factors r_i (Avg-to-NP)

Because NP ≥ AvgPower when variability exists, we define conservative defaults:

### 7.1 r_i table (defaults)
- RECOVERY / ENDURANCE steady: `r = 0.97`  
- TEMPO steady-ish: `r = 0.95`  
- SST / Threshold-like: `r = 0.92`  
- VO2MAX intervals: `r = 0.88`  
- Highly stochastic (race/event): `r = 0.90` (override recommended)

**Rules:**
- If a workout is explicitly “steady” (continuous, low-variability), you MAY set `r` closer to 1.00.
- If a workout contains hard/soft repeats, keep r conservative.
- r is a *planning heuristic*; do not overfit.

### 7.2 Confidence scoring for kJ
Set `kJ_confidence`:
- HIGH: steady sessions, clear duration, domain stable, r well-matched
- MED: mixed session but segment split is clear
- LOW: unclear structure, uncertain FTP, event-like variability, missing segment split

---

## 8) Practical workflow per agent

### 8.1 Macro-Planner (8–32 weeks)
Macro does NOT estimate per-session. Macro produces:
- `kJ_week_band` per phase (min–max)
- optional `TSS_week_band` as explanatory cross-check
- constraints: allowed domains, max QUALITY density, protected recovery

Macro inputs:
- past IST trends (kJ/week) + event calendar + phase objective
Macro outputs:
- **bands**, never point targets.

### 8.2 Meso-Architect (4 weeks)
Block sets 4-week guardrails:
- `kJ_week_band` for each week (or for the block with week-level notes)
- optional `TSS_week_band` as cross-check
- max QUALITY days/week, allowed domains, modality rules (e.g., K3 allowed)

Meso-Architect must ensure:
- the Micro-Planner can satisfy the kJ bands using *volume* adjustments,
  without forcing forbidden domains.

### 8.3 Micro-Planner (weekly ops + workouts)

Micro estimates per workout:
- planned_kJ (volume target)
- planned_Load_kJ (stress)
- planned_TSS (secondary)

Micro adjusts volume to hit kJ targets
and intensity distribution to keep Load within guardrails.


Micro must not:
- invent new QUALITY to “hit kJ”.

---

## 9) Worked examples (template)

### Example A: 2h ENDURANCE (steady)
Inputs:
- FTP=300W
- duration=120min
- domain=ENDURANCE (IF from zone model)
- r=0.97

Compute:
- NP = IF×FTP
- Avg = NP×r
- kJ = Avg×7200/1000
- TSS = 2×IF²×100

### Example B: SST session with warm-up/cool-down
Segments:
- 20min ENDURANCE
- 60min SST (steady)
- 20min ENDURANCE

Compute:
- IF_adj via IF^4 weighting
- planned_kJ via segment kJ sum
- planned_TSS via IF_adj

### Example C: VO2MAX intervals
Segments:
- 20min ENDURANCE
- 40min VO2MAX (interval block)
- 20min ENDURANCE
Use:
- r=0.88 for VO2MAX segment
- IF_adj for TSS

(Use actual typical IFs from the zone model file.)

---

## 10) Compliance & traceability requirements

Every artefact that reports kJ/TSS MUST include:
- `FTP_W` used (or “unknown” + STOP if required)
- `ZoneModelVersion`
- `load_estimation_spec`
- Whether kJ is estimated from AvgPower or from IF+r

Weekly reports MUST include both:
- planned_kJ_week
- planned_Load_kJ_week

Reporting one without the other is non-compliant.

If required inputs are missing:
- Micro-Planner must STOP with `E_BLOCK_INPUT_EMPTY` (or a dedicated `E_LOAD_INPUT_MISSING` if you add it to ERROR_CODES).

---

## 11) Estimation Confidence Classification (Binding)

**Purpose:**
Classify the reliability of kJ load estimations per workout based on
structural and intensity characteristics. Confidence is used for
reporting, traceability, and downstream interpretation only.
It MUST NOT be used for decision-making or governance overrides.

### Confidence Levels

- HIGH
  - steady-state workouts
  - single dominant intensity domain
  - no mixed or stochastic structure
  - examples:
    - ENDURANCE
    - LONG
    - RECOVERY
    - OPTIONAL endurance

- MED
  - structured mixed-intensity workouts
  - clearly bounded intensity blocks
  - predictable distribution
  - examples:
    - SST
    - TEMPO with recoveries
    - VO2 with fixed work/rest

- LOW
  - stochastic or highly variable workouts
  - race simulations
  - variable pacing or intensity drift by design
  - examples:
    - RACE_PACE simulations
    - free-ride equivalents
    - highly variable group rides

### Binding Rules

- Confidence MUST be assigned per workout when kJ estimation is reported.
- Confidence MUST NOT be aggregated or averaged.
- Confidence MUST NOT influence planning decisions.
- If classification is ambiguous:
  → default to the LOWER confidence level.



---

## End of load_estimation_spec
