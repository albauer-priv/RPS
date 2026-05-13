---
Version: 1.0
Status: Accepted
Last-Updated: 2026-05-13
Owner: Coach Runtime
---
# ADR-045: Coach Hierarchical Conversational Crew

## Context

Coach and Workout Editor accumulated duplicated conversational control logic across:
- page-level heuristics
- outer-flow phrase routing
- one broad chat agent with too many tools

This created conflicting pending-state behavior and unstable tool selection.

## Decision

Adopt one shared manager-plus-specialist conversational runtime for both `Coach` and `Workout Editor` chat surfaces.

The runtime uses:
- `conversation_manager`
- `week_context_analyst`
- `coaching_recommendation_specialist`
- `week_preview_specialist`
- `pending_resolution_specialist`

Tool visibility and knowledge injection are assigned per specialist.

The Streamlit pages become thin callers that:
- inject snapshot memory and scope
- invoke one shared conversational runtime
- render the final reply
- show pending state passively

Phrase-based semantic routing for preview/apply/discard is removed from the Coach outer flow.

## Alternatives considered

### Keep page/flow bridges

Rejected because state interpretation stayed duplicated across UI, flow, and model layers.

### Keep one broad coach agent with all tools

Rejected because tool competition and mixed responsibilities remained the main failure mode.

## Consequences

### Positive

- Smaller, closed responsibilities per specialist.
- Testable tool and knowledge assignment.
- Shared runtime across Coach and Workout Editor.
- Pending-state handling becomes conversational-runtime-owned instead of UI-owned.

### Negative

- Larger runtime refactor.
- More prompt/config files to maintain.

## Notes

This ADR supersedes the conversational intent-routing part of the earlier Coach flow phrase-routing approach, but keeps the outer Flow wrapper and telemetry structure.
