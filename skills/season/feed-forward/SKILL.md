---
name: feed-forward
description: Produce season-to-phase feed-forward guidance as bounded season-level deltas only.
metadata:
  author: rps
  version: "2.0"
---
Write `SEASON_PHASE_FEED_FORWARD` as a bounded season-to-phase adjustment layer.

Method:
1. Use the season plan and DES analysis report as the source context.
2. State whether the conclusion is `no_change`, `adjust_phase`, or `reweight_season`.
3. Limit output to phase-facing deltas: affected weeks, corridor direction/percent, and quality-density action/details.
4. Preserve explicit non-actions so the artefact cannot become a week-level intervention.
5. Validate against `season_phase_feed_forward.schema.json` before storing.

Required content:
- `source_context.season_plan_ref`
- `source_context.des_analysis_report_ref`
- `source_context.affected_phase_id`
- `decision_summary.conclusion`
- `decision_summary.rationale`
- `explicit_non_actions` with exactly:
  - `No weekly workout changes`
  - `No week-level intervention`
  - `No KPI threshold enforcement`
- `phase_adjustment.applies_to_weeks`
- `phase_adjustment.adjustments.kj_corridor`
- `phase_adjustment.adjustments.quality_density`

Hard rules:
- do not emit weekly workout changes
- do not emit week-level intervention
- do not emit KPI-threshold enforcement instructions
- do not store if schema-invalid or if the adjustment fields are incomplete
