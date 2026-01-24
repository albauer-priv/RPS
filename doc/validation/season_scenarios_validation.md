# SEASON_SCENARIOS Validation

- [ ] Validates against `season_scenarios.schema.json`.
- [ ] `meta` includes required fields and correct `artifact_type` / `schema_id`.
- [ ] `data.season_brief_ref` and `data.kpi_profile_ref` are present.
- [ ] Exactly three scenarios (A, B, C) with required fields.
- [ ] `scenario_guidance` present per scenario with:
  - deload cadence + phase length consistency (3:1 → 4 weeks, 2:1 → 3 weeks, 2:1:1 → 4 weeks)
  - phase plan summary (full phases + shortened phases)
  - risk flags, fixed rest days, constraints, KPI guardrails, decision notes, intensity guidance
- [ ] `data.planning_horizon_weeks` matches weeks implied by `meta.iso_week_range`.
- [ ] No workouts, sessions, or daily/weekly plans included.
