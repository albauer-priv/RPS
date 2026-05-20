# Week Workout Validation Checklist

Use this checklist as the compact runtime review reference.

## Blocking syntax checks

- step lines must use `- <duration> <target> <cadence>`
- duration must be time-based only
- target must be percent, percent range, or ramp
- cadence must appear on every step line
- required sections:
  - `Warmup`
  - `Main Set`
  - `Cooldown`
- `#### Activation` is required for:
  - `Sweet Spot`
  - `Threshold`
  - `VO2max`

## Blocking token checks

Reject when any workout text contains:

- absolute watts
- `Z1` to `Z7`
- HR targets
- pace targets
- `@`
- `freeride`
- distance durations
- `Warmup:` / `Main Set:` prose serialization
- `MM:SS` or `HH:MM:SS` inside step lines
- hidden device/export flags like `press lap`, `power=`, `hr=`, `hidepower`

## Semantic checks

- family must match the declared day/domain intent
- targets must stay inside the legal family range
- week legality follows `PHASE_GUARDRAILS` first
- if the active week forbids `RECOVERY`, a recovery-like low-load day must be written as legal low-end `ENDURANCE`
- inherited `phase_intent` can narrow workout choice even when syntax is valid
