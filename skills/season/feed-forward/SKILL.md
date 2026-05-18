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
  - `Season-level signal only`
  - `Week-level plan remains governed by active week artefacts`
  - `KPI evidence remains diagnostic at season-feed-forward scope`
- `phase_adjustment.applies_to_weeks`
- `phase_adjustment.adjustments.kj_corridor`
- `phase_adjustment.adjustments.quality_density`

Hard rules:
- keep output at season feed-forward scope
- route week-level intervention to week planning tasks
- keep KPI-threshold interpretation diagnostic at this scope
- store only schema-valid outputs with complete adjustment fields

Positive operating guidance:
- Use the active task, injected context, and configured skill role to choose the smallest coherent contribution.
- Read the available evidence, check the governing constraints, and explain the decision path in direct operational language.
- Produce actionable content that helps the next task continue without recomputing or guessing.
- Include required facts, assumptions, warnings, and trace cues when they are available.
- Return a concise result that supports the task expected_output and preserves the authoritative runtime context.

Output format:
- Return the task expected_output as advisory feed-forward guidance.
- Include evidence summary, affected scope, recommended adjustment theme, warnings, and trace references.
- Keep feed-forward diagnostic or advisory unless the active artifact schema makes it binding.
