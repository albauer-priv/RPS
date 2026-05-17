# Cadence Selection

Sources: `DurabilityFirstPrinciples`, Section 3.3; `ProgressiveOverloadPolicy`, Section 4.

## Authority

- Scenario/Season selects or constrains cadence.
- Phase applies the selected cadence to the exact phase range.
- Week executes the active phase/week role.
- Phase and Week must not invent a more aggressive cadence.

## Cadence models

- `3:1`: 4-week phase, `3 load weeks + 1 deload`.
- `2:1`: 3-week phase, `2 load weeks + 1 deload`.
- `2:1:1`: 4-week phase, `2 load weeks + 1 mini-reset + 1 reload/consolidation`.

## Prefer 2:1 when

- high life stress or variable sleep
- masters athlete or reduced recovery capacity
- fragile history: injury, illness, repeated overreaching signs
- higher intensity density
- frequent back-to-back long sessions

## Prefer 3:1 when

- high robustness and stable recovery
- multiple years of consistent training
- three progressive build weeks are needed and likely sustainable

## Prefer 2:1:1 when

- two build weeks are tolerated but week 3 often breaks down
- smaller fatigue waves are desired over a long season
- a mini-reset is useful without a full deload drop

## Constrained time window

Set `constrained_time_window = true` when any is true:

- `weeks_to_next_A_event < default_phase_length_weeks`
- a complete load -> deload -> adaptation sequence cannot fit before a required checkpoint
- external constraints such as travel, work, or illness compress/remove weeks

When constrained:

- shorten phase length
- reduce weekly load accumulation
- increase recovery frequency
- prioritize stability over progression elegance

Forbidden when constrained:

- stacking multiple load weeks without deload
- borrowing recovery from future phases
- attempting repeated peak logic
