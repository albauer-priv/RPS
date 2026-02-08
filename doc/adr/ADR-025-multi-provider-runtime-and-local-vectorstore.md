---
Version: 1.0
Status: Proposed
Last-Updated: 2026-02-06
Owner: ADR
---
# ADR-025: Multi-provider LLM runtime + local vectorstore

**Status:** Proposed  
**Date:** 2026-02-06  

## Context

RPS is currently bound to the OpenAI Responses API and OpenAI-managed vectorstores.
The roadmap requires multi-provider support, offline/local vectorstore capability,
and a clean path to orchestration frameworks (CrewAI).

## Decision

Adopt LiteLLM as the sole runtime path for LLM calls and move vector search to an
embedded Qdrant backend. For non-OpenAI providers, implement a **custom Coach
compaction strategy** to replace `/responses/compact` (OpenAI-only). Server mode
and CrewAI orchestration are deferred to a second phase once parity with current
behaviors (streaming, tool calls, prompt injection) is verified.

## Consequences

- Provider-agnostic runtime with explicit provider/model routing via config.
- Local vectorstore persistence with deterministic manifest-based resets.
- Additional dependency and adapter work to keep tool/stream semantics compatible.
- Coach compaction quality depends on custom heuristics; monitor for regressions.

## Exceptions

None.
