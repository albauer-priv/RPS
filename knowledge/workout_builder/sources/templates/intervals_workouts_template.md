---
Type: Template
Template-For: INTERVALS_WORKOUTS
Template-ID: IntervalsWorkoutsTemplate
Version: 1.0

Scope: Agent
Authority: Binding
Implements:
  Interface-ID: IntervalsWorkouts
  Version: 1.0

Owner-Agent: Workout-Builder
Notes: >
  Schema-aligned blueprint for INTERVALS_WORKOUTS. Replace every <!--- FILL --->
  marker with concrete values before output.
---

# Intervals Workouts Template (Array)

```json
[
  {
    "start_date_local": "<!--- FILL --->",
    "category": "WORKOUT",
    "type": "Ride",
    "name": "<!--- FILL --->",
    "description": "<!--- FILL --->"
  }
]
```
