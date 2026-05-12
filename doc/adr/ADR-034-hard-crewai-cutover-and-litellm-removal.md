---
Version: 1.0
Status: Accepted
Last-Updated: 2026-05-12
Owner: Runtime
---
# ADR-034: Hard CrewAI Cutover and LiteLLM Removal

## Context

RPS already runs on Python 3.13 in the deployment container and explicitly selects CrewAI at runtime. The remaining LiteLLM modules existed only as compatibility scaffolding and a small number of still-active helper paths.

That hybrid state contradicted the intended architecture and the requested hard cutover.

## Decision

1. Remove legacy runtime fallback from `rps.agents.runtime`.
2. Remove active dependencies on `rps.agents.multi_output_runner` and `rps.ui.rps_chatbot`.
3. Replace remaining reusable legacy helper logic with neutral shared normalization helpers.
4. Replace vector embedding calls that still depended on `litellm` with direct provider calls.
5. Remove the `litellm` dependency from packaging.

## Consequences

### Positive

* The production runtime becomes CrewAI-only.
* No silent fallback remains.
* The codebase is easier to reason about.

### Negative

* Rollback now requires git revert rather than env toggles.
* Legacy tests and modules are intentionally deleted.

### Follow-up

* Keep monitoring end-to-end planner/report runs in the container after deployment.
