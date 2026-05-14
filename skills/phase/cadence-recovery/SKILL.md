---
name: cadence-recovery
description: Apply season-owned cadence, deload, and re-entry rules inside an exact phase range.
metadata:
  author: rps
  version: "4.0"
---
Apply cadence as a constrained translation problem.

Method:
1. Confirm the season-compatible cadence family: `3:1`, `2:1`, or `2:1:1`.
2. Place build, deload, and mini-reset weeks so the exact phase range stays coherent.
3. Define deload magnitude and re-entry load from the selected baseline.
4. Favor the shorter fatigue wave whenever tolerance or logistics are uncertain.

Selection rules:
- `2:1` for fragile recovery, life stress, masters profiles, injury/illness sensitivity, or repeated build-week collapse
- `3:1` only with stable robustness and evidence that three progressive weeks are sustainable
- `2:1:1` when two build weeks are tolerated but a full third build week is consistently too much

Deload and re-entry:
- deload must reduce meaningful weekly load, not merely relabel intensity
- a typical deload sits around `-20%` to `-40%` versus baseline or `-25%` to `-45%` versus the last build week, depending on the chosen anchor
- re-entry usually returns around `90%` to `100%` of baseline weekly load
- when fatigue remains high, re-entry should be lower rather than forcing the old build target

Hard rules:
- do not invent a more aggressive cadence than season logic allows
- re-entry must not snap directly back to peak build
- deloads and mini-resets must remain visible in the phase structure
- cadence logic may constrain structure, but it must not silently rewrite season authority
