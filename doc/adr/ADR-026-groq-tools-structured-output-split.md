---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-08
Owner: ADR
---
# ADR-026: Split Tools vs Structured Output for Groq (LiteLLM)

**Status:** Accepted  
**Date:** 2026-02-08  

## Context

Groq + LiteLLM can fail when a single agent mixes tool calls and structured output.
This presents as request templating errors (e.g., Harmony tool rendering issues).
We need a stable pattern that avoids the incompatibility while keeping tool use and
structured output.

## Decision

Use a two-agent chain for flows that require both tools and structured output:

1) **Tools Agent**: tool use only, no structured output.
2) **Formatter Agent**: structured output only, no tools.

The Tools Agent runs first to gather data. The Formatter Agent takes the Tools
Agent output and produces the structured response.

## Consequences

- **Positive outcomes**
  - Avoids Groq/LiteLLM tool + structured output conflict.
  - Keeps structured output contracts intact.

- **Trade-offs / risks**
  - Adds an extra model call and latency.
  - Requires orchestration to pass the intermediate output.

## Exceptions

None yet. If Groq/LiteLLM resolves tool + structured output in a single call,
this ADR can be revisited and potentially superseded.
