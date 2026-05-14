---
Type: InterfaceSpecification
Interface-For: PLANNING_EVENTS
Interface-ID: PlanningEventsInterface
Version: 1.2

Scope: Shared
Authority: Binding

Applies-To:
  - Season-Scenario-Agent
  - Season-Planner
  - Phase-Architect
  - Week-Planner

Binding-Specs:
  - Specification-ID: TraceabilitySpec
    Version: 1.0
  - Specification-ID: FileNamingSpec
    Version: 1.0

Notes: >
  Canonical interface for A/B/C events used for planning. This replaces legacy
  event sections in season briefs. It is input-only.
---

> Status: Superseded as a canonical planning-runtime source.
> Canonical runtime method logic now lives in:
> - `skills/season/context-analysis/SKILL.md`
> - `skills/season/constraint-synthesis/SKILL.md`
> - `skills/phase/context-analysis/SKILL.md`
> This file remains as legacy source material and migration evidence.

# Planning Events Interface Specification

## 1) Purpose (Binding)
**PLANNING_EVENTS** provides the authoritative A/B/C event list used to anchor
season and phase planning.

## 2) Required Fields (Binding)
Each event MUST include:
- `type` (A/B/C)
- `priority_rank` (1-3)
- `event_name`
- `date` (YYYY-MM-DD)
- `event_type`
- `goal`
- `distance_km`
- `elevation_m`
- `expected_duration`
- `time_limit`

## 3) Forbidden Content (Binding)
- Planning outputs, load corridors, or workout prescriptions.
