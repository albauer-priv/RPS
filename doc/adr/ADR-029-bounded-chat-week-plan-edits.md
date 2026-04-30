---
Version: 1.0
Status: Accepted
Last-Updated: 2026-04-30
Owner: ADR
---
# ADR-029: Bounded Chat Week Plan Edits

**Status:** Accepted  
**Date:** 2026-04-30

## Context

RPS already has a conversational `Coach`, but it is intentionally read-only. Users now need a chat-driven way to make small tactical changes to an existing `WEEK_PLAN`, such as moving a workout to another day or replacing one workout text block.

A generic writable coach or raw workspace JSON writer would conflict with existing source-of-truth, validation, and UI-delegation decisions.

## Decision

RPS will introduce a separate, bounded write-capable chat editor on `Plan -> Workouts` for the currently selected ISO week.

Rules:

* `Coach` remains read-only.
* The editor is scoped to the current `WEEK_PLAN` only.
* Supported operations are narrow and deterministic.
* Chat is used for intent interpretation and confirmation, not for free-form artefact writing.
* Preview and apply are separate steps.
* Apply must persist through `GuardedValidatedStore` and rebuild `INTERVALS_WORKOUTS` deterministically.

Initial supported operations:

1. move a workout to an empty target day within the week
2. change workout start time
3. replace a workout text block (with optional title/notes updates)
4. discard a pending edit
5. apply a pending edit

## Consequences

### Positive

* Users can make targeted week-level changes without rerunning the whole planner.
* Artefact validation and exportability remain enforced.
* The system gains a clear path for future bounded plan-edit operations.

### Negative

* The initial scope is intentionally limited and will reject more complex requests such as day swaps or phase-level edits.
* Session-state pending edits require explicit clearing when the selected athlete/week changes.

## Rejected Alternatives

### Generic writable `Coach`

Rejected because it blurs the boundary between advice and artefact authority.

### Direct raw JSON write tools from chat

Rejected because they bypass domain-specific consistency checks and widen the blast radius of model errors.

## Exceptions

None.
