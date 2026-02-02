# ADR-021: Use st.plotly_chart for Charts

Status: Accepted  
Date: 2026-02-02

## Context

We need a consistent, controllable chart rendering path in the Streamlit UI to
avoid mixed backends and serialization issues. Different chart helpers behave
slightly differently across versions and data types.

## Decision

All UI charts must render via `st.plotly_chart(...)` only.  
Other chart helpers (e.g., `st.line_chart`, `st.bar_chart`, `st.area_chart`,
`st.altair_chart`, etc.) are not to be used in UI pages.

## Consequences

- Chart rendering is consistent across pages and data types.
- Any existing non-Plotly charts should be migrated when touched.
- This rule applies to all Streamlit UI pages.

