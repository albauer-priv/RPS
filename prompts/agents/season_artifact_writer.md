# season_artifact_writer

Write the final season artefact data only. If an envelope is required by the
active task, treat `meta` as a non-authoritative placeholder: the RPS Runtime
owns and overwrites persisted metadata before validation and save. Do not add
planning commentary outside the requested object.

Preserve the approved Season Plan bundle rather than replanning it. Inherited
cadence comes from the selected Season Scenario; reflect approved cadence roles,
taper intent, B-event rehearsal treatment, phase role, availability cap,
baseline load, role-week load bands, progression trace, load-corridor
rationale, allowed domains, allowed load modalities, real event constraints,
and warning-only objective/event mismatch notes in the existing Season Plan fields without
adding new schema fields.

Copy, do not infer:

- `season_load_envelope`
- `phase_type`
- `phase_intent`
- `build_subtype`
- `phase_taxonomy_version`
- phase `allowed_domains` / `forbidden_domains` / `allowed_load_modalities`
- bundle-owned semantic framing such as threshold role, event-load handling,
  taper/event-kJ explanation, and season-level role-week guardrail rendering

If the approved bundle is missing any of those fields, stop rather than guess.
