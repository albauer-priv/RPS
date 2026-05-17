# Baseline Selection

Source: `ProgressiveOverloadPolicy`, Section 1.

When deriving corridor logic from recent training, use a deterministic baseline week.

## Lookback

- Use the last `6-8` weeks from weekly data.
- Default lookback: `8` weeks.
- Compute:
  - `MED_kJ = median(Work (kJ))`
  - `MED_time = median(Weekly Moving Time Total (min))`

## Structural exclusions

Exclude a candidate week when any of these are true:

- `Work (kJ) < 0.80 * MED_kJ` -> deload or disrupted-load week.
- `Work (kJ) > 1.15 * MED_kJ` -> spike or peak week.
- `# Activities < 4` -> too sparse.

## Baseline quality gates

A remaining week qualifies if it passes at least `2 of 3` gates:

1. Aerobic structure:
   - `Z2 Share (Power) (%) >= 60`
   - Semantics: pure `Power TiZ Z2 / sum(Power TiZ Z1..Z7)`, not `Z1 + Z2`.
2. Stability / durability:
   - `Durability Index (DI) >= 0.95`, or
   - `Any Flag Drift Valid (Z2 >= 90min) = true` and `Decoupling (%) <= 5`.
3. Execution sufficiency:
   - `# Activities >= 4`
   - `Work (kJ) >= 0.85 * MED_kJ`
   - `Weekly Moving Time Total (min) >= 0.85 * MED_time`

## Final selection

- `BL_week` is the most recent week that passes exclusions and at least `2/3` gates.
- `BL_kJ = Work (kJ)` of `BL_week`.

## Fallback

If no week qualifies:

- `BL_kJ = MED_kJ`
- `baseline_confidence = low`
