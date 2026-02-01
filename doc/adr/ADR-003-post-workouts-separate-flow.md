# ADR-003: Posting Workouts is a Separate Flow

**Status:** Accepted  
**Date:** 2026-02-01  

## Context

Planning completion should not be coupled to external posting. Auto-posting mixes concerns and can block planning UX.

## Decision

Planning flow ends after workout export. Posting to Intervals is a separate “Post Workouts” flow initiated from the Workouts page.

## Consequences

- Planning is considered complete when exports are current.
- Posting can be retried independently without re-running planning.

## Exceptions

None.
