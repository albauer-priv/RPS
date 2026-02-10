---
Type: Specification
Specification-For: DES_EVALUATION_POLICY
Specification-ID: DESEvaluationPolicy
Version: 1.0

Scope: Shared
Authority: Binding
Normative-Role: Guardrails
Decision-Authority: GuardrailOnly

Applies-To:
  - Performance-Analyst
  - Season-Planner

Explicitly-Not-For:
  - Phase-Architect
  - Week-Planner

Purpose: >
  Defines the normative evaluation logic for interpreting DES KPI domains
  and deriving diagnostic phase health status. This specification does not
  authorize actions, adjustments, or planning decisions.

---

# DES Evaluation Policy

---

## Authority Separation

This evaluation policy is diagnostic only.

Durability metrics are diagnostically dominant but do not mandate
governance actions.

All training decisions (e.g. progression, deloads, phase termination)
remain the exclusive responsibility of KPI profiles and governance artefacts.

---

## 1. Priority Rule (Dominance Principle)

**The weakest KPI domain determines the overall phase health status.**

Domain dominance order:

1. Durability
2. Recovery / Tolerability
3. Energetic Load
4. Intensity Density
5. Execution / Adherence

> A single RED signal in a higher-ranked domain dominates multiple GREEN signals
> in lower-ranked domains.

---

## 2. Durability Domain (Highest Diagnostic Authority)

Durability KPIs assess fatigue resistance and structural robustness under load.

### Interpretation Rules

- Any **RED** durability indicator results in:
  - `phase_health_status: red`
- **YELLOW** indicators imply limited tolerance and instability.
- **GREEN** indicates sufficient durability for current demands.

Durability indicators include (non-exhaustive):
- Durability Index (DI)
- Pa:Hr during prolonged efforts
- Back-to-Back performance stability
- Sustained power degradation under preload

> Durability signals dominate all other KPI domains.

Durability-based RED classification MUST consider test readiness.

A RED durability outcome SHALL be interpreted as structural ONLY if:
- no high-intensity residual fatigue is present
  (e.g. no VO2max / anaerobic sessions within the preceding 48–72 h), AND
- environmental conditions are comparable (temperature, indoor/outdoor),
- energetic pre-load criteria are met.

Otherwise, the outcome SHALL be flagged as "inconclusive (context-limited)".

Inconclusive evaluations are diagnostic null results.
They MUST NOT be interpreted as Yellow or Red signals
and MUST NOT influence phase health status.

---

## 3. Recovery / Tolerability Domain

Recovery KPIs reflect the athlete’s ability to absorb and recover from load.

### Interpretation Rules

- Persistent recovery degradation outweighs short-term performance stability.
- **RED** recovery signals imply insufficient recovery capacity at current load.
- **YELLOW** signals indicate reduced tolerance.

Indicators may include:
- TSB (trend-based, not point values)
- Subjective fatigue persistence
- Sleep / recovery proxy signals (if available)

---

## 4. Energetic Load Domain (kJ-first)

Energetic KPIs assess load magnitude and progression behavior.

### Interpretation Rules

- Evaluation is based on **weekly and multi-week aggregates**, not single days.
- **RED** energetic signals indicate mismatch between planned and absorbed load.
- Energetic RED without Durability RED does **not automatically** imply structural failure.

> Energetic domain does not override Durability or Recovery domains.

---

## 5. Intensity Density Domain (Subordinate)

Intensity density KPIs evaluate distribution and concentration of high-intensity work.

### Interpretation Rules

- Intensity alone does not determine phase health.
- RED intensity signals only influence phase status
  when higher domains are non-critical.

---

## 6. Execution / Adherence Domain (Lowest Priority)

Execution KPIs describe how consistently the plan was executed.

### Interpretation Rules

- Low adherence reflects system–athlete mismatch, not athlete failure.
- Execution signals are interpreted as **contextual modifiers**, never as primary drivers.

---

## 7. Diagnostic Phase Health Logic (Non-Actionable)

```text
IF any Durability KPI = RED
→ phase_health_status = RED

ELSE IF any Recovery KPI = RED
→ phase_health_status = RED

ELSE IF any KPI = YELLOW
→ phase_health_status = YELLOW

ELSE
→ phase_health_status = GREEN
```
This logic is diagnostic only.
It does not prescribe actions, adjustments, deloads, or phase termination.

---

## 8. Output Semantics

This policy MAY be used to:
- justify status labels (green / yellow / red)
- explain diagnostic dominance
- support narrative interpretation

This policy MUST NOT be used to:
- mandate deloads
- enforce phase termination
- restrict or authorize progression
- issue feed-forwards or governance changes
