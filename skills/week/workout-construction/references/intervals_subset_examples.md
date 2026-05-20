# Week Workout Intervals Subset

Use these references as compact runtime examples. They are not optional style suggestions.

## Required top-level order

1. `Warmup`
2. `#### Activation` when required
3. `Main Set`
4. `#### Add-On` or `#### Z2 Add-On` when used
5. `Cooldown`

## Accepted step-line form

```text
- <duration> <target> <cadence>
```

Accepted target forms:
- `90%`
- `65%-72%`
- `ramp 50%-75%`

Accepted cadence forms:
- `85rpm`
- `85-95rpm`

## Allowed examples

### Endurance

```text
Warmup
- 8m ramp 50%-65% 85-90rpm

Main Set
- 1h40m 68%-72% 85-90rpm

Cooldown
- 8m ramp 60%-45% 80-85rpm
```

### Low-load endurance when RECOVERY is forbidden upstream

```text
Warmup
- 6m ramp 50%-60% 85-90rpm

Main Set
- 40m 60%-65% 85-90rpm

Cooldown
- 6m ramp 55%-45% 80-85rpm
```

### Tempo

```text
Warmup
- 8m ramp 50%-70% 85-90rpm

Main Set
3x
- 10m 80%-83% 85-90rpm
- 3m 60% 85rpm

Cooldown
- 8m ramp 60%-45% 80-85rpm
```

### Sweet Spot

```text
Warmup
- 8m ramp 50%-70% 85-90rpm

#### Activation
3x
- 20s 120% 95rpm
- 40s 60% 85rpm

Main Set
3x
- 12m 88%-90% 85-90rpm
- 3m 60% 85rpm

Cooldown
- 8m ramp 60%-45% 80-85rpm
```

## Forbidden examples

Never emit forms like:

```text
Warmup: 20 min progressive spin, power 160-190 W
Main Set: 3 x 25 min steady Z2 endurance
Cooldown: 15 min easy spin
```

Forbidden tokens/patterns:
- absolute watts
- `Z1` to `Z7`
- HR targets
- pace targets
- `@` shorthand
- `MM:SS` or `HH:MM:SS` inside step lines
