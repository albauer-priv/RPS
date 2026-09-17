---
Version: 1.2
Status: Updated
Last-Updated: 2026-09-17
Owner: Architecture
---
# CrewAI Skill Attachment Model

This document is the canonical description of how RPS attaches repo-local CrewAI
skills after the skills-first planning cutover.

Use this together with:
- `config/crewai/skills.yaml`
- [doc/adr/ADR-049-single-method-skill-attachment.md](../adr/ADR-049-single-method-skill-attachment.md)
- [doc/architecture/agents.md](agents.md)

## Core Rule

RPS uses a stricter local rule than raw CrewAI:

- each agent gets exactly one method skill
- crew-level attachments are allowed only for operational cross-cutting skills
- planning methodology must live in the owning agent skill
- **`references/` are human documentation only; `SKILL.md` must be fully operational without them**
- skills are activated through native CrewAI `skills=[...]`; RPS must not manually append `SKILL.md` bodies into agent `goal`, `backstory`, or task descriptions

This is a local architecture constraint, not a CrewAI platform limitation.

## Content Delivery Architecture

There are three delivery mechanisms in RPS; only the first is guaranteed to reach agents:

### 1. SKILL.md Body (guaranteed)

Every operational planning rule, threshold, decision logic, and behavioral constraint **must** live
in the `SKILL.md` body of the skill that owns it. This is the only delivery path that is
deterministic and unconditional.

- `build_crewai_skill_kwargs` passes the skill directory path; CrewAI loads `SKILL.md` body always
- `references/` subdirectory content is **not** automatically injected — it requires an explicit
  `load_resources()` call which is not used in this codebase
- Consequence: any rule added only to `references/` is invisible to the agent

**Rule: when adding a rule to a `references/*.md` file, ask: does the responsible SKILL.md body
already state this rule? If not, add it there first.**

### 2. Crew-Level Shared Skills (guaranteed for specific crews)

For rules used by multiple agents in the same crew, add a shared skill to `skills/shared/<name>/`
and register it under `crews:` → `<crew_name>:` → `skills:` in `config/crewai/skills.yaml`.

Pattern used for: `runtime-boundaries`, `resolved-context-consumption`, `traceability-and-naming`,
`replan-instruction-authoring`, `blueprint-contract-validation`, etc.

### 3. Knowledge Sources / RAG (supplementary, not reliable)

`config/crewai/knowledge_sources.yaml` configures `StringKnowledgeSource` bundles for some agents.
This mechanism is **not reliable** as the primary delivery path:

- `StringKnowledgeSource` is imported with a try/except — if `lancedb` or `chromadb` fails to
  import (e.g. missing platform wheel), the import silently returns `None` and no sources are loaded
- RAG uses semantic search with a score threshold (0.45–0.5) — content only appears when the query
  matches; critical rules may be missed under unusual phrasing
- The `crews:` section in `knowledge_sources.yaml` is **dead code** — `resolve_crew_knowledge_profile`
  is defined but never called; crew-level knowledge bundles have no effect

**Use knowledge bundles for supplementary reference data only** (bibliography, interface specs, workout
syntax specs) — content that enriches responses when available but whose absence does not break
correctness. Never rely on knowledge bundles for hard rules or thresholds.

## Native CrewAI Activation

CrewAI skills are self-contained directories. During skill activation, CrewAI
loads the full `SKILL.md` body. The optional `references/`, `scripts/`, and
`assets/` directories are resources on that skill path; they are not treated as
automatic prompt context in RPS.

RPS therefore follows these rules:

- pass configured skill directories to CrewAI through `skills=[...]`
- do not render `SKILL.md` bodies manually into prompts
- keep mandatory behavior in `SKILL.md` — not in `references/`
- keep long supporting / human-readable material in `references/` as documentation
- do not use cross-skill file paths such as `../...` or `skills/.../references/...`

## Attachment Layers

### Crew-Level Skills

Crew-level skills are limited to reusable operational guidance that every agent
inside the same crew should inherit.

Allowed crew-level skills:
- `skills/shared/runtime-boundaries`
- `skills/shared/resolved-context-consumption`
- `skills/shared/traceability-and-naming`
- `skills/shared/replan-instruction-authoring` on review crews only

Crew-level skills must not carry planning algorithms, load math, workout syntax,
macrocycle logic, or similar domain-method content.

### Agent-Level Skills

Each agent gets exactly one domain/method skill. That skill owns the planning or
review method for that agent.

Examples:
- `macrocycle_architect` -> `skills/season/macrocycle-architecture`
- `phase_guardrail_band_specialist` -> `skills/phase/guardrails-authoring`
- `week_workout_authoring_specialist` -> `skills/week/workout-construction`
- `week_workout_syntax_reviewer` -> `skills/week/workout-syntax-review`
- `report_artifact_writer` -> `skills/report/artifact-writing`

## Current Crew Attachments

### Planning Crews

Planning crews attach:
- `skills/shared/runtime-boundaries`
- `skills/shared/resolved-context-consumption`
- `skills/shared/traceability-and-naming`

