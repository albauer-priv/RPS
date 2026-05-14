# Load Estimation Terms and Invariants

## Terms
- `planned_kj`: mechanical work estimate
- `planned_if`: session intensity factor
- `planned_load_kj`: governance load metric used for corridors and bands

## Invariants
- `weekly_kj_bands` refer to governance load, not raw mechanical work
- `IF_ref_load` is a normalization constant, not a second intensity factor
- intensity weighting is applied exactly once
- rounding happens only at output, never in intermediate math
