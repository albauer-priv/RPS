# ADR-005: Run Store + Queue + Scheduler Separation

**Status:** Accepted  
**Date:** 2026-02-01  

## Context

Run Store currently holds state, but scheduling and execution were embedded in page-level workers. This limited reuse and made orchestration harder to scale.

## Decision

Keep Run Store as state only. Add a file-based queue + scheduler that decides run eligibility and delegates to workers.

## Consequences

- UI pages enqueue runs instead of running them directly.
- Worker(s) consume queue items and update Run Store.
- System/Status can display queue states consistently.

## Exceptions

None.
