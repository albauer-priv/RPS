---
Type: InterfaceSpecification
Interface-For: WELLNESS
Interface-ID: WellnessInterface
Version: 1.0

Scope: Context
Authority: Informational

Applies-To:
  - Data-Pipeline
  - Macro-Planner
  - Meso-Architect
  - Micro-Planner
  - Performance-Analyst

Temporal-Scope:
  From: YYYY-MM-DD
  To: YYYY-MM-DD

Binding-Specs:
  - Specification-ID: TraceabilitySpec
    Version: 1.0

Notes: >
  Defines the canonical wellness structure derived from daily self-report and
  biometric inputs. This artefact is factual and informational only; it must
  never override governance.
---

# Wellness — Interface Template v1.0

## Purpose

Capture daily wellness signals for readiness and recovery context:

- weight
- resting HR / HRV
- sleep duration and quality
- subjective readiness markers

This artefact is **informational only**.
It MUST NOT prescribe training actions or override governance.

---

## Entry Fields (REQUIRED)

Each entry MUST provide every field (values may be null):

- `date` (YYYY-MM-DD)
- `weight_kg`
- `resting_hr_bpm`
- `hrv_ms`
- `sleep_seconds`
- `sleep_quality`
- `soreness`
- `fatigue`
- `stress`
- `mood`
- `motivation`
- `spo2_percent`
- `systolic_mm_hg`
- `diastolic_mm_hg`
- `kcal_consumed`
- `menstrual_phase`
- `updated_at`
- `source`

---

## Data-Level Fields (REQUIRED)

In addition to entries, the artefact MUST include:

- `body_mass_kg` (number or null)
  - Derived from Intervals.icu athlete profile weight when available.
  - If not available, use the latest non-null wellness weight.
  - If neither is available, set to null and note the limitation.

---

## Interpretation Rules

### Macro-Planner
- MAY use wellness signals for contextual risk flags only.
- MUST NOT adjust macro corridors without explicit governance inputs.

### Meso-Architect
- MAY use wellness signals to inform block notes or feed-forward recommendations.
- MUST NOT treat wellness as automatic triggers.

### Micro-Planner
- MAY use wellness signals to adjust session logistics within governance.
- MUST NOT override block guardrails.

---

## Explicit Non-Actions

This artefact MUST NOT:
- define training prescriptions
- recommend load changes on its own
- replace macro/meso guardrails

---

## Self-Check

- [ ] YAML header complete
- [ ] All required fields present for each entry
- [ ] Nulls allowed for missing values
- [ ] No training instructions included

---

## End of WELLNESS Interface Template v1.0
