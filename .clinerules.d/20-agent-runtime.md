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
- `doc/adr/ADR-062-skill-content-delivery-rules.md`

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

## Agentic-readiness principles (Fowler)

When adding or modifying skills, orchestrators, or agent prompts, apply all four principles:

**1. Input contracts — validate before running**
- Every crew entry point that requires external data (events, availability, profile) must validate that data exists and is usable before starting the crew.
- Return a structured `{"ok": False, "error": "..."}` with a human-readable message; do not let a crew silently run with empty or invalid inputs.
- Reference: `create_season_scenarios` pre-flight check in `src/rps/orchestrator/season_flow.py`.

**2. Traceability — cite governing rules**
- When adding a skill rule that produces a `blocking_issue`, `warning`, or corridor value, the skill must instruct agents to cite the specific governing rule (skill name, section, or threshold).
- Vague sources ("training principles", "general guidelines") are prohibited.
- If no rule applies: state "judgment — no specific rule applies" explicitly.
- Reference: `skills/shared/traceability-and-naming/SKILL.md` Reasoning citation rules.

**3. Semantic layer — use canonical vocabulary**
- Do not redefine `kJ`, `BL_kJ`, `W_prev_actual`, `availability_load_capacity_kj`, phase cycle names, event priority labels, cadence families, or `blocking_issue` vs `warning` semantics inside individual skill files.
- These terms are defined once in `skills/shared/domain-glossary/SKILL.md`; reference or extend there.
- When adding a new domain term used across more than one skill, add it to the domain glossary first.

**4. Capability model — respect tier authority**
- Specialist agents propose and flag; they do not authorize.
- Manager/synthesis agents aggregate and dispatch; they do not substitute for specialist decisions.
- Audit/review agents emit issues and warnings; they do not rewrite plan content.
- Writer agents transform; they do not alter load math or corridor values.
- The plan advances only when the review layer approves it — no agent can self-authorize.
- Reference: `skills/shared/runtime-boundaries/SKILL.md` Capability tiers.

## Runtime memory vs developer handoff

Runtime memory is part of product architecture and must follow ADR-028 and ADR-046.

Do not introduce generic runtime `memory.md`, `memory.json`, or similar files as runtime truth.

Local `.developer_handoff/` notes, if used, are development-time only and non-authoritative.