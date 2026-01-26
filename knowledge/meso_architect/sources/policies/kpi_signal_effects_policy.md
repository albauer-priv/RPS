---
Type: Policy
Policy-For: KPI_SIGNAL_EFFECTS
Policy-ID: KPISignalEffectsPolicy
Version: 1.0

Scope: Shared
Authority: Informational

Applies-To:
  - Micro-Planner
  - Meso-Architect
  - Performance-Analyst

Dependencies:
  - Interface-ID: KPIProfileInterface
    Version: 1.0

Notes: >
  Informational mapping of workout types to KPI signals. Non-decision content.
---

# KPI Signal Effects by Workout Type (Informational)

> **Purpose**  
> These notes provide transparency about which workout types typically provide
> signals relevant to DES KPIs.  
>
> **Non-decision policy:**
> - This mapping is **informational only**.
> - It **MUST NOT** create gates, progression decisions, deloads, or overrides.
> - Decisions remain exclusively in KPI profiles / macro governance.

---

## 1) VO₂max — Long Intervals (Seiler-Type)

**Primary KPIs addressed**
- VO₂ TiZ / week (supportive KPI)
- FIR (5′/20′) *fresh*

**Secondary effects**
- Central VO₂ adaptation → long-term FTP stability

**Non-target metrics**
- Durability Index (DI)
- Pa:Hr under fatigue

**Interpretation note**  
FIR changes are **indicative**, not diagnostically dominant.

---

## 2) VO₂max — Ramp Intervals (Slow-Burn)

**Primary KPIs addressed**
- VO₂ TiZ / week
- FIR (5′/20′) *fresh to lightly fatigued*

**Secondary effects**
- Reduced neuromuscular fatigue → higher block tolerance (masters)

**Non-target metrics**
- BBR
- DI

---

## 3) Sweet Spot — Extensive / Low-Stress

**Primary KPIs addressed**
- FTP durability (3 h @ 0.80–0.85 IF, indirect)
- EF trend (flat / rising)

**Secondary effects**
- VLamax reduction (model-based, not directly measured)

**Non-target metrics**
- VO₂ TiZ

---

## 4) Tempo — Steady State (Brevet-Pace)

**Primary KPIs addressed**
- Pa:Hr (Z2/GA2-adjacent load)
- HR Drift @ Race Pace
- FTP-Durability

**Secondary effects**
- EF stability over long duration

**Non-target metrics**
- FIR

---

## 5) Endurance — Fatigue Finish

**Primary KPIs addressed**
- Durability Index (DI) **after preload**
- Sustained Power Drop (3h vs 1h)
- HR drift under fatigue

**Secondary effects**
- FTP durability under pre-fatigue

**Non-target metrics**
- VO₂ TiZ

**Interpretation note**  
DI is **diagnostically dominant**, but **decision‑neutral**.

---

## 6) Endurance — Back-to-Back Load

**Primary KPIs addressed**
- Back-to-Back Ratio (BBR)
- FIR (5′/20′) *fatigued*

**Secondary effects**
- Tolerance for multi-day kJ load

**Non-target metrics**
- VO₂ TiZ

---

## 7) VO₂max — Tabata / Rønnestad (2:1)

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

## 8) Sweet Spot — Standard (90–93 % FTP)

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

## 9) Threshold

**Primary KPIs addressed**
- Sustained Power (20–40 min)
- FIR (5′/20′) fresh

**Secondary effects**
- Threshold stability under moderate fatigue

**Non-target metrics**
- Durability Index (DI)
- Back-to-Back Ratio (BBR)

---

## 10) Tempo / Over-Under

**Primary KPIs addressed**
- HR-Drift (sub-threshold)
- EF stability

**Secondary effects**
- Lactate shuttle efficiency
- Transition stability under load changes

**Non-target metrics**
- VO₂ TiZ
- BBR

---

## End of KPI Signal Effects Policy

---

## 11) K3 / Strength Endurance

**Primary KPIs addressed**
- Economy-adjacent power stability
- EF-Trend (contextual)

**Secondary effects**
- Neuromuscular fatigue resistance

**Non-target metrics**
- VO₂ TiZ
- FIR
- DI

---

## 12) Endurance / Z2 (Standard)

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

## 13) Recovery

**Primary KPIs addressed**
- None (recovery)

**Secondary effects**
- Improved recovery capacity
- TSB stabilization (indirect)

**Non-target metrics**
- All performance KPIs

---

## 14) Cross-cutting Note (Normative Clarification)

- **Durability metrics are diagnostically dominant, but not decisive.**  
- **Governance actions (Progress, Hold, Deload)** remain with:
  - KPI-Profile
  - Macro-/Meso-Gates
- Workout types **provide data**; they **do not interpret them**.


---

## End of KPI Signal Effects Policy
