---
Version: 1.0
Status: Implemented
Last-Updated: 2026-06-09
Owner: UI / Planning Runtime
---
# FEAT: Plan Hub Runtime Progress Visibility

* **ID:** FEAT_plan_hub_runtime_progress_visibility
* **Status:** Implemented
* **Owner/Area:** UI / Planning Runtime
* **Last-Updated:** 2026-06-09

## Context / Problem

The Plan Hub `Run Execution` section showed only coarse pipeline state:

* active run id
* current top-level step
* step table
* raw event table

The runtime already emits richer CrewAI telemetry (`FLOW_*`, `CREW_*`, `CREW_TASK_*`), but Plan Hub did not surface:

* active flow
* active crew
* active task
* task progress like `2/9`

That made it hard to understand what is actually happening during longer Phase/Season runs.

## Implemented Behavior

Plan Hub now surfaces two additional runtime layers without changing the telemetry contract:

1. **Pipeline progress**
   * derived from queued run steps and current top-level step
   * shown as `x/y`

2. **Runtime detail**
   * derived from existing run events
   * shows, when available:
     * current flow
     * current flow step
     * current crew
     * current task
     * task progress (`n/total`)
     * active agent
     * active model

The run event table also exposes more existing fields directly:

* `Crew`
* `Agent`
* `Progress`
* `Model`
* `Component`

## Implementation Notes

* No new runtime events were added.
* Event interpretation is code-owned in `rps.ui.run_store`.
* Plan Hub remains a consumer of existing telemetry rather than a producer of new state.

## Acceptance

* Active runs show pipeline progress when `current_step` maps to a known queued step.
* Active CrewAI runs show current flow/crew/task details when corresponding events exist.
* Event rows expose crew/task progress fields already present in telemetry.
* No schema or persistence contract changes are required.