Applies to:
- `season_planning`
- `phase_planning`
- `week_planning`
- `report_planning`
- `coach_conversation`
- `workout_editor_conversation`

### Review Crews

Review crews attach:
- `skills/shared/runtime-boundaries`
- `skills/shared/traceability-and-naming`
- `skills/shared/replan-instruction-authoring`

Applies to:
- `season_review`
- `phase_review`
- `week_review`
- `report_review`

### Writer Crews

Writer crews attach:
- `skills/shared/runtime-boundaries`
- `skills/shared/traceability-and-naming`

Applies to:
- `season_writer`
- `phase_writer`
- `week_writer`
- `report_writer`

## Current Agent Skill Families

### Season

- `season_scenario` -> `skills/season/scenario-generation`
- `season_context_specialist` -> `skills/season/context-analysis`
- `scenario_interpreter` -> `skills/season/scenario-interpretation`
- `event_priority_specialist` -> `skills/season/event-priority-anchoring`
- `peak_window_specialist` -> `skills/season/macrocycle-architecture`
- `macrocycle_architect` -> `skills/season/macrocycle-architecture`
- `season_constraint_specialist` -> `skills/season/constraint-synthesis`
- `season_historical_context_specialist` -> `skills/season/historical-context`
- `season_kpi_guidance_specialist` -> `skills/season/kpi-guidance`
- `season_load_corridor_specialist` -> `skills/season/load-governance`
- `season_progression_specialist` -> `skills/season/load-governance`
- `season_plan_manager` -> `skills/season/plan-synthesis`
- `season_plan_auditor` -> `skills/season/audit`
- `season_governance_auditor` -> `skills/season/governance-review`
- `season_constraints_reviewer` -> `skills/season/constraint-synthesis`
- `season_review_manager` -> `skills/season/review-decision`
- `season_artifact_writer` -> `skills/season/artifact-writing`
- `season_feed_forward_manager` -> `skills/season/feed-forward`

### Phase

- `phase_context_specialist` -> `skills/phase/context-analysis`
- `phase_guardrail_band_specialist` -> `skills/phase/guardrails-authoring`
- `phase_execution_rules_specialist` -> `skills/phase/execution-rules`
- `phase_structure_specialist` -> `skills/phase/structure-authoring`
- `phase_cadence_recovery_specialist` -> `skills/phase/cadence-recovery`
- `phase_intensity_distribution_specialist` -> `skills/phase/intensity-distribution`
- `phase_event_integration_specialist` -> `skills/phase/event-integration`
- `phase_preview_synthesizer` -> `skills/phase/preview-synthesis`
- `phase_constraint_auditor` -> `skills/phase/constraint-audit`
- `phase_governance_auditor` -> `skills/phase/load-governance-audit`
- `phase_structure_reviewer` -> `skills/phase/structure-review`
- `phase_preview_reviewer` -> `skills/phase/preview-review`
- `phase_bundle_manager` -> `skills/phase/bundle-synthesis`
- `phase_review_manager` -> `skills/phase/review-decision`
- `phase_artifact_writer` -> `skills/phase/artifact-writing`
- `phase_feed_forward_manager` -> `skills/phase/feed-forward`

### Week

- `week_context_specialist` -> `skills/week/context-analysis`
- `week_constraint_specialist` -> `skills/week/constraint-analysis`
- `week_recommendation_specialist` -> `skills/week/recommendation-and-adjustment`
- `week_load_target_specialist` -> `skills/week/load-estimation-week`
- `week_revision_specialist` -> `skills/week/revision-methodology`
- `week_workout_authoring_specialist` -> `skills/week/workout-construction`
- `week_consistency_auditor` -> `skills/week/consistency-audit`
- `week_load_governance_reviewer` -> `skills/week/load-governance-review`
- `week_workout_syntax_reviewer` -> `skills/week/workout-syntax-review`
- `week_plan_manager` -> `skills/week/plan-synthesis`
- `week_review_manager` -> `skills/week/review-decision`
- `week_artifact_writer` -> `skills/week/artifact-writing`

### Conversation and Report

- `coach` -> `skills/conversation/guarded-operations`
- `conversation_manager` -> `skills/conversation/routing-and-finalization`
- `pending_resolution_specialist` -> `skills/conversation/pending-resolution`
- `performance_context_specialist` -> `skills/report/context-analysis`
- `des_diagnostic_specialist` -> `skills/report/analysis-methodology`
- `des_review_manager` -> `skills/report/review-decision`
- `report_artifact_writer` -> `skills/report/artifact-writing`

## Validation Rules

Runtime config validation fails when:
- an agent resolves to more than one method skill
- an agent resolves to no method skill
- a crew attaches a non-operational skill
- an unknown agent or skill is referenced
- a skill body references another skill's files or a missing local reference

The canonical source for this validation is `config/crewai/skills.yaml`, backed
by runtime checks in `src/rps/crewai_runtime/config.py` and skill package tests.
