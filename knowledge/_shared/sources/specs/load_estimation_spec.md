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
  kJ is the primary planning and governance metric.
---

# load_estimation_spec (kJ-first)

This specification defines **how to estimate training load** for planning and governance in RPS.
Primary steering metric is **kJ**.

**Key idea:**  
- **planned_kJ** captures mechanical work / fueling demand (energy anchor).
- **planned_Load_kJ** is the stress‑weighted load used for governance.
> **Terminology note:** When templates or corridors say “Weekly kJ”, they mean
> **planned_Load_kJ_week** (stress‑weighted load used for governance).
> Mechanical `planned_kJ_week` remains the energy/fueling anchor.

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

### 1.2 planned_kJ (Mechanical Work)

`planned_kJ` is the planned **mechanical work** (unweighted):
- energy / fueling anchor
- volume reality check
- not stress‑weighted

### 1.3 planned_IF (Intensity Factor)

`planned_IF` is the planned session intensity factor (dimensionless).
It characterizes intensity and is used only once in the load formula.

### 1.4 planned_Load_kJ (Stress-Weighted Load Metric)

`planned_Load_kJ` is the stress‑weighted load metric for:
- weekly governance bands
- progression decisions
- overload / deload gating

### 1.3 Outputs
Per session:
- `planned_kJ` (mechanical)
- `planned_Load_kJ`   # stress‑weighted kJ (governance metric)
- `planned_IF_adj` (planned_IF, session‑level)
- `kJ_confidence` (HIGH/MED/LOW)

Per week / block:
- sums and bands (`planned_kJ_week`, `planned_Load_kJ_week`)
- compliance flags vs guardrails (bands refer to `planned_Load_kJ_week`).

---

## 2) Priority Rule (kJ-first)

1) All governance bands **must exist in planned_Load_kJ** (weekly and/or per key session).
2) Agents MUST NOT “fix” load by inflating intensity; load is corrected primarily via **duration/volume** adjustments.

Mechanical `planned_kJ_week` remains the energy anchor.
When a template or corridor says “Weekly kJ”, interpret it as `planned_Load_kJ_week`.

---

## 3) kJ Estimation (primary)

Primary planning input is target_kJ_per_session
(or derived from target_duration × domain power).

Intensity (IF) is used only to shape how kJ is accumulated,
not to define kJ.

**Mechanical work definition (session):**
- Let each segment have duration `t_i` (seconds) and target factor `r_i` (relative to FTP).
- Compute the time‑weighted mean factor:
  - `r_mean = Σ(t_i × r_i) / Σ(t_i)`
- Then:
  - `planned_kJ = (FTP_W × r_mean × T_sec) / 1000`


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

### 3.3 planned_IF derivation (preferred)

When workout segments are available, derive a **planned_IF** that reflects
interval variability without double‑counting intensity:

1) Compute a power‑mean factor (NP‑like):
- `r_eq = ( Σ(t_i × r_i^p) / Σ(t_i) )^(1/p)`
- Use `p = 4` (fixed constant) unless overridden by LoadEstimationSpec.

2) Set:
- `planned_IF = r_eq`

This keeps `planned_kJ` linear in `r_mean` while `planned_IF` captures variability.

### 3.4 Range targets (deterministic midpoint)
If a segment specifies a **range** (e.g., 0.88–0.94), set:
- `r_i = (low + high) / 2`

Do not bias toward the top or bottom of the range unless an explicit
target is provided.

### 3.5 Safety clamps (normative)
Before exponentiation or aggregation, clamp inputs to avoid pathological values:
- `T_sec ≥ 0` (if `T_sec = 0`, then planned_kJ = planned_Load_kJ = 0)
- `r_i` clamped to `[0.0, 1.5]` unless a sport‑specific override exists
- `planned_IF` clamped to `[0.0, 1.3]` unless a sport‑specific override exists

### 3.6 Segment parsing edge cases (normative)
- If `workout_text` exists but **no valid segments** can be extracted
  (parse error or empty list), use **Fallback mode** (Section 5) based on
  the workout intent. If intent is missing, default to `ENDURANCE`.
- If `Σ(t_i) = 0` (all segment durations are zero):
  - set `planned_IF = 0`
  - set `planned_kJ = 0`
  - set `planned_Load_kJ = 0`
- If segments are **mixed notation** (some %FTP, some zone/label):
  - map zone/label segments to `r_i` using the default IF for that domain
    (zone model typical IF or fallback table),
  - include those segments in `Σ(t_i)` and in the power‑mean calculation,
  - do NOT skip unlabeled segments.

### 3.7 Unit conventions (normative)
- Segment duration `t_i` and total duration `T_sec` are **seconds**.
- FTP is **watts**.
- `planned_kJ = (W × seconds) / 1000`.
- `planned_minutes` in the plan is minutes, but conversions to seconds MUST
  multiply by 60 before kJ calculation.

### 3.8 Clamp order (normative)
- Clamp `r_i` **before** applying `r_i^p` in the power‑mean.
- Compute `planned_IF_raw`, then clamp `planned_IF_raw` **before** computing
  `planned_Load_kJ`.
- `planned_Load_kJ` MUST use the **clamped** `planned_IF_raw`.

---

## 4) kJ-based Load Estimation (primary)

planned_Load_kJ is computed as:

planned_Load_kJ = planned_kJ × IF^α
IF = planned_IF_adj (session-level intensity factor)


Where:
- α defaults to 1.3
- α may be adjusted per sport or athlete profile
- α MUST be constant within a block


