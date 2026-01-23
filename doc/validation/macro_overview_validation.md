# MACRO_OVERVIEW Validation

## Schema & meta
- [ ] Validates against `macro_overview.schema.json`.
- [ ] `meta.schema_id` = `MacroOverviewInterface` and `meta.schema_version` is current.
- [ ] `meta.iso_week_range` spans the intended planning horizon.

## Upstream coverage
- [ ] `body_metadata.season_brief_ref` and `kpi_profile_ref` are set.
- [ ] `global_constraints.availability_assumptions`, `risk_constraints`, `planned_event_windows`, and `recovery_protection` are present.
- [ ] If fixed rest days are known, `global_constraints.recovery_protection.fixed_rest_days` is set.
- [ ] If `global_constraints.recovery_protection` is present, `notes` is filled (can be empty if explicitly unknown).
- [ ] Risk and availability statements reflect the season brief inputs.
- [ ] Availability assumptions reflect the Season Brief weekday availability table.

## Content sanity
- [ ] Phases cover the full horizon with no gaps.
- [ ] Allowed/forbidden domains match `agenda_enum_spec.md`.
- [ ] `explicit_forbidden_content` includes no micro or meso planning detail.

## Principles compliance
- [ ] Phase narratives or rationale state the intended intensity distribution (polarized vs pyramidal-leaning) in line with section 4.6.
- [ ] Progressive overload follows section 5 (time/kJ primary, intensity last) and deload rationale is explicit where load drops.
- [ ] If any phase uses steady-state load corridors, the narrative explains the macro-level reason.
- [ ] `data.justification` includes a summary, citations (principles + evidence), and per-phase justifications.
