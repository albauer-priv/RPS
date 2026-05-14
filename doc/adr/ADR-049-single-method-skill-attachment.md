---
Version: 1.0
Status: Accepted
Last-Updated: 2026-05-14
Owner: Architecture
---
# ADR-049: Single-Method Skill Attachment Model

**Status:** Accepted  
**Date:** 2026-05-14  

## Context

CrewAI supports skills on both agents and crews, and technically allows multiple skills. RPS used that freedom to compose broad bundles, but the result was unclear method ownership, thin skill packages, and real planning logic still stranded in legacy prose specs.

## Decision

Adopt a stricter local rule than CrewAI requires:

* each agent receives exactly one method skill package
* crews may attach only operational cross-cutting skills
* planning methodology must live in the owning agent skill, not in crew-level attachments
* runtime validation fails when the attachment rule is violated
* the runtime compatibility layer injects `SKILL.md` and local `references/` content for activated skills

Operational crew-level skills are limited to:
- `runtime-boundaries`
- `resolved-context-consumption`
- `traceability-and-naming`
- `replan-instruction-authoring` on review crews

## Consequences

- Positive outcomes
  - clearer method ownership per agent
  - less domain leakage across crews
  - richer, more explicit skill packages
  - easier runtime validation and debugging

- Trade-offs / risks
  - more dedicated skill packages for managers/reviewers
  - stronger pressure to keep each single skill operationally complete
  - existing bundle-based config becomes incompatible

## Exceptions

No exceptions approved in this cutover. If an agent cannot operate with one method skill, the default response is to create a better dedicated method skill, not to reintroduce composition.