Weekly progression, overload and deload decisions
MUST be based on planned_Load_kJ_week,
not on any secondary stress metric.


---

## 5) Default IF values (from zone model)

Agents should pull default typical IF values from the active zone model.
If the zone model provides typical IFs such as:
- ENDURANCE: 0.68
- TEMPO: 0.83
- SST: 0.92
- VO2MAX: 1.12
(illustrative; use the file as source of truth)

Then for a segment with only a domain label:
- `IF_i = IF_typical(domain)`

If the zone model does not provide typical IF defaults, use this deterministic fallback:

| Domain / Intent | planned_IF default |
| --- | ---: |
| REST / OFF | 0.000 |
| RECOVERY | 0.55 |
| ENDURANCE | 0.65 |
| ENDURANCE+ | 0.70 |
| TEMPO | 0.80 |
| SWEET SPOT | 0.90 |
| THRESHOLD | 1.00 |
| VO2MAX | 1.10 |
| ANAEROBIC / SPRINT | 1.15 |

**Fallback mode (normative):** The table above supplies **planned_IF directly**
(not r_i). When using this fallback:
- set `planned_IF = IF_default`
- compute `planned_kJ = (FTP × planned_IF × T_sec) / 1000`

---

## 6) Default variability factors r_i (Avg-to-NP)

Because NP ≥ AvgPower when variability exists, we define conservative defaults:

### 6.1 r_i table (defaults)
- RECOVERY / ENDURANCE steady: `r = 0.97`  
- TEMPO steady-ish: `r = 0.95`  
- SST / Threshold-like: `r = 0.92`  
- VO2MAX intervals: `r = 0.88`  
- Highly stochastic (race/event): `r = 0.90` (override recommended)

**Rules:**
- If a workout is explicitly “steady” (continuous, low-variability), you MAY set `r` closer to 1.00.
- If a workout contains hard/soft repeats, keep r conservative.
- r is a *planning heuristic*; do not overfit.

### 6.2 Confidence scoring for kJ
Set `kJ_confidence`:
- HIGH: steady sessions, clear duration, domain stable, r well-matched
- MED: mixed session but segment split is clear
- LOW: unclear structure, uncertain FTP, event-like variability, missing segment split

---

## 7) Weekly band interpretation & rounding

### 7.1 Governance interpretation
`weekly_kj_bands` refer to **planned_Load_kJ_week** (stress‑weighted).
Mechanical `planned_kJ_week` remains the energy anchor for fueling and volume reality checks.

### 7.2 Rounding rules (output)
Compute using **unrounded** floats and round only at output:
- `planned_IF_out = round(planned_IF_raw, 3)`
- `planned_kJ_out = int(round(planned_kJ_raw))`
- `planned_Load_kJ_out = int(round(planned_kJ_raw * planned_IF_raw**α))`

Do NOT round `planned_IF` before computing `planned_Load_kJ`.
Store `planned_kJ_out` and `planned_Load_kJ_out` as 64‑bit integers
or a safe integer type to avoid overflow in large weeks.

### 7.3 Optional weekly distribution policy (non‑binding)
If a **Load Distribution Policy** is provided (optional), it may define
day‑weighting rules for distributing weekly planned_Load_kJ across the week.
This policy is advisory only and MUST NOT override governance bands.

---

## 8) α source of truth (normative)
`α` MUST come from LoadEstimationSpec (global default).
It may only be overridden by an explicit governance artefact if such a field
is introduced; otherwise treat it as constant for all weeks.

---

## 9) Practical workflow per agent

### 8.1 Macro-Planner (8–32 weeks)
Macro does NOT estimate per-session. Macro produces:
- `kJ_week_band` per phase (min–max)
- constraints: allowed domains, max QUALITY density, protected recovery

Macro inputs:
- past IST trends (kJ/week) + event calendar + phase objective
Macro outputs:
- **bands**, never point targets.

### 8.2 Meso-Architect (4 weeks)
Block sets block-level guardrails:
- `kJ_week_band` for each week (or for the block with week-level notes)
- max QUALITY days/week, allowed domains, modality rules (e.g., K3 allowed)

Meso-Architect must ensure:
- the Micro-Planner can satisfy the kJ bands using *volume* adjustments,
  without forcing forbidden domains.

### 8.3 Micro-Planner (weekly ops + workouts)

Micro estimates per workout:
- planned_kJ (volume target)
- planned_Load_kJ (stress)

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
- domain=ENDURANCE (IF default 0.65)
- r=0.97 (steady)

Steps:
1) r_mean = 0.65
2) planned_kJ = (300 × 0.65 × 7200) / 1000 = 1404 kJ
3) planned_IF = 0.65 (steady; r_eq = r_mean)
4) planned_Load_kJ = 1404 × 0.65^1.3 ≈ 802 kJ

Compute:
- NP = IF×FTP
- Avg = NP×r
- kJ = Avg×7200/1000

### Example B: SST session with warm-up/cool-down
Segments:
- 20min ENDURANCE
- 60min SST (steady)
- 20min ENDURANCE

Compute:
- IF_adj via IF^4 weighting
- planned_kJ via segment kJ sum

### Example C: VO2MAX intervals
Segments:
- 20min ENDURANCE
- 40min VO2MAX (interval block)
- 20min ENDURANCE
Use:
- r=0.88 for VO2MAX segment

(Use actual typical IFs from the zone model file.)

---

## 10) Compliance & traceability requirements

Every artefact that reports kJ MUST include:
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
