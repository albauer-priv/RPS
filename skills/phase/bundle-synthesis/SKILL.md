---
name: bundle-synthesis
description: Synthesize phase specialist drafts into one internal PhaseBundle.
metadata:
  author: rps
  version: "2.0"
---
Combine phase drafts into one internal bundle.

Definitions:
- `weekly_kj_bands`: exact-range governance-load bands copied from approved phase guardrails
- `planned_weekly_load_kj`: governance load metric represented by those bands
- `week_role`: inherited deterministic cadence role for an exact-range ISO week
- `phase_role`: deterministic role of the exact phase block
- `reload`: controlled return near prior build load
- `re-entry`: baseline-anchored controlled return after deload or unresolved fatigue

Authority / injected sources:
- `week_role`, `phase_role`, exact range, and contract values come from deterministic phase execution context and slot contract tools
- `weekly_kj_bands` come from approved phase guardrails
- inherited scenario posture comes from `inherited_scenario_contract`; operationalize it rather than reopening scenario choice
- this layer synthesizes the bundle; it must not invent a more aggressive overload interpretation than the approved cadence/recovery logic
- nested `phase_intent` fields inside `guardrails`, `structure`, and `preview` are canonical taxonomy tokens only, never prose or narrative summaries
- `inherited_scenario_contract` is an exact deterministic contract object; freeze it verbatim and do not paraphrase nested fields such as `constraint_summary` or `risk_flags`
- `structure.upstream_intent.constraints` is planning-facts only: inherited availability/logistics constraints, risk/recovery constraints, event-window anchors, and genuine external planning constraints
- keep runtime/process/governance rules out of `structure.upstream_intent.constraints`
- if deterministic phase contracts are injected, do not call `workspace_get_phase_execution_context` or `workspace_get_phase_slot_contract`
- use tools only as fallback for genuinely missing authority fields
- use the injected `phase_allowed_intensity_domains` exactly; do not re-fetch them

Method:
1. Pass 1 - structural draft: keep guardrails authoritative over structure.
2. Pass 2 - semantic finalization: apply cadence/recovery as a constraint on structure, not as a separate plan.
3. Preserve event integration only where it does not violate season authority.
4. Use deterministic contract tools directly when exact phase-slot or phase-execution values are needed:
   - `workspace_get_phase_execution_context`
   - `workspace_get_phase_slot_contract`
5. Final synthesis is integration work, not rediscovery. Do not ask coworkers to re-derive deterministic week roles, exact phase range, or S5 bands during this step.
6. Emit one review-ready phase bundle.
7. Review should mostly confirm. Resolve all context-decidable role/load/structure/event contradictions before handoff.
8. Pass 3 - planner self-audit: before handoff, explicitly self-check:
   - week roles complete and coherent
   - S5/load-band logic coherent
   - guardrails / structure / preview agree
   - phase semantics and domain shaping contain no unresolved contradictions
   - inherited overload policy is visible in exact-range structure
   - deload / mini-reset / reload / re-entry semantics are explicit where required
   - Build-entry logic stays conservative after shortened/base/re-entry context
   - no phase-level drift away from durability-first repeatability logic
   - no assumption that the writer will repair bundle semantics
   - if exact-range structure, week-role skeleton, or phase-slot alignment is wrong, return to Pass 1
   - if structure is valid but reload/re-entry semantics, legality framing, preview meaning, or writer-ready summary is incomplete, return to Pass 2
9. Mandatory Pass-2 authority freeze:
   - freeze exact inherited scenario contract
   - freeze exact allowed intensity domains
   - freeze exact forbidden intensity domains
   - freeze exact allowed load modalities
   - freeze exact role-week load bands
   - freeze exact phase-local objective
   - keep operational `NONE` out of structural legality; it belongs only to preview/non-training-day semantics

Compact authority-freeze example:

```json
{
  "phase_id": "P01",
  "phase_range": "2026-24--2026-25",
  "phase_allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
  "phase_forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
  "phase_allowed_load_modalities": ["NONE"],
  "week_role_by_iso_week": {"2026-24": "LOAD_1", "2026-25": "RELOAD"}
}
```

Operational synthesis rules:
- preserve load-estimation semantics exactly:
  - `weekly_kj_bands` = governance load bands
  - do not reinterpret them as raw mechanical work
- keep week structure subordinate to:
  - deterministic week roles
  - phase guardrails legality
  - inherited cadence family
- if a nominal reload is baseline-anchored after fatigue, synthesize it as re-entry
- if a phase intent depends on a forbidden domain, replan rather than hiding the contradiction in prose
- preserve durability-first logic:
  - repeatability over cosmetic load centering
  - no hidden catch-up
  - no recovery compression

Retrieval policy:
- Use deterministic injected runtime contracts first when they are present.
- Use `workspace_get_phase_execution_context` and `workspace_get_phase_slot_contract` for exact authoritative phase values.
- Use `workspace_get_latest` for latest authoritative planning artefacts and runtime snapshots only when direct retrieval is still needed.
- Use `workspace_get_input` only for athlete-managed inputs.

Output format:
- Return the task expected_output as one consolidated planning bundle or synthesis contribution.
- Include the selected inputs, decisions, unresolved risks, and writer-ready summary needed by the next task.
- Preserve task boundaries and emit competing variants only when the task explicitly asks for them.
