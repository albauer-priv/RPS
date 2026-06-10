---
name: structure-authoring
description: Define week roles and structural skeleton for the exact phase range.
metadata:
  author: rps
  version: "4.0"
---
Author the phase structure after guardrails are known.

Definitions:
- `week_role`: inherited deterministic week-role label for an ISO week in the exact phase range
- `phase_role`: deterministic role of the exact phase block
- `weekly_kj_bands`: exact-range governance-load bands copied from phase guardrails
- `reload`: controlled return near prior build load after a limited reset
- `re-entry`: baseline-anchored conservative return after true deload or unresolved fatigue
- `Build-entry`: the first build-oriented step after shortened/base/re-entry context

Authority / injected sources:
- `week_role`, `phase_role`, and exact phase range come from deterministic phase context
- `weekly_kj_bands` come from approved phase guardrails
- this layer shapes week-role structure; it must not invent new cadence families or rewrite guardrail legality

Method:
1. Translate phase purpose into week roles and structural sequence covering every ISO week in the exact phase range.
2. Use injected `week_role_by_iso_week` exactly; week roles come from the selected scenario cadence and role-aware S5 context, not from structure authoring.
3. Use inherited canonical `phase_type` as the semantic container; do not invent or rename phase semantics during structure authoring.
4. Keep the structure compatible with cadence, recovery protection, event windows, phase role, weekly S5 bands, and allowed agenda semantics.
4a. Keep the structure explicitly compatible with inherited `phase_type`, `phase_intent`, and `build_subtype`; structure must narrow around intent, not reinterpret it.
5. Leave workout-level design and numeric targets to lower layers.

Required structure rules:
- `week_skeleton_logic.week_roles.week_roles` must cover every ISO week in `meta.iso_week_range` exactly.
- `week_skeleton_logic.week_roles.week_roles` must match the injected inherited week roles.
- `structural_phase_elements.allowed_intensity_domains` must equal exact inherited phase legality only; do not add `NONE`.
- `structural_phase_elements.allowed_load_modalities` must equal exact inherited load modalities only.
- `execution_principles.load_intensity_handling.forbidden_intensity_domains` must equal exact inherited forbidden domains only.
- `load_ranges.weekly_kj_bands` must be copied exactly from phase guardrails.
- `load_ranges.source` must use the stored phase-guardrails filename, not a guessed name.
- `upstream_intent.constraints` must include inherited planning constraints only and use season/global wording verbatim where required.
- `upstream_intent.constraints` must not contain runtime/process rules, authority-copy reminders, validation discipline, or preview-only semantics.
- Valid examples:
  - `Fixed rest days are Monday and Friday.`
  - `Weekday training must fit compact Tue-Thu windows, with longer work shifting to the weekend.`
  - `2026-15 B Brevet 200 km Toelzer-Land-Runde`
- Invalid examples:
  - `Use the injected role-week banding exactly.`
  - `Do not widen legality from scenario eligibility.`
  - `Operational NONE stays in preview/non-training-day semantics only.`
- `key_risks_warnings` must stay aligned with phase guardrails.

Canonical exact-authority fragment:

```json
{
  "structural_phase_elements": {
    "allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
    "allowed_load_modalities": ["NONE"]
  },
  "execution_principles": {
    "load_intensity_handling": {
      "forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"]
    }
  },
  "load_ranges": {
    "weekly_kj_bands": [
      {"week": "2026-24", "band": {"min": 7200, "max": 8200}},
      {"week": "2026-25", "band": {"min": 7300, "max": 8300}}
    ],
    "source": "phase_guardrails_2026-24--2026-25__20260608_090000.json"
  }
}
```

Structural content rules:
- define role progression and recovery opportunities, not daily workouts
- include allowed role set, mandatory elements, optional elements, and excluded patterns
- preserve fixed non-training days and long-endurance anchor protection
- prefer repeatable structure over brittle optimization
- make inherited cadence operational in the structure: build, deload, mini-reset, reload, and re-entry must be visibly distinguishable where policy requires it
- keep reload distinct from re-entry; when fallback logic turns a nominal reload into baseline-anchored resumption, say so explicitly
- preserve conservative Build-entry logic when shortened/base/re-entry context precedes the phase
- `specificity_build` must push structure toward pacing/fueling/terrain/logistics realism
- `durability_build` must emphasize B2B, preload, hard-late, and long-ride protection rather than rehearsal semantics
- `vo2_build` must keep VO2 weeks fresh and bounded rather than broad mixed-density
- `threshold_build` must center sustained-power structure
- `sst_build` must keep moderate density bounded
- `taper_freshening` must preserve freshness and reduce accumulation patterns
- `race_execution` must keep event logistics and recovery runway explicit

Progression axes in structure:
- duration / total governance work
- density / complexity of key-work placement
- intensity last

Structure-level progression rule:
- the structure must never imply simultaneous escalation of duration, density, and intensity unless an explicit bounded exception exists upstream

Operational cadence rules for structure authoring:
- `3:1` structure should read as:
  - W1 controlled build entry
  - W2 progressive build
  - W3 further build progression
  - W4 materially reduced deload
- `2:1` structure should read as:
  - W1 controlled build entry
  - W2 progressive build
  - W3 materially reduced deload
- `2:1:1` structure should read as:
  - W1 controlled build entry
  - W2 progressive build
  - W3 mini-reset, not full collapse
  - W4 reload near W2 if readiness is adequate
- fallback interpretation:
  - if readiness is poor after W2/W3, W3 may become true deload
  - then W4 must be written as re-entry, not reload

Build-entry conservatism:
- after shortened/base/re-entry context, the first Build week should use lower-corridor or otherwise conservative structure
- avoid writing the first Build week as the densest or most specific week of the phase
- if the inherited phase intent is `durability_build`, early structure should earn durability load through repeatability before hard-late or heavy preload escalation

Hard rules:
- keep numeric daily targets in downstream week artifacts
- keep workouts, intervals, zones, and %FTP in downstream week/workout artifacts
- provide complete week-role coverage
- preserve the season objective inside the phase
- objective mismatch remains warning-only and input-owned; do not rewrite it in phase structure authoring
- emit `upstream_intent.phase_type`, `upstream_intent.phase_intent`, and `upstream_intent.phase_taxonomy_version` explicitly and keep them identical to upstream authority
- emit `upstream_intent.build_subtype` explicitly for `BUILD` phases and keep it identical to upstream authority

Positive operating guidance:
- Use the active task, injected context, and configured skill role to choose the smallest coherent contribution.
- Read the available evidence, check the governing constraints, and explain the decision path in direct operational language.
- Produce actionable content that helps the next task continue without recomputing or guessing.
- Include required facts, assumptions, warnings, and trace cues when they are available.
- Return a concise result that supports the task expected_output and preserves the authoritative runtime context.

Output format:
- Return the active task expected_output with clear sections for facts, decision, rationale, warnings, and next action when applicable.
- Include only information needed by the active task and downstream consumer.
