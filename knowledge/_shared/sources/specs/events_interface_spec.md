---
Type: InterfaceSpecification
Interface-For: EVENTS
Interface-ID: EventInterface
Version: 1.0

Scope: Context
Authority: Informational

Applies-To:
  - Season-Planner
  - Phase-Architect
  - Week-Planner
  - Performance-Analyst

Temporal-Scope:
  From: YYYY-MM-DD
  To: YYYY-MM-DD

Binding-Specs:
  - Specification-ID: TraceabilitySpec
    Version: 1.0

Notes: >
  Defines the canonical structure for non-training events that provide
  contextual information only. Events may inform planning considerations
  but never prescribe actions, override governance, or trigger decisions
  automatically.
---

# 📅 Events — Interface Template v1.0

## Purpose

This artefact captures **non-training events** that may affect:
- availability
- logistics
- recovery
- data quality

It provides **context only**.
It NEVER prescribes training actions and NEVER overrides governance.

---

## Event List (REQUIRED)

| Date | Event-ID | Event-Type | Status | Impact | Description |
|---|---|---|---|---|---|
| YYYY-MM-DD | EVT-001 | TRAVEL | planned | availability | Business travel |
| YYYY-MM-DD | EVT-002 | WORK | occurred | missed_session | Overtime |
| YYYY-MM-DD | EVT-003 | WEATHER | occurred | modality | Heavy rain |

---

## ENUM Definitions (MANDATORY)

### Event-Type

- TRAVEL
- WORK
- WEATHER
- HEALTH
- FAMILY
- EQUIPMENT
- OTHER

---

### Status

- planned
- occurred
- cancelled

---

### Impact

- availability
- missed_session
- modality
- recovery
- data_quality
- none
- other

---

## Agent Interpretation Rules

### Season-Planner
- MAY consider planned events as phase constraints
- MUST NOT react to single short-term events

### Phase-Architect
- MAY use occurred events as input for:
  - PHASE_FEED_FORWARD
  - new PHASE_GUARDRAILS
- MUST NOT treat events as automatic triggers

### Week-Planner
- MAY adapt logistics only
- MUST report consequences via PLANNER_COACH_FEED_BACK
- MUST NOT compensate load or change intent

---

## Explicit Non-Actions

This artefact MUST NOT:
- define training actions
- recommend load or intensity changes
- override governance

---

## Self-Check

- [ ] YAML header complete
- [ ] Valid ENUM values used
- [ ] Impact specified for each event
- [ ] No training instructions included

---

## End of EREIGNISSE Interface Template v1.0
