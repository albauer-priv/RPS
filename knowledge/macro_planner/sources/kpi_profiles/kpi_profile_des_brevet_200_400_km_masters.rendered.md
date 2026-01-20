
# KPI_PROFILE - Decision Thresholds

## YAML Header
```yaml
---
Artifact-Type: KPI_PROFILE
Schema-ID: KPIProfileInterface
Schema-Version: 1.0
Version: 1.0
Created-At: 2026-01-17T06:21:32.377139+00:00
Owner-Agent: Policy-Owner
Authority: Binding
Run-ID: manual-kpi-profile-brevet-200-400-masters
Scope: Shared
Data-Confidence: UNKNOWN
Trace-Upstream:
  - kpi_profile_des_brevet_200_400_km_masters.md@1.0
Trace-Data:
  - N/A
Trace-Events:
  - N/A
---
```

## 1) Profile Metadata

- Profile ID: KPI_Profile_DES_Brevet_200-400km_Masters
- Event type: Brevet
- Distance range: 200-400 km
- Athlete class: Masters 50+
- Primary objective: Performance

## 2) Energetic Load Targets

### 2.1 Weekly Load

| KPI | Green | Yellow | Red | Notes |
|---|---|---|---|---|
| kJ / week | target +/-5 % | +/-5-10 % | > +/-10 % | N/A |

### 2.2 Progression Limits

| KPI | Allowed | Warning | Stop |
|---|---|---|---|
| Weekly kJ increase | <= 7 % | 7-10 % | > 10 % |
| Long ride kJ increase | <= 10 % | 10-15 % | > 15 % |

## 3) Durability

### 3.1 Energetic Pre-Load Requirement

- Single-ride preload (kJ/kg): 30.9-35.3
- Back-to-back preload (kJ/kg): 61.9-70.6
- Single-ride preload (kJ): 3000
- Back-to-back preload (kJ): 6000
- Derived from: kJ / body_mass_window_variants_75_107kg

### 3.2 Body Mass Window Sensitivity

| Body mass window (kg) | Single-day kJ/kg | Back-to-back kJ/kg |
|---|---:|---:|
| 75-87 kg | 34.5-40 | 69-80 |
| 80-92 kg | 32.6-37.5 | 65.2-75 |
| 85-97 kg | 30.9-35.3 | 61.9-70.6 |
| 90-102 kg | 29.4-33.3 | 58.8-66.7 |
| 95-107 kg | 28-31.6 | 56.1-63.2 |

### 3.3 Durability KPIs

| KPI | Green | Yellow | Red | Context | Notes |
|---|---|---|---|---|---|
| Durability Index (DI) | >= 1.00 | 0.98-1.00 | < 0.98 | post preload | N/A |
| Sustained Power Drop (3h vs 1h) | <= 8 % | 8-12 % | > 12 % | long Z2 (3h vs 1h) | N/A |
| Back-to-Back Ratio (BBR) | >= 0.90 | 0.85-0.90 | < 0.85 | IF day2/day1 | N/A |
| FIR (5'/20') | 1.10-1.15 | 1.05-1.10 | < 1.05 | under fatigue | N/A |

## 4) Multi-Day Durability

### 4.1 Applicability
- Not applicable for 200-400 km


### 4.2 Evaluation Window
Not applicable

### 4.3 Purpose
Not applicable

### 4.4 Multi-Day KPIs

| KPI | Green | Yellow | Red | Context | Notes |
|---|---|---|---|---|---|
| BBR Trend (Day n vs Day n-1) | N/A | N/A | N/A | N/A | N/A |
| IF Stability (Delta day-to-day) | N/A | N/A | N/A | N/A | N/A |
| HR Drift Trend | N/A | N/A | N/A | N/A | N/A |

### 4.5 Dominance Rule
Not applicable

## 5) Fueling Stability

- Validity requirement: Not applicable
- Purpose: Not applicable
- Interpretation rule: Not applicable

### 5.1 Fueling KPIs

| KPI | Green | Yellow | Red | Context | Notes |
|---|---|---|---|---|---|
| IF Decline under Preload | N/A | N/A | N/A | N/A | N/A |
| HR Drift under Preload | N/A | N/A | N/A | N/A | N/A |
| Decoupling under Preload | N/A | N/A | N/A | N/A | N/A |

## 6) Efficiency and Drift

| KPI | Green | Yellow | Red | Context | Notes |
|---|---|---|---|---|---|
| Pa:Hr (Z2 >= 90 min) | <= 5 % | 5-7 % | > 7 % | incl. fatigue | N/A |
| HR Drift (Race Pace) | <= 5 % | 5-8 % | > 8 % | late hours | N/A |
| EF trend | stable / up | flat | down | block trend | N/A |

## 7) Intensity Control

| KPI | Green | Yellow | Red | Context | Notes |
|---|---|---|---|---|---|
| VO2 TiZ / week | 18-30 min | 30-35 min | > 35 min | N/A | N/A |
| SST TiZ / week | phase +/-10 % | +/-15 % | > +15 % | N/A | N/A |

## 8) Recovery and Tolerability

| KPI | Green | Yellow | Red | Context | Notes |
|---|---|---|---|---|---|
| TSB (Sun) | -10 to -25 | -25 to -35 | < -35 | N/A | N/A |
| Subjective fatigue | manageable | elevated | persistent | N/A | N/A |

## 9) Decision Rules

- Green: progress via kJ or duration
- Yellow: hold load, repeat block
- Red: mandatory deload (-20-40 % kJ)

## 10) Traceability

- KPI & DES System
- Principles Paper (Section 2 Load, Section 4 Durability, Section 5 Overload)
- Energetic preload: >= 3,000-3,500 kJ single-day; >= 6,000-8,000 kJ back-to-back.
- Relative preload preferred: >= 35-45 kJ/kg single-day; >= 70-90 kJ/kg back-to-back.
- Micro-Planner MAY report KPI observations factually.
- Micro-Planner MUST NOT trigger progression, hold/deload decisions, or interpret KPI color states.
