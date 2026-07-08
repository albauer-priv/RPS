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
- `guardrails`, `structure`, and `preview` payloads are not part of this task's output; they are owned by `phase_guardrail_band_draft`, `phase_structure_draft`, and `phase_preview_draft` respectively, which complete earlier in the same crew, and are assembled deterministically from those tasks' own typed outputs after this synthesis is produced. Do not reproduce, paraphrase, or reference their shapes here.
- when injected season/global wording exists, keep that wording instead of paraphrasing it
- if deterministic phase contracts are injected, do not call `workspace_get_phase_execution_context` or `workspace_get_phase_slot_contract`
- use tools only as fallback for genuinely missing authority fields
- use the injected `phase_allowed_intensity_domains` exactly; do not re-fetch them

Method:
1. Pass 1 - structural draft: emit a structurally coherent exact-range week-blueprint draft only.
2. Pass 2 - semantic finalization: apply cadence/recovery as a constraint on the week blueprints, not as a separate plan.
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
   - constraint_audit and load_governance_audit internally consistent with the week blueprints
   - phase semantics and domain shaping contain no unresolved contradictions
   - inherited overload policy is visible in exact-range structure
   - deload / mini-reset / reload / re-entry semantics are explicit where required
   - Build-entry logic stays conservative after shortened/base/re-entry context
   - no phase-level drift away from durability-first repeatability logic
   - no assumption that the writer will repair bundle semantics
   - if exact-range structure, week-role skeleton, or phase-slot alignment is wrong, return to Pass 1
   - if structure is valid but reload/re-entry semantics, legality framing, preview meaning, or writer-ready summary is incomplete, return to Pass 2
9. Mandatory Pass-2 authority consistency: keep the week blueprints consistent with the exact injected inherited scenario contract, exact allowed/forbidden intensity domains, exact allowed load modalities, exact role-week load bands, and exact phase-local objective. These values are not this task's output — they stay injected input context that constrains week-blueprint content.

Compact week-blueprint example:

```json
{
  "phase_id": "P01",
  "phase_range": "2026-24--2026-25",
  "week_blueprints": [
    {"week": "2026-24", "phase_role": "LOAD_1", "week_role": "LOAD_1"},
    {"week": "2026-25", "phase_role": "RELOAD", "week_role": "RELOAD"}
  ]
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
