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
