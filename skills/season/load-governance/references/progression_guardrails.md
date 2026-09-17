# Progression Guardrails

Source: `ProgressiveOverloadPolicy`, Sections 2-4.

Weekly kJ progression is primarily driven through volume/work, not intensity density.

## Global week-over-week ramp ranges

- Conservative: `+5%` to `+8%`
  - Use for high life stress, masters athletes, injury/illness history, low robustness, or poor recovery bandwidth.
- Standard: `+8%` to `+12%`
  - Use when recovery and execution stability are normal.
- Aggressive and rare: `+12%` to `+18%`
  - Use only for highly robust athletes with consistently strong recovery.

Hard safety cap:

- Avoid sustained ramps above `+15%` week-over-week outside explicit special cases such as return from very low load or planned camp patterns.

## Load/intensity interaction

- Progress weekly kJ primarily via volume/work, not by increasing intensity density.
- Do not simultaneously push kJ ramp to the top of the range and increase intensity density.
- Increase intensity only after stable tolerance to the current kJ level is demonstrated.

## Long-session dominance warning

If time metrics exist:

- `LR_share = Weekly Moving Time Max / Weekly Moving Time Total`
- Flag "long-ride dominated" weeks when `LR_share > 0.50`.
- Repeated dominance should trigger tighter ramps and preference for `2:1` or `2:1:1`.

## Deload target

Choose one anchor method and keep it consistent:

- Baseline anchored, recommended:
  - `DL_kJ = BL_kJ * 0.60 to 0.80`
  - Equivalent: `-20%` to `-40%` versus baseline.
- Last-build anchored:
  - `DL_kJ = prior_week_kJ * 0.55 to 0.75`
  - Equivalent: typically `-25%` to `-45%` versus last build week.

Content rules:

- A deload must reduce weekly kJ materially, not only intensity.
- Intensity during deload is only a short low-volume touch.

## Re-entry target

Baseline is the anchor; do not snap back to the peak build week.

- Default:
  - `RE_kJ = BL_kJ * 0.90 to 1.00`
- High fatigue or deload clearly needed:
  - `RE_kJ = BL_kJ * 0.85 to 0.95`
- Clearly fresh and robust, with no spike/dominance warnings:
  - `RE_kJ = BL_kJ * 0.95 to 1.05`

Readiness override:

- If readiness is still poor at the end of deload, extend deload or choose the lower end of the re-entry range.

## Disrupted week re-entry

When the most recent completed week load (`W_prev_actual`) is materially below the deterministic
`BL_kJ` (specifically: `W_prev_actual < BL_kJ × 0.85`), classify that week as a **disrupted
week** — below-baseline due to illness, travel, vacation, or other transient cause.

Rules for disrupted week:
- Do **not** use `W_prev_actual` as the re-entry anchor.
- Use the deterministic `BL_kJ` (historical baseline from the load-context) as the anchor.
- Apply the normal re-entry formula: `RE_kJ = BL_kJ × 0.90 to 1.00`.
- A season phase corridor starting at `RE_kJ = BL_kJ × 0.90–1.00` is valid re-entry even if it is
  substantially above `W_prev_actual` — the gap to `W_prev_actual` is explained by the disrupted
  week, not a planning error.

Blocker threshold: only raise a `blocking_issue` when the first planned corridor exceeds
`BL_kJ × 1.10` (aggressive overreach above baseline) **without** an explicit re-entry rationale,
or when the corridor materially exceeds the athlete's demonstrated maximum across the full
historical record. A corridor within `BL_kJ × 0.90–1.05` is never a blocker; it is the intended
re-entry range.

## Progressive overload lever rule

Season progression uses five independent levers:
1. Interval count (more repetitions per set)
2. Interval duration (longer intervals)
3. Interval intensity (higher target power or zone)
4. Total weekly kJ (more volume)
5. Fatigued-state quality (maintaining performance after substantial preload)

Advance **at most one or two** levers per phase or mesocycle step. Never combine top-of-range kJ
ramp with simultaneous density escalation in the same cycle step.
