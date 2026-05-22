---
Version: 1.0
Status: Accepted
Last-Updated: 2026-05-22
Owner: Planning Runtime
---
# ADR-056: Upstream-First Planning Pipeline

## Context

Season, Phase, and Week currently use the same staged pattern:

* finalize/planning synthesis
* review
* writer

In practice, the writer still receives semantically unstable or partially normalized content and fails on issues that are either:

* deterministic and code-owned, or
* semantically resolvable earlier with richer context

This creates unstable writer retries and puts semantic correction in the lowest-context stage.

## Decision

Adopt an upstream-first ownership model across Season, Phase, and Week:

* **Finalize** owns semantic repair and bundle completion.
* **Review** owns approval, warning surfacing, and bounded escalation.
* **Writer** owns serialization and deterministic final projection only.

Additional rules:

* semantic blockers should be caught in finalize or review, not first in writer
* deterministic writer projection may still overwrite code-owned fields
* week exportability and workout-structure checks remain hard writer protections

## Alternatives Considered

### Keep writer-heavy recovery

Rejected because the writer has the least context and is the wrong stage for semantic repair.

### Remove review entirely

Rejected because review still provides a useful approval and escalation boundary.

## Consequences

### Positive

* fewer writer retries
* cleaner ownership model
* earlier, more explainable failures
* stronger consistency across Season / Phase / Week

### Negative

* finalize stages become more demanding
* prompts, skills, guardrails, and runtime validation must stay aligned

## Follow-up

* add finalize-readiness guardrails
* lighten review prompts and decision criteria
* keep writer-stage deterministic projection technical only
