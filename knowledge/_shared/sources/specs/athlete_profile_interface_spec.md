---
Type: InterfaceSpecification
Interface-For: ATHLETE_PROFILE
Interface-ID: AthleteProfileInterface
Version: 1.0

Scope: Shared
Authority: Binding

Applies-To:
  - Season-Scenario-Agent
  - Season-Planner
  - Phase-Architect
  - Week-Planner
  - Performance-Analyst
  - Coach

Binding-Specs:
  - Specification-ID: TraceabilitySpec
    Version: 1.0
  - Specification-ID: FileNamingSpec
    Version: 1.0

Notes: >
  Canonical interface for athlete profile + goals. This replaces legacy season
  brief content. It is input-only and must not contain planning decisions.
---

# Athlete Profile Interface Specification

## 1) Purpose (Binding)
An **ATHLETE_PROFILE** captures stable athlete context, objectives, and constraints
that shape planning decisions. It is consumed by planning agents and the coach.

## 2) Required Fields (Binding)
Implementations MUST provide:

### 2.1 Profile
- `athlete_id`
- `year`

### 2.2 Objectives
- `primary`

## 3) Recommended Fields (Non‑binding)
- `athlete_name`, `age`, `sex`, `age_group`
- `body_mass_kg`, `training_age_years`, `primary_disciplines`
- `location_time_zone`, `athlete_story`
- `secondary`, `priority_order`
- `constraints`, `strengths`, `limitations`, `risk_flags`
- `success_criteria`
- `endurance_anchor_w`, `ambition_if_range`

## 4) Forbidden Content (Binding)
- Planning outputs, load corridors, or workout prescriptions.
