# Workout Syntax Review Checklist

Validate candidate workout text against the project subset.

## Required
- top-level sections follow `Warmup -> Activation? -> Main Set -> Add-On? -> Cooldown`
- every step line starts with `-`
- duration is time-based only: `30s`, `4m`, `1h30m`, `1m30`
- target is `%`, `%- %`, or `ramp low%-high%`
- cadence is always present as `NNrpm` or `NN-NNrpm`

## Forbidden
- `@` shorthand
- `Z1`-`Z7`
- HR or pace targets
- absolute watts
- `MM:SS` / `HH:MM:SS` in step lines
- nested loops
- free-form cadence labels
