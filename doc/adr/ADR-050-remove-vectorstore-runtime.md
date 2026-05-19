---
Version: 1.0
Status: Accepted
Last-Updated: 2026-05-18
Owner: ADR
---
# ADR-050: Remove Vectorstore Runtime

**Status:** Accepted  
**Date:** 2026-05-18

## Context

RPS now uses CrewAI skills and configured `knowledge_sources` for static domain knowledge. The former local Qdrant/vectorstore path created extra startup work, noisy housekeeping logs, duplicate knowledge wiring, and an optional recovery surface that was no longer part of the primary runtime.

## Decision

Remove the local vectorstore subsystem from the active product:

- no Streamlit startup vectorstore sync
- no Plan Hub knowledge-store readiness panel
- no `knowledge_search` workspace tool
- no Qdrant-backed vectorstore modules or smoke/sync scripts
- no vectorstore manifest or vectorstore-specific runtime settings

Static reference material remains in `specs/knowledge/` and is attached through `config/crewai/knowledge_sources.yaml`. Athlete/runtime state remains code-owned and is accessed through workspace tools.

## Consequences

- Startup and housekeeping no longer spend time embedding or rebuilding static knowledge.
- Logs focus on planning/crew/workspace activity instead of embedding transport noise.
- Recovery is simpler because there is no separate vectorstore state to rebuild.
- Static knowledge updates require updating the CrewAI knowledge configuration and rerunning normal validation, not vectorstore sync.

## Supersedes

- ADR-022: Vector Store Sync Policy
- ADR-025: Multi-provider LLM runtime + local vectorstore, for the local vectorstore portion
