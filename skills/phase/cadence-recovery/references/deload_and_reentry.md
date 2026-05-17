# Deload and Re-Entry

Source: `ProgressiveOverloadPolicy`, Sections 3 and cadence chapters A-C.

## Deload targets

Choose one reference method and keep it consistent:

- Baseline anchored, recommended:
  - `DL_kJ = BL_kJ * 0.60 to 0.80`
  - `-20%` to `-40%` versus baseline.
- Last-build anchored:
  - `DL_kJ = prior_week_kJ * 0.55 to 0.75`
  - typically `-25%` to `-45%` versus last build week.

Deload content:

- Deload must reduce weekly kJ meaningfully, not just intensity.
- Intensity touches during deload remain short and low-volume.

## Re-entry targets

- Default:
  - `RE_kJ = BL_kJ * 0.90 to 1.00`
- If fatigue was high or the deload was clearly needed:
  - `RE_kJ = BL_kJ * 0.85 to 0.95`
- If clearly fresh and robust, with no spike/dominance warnings:
  - `RE_kJ = BL_kJ * 0.95 to 1.05`

Rules:

- Re-entry returns near baseline, not peak build.
- If fatigue remains high, use the lower end of the re-entry range or extend deload.

## 3:1 targets

- `W1_kJ = BL_kJ * 1.00 to 1.05`
- `W2_kJ = W1_kJ * 1.08 to 1.12`
- `W3_kJ = W2_kJ * 1.06 to 1.10`
- `DL_kJ` follows the deload target above, commonly `-25%` to `-45%` versus W3 or `-20%` to `-40%` versus BL.
- Re-entry after deload: `RE_kJ = BL_kJ * 0.90 to 1.00`.
- Do not restart at `W3_kJ`.

Switch away from 3:1 when week 3 repeatedly collapses, deload does not restore readiness, or long-session dominance repeats.

## 2:1 targets

- `W1_kJ = BL_kJ * 1.00 to 1.05`
- `W2_kJ = W1_kJ * 1.08 to 1.15`
- `DL_kJ` follows the deload target above, commonly `-25%` to `-45%` versus W2.
- Re-entry after deload: `RE_kJ = BL_kJ * 0.90 to 1.05`.
- If fatigue persists: `RE_kJ = BL_kJ * 0.85 to 0.95`.

## 2:1:1 targets

- `W1_kJ = BL_kJ * 1.00 to 1.05`
- `W2_kJ = W1_kJ * 1.08 to 1.12`
- `MR_kJ = W2_kJ * 0.80 to 0.90`
- `W4_kJ = W2_kJ * 0.95 to 1.05`

Fallback path:

- If fatigue in W2 is high or readiness in W3 is poor, replace `MR_kJ` with a true `DL_kJ`.
- Treat W4 as `RE_kJ` when mini-reset becomes true deload.

Baseline update for next phase:

- `BL_kJ_next = mean(W2_kJ, W4_kJ)`
- Or use `CH_kJ` when rolling stability is the chosen reference.
