---
Version: 1.0
Status: Accepted
Last-Updated: 2026-04-28
Owner: ADR
---
# ADR-028: Snapshot-Based Planner Memory

**Status:** Accepted  
**Date:** 2026-04-28

## Context

Planner agents need a growing set of deterministic athlete-, pipeline-, and planning-derived facts. Earlier prompt-only approaches forced the model to rediscover known values. Recent resolved-context work moved this interpretation into orchestrator code, but the result still exists only as ad hoc inline prompt blocks.

A proposal was raised to consolidate these inputs into a single central memory artifact so agents do not repeatedly search for or infer known facts.

The main architectural risk is introducing a second mutable source of truth that competes with the append-only workspace artefacts.

## Decision

RPS will use **snapshot-based planner memory** instead of a mutable free-form memory document.

Two code-owned derived artefacts are introduced:

1. `ATHLETE_STATE_SNAPSHOT`
   - stable deterministic state from athlete inputs and Intervals/data-pipeline artefacts
2. `PLANNING_CONTEXT_SNAPSHOT`
   - target-week planning context derived from season/phase/week predecessors and scoped planning facts
3. `ADVISORY_MEMORY`
   - non-binding narrative memory derived from recent planning and performance outputs for conversational/advisory use

Rules:

* Source artefacts remain authoritative.
* Snapshots are rebuilt by code from authoritative artefacts.
* Agents do not directly mutate snapshot artefacts.
* Snapshots are append-only workspace artefacts with traceable metadata.
* Planner prompts treat snapshot content as authoritative derived context, while raw workspace tools remain available for exact predecessors, traceability, and unresolved details.
* Advisory memory is explicitly non-binding and may summarize recent outputs, but it never overrides authoritative artefacts.

## Consequences

### Positive

* Deterministic planning memory becomes explicit and inspectable in the workspace.
* Repeated prompt composition is simplified.
* Agents need fewer redundant lookup/reconstruction steps.
* The system gains a clean path for future inspection/debug UI around current planning memory.
* Coach and feed-forward flows can use the same memory architecture instead of bespoke context assembly.

### Negative

* Two new artefact types and schemas increase workspace surface area.
* Snapshot builders must be kept aligned with source artefact evolution.

## Rejected Alternatives

### Single mutable `memory.md` / `memory.json` maintained by agents

Rejected because it:

* weakens source-of-truth boundaries
* introduces drift/concurrency risk
* blurs traceability between facts and interpretation

### Keep only transient inline resolved blocks

Rejected because it preserves duplication across orchestrators and misses the opportunity to make runtime planning memory inspectable and reusable.

## Exceptions

None.
