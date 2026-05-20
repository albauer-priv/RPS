---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: Specs
---
# PHASE_PREVIEW Validation

## Schema & meta
- [ ] Validates against `phase_preview.schema.json`.
- [ ] `data.traceability.derived_from` references the exact stored `phase_structure_<version>.json` it summarizes.
- [ ] `weekly_agenda_preview` covers the same phase weeks as the stored `phase_structure`.

## Content
- [ ] Preview is agenda-style and derived only from phase structure.
- [ ] No workouts, intervals, zones, or kJ prescriptions.
- [ ] Deterministic repair is allowed only for strictly derived fields: exact structure traceability, fixed non-training-day semantics, and excess `QUALITY` labels above the structure cap.
- [ ] Agenda day roles, intensity domains, and load modalities stay inside `phase_structure.structural_phase_elements`.
- [ ] `PHASE_STRUCTURE` operational intensity domains required by allowed day roles (`NONE` for fixed non-training semantics, `RECOVERY` for recovery semantics) are normalized before preview validation.
- [ ] Fixed non-training days remain non-training with `intensity_domain: NONE` and `load_modality: NONE`.
- [ ] Preview does not exceed the structure `max_quality_days_per_week`.
