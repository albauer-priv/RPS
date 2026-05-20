---
Version: 1.0
Status: Accepted
Last-Updated: 2026-05-20
Owner: Planning
---

# ADR-052: Protocol-driven week workout generation

## Context

The deterministic Week engine removed Week crews, but workout generation still relied on coarse family/profile templates. Local policy sources already define protocol-level constraints, progression order, and structural rules that are richer than the Intervals export subset.

## Decision

Week workout generation becomes protocol-driven:

* protocol config defines allowed structures, constraints, progression axes, and add-on rules
* the Week engine selects and parameterizes protocols
* a deterministic solver computes the concrete workout instance
* the workout renderer projects that richer internal model into flat Intervals subset text
* `freeride` remains unsupported

## Alternatives considered

1. Keep extending family/profile templates with more branches.
2. Move back to LLM-authored workout text.

Both were rejected because they keep export constraints and training logic entangled and brittle.

## Consequences

* Internal week blueprints carry richer protocol metadata.
* Week preview/replan/regen paths stay aligned because they share the same protocol solver.
* Export syntax remains constrained by the RPS Intervals subset; richer semantics stay internal.
