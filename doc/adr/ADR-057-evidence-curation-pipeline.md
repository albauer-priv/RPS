---
Version: 1.0
Status: Accepted
Last-Updated: 2026-05-27
Owner: Architecture
---
# ADR-057: Evidence Curation Pipeline

## Context

RPS already maintains a canonical evidence registry and a weekly literature refresh. That refresh verified new references bibliographically and activated them immediately. This left a gap between “verified source exists” and “RPS can safely use this source as curated evidence.”

## Decision

Adopt a mandatory staged evidence pipeline:

1. discover
2. verify
3. classify
4. curate with a dedicated CrewAI evidence agent
5. quality-gate deterministically
6. activate automatically
7. render registry-derived markdown briefs

Key architectural choices:

* The curation agent must emit native Pydantic structured output.
* YAML remains the canonical registry, not the home of long-form summaries.
* Long research briefs are deterministically rendered markdown.
* Existing entries remain visible via `legacy_active` until they are re-curated.
* Trusted sources may skip manual review, but never skip curation or gate checks.

## Alternatives Considered

### Keep auto-activation after verification

Rejected because bibliographic verification is not sufficient for safe agent-facing use.

### Store long summaries directly in YAML

Rejected because it would blur registry vs. narrative roles and make maintenance and diffing worse.

### Manual-only curation

Rejected because it does not scale to weekly discovery.

## Consequences

* Evidence refresh becomes slower but safer.
* CrewAI config grows with one new agent/task/skill and runtime profile.
* Evidence activation becomes explicitly stateful (`candidate`, `verified`, `curated`, `active`, `rejected`).
* Study detail pages become higher fidelity and provenance-aware.
