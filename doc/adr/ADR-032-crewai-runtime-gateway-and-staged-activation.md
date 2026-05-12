---
Version: 1.0
Status: Accepted
Last-Updated: 2026-05-12
Owner: Runtime
---
# ADR-032: CrewAI Runtime Gateway and Staged Activation

## Context

RPS now contains CrewAI YAML/task foundations and active coach operations, but planning/advisory flows were still hard-wired to `rps.agents.multi_output_runner`.

At the same time, upstream CrewAI `1.14.4` declares `Requires-Python: >=3.10,<3.14`, while this repo currently runs on Python `3.14`.

That creates a real runtime contradiction:

* the codebase needs a CrewAI cutover path,
* but the current interpreter cannot activate CrewAI safely.

## Decision

1. Introduce `rps.agents.runtime` as the single planner/advisory runtime gateway.
2. All orchestrators and shared UI helpers must import the gateway instead of `multi_output_runner` directly.
3. Runtime selection is controlled by `RPS_AGENT_RUNTIME` with three modes:
   * `auto`
   * `legacy`
   * `crewai`
4. `auto` must preserve current behavior by falling back to the legacy backend whenever CrewAI cannot execute.
5. Explicit `crewai` mode must fail fast when CrewAI is unavailable or unsupported; it must not silently fall back.
6. Coach UI should surface the effective runtime state to avoid ambiguity.
7. The current repo does **not** claim production CrewAI execution readiness until:
   * Python baseline moves to a supported version, and
   * a real CrewAI execution bridge is implemented.

## Consequences

### Positive

* Future CrewAI activation is now a contained backend change rather than a broad import refactor.
* The repo remains runnable on Python `3.14`.
* Runtime state and fallback semantics become explicit and testable.

### Negative

* This is a staged cutover, not a final CrewAI activation.
* Legacy LiteLLM/runtime modules remain necessary for now.

### Neutral / Follow-up

* A later change must either:
  * move the app runtime to Python `<3.14`, or
  * wait for upstream CrewAI Python `3.14` support.
* The real CrewAI execution bridge remains a follow-up feature.
