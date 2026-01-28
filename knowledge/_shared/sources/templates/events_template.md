---
Type: Template
Template-For: EVENTS
Template-ID: EventsTemplate
Version: 1.0

Scope: Context
Authority: Informational

Implements:
  Interface-ID: EventInterface
  Version: 1.0

Owner-Agent: User

Dependencies:
  - Specification-ID: TraceabilitySpec
    Version: 1.0

Notes: >
  Template for non-training events that provide context only (availability,
  logistics, recovery, data quality). Events must never prescribe actions
  or override governance.
---

# Events - Template

This artefact captures non-training events that may affect:
- availability
- logistics
- recovery
- data quality

It provides context only.
It NEVER prescribes training actions and NEVER overrides governance.

---

## YAML Header (to be filled in artefact)

```yaml
---
Artifact-Type: EVENTS
Version: 1.0
Created-At: YYYY-MM-DDT00:00:00Z
Owner-Agent: User
Authority: Informational
Run-ID: YYYYMMDD_evt01
Scope: Context
Temporal-Scope:
  From: YYYY-MM-DD
  To: YYYY-MM-DD
Implements:
  Interface-ID: EventInterface
  Version: 1.0
Trace-Upstream: []
Notes: >
  Context artefact (non-training). Events provide context only
  (availability/logistics/recovery/data quality) and never drive
  training decisions or override governance.
---
```

---

## Event List (REQUIRED)

| Date | Event-ID | Event-Type | Status | Impact | Description |
|---|---|---|---|---|---|
| 2025-11-04 | EVT-001 | WORK | occurred | missed_session | Overtime; planned workout not completed |
| 2025-11-06 | EVT-002 | WORK | occurred | missed_session | Overtime; planned workout not completed |
| 2025-11-07 | EVT-003 | TRAVEL | occurred | availability | Business travel |
| 2025-11-21 | EVT-004 | TRAVEL | occurred | availability | Business travel |
| 2025-11-23 | EVT-005 | WEATHER | occurred | modality | Cold snap (~-10C); training done indoors |
| 2025-11-24 | EVT-006 | WEATHER | occurred | modality | Cold snap (~-10C); training done indoors |
| 2025-11-26 | EVT-007 | TRAVEL | occurred | availability | Business travel |

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

### Status
- planned
- occurred
- cancelled

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

## End of Events Template
