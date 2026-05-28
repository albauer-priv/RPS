---
name: artifact-writing
description: Serialize the final approved season artifact envelope without adding planning content.
metadata:
  author: rps
  version: "3.1"
---
Write the approved `SEASON_PLAN` data only.

Method:
1. Prefer emitting the approved `data` payload. If the active task still requires an envelope, emit one top-level object with exactly `meta` and `data`.
2. Writer runs only after Pass 3 self-audit passed and Review approved. If Review classified a Pass 1 or Pass 2 return finding, writer must not run.
3. Preserve the approved season bundle exactly and write only the approved planning content.
4. Do not invent persisted `meta`. Runtime owns `artifact_type`, `schema_id`, `schema_version`, `authority`, `owner_agent`, `run_id`, and `created_at`.
5. Preserve exact `iso_week`, `iso_week_range`, `temporal_scope`, `trace_upstream`, `trace_data`, and `trace_events` only as non-authoritative context/trace hints when available.
6. Preserve approved phase blueprint semantics, including inherited `scenario_cadence`, `cadence_week_roles`, A/B event treatment, taper intent, allowed domains, allowed load modalities, and canonical phase taxonomy, by reflecting them in existing Season Plan fields.
   Also preserve `season_phase_role`, availability cap, baseline load, role-week load bands, progression trace, and load feasibility status in existing narrative/notes fields.
   Preserve explicit `phase_type`, `phase_intent`, `build_subtype`, and `phase_taxonomy_version` on every written phase.
7. Keep season-wide constraints, event windows, phase definitions, and citations complete and schema-valid.
8. Validate locally against `season_plan.schema.json` before any store call.

Writer rules:
- season output is binding; scenario artifacts remain informational
- required strings must be non-empty
- use the real approved phase ranges and dates exactly as provided during writing
- do not choose, rewrite, or normalize cadence during writing; cadence has already been selected upstream by Scenario Selection
- when cadence roles exist in the approved bundle, reflect them in `deload_rationale`, `typical_duration_intensity_pattern`, and `weekly_load_corridor.weekly_kj.notes`
- `weekly_load_corridor.weekly_kj.min/max` must come from the approved phase blueprint's availability-bounded recommended phase corridor
- `weekly_load_corridor.weekly_kj.notes` must mention phase role, availability cap, baseline, and role-week load semantics when available, and must render role-week bands as inherited season-level guardrails rather than week prescriptions
- `phase_type`, `phase_intent`, `build_subtype`, and `phase_taxonomy_version` must be copied exactly from the approved phase blueprint; do not infer, rename, or backfill legacy labels during writing
- `season_load_envelope` must be copied exactly from the approved bundle; do not recalculate or widen it during writing
- approved phase `allowed_domains` / `forbidden_domains` / `allowed_load_modalities` must be copied into the existing phase semantics fields exactly; do not broaden or reinterpret them during writing
- approved bundle `semantic_contract` notes own the method framing for threshold role, B-event handling, and taper/event-kJ explanation; serialize them into existing narrative fields without inventing a new interpretation
- `events_constraints` must contain real A/B/C planning events only; do not serialize synthetic “no event” placeholders
- if a primary objective appears materially misaligned with the highest in-horizon A event, preserve the warning in the plan but do not block writing
- if a required field is missing, unknown, or schema-invalid: stop rather than guess
- do not treat the writer as a semantic repair pass; if the approved bundle is not writer-ready, fail rather than reinterpret

Hard rules:
- write only approved season logic during writing
- render user-facing chat as readable prose/tables instead of raw JSON
- call persistence tools only after schema validity is satisfied
- fill required fields and citations with real approved content

Positive operating guidance:
- Use the active task, injected context, and configured skill role to choose the smallest coherent contribution.
- Read the available evidence, check the governing constraints, and explain the decision path in direct operational language.
- Produce actionable content that helps the next task continue without recomputing or guessing.
- Include required facts, assumptions, warnings, and trace cues when they are available.
- Return a concise result that supports the task expected_output and preserves the authoritative runtime context.

Output format:
- Return only the schema-compliant object required by the active task expected_output.
- Focus on `data`; if an envelope is requested, `meta` is a runtime-overwritten placeholder/hint.
- Preserve approved bundle content, review decisions, deterministic context, and trace references.
- Emit only the artifact object.
