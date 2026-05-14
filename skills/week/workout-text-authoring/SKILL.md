---
name: workout-text-authoring
description: Author valid workout text for the RPS project subset and execution intent.
metadata:
  author: rps
  version: "5.0"
---
Author workout text only after the governing role, duration, and load intent are already set.

Top-level document rules:
- optional description paragraphs may appear before the first block
- allowed blocks are: section blocks, loop blocks with `Nx` header, standalone steps, and at most one `Category:` line
- in RPS, use the ordered top-level sections:
  1. `Warmup`
  2. `#### Activation` when required
  3. `Main Set`
  4. `#### Add-On` or `#### Z2 Add-On` when used
  5. `Cooldown`
- omit optional sections entirely when unused; never leave empty headings

Step grammar in the project subset:
- every step line starts with `-`
- every step line uses a time duration, a power target, and a cadence value
- only these target forms are allowed:
  - percent: `90%`
  - percent range: `65%-72%`
  - ramp: `ramp 60%-75%`
- cadence is always required as `NNrpm` or `NN-NNrpm`
- loops use a separate `Nx` header and are never nested
- comments, if used, are on their own line and separated cleanly from steps and loops

Warmup / activation / cooldown rules:
- every workout has a WarmupBlock and a CooldownBlock
- warmup should be `1-4` step lines and should not exceed roughly `10` minutes total
- cooldown should be `1-3` step lines and should not exceed roughly `8` minutes total
- activation is mandatory for `VO2max`, `Threshold`, and `Sweet Spot`; optional for `Tempo`
- add-ons may extend aerobic load but must not change workout classification

Intent mapping rules:
- every workout maps to exactly one agenda/intensity configuration
- workout text must not change the governing day role or intensity domain
- `Endurance`, `Recovery`, `Tempo`, `Sweet Spot`, `Threshold`, `VO2max`, and `K3` intents must remain structurally recognizable

Hard prohibitions:
- no `@` shorthand
- no zone targets (`Z1`-`Z7`)
- no HR or pace targets
- no absolute-watt targets
- no distance durations
- no missing cadence
- no decorative or motivational filler that changes workout meaning
- no nested loops or hidden main work inside warmup/cooldown blocks
- no unsupported time formats like `MM:SS` or `HH:MM:SS` inside step lines
