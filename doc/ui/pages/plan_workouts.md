---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: UI
---
# Plan → Workouts

## Purpose
- Display exported workouts.
- Post or delete workouts to/from Intervals.
- Support bounded chat-based edits to the current week's existing `WEEK_PLAN`.

## Actions
- Post to Intervals (commit)
- Delete posted workouts
- Revise week plan (coach message)
- Workout Editor chat

## Workout Editor
- Scope: current selected ISO week only
- Requires an existing `WEEK_PLAN`
- Supported operations:
  - list current week workouts
  - move one workout to an empty target day
  - change one workout start time
  - replace one workout text block (optional title/notes/start updates)
  - apply or discard a pending edit
- Behavior:
  - editor always previews first
  - user must confirm before apply
  - apply writes a new guarded `WEEK_PLAN` version and rebuilds `INTERVALS_WORKOUTS`
