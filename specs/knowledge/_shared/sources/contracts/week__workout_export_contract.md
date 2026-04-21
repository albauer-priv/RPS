---
Type: Contract
Contract-Name: week__workout_export
Version: 1.2
Status: Active

Scope: Shared
Authority: Binding

From-Agent: Week-Planner
To-Agent: Workout Export

Dependencies:
  - ID: IntervalsWorkoutEBNF
    Version: 1.0
  - ID: WorkoutSyntaxAndValidation
    Version: 1.0
  - ID: WorkoutPolicy
    Version: 1.1
  - ID: WeekPlanInterface
    Version: 1.0
  - ID: TraceabilitySpec
    Version: 1.0
  - ID: FileNamingSpec
    Version: 1.0
---

# Contract: Week-Planner -> Workout Export (v1.2)

## 1) Purpose (Binding)
Define the binding interface between workout design (Week-Planner)
and technical transformation/validation (Workout Export).

## 2) Producer Responsibilities (Week-Planner)
- MUST design workouts and encode them in EBNF-compliant workout text.
- MUST validate workouts before emitting `week_plan_yyyy-ww.json`.
- MUST emit `week_plan_yyyy-ww.json` validated against `week_plan.schema.json`.
- MUST follow:
  - `intervals_workout_ebnf.md`
  - `workout_syntax_and_validation.md`
  - `workout_policy.md`
- MUST NOT emit Intervals.icu JSON.

## 3) Consumer Responsibilities (Workout Export)
- MUST validate input JSON (`week_plan_yyyy-ww.json`) before use and STOP on invalid artefacts.
- MUST validate workout text per the binding rules and validation order.
- MUST convert workout text to Intervals.icu-compatible JSON per `workout_json_spec.md`.
- MUST emit `workouts_yyyy-ww.json` validated against `workouts.schema.json`.
- MUST NOT make training decisions or alter workout intent.

## 4) Artefacts and Schemas (Binding)

### Input (Workout Export consumes)
- `week_plan_yyyy-ww.json` -> `week_plan.schema.json`

### Outputs (Workout Export produces)
- `workouts_yyyy-ww.json` -> `workouts.schema.json`
- ERROR output (text) when validation fails

## 5) Required Content (Binding)

### 5.1 Week Plan Content
The input artefact MUST include:
1. Weekly agenda (Mon-Sun) with Workout-ID per workout day.
2. Exactly one workout definition per Workout-ID including:
   - metadata (ID, title, date, duration, estimated kJ)
   - one workout text block encoded in the binding EBNF

### 5.2 Mandatory Encoding Rules
For every workout text block:
- Durations MUST be time-based only.
- Intensity targets MUST be power % (FTP-based).
- Cadence MUST be specified on every step line.
- Allowed constructs: Warmup, Activation (optional), Main Set, Add-On/Z2 Add-On (optional), Cooldown.
- Repeats/loops MUST follow EBNF rules.
- Plain text descriptions are allowed outside step lines.

## 6) Constraints / Forbidden (Binding)
The input artefact MUST NOT contain:
- Intervals.icu JSON
- absolute power targets (watts)
- heart rate targets
- pace/speed targets
- zone labels (Z1-Z7)
- distance-based steps
- free-ride or unstructured steps
- governance changes or planning decisions

## 7) Validation Order (Binding)
1. Warmup/Cooldown structure (WorkoutPolicy rules).
2. Cadence presence on every step line.
3. EBNF parse (IntervalsWorkoutEBNF).
4. Project subset checks (WorkoutSyntaxAndValidation).
5. Policy checks (WorkoutPolicy, excluding QUALITY target-band lookup).

On any failure: output a Validation Fail Report and do not emit workout outputs.

## 8) Error Handling & STOP Rules
- Workout text not EBNF-conform -> STOP.
- Project subset rules violated -> STOP.
- Required cadence missing -> STOP.
- Forbidden tokens detected -> STOP.
- Workout-ID references inconsistent -> STOP.
- ISO-Week mismatch between artefact header and filename -> STOP.

## 9) Traceability
- Outputs MUST reference input `week_plan_yyyy-ww.json` filename + version.
- Outputs MUST reference Workout-ID and Export Run-ID.

## 10) Precedence
- Not specified.
