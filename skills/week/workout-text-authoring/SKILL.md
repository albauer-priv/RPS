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
- omit optional sections entirely when unused and include headings only when content is present

Step grammar in the project subset:
- every step line starts with `-`
- every step line uses a time duration, a power target, and a cadence value
- only these target forms are allowed:
  - percent: `90%`
  - percent range: `65%-72%`
  - ramp: `ramp 60%-75%`
- cadence is always required as `NNrpm` or `NN-NNrpm`
- loops use a separate `Nx` header and stay single-level
- comments, if used, are on their own line and separated cleanly from steps and loops

Warmup / activation / cooldown rules:
- every workout has a WarmupBlock and a CooldownBlock
- warmup should be `1-4` step lines and should not exceed roughly `10` minutes total
- cooldown should be `1-3` step lines and should not exceed roughly `8` minutes total
- activation is mandatory for `VO2max`, `Threshold`, and `Sweet Spot`; optional for `Tempo`
- use add-ons to extend aerobic load while preserving the workout classification

Intent mapping rules:
- every workout maps to exactly one agenda/intensity configuration
- keep workout text aligned with the governing day role and intensity domain
- `Endurance`, `Recovery`, `Tempo`, `Sweet Spot`, `Threshold`, `VO2max`, and `K3` intents must remain structurally recognizable

Required text discipline:
- spell out workout steps with the supported workout-text syntax instead of `@` shorthand
- use RPS-supported workout text targets instead of zone labels (`Z1`-`Z7`)
- use supported cycling workout targets instead of HR or pace targets
- use relative/intended workout semantics instead of absolute-watt targets
- express step duration with supported time syntax
- include cadence guidance where the workout text contract requires it
- keep workout text operational and semantically faithful
- keep loops flat and place main work in the main-work section
- use supported step-line time formats

Positive operating guidance:
- Use the active task, injected context, and configured skill role to choose the smallest coherent contribution.
- Read the available evidence, check the governing constraints, and explain the decision path in direct operational language.
- Produce actionable content that helps the next task continue without recomputing or guessing.
- Include required facts, assumptions, warnings, and trace cues when they are available.
- Return a concise result that supports the task expected_output and preserves the authoritative runtime context.

Positive execution pattern:
- Build workout text from the allowed subset, selected day role, active duration, load intent, and export constraints.
- Choose warm-up, main-set, aerobic add-on, and cooldown wording that matches the planned purpose and available time.
- Include clear syntax decisions and export-safe structure so the reviewer can validate the workout without guessing.
- Produce concise workout-authoring guidance that helps the Week Plan writer emit valid workout text.

Output format:
- Return the task expected_output with workout construction decisions, syntax checks, and export-safety findings separated clearly.
- Include day role, duration, load intent, allowed intensity domain, and any syntax or recovery constraints that govern the workout.
- Keep recommendations actionable and compatible with downstream workout export.
