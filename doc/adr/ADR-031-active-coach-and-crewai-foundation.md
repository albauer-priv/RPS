---
Version: 1.0
Status: Accepted
Last-Updated: 2026-05-12
Owner: ADR
---
# ADR-031: Active Coach Operations and CrewAI Foundation

**Status:** Accepted  
**Date:** 2026-05-12  

## Context

RPS currently splits conversational and write-capable planning behavior:

* `Coach` is read-only.
* tactical week edits live in a separate bounded workout editor.
* report/feed-forward actions are page-local flows, not reusable coach operations.

At the time of this decision, a broader CrewAI rewrite was desired, but official CrewAI documentation and PyPI metadata required Python `<3.14` while the repo still ran on Python `3.14`.

## Decision

1. `Coach` becomes an active planning surface.
2. Coach mutations remain operation-based and preview-first; no arbitrary workspace writes are allowed.
3. Persisted changes continue to flow through existing guarded store and deterministic helpers.
4. Report and feed-forward actions are extracted into reusable orchestrator helpers so they can be triggered from chat.
5. CrewAI-facing config/model foundation is added now:
   * `config/crewai/agents.yaml`
   * `config/crewai/tasks.yaml`
   * typed config/model helpers under `src/rps/crewai_runtime/`
6. CrewAI package/runtime activation is deferred until the repo runs on a supported Python version.

## Consequences

- Positive outcomes
  - Users gain a single conversational surface for plan inspection and adjustment.
  - Coach/product capability is no longer blocked on the full runtime rewrite.
  - CrewAI migration groundwork exists in-repo and can be activated later.
- Trade-offs / risks
  - Runtime remains hybrid for now: active coach behavior on the existing transport, CrewAI only as foundation/config.
  - Documentation must clearly distinguish “foundation added” from “runtime cutover complete”.

## Exceptions

* ADR-029 stated that `Coach` remains read-only.
  * Approved exception: `Coach` now becomes write-capable through narrow explicit operations only.
* Full CrewAI runtime activation was intentionally deferred at the time because upstream support excluded Python `3.14`.
