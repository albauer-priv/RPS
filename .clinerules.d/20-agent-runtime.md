# 20 — Agent Runtime, Prompts, Skills

## Required canonical reads for runtime/agent changes

- `doc/architecture/agents.md`
- `doc/architecture/crewai_flows.md`
- `doc/adr/ADR-028-snapshot-based-planner-memory.md`
- `doc/adr/ADR-035-crewai-agent-authority-boundaries.md`
- `doc/adr/ADR-037-crewai-flow-outer-orchestration.md`
- `doc/adr/ADR-046-crewai-state-memory-knowledge-guardrails.md`
- `doc/adr/ADR-049-single-method-skill-attachment.md`
- `doc/adr/ADR-056-upstream-first-planning-pipeline.md`

## Top-level authority boundaries

- `Season-Scenario-Agent` is advisory only.
- `Season-Planner` is the first binding season authority.
- `Phase-Architect` owns phase artifacts only.
- `Week-Planner` owns the week plan only.
- `Performance-Analyst` is diagnostic only.
- `Coach` is an orchestration surface, not a planning artifact authority.
- Internal specialists do not create new persisted artifact authorities.

## Planning / review / writer discipline

- Planning/finalize owns domain reasoning and semantic completion.
- Review owns audit, approval/rejection, and bounded replan requests.
- Writer owns serialization and deterministic final projection only.

Do not let review become a second planner or writer become a semantic repair stage.

## Deterministic code-owned truth

Do not recompute, widen, or override code-owned truth from:

- `src/rps/planning/load_bands.py`
- `src/rps/planning/deterministic_context.py`
- runtime-built guardrail context
- workspace metadata / version keys

## Prompt / skill / task ownership

- Each agent gets exactly one method skill package.
- Crew-level skills are operational cross-cutting helpers only.
- Active planning logic must live in the owning prompt/skill/task layer.
- Writer prompts serialize; they do not re-plan.
- Review prompts audit; they do not invent planning logic.

## Active-layer rule

For active Season / Phase / Week files:

- operative rules must be locally usable
- variable-like terms must be locally defined, mapped to injected runtime truth, or explicitly forbidden
- thin “see reference X” wrappers are not sufficient as active planning logic

## Runtime memory vs developer handoff

Runtime memory is part of product architecture and must follow ADR-028 and ADR-046.

Do not introduce generic runtime `memory.md`, `memory.json`, or similar files as runtime truth.

Local `.developer_handoff/` notes, if used, are development-time only and non-authoritative.