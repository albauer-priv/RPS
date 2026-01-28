---
Type: Policy
Policy-For: PROGRESSIVE_OVERLOAD
Policy-ID: ProgressiveOverloadPolicy
Version: 1.0

Scope: Shared
Authority: Binding

Applies-To:
  - Season-Planner
  - Phase-Architect
  - Week-Planner

Notes: >
  Binding rules for kJ-based progressive overload, deload, re-entry, and
  cadence selection. Applies to phase/phase planning and weekly corridor
  derivation in Season/Phase, and weekly execution planning in Week.
---

# Progressive Overload Policy (kJ-based)

## Phase Cadence, Deload and Re-Entry Rules for Phase Planning (2:1 / 3:1 / 2:1:1)

## Scope and intent

This policy defines enforceable rules for planning phases/phases using
weekly work (kJ) as the primary load metric. It specifies:

- how to progress load within a phase,
- how to execute a deload (or mini-reset),
- how to set re-entry load after deload,
- and how to choose between 2:1, 3:1, and 2:1:1 cadences based on athlete
  robustness and recovery capacity.

It is designed for endurance contexts (brevets/ultra) where weekly work is
an accurate proxy for overall load.

---

## 0) Definitions and required inputs

### Primary metric

- weekly_kJ: total training work (kJ) in a calendar week.

### Reference values (computed consistently)

- BL_week: baseline week (definition in Section 1).
- BL_kJ: weekly_kJ of BL_week (anchors progression, deload, and re-entry).
- PK_kJ: highest weekly_kJ in the most recent build segment.
- CH_kJ: rolling mean of weekly_kJ over the last 3-4 weeks (optional; for
  stability checks).

### Optional guardrails (recommended if available)

- weekly_time_min: total weekly moving time (minutes).
- LR_share: dominance indicator of the longest session, e.g.
  Weekly Moving Time Max (min) / Weekly Moving Time Total (min) (if available).
- Aerobic structure and stability indicators (e.g., Z2 share, decoupling,
  DI), if available.

---

## 1) Baseline Week (BL_week) and BL_kJ: deterministic selection (kJ + time)

This replaces any earlier "well-tolerated" wording with a deterministic rule and
avoids Adherence (%) because it is not populated in the weekly file.

### 1.1 Lookback window

Use the last 6-8 weeks (default: 8) from the weekly dataset.

Compute robust reference medians over the lookback:

- MED_kJ = median(Work (kJ))
- MED_time = median(Weekly Moving Time Total (min))

### 1.2 Structural exclusions (must NOT be true)

Exclude any week if any of the following is true:

(E1) Deload / disrupted-load week (kJ)
- Work (kJ) < 0.80 x MED_kJ

(E2) Spike / peak week (kJ)
- Work (kJ) > 1.15 x MED_kJ

(E3) Too sparse
- # Activities < 4

### 1.3 Baseline quality gates (must pass 2 of 3)

From remaining weeks, a week qualifies as a baseline candidate if it passes
at least 2 of:

G1 - Structure (aerobic distribution)
- Z2 Share (Power) (%) >= 60%

G2 - Stability (durability / efficiency)
Pass if either:
- Durability Index (DI) >= 0.95, or
- Any Flag Drift Valid (Z2 >= 90min) (bool) = True AND Decoupling (%) <= 5%

G3 - Execution (kJ + time; relative, athlete-scaled)
Pass if all are true:
- # Activities >= 4, and
- Work (kJ) >= 0.85 x MED_kJ, and
- Weekly Moving Time Total (min) >= 0.85 x MED_time

### 1.4 Final selection rule

- BL_week = the most recent week in lookback that passes exclusions (1.2)
  and at least 2/3 gates (1.3)
- BL_kJ = Work (kJ) of BL_week

### 1.5 Fallback (if no week qualifies)

- Set BL_kJ = MED_kJ and mark baseline confidence = low.

---

## 2) Global progression guardrails (apply to all cadences)

### 2.1 Weekly progression ramp (default ranges)

Progress weekly_kJ primarily via volume/work, not via intensity increases.

Allowed week-over-week ramp (vs prior week):

- Standard: +8-12%
- Conservative: +5-8% (high life stress, masters, injury/illness history,
  low robustness)
- Aggressive (rare): +12-18% (only if athlete is highly robust and recovery
  is consistently strong)

Hard safety cap:
- Avoid sustained ramps >15% week-over-week outside special cases (return from
  very low load; planned camp patterns).

### 2.2 Long-session dominance (recommended warning, not a hard gate)

If time metrics exist:
- Flag "long-ride dominated" weeks if LR_share > 0.50 (longest session exceeds
  50% of weekly time). If flagged repeatedly, prefer 2:1 or 2:1:1 cadence and/or
  tighten ramps.

### 2.3 Intensity containment during overload

To keep kJ-based overload safe:
- Do not simultaneously push kJ ramp to the top of the range and increase
  intensity density.
- Increase intensity only after stable tolerance to the current kJ level
  is demonstrated.

---

## 3) Deload and re-entry (cadence-independent rules)

### 3.1 Deload target (DL_kJ)

Choose one reference method and keep it consistent across the plan.

Method A (baseline-anchored, recommended):
- DL_kJ = BL_kJ x (0.60 to 0.80)  -> -20% to -40% vs baseline

Method B (last build week anchored):
- DL_kJ = prior_week_kJ x (0.55 to 0.75) -> typically -25% to -45% vs last build

Deload content rules:
- A deload must reduce weekly_kJ meaningfully (not only intensity).
- Prefer mostly low intensity; if including intensity, keep it as a short
  "touch" with low total time-in-zone.

### 3.2 Re-entry target (RE_kJ)

Re-entry should not snap back to peak build; baseline is the anchor.

Default:
- RE_kJ = BL_kJ x (0.90 to 1.00)

If fatigue was high / deload clearly needed:
- RE_kJ = BL_kJ x (0.85 to 0.95)

If athlete is clearly fresh and robust:
- RE_kJ = BL_kJ x (0.95 to 1.05) (only if spike/dominance warnings are not
  triggered)

### 3.3 Readiness gate (override logic)

If readiness is still poor at end of deload:
- extend deload or set RE_kJ at the lower end of the allowed range.

---

## 4) Cadence selection (2:1 vs 3:1 vs 2:1:1)

### Prefer 2:1 when

- high life stress / variable sleep
- masters athlete or reduced recovery capacity
- fragile history (injury/illness, repeated overreaching signs)
- higher intensity density or frequent back-to-back long sessions

### Prefer 3:1 when

- high robustness and stable recovery
- multiple years of consistent training
- need 3 progressive build weeks to expand weekly_kJ safely

### Prefer 2:1:1 when

- athlete tolerates two build weeks but week 3 often breaks down
- you want smaller fatigue waves over long seasons
- you want a mini-reset without a full deload drop

---

# Cadence-specific chapters

## Chapter A: 3:1 Policy (3 build weeks + 1 deload)

### A1) Planning rules (kJ targets)

- W1_kJ = BL_kJ x (1.00 to 1.05)
- W2_kJ = W1_kJ x (1.08 to 1.12)
- W3_kJ = W2_kJ x (1.06 to 1.10) (often slightly flatter than W2)
- DL_kJ per Section 3.1 (commonly -25% to -45% vs W3, or -20% to -40% vs BL)

### A2) Re-entry after deload

- RE_kJ = BL_kJ x (0.90 to 1.00) (default)
- Do not restart at W3_kJ.

### A3) Exit criteria (switch cadence)

Switch from 3:1 to 2:1 or 2:1:1 if repeated:
- week 3 quality/consistency collapses,
- deload does not restore readiness,
- or long-session dominance is repeatedly flagged.

---

## Chapter B: 2:1 Policy (2 build weeks + 1 deload)

### B1) Planning rules (kJ targets)

- W1_kJ = BL_kJ x (1.00 to 1.05)
- W2_kJ = W1_kJ x (1.08 to 1.15) (slightly wider because deload arrives earlier)
- DL_kJ per Section 3.1 (commonly -25% to -45% vs W2)

### B2) Re-entry after deload

- RE_kJ = BL_kJ x (0.90 to 1.05) (often tolerable because fatigue accumulation
  is smaller)
- If fatigue persists: RE_kJ = BL_kJ x (0.85 to 0.95)

### B3) Exit criteria

If deload is repeatedly unnecessary and baseline stalls for multiple cycles,
consider 3:1 or 2:1:1.

---

## Chapter C: 2:1:1 Policy (2 build weeks + mini-reset + consolidation build)

### C1) Planning rules (kJ targets)

- W1_kJ = BL_kJ x (1.00 to 1.05)
- W2_kJ = W1_kJ x (1.08 to 1.12)
- MR_kJ = W2_kJ x (0.80 to 0.90) -> mini-reset (-10% to -20%)
- W4_kJ = W2_kJ x (0.95 to 1.05) -> consolidate around W2

### C2) Fallback path: mini-reset becomes a true deload

If fatigue in W2 is high or readiness in W3 is poor:
- replace MR_kJ with a true DL_kJ per Section 3.1,
- treat W4 as RE_kJ per Section 3.2 (baseline-anchored re-entry).

### C3) Baseline update for next phase

Update BL_kJ conservatively:
- BL_kJ_next = mean(W2_kJ, W4_kJ) (or use CH_kJ if you prefer rolling stability).

---

## Implementation notes (policy-relevant)

- Keep the policy metric-consistent: if weekly_kJ is the primary load, do not
  let time or TSS override it; time is used as a baseline validity and
  dominance check.
- Always prioritize repeatability: the "best" week is the week the athlete can
  execute consistently, not the week with the highest kJ.

---

## End of ProgressiveOverloadPolicy (Binding)
