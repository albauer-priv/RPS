---
Version: 1.0
Status: Accepted
Last-Updated: 2026-05-14
Owner: CrewAI Runtime
---
# ADR-047: CrewAI Skills as the Unified Methodology Layer

## Context

RPS was using three overlapping mechanisms for agent methodology:
- long prompt markdown files
- `config/agent_knowledge_injection.yaml`
- selective knowledge bundles

That created duplication, runtime document slicing, and separate methodology paths between Coach and planning flows.

## Decision

Adopt repo-local CrewAI Skills as the primary methodology layer for conversational and planning specialists.

Key points:
- Shared week/phase/season specialists reuse shared skill bundles.
- Coach and Workout Editor keep thin conversational orchestration but reuse the same week-domain specialists as planning surfaces.
- `agent_knowledge_injection` is removed.
- Runtime chapter slicing is removed; decomposed canonical source docs replace mixed master documents.
- Persisted artifact tasks are owned by dedicated writer agents.
- Contracts and schemas remain explicit authoritative files outside the skill system.

## Alternatives considered

### Keep injection and add skills opportunistically
Rejected because it preserves two methodology systems and unclear precedence.

### Move all contracts and schemas into skills
Rejected because deterministic validation and cross-agent contracts must remain explicit and machine-owned.

## Consequences

### Positive
- One explicit methodology layer.
- Reusable shared specialist families across Coach, Workout Editor, and planners.
- Cleaner separation between methodology, knowledge, tools, and contracts.

### Negative
- Coordinated rename/refactor across config, prompts, tests, and docs.
- Compatibility prompt rendering is still needed while local CrewAI execution remains blocked on Python 3.14.

## Follow-up

- Run real CrewAI-capable container smokes for Coach, Workout Editor, Season, Phase, and Week.
- Continue shrinking residual prompt contract glue where `output_json`/guardrails prove stable.
