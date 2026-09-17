---
Version: 1.0
Status: Accepted
Last-Updated: 2026-09-17
Owner: ADR
---
# ADR-062: Skill Content Delivery Rules — SKILL.md Body as the Only Guaranteed Path

**Status:** Accepted  
**Date:** 2026-09-17

## Context

RPS uses three mechanisms to deliver content to CrewAI agents: SKILL.md bodies (via `skills=[...]`),
knowledge bundles (via `StringKnowledgeSource`), and `references/` subdirectories inside skill
directories. Investigation in v0.37.14–15 revealed that two of these three mechanisms are either
unreliable or inactive:

1. **`references/` directories are not automatically injected.** CrewAI loads only the `SKILL.md`
   body during skill activation. Accessing `references/` requires an explicit `load_resources()`
   call, which is not used anywhere in this codebase. Content in `references/*.md` is human
   documentation; agents cannot read it unless a reference is explicitly mentioned in the SKILL.md
   body and the agent decides to look it up.

2. **Knowledge bundles (RAG) fail silently.** `build_crewai_knowledge_kwargs` wraps the
   `StringKnowledgeSource` import in a try/except. On platforms where `lancedb` or `chromadb`
   has no compatible wheel, the import returns `None` and no sources are loaded — with no log
   warning and no error. Even when the import succeeds, RAG uses semantic search with a score
   threshold (0.45–0.5), so critical rules may be missed when the query does not match well.

3. **`crews:` section in `knowledge_sources.yaml` is dead code.** `resolve_crew_knowledge_profile`
   is defined but never called anywhere; crew-level knowledge bundles have no effect on agents.

The consequence was that rules added to `references/*.md` files in v0.37.12 (RELOAD→TAPER warning,
minimum taper window, brevet sequencing, kJ/kg milestones) were invisible to the agents responsible
for applying them. v0.37.14–15 moved these rules into the SKILL.md bodies.

## Decision

### Content delivery rule

**Operational planning rules, thresholds, decision logic, and behavioral constraints must live in
the `SKILL.md` body of the skill that owns them.** This is the only delivery path guaranteed to
reach the agent unconditionally.

Specific sub-rules:

- When adding a rule to `references/*.md`, check whether the same rule is stated in the owning
  `SKILL.md` body. If not, add it there first. `references/` entries are documentation that
  supplements the SKILL.md, not a substitute for it.
- When fixing a behavioral gap (wrong blocker, missing threshold, incorrect anchor), make the fix
  in the SKILL.md body — not only in a reference file.
- Content that is needed by multiple agents in the same crew belongs in a shared skill under
  `skills/shared/`, registered in `skills.yaml` → `crews:` → `skills:`, not in a knowledge bundle.

### Knowledge bundles (RAG) — supplementary only

Knowledge bundles remain in `knowledge_sources.yaml` for supplementary reference data: bibliography
entries, durability study tables, interface specs, workout syntax specs. These bundles may help
agents when they work; their absence must never break correctness.

Do not add operational planning rules to knowledge bundles as a delivery path.

### `crews:` section in knowledge_sources.yaml — removed

The `crews:` section was removed from `knowledge_sources.yaml` because `resolve_crew_knowledge_profile`
is never called. Crew-level content sharing uses `skills.yaml` → `crews:` → `skills:` instead.

## Consequences

### Positive

- Agents always receive the operational rules they need; no silent delivery failures.
- Adding a rule to a `references/` file without updating the SKILL.md body is a detectable audit
  gap: the architecture doc and this ADR define the check.
- No hidden dependency on lancedb wheel availability or RAG score thresholds for correctness.

### Negative

- SKILL.md bodies grow when rules are migrated from references. Keep rules concise; long supporting
  context belongs in `references/` as human documentation alongside the concise body rule.
- Shared rules that belong to multiple skills must be duplicated across SKILL.md bodies, or
  extracted into a shared skill. Duplication is acceptable for small rule sets; a shared skill is
  the right model when the same rule text appears in three or more SKILL.md files.

## Exceptions

Knowledge bundles may carry rules if and only if:
- a future upgrade verifies that `StringKnowledgeSource` is reliably imported on all deployment
  targets, AND
- the bundle is assigned in the `agents:` section (not `crews:`), AND
- the same rule also remains in the SKILL.md body as the primary path.

## Related

- [doc/architecture/crewai_skills_attachment.md](../architecture/crewai_skills_attachment.md) — canonical rule reference; consult when writing or reviewing skills
- [ADR-046](ADR-046-crewai-state-memory-knowledge-guardrails.md) — original knowledge/skill separation decision; this ADR refines the knowledge-delivery guidance
- [ADR-049](ADR-049-single-method-skill-attachment.md) — one-skill-per-agent rule
