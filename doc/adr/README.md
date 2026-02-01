# Architecture Decision Records (ADR)

This folder contains the ADR log for RPS.

## Index
- ADR-001: UI Pages Delegate to Orchestrators
- ADR-002: Run Store is the Source of Truth for Planning Status
- ADR-003: Posting Workouts is a Separate Flow
- ADR-004: Latest Artefact Reset/Delete Semantics
- ADR-005: Run Store + Queue + Scheduler Separation
- ADR-006: Logging Standards
- ADR-007: Naming Conventions
- ADR-008: Header Schema for Artefacts
- ADR-009: JSON as Primary Agent Communication Format
- ADR-010: Caching Policy (Streamlit)
- ADR-011: Error Handling (Retry vs Fail-Fast)
- ADR-012: Run Cancellation (cancel_requested)
- ADR-013: Data Ownership (Source of Truth vs Derived)

## Process (Short)

- Use the template in `ADR_TEMPLATE.md`.
- Name files `ADR-00X-<short-slug>.md`.
- Status values: Proposed, Accepted, Superseded, Deprecated.

## Naming

Example: `ADR-006-queue-scheduler.md`

## Suggested ADR Topics (Simple)

1) Data Ownership: source-of-truth vs derived artefacts
2) Caching Policy: when to use st.cache_resource vs st.cache_data
3) Error Handling: retry vs fail-fast defaults
4) Run Cancellation: cancel_requested semantics