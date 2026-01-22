---
Type: Template
Template-For: WORKOUTS_PLAN
Template-ID: WorkoutsPlanTemplate
Version: 1.0

Scope: Agent
Authority: Binding
Implements:
  Interface-ID: WorkoutsPlanInterface
  Version: 1.2

Owner-Agent: Micro-Planner
Dependencies:
  - Specification-ID: AgendaEnumSpec
    Version: 1.0
  - Specification-ID: LoadEstimationSpec
    Version: 1.0
Notes: >
  Schema-aligned blueprint for WORKOUTS_PLAN. Replace every <!--- FILL --->
  marker with concrete values before output.
---

# Workouts Plan Template (Envelope)

```json
{
  "meta": {
    "artifact_type": "WORKOUTS_PLAN",
    "schema_id": "WorkoutsPlanInterface",
    "schema_version": "1.2",
    "version": "1.0",
    "authority": "Binding",
    "owner_agent": "Micro-Planner",
    "run_id": "<!--- FILL --->",
    "created_at": "<!--- FILL --->",
    "scope": "Micro",
    "iso_week": "<!--- FILL --->",
    "trace_upstream": [
      {
        "artifact": "<!--- FILL --->",
        "version": "<!--- FILL --->",
        "run_id": "<!--- FILL --->"
      }
    ],
    "trace_data": [],
    "trace_events": [],
    "notes": "<!--- FILL --->"
  },
  "data": {
    "week_summary": {
      "week_objective": "<!--- FILL --->",
      "weekly_load_corridor_kj": { "min": 0, "max": 0, "notes": "<!--- FILL --->" },
      "planned_weekly_load_kj": 0,
      "cross_check_tss": 0,
      "notes": "<!--- FILL --->"
    },
    "agenda": [
      { "day": "Mon", "date": "<!--- FILL --->", "day_role": "REST", "planned_duration": "00:00", "planned_kj": 0, "planned_tss": 0, "workout_id": null },
      { "day": "Tue", "date": "<!--- FILL --->", "day_role": "ENDURANCE", "planned_duration": "00:00", "planned_kj": 0, "planned_tss": 0, "workout_id": "<!--- FILL --->" },
      { "day": "Wed", "date": "<!--- FILL --->", "day_role": "RECOVERY", "planned_duration": "00:00", "planned_kj": 0, "planned_tss": 0, "workout_id": "<!--- FILL --->" },
      { "day": "Thu", "date": "<!--- FILL --->", "day_role": "ENDURANCE", "planned_duration": "00:00", "planned_kj": 0, "planned_tss": 0, "workout_id": "<!--- FILL --->" },
      { "day": "Fri", "date": "<!--- FILL --->", "day_role": "REST", "planned_duration": "00:00", "planned_kj": 0, "planned_tss": 0, "workout_id": null },
      { "day": "Sat", "date": "<!--- FILL --->", "day_role": "QUALITY", "planned_duration": "00:00", "planned_kj": 0, "planned_tss": 0, "workout_id": "<!--- FILL --->" },
      { "day": "Sun", "date": "<!--- FILL --->", "day_role": "ENDURANCE", "planned_duration": "00:00", "planned_kj": 0, "planned_tss": 0, "workout_id": "<!--- FILL --->" }
    ],
    "workouts": [
      {
        "workout_id": "<!--- FILL --->",
        "title": "<!--- FILL --->",
        "date": "<!--- FILL --->",
        "start": "<!--- FILL --->",
        "duration": "<!--- FILL --->",
        "workout_text": "<!--- FILL --->",
        "notes": "<!--- FILL --->"
      }
    ]
  }
}
```
