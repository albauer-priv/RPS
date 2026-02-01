# ADR-010: Caching Policy (Streamlit)

**Status:** Accepted  
**Date:** 2026-02-01  

## Context

Streamlit reruns are frequent; caching must prevent redundant IO while avoiding stale data or cross-session bugs.

## Decision

- Use `st.cache_resource` for long-lived, thread-safe resources (clients, connections).
- Use `st.cache_data` for deterministic computations and file parsing.
- Do not cache mutable per-athlete state unless it is version-keyed.
- Background schedulers/queues use `st.cache_resource` to ensure one instance per process.

## Consequences

- Faster UI with consistent behavior across reruns.
- Reduced risk of stale or cross-session data leaks.

## Exceptions

- If a resource is not thread-safe, do not cache it; instantiate per call.
