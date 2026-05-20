---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: Specs
---
# PHASE_PREVIEW Validation

## Schema & meta
- [ ] Validates against `phase_preview.schema.json`.
- [ ] `data.traceability.derived_from` references the `phase_structure` it summarizes.
- [ ] `weekly_agenda_preview` covers the same phase weeks as the stored `phase_structure`.

## Content
- [ ] Preview is agenda-style and derived only from phase structure.
- [ ] No workouts, intervals, zones, or kJ prescriptions.
- [ ] Agenda day roles, intensity domains, and load modalities stay inside `phase_structure.structural_phase_elements`.
- [ ] Fixed non-training days remain non-training with `intensity_domain: NONE` and `load_modality: NONE`.
- [ ] Preview does not exceed the structure `max_quality_days_per_week`.
