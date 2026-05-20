---
name: workout-construction
description: Construct valid workouts for the RPS project subset and execution intent.
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
- duration is time-based only; do not use distance durations
- only these target forms are allowed:
  - percent: `90%`
  - percent range: `65%-72%`
  - ramp: `ramp 60%-75%`
- only one optional `Category:` line may exist in the whole workout document
- description paragraphs may appear only before the first structural block
- cadence is always required as `NNrpm` or `NN-NNrpm`
- loops use a separate `Nx` header and stay single-level
- comments, if used, start with `#`, remain on their own line, and are separated cleanly from steps and loops by a blank line
- keep at least one blank line between blocks, comment blocks, and pauses so parsing stays deterministic

Subset restrictions against the wider EBNF:
- do not use distance durations such as `10km`, `400m`, `5mi`
- do not use absolute watts, HR targets, pace targets, zone shorthand, or `freeride`
- do not use ramp basis suffixes such as `FTP`, `HR`, `LTHR`, `Pace`, or `MMP`
- do not use `MM:SS` or `HH:MM:SS` time notation inside step lines
- do not use hidden device/export flags such as `press lap`, `power=lap`, `hr=1s`, `hidepower`, or similar advanced tokens
- if optional intensity flags are used at all, keep them to `intensity=warmup`, `intensity=recovery`, `intensity=interval`, or `intensity=cooldown`

Warmup / activation / cooldown rules:
- every workout has a WarmupBlock and a CooldownBlock
- warmup should be `1-4` step lines and should not exceed roughly `10` minutes total
- cooldown should be `1-3` step lines and should not exceed roughly `8` minutes total
- activation is mandatory for `VO2max`, `Threshold`, and `Sweet Spot`; optional for `Tempo`
- use add-ons to extend aerobic load while preserving the workout classification
- warmup must stay at or below endurance, except short activation spikes of `<= 30s` that do not exceed `TEMPO`
- warmup must not hide sustained Sweet Spot, Threshold, or VO2max work
- cooldown must be descending, low-intensity, and must not contain loops, spikes, or load modalities

Intent mapping rules:
- every workout maps to exactly one agenda/intensity configuration
- keep workout text aligned with the governing day role and intensity domain
- keep workout text aligned with the active phase week role; do not write build-style quality into deload, mini-reset, or shortened reset weeks
- keep workout text aligned with inherited `phase_intent`; legal syntax is not sufficient when the workout family contradicts the active phase semantics
- add-ons may extend aerobic load only when they preserve the workout classification and phase domain allowance
- `Endurance`, `Recovery`, `Tempo`, `Sweet Spot`, `Threshold`, `VO2max`, and `K3` intents must remain structurally recognizable

Phase-intent family bias:
- `ceiling_support`
  - may use VO2-oriented families only when fresh, explicitly allowed, and still clearly support-oriented
- `transition_coupling`
  - bias toward endurance/tempo/sweet-spot bridge work; avoid repeated VO2 loading
- `durability_build`
  - bias toward long endurance, hard-late endurance, preload, K3 where allowed, and controlled tempo/sweet-spot support
- `specificity_build`
  - bias toward event-like pacing blocks, fueling-practice structures, terrain/cadence/logistics-specific constructions, and race-like long sessions without taper behavior
- `b_event_rehearsal`
  - bias toward rehearsal-specific event-simulation structures tied to the real B anchor
- `peak_preparation`
  - bias toward short sharpness, execution, and opener-like specificity without new accumulation
- `a_event_peak_taper`
  - allow only primer/openers semantics; no new accumulation families

Binding agenda/intensity mapping:
- `Endurance` -> `ENDURANCE` day role, `ENDURANCE` intensity domain, `NONE` load modality
- `Recovery` -> `RECOVERY` day role, `RECOVERY` intensity domain, `NONE` load modality
- `Tempo` -> `QUALITY` day role, `TEMPO` intensity domain, `NONE` load modality
- `Sweet Spot` -> `QUALITY` day role, `SWEET_SPOT` intensity domain, `NONE` load modality
- `Threshold` -> `QUALITY` day role, `THRESHOLD` intensity domain, `NONE` load modality
- `VO2max` -> `QUALITY` day role, `VO2MAX` intensity domain, `NONE` load modality
- `K3` -> `QUALITY` day role, `ENDURANCE` or `SWEET_SPOT` intensity domain, `K3` load modality
- if the candidate workout cannot map cleanly to one row, do not invent it

QUALITY intent target-band lookup:
- apply only when an explicit QUALITY intent is present upstream and the domain is already allowed
- precedence is: `Phase Guardrails` > `Phase Structure` > this lookup
- QUALITY intent selects placement inside the allowed range; it does not redefine zone boundaries or create progression
- if no explicit QUALITY intent exists, use the midpoint of the allowed domain range or conservative placement from athlete context

Preferred target bands by QUALITY intent:
- `Stabilization`
  - `TEMPO`: `76-83%`
  - `SWEET_SPOT`: `84-90%`
  - `THRESHOLD`: `91-96%` only if explicitly allowed
- `Build`
  - `TEMPO`: `83-90%`
  - `SWEET_SPOT`: `90-95%`
  - `THRESHOLD`: `96-102%`
- `Overload`
  - `TEMPO`: `88-90%`
  - `SWEET_SPOT`: `93-97%`
  - `THRESHOLD`: `100-105%`
- all placements must still remain within zone-model boundaries and workout-type parameter ranges

Workout-type principles and progression:
- only one progression dimension may increase per week-cycle: intensity, volume/TiZ, or repetitions
- never progress multiple dimensions at once
- `VO2max`: repetitions -> phases -> interval length -> intensity
- `Sweet Spot` and `K3`: increase TiZ/duration before intensity
- `Endurance`: increase duration by `5-10%`; back-to-back days are allowed only when upstream week structure permits
- `Tempo / Over-Under`: increase oscillations or total time before intensity changes

Canonical workout families:
- choose from these families unless upstream context explicitly demands a closer variant within the same family
- do not invent unsupported archetypes when a canonical family already matches the intent/domain

`Recovery`
- purpose: down-regulation and low-cost movement
- keep all work inside `RECOVERY`
- no hidden quality, no load modality, no activation
- keep the text simple; recovery should not masquerade as endurance progression

`Endurance / Z2`
- purpose: aerobic base and fatigue resistance
- intensity: `65-75% FTP`
- duration: `60 min` to multi-hour as allowed by the day blueprint
- progression: duration first; optional variability must stay low-intensity
- canonical structure may be simple steady main work with minimal syntax overhead
- endurance can be plain steady work; do not force activation or fake interval structure

`Tempo`
- purpose: controlled aerobic pressure without threshold escalation
- use `TEMPO` domain and respect QUALITY intent placement when present
- if authored as over-under, it must remain rhythmic and structurally recognizable, not threshold-heavy by accident

`Tempo / Over-Under`
- purpose: rhythmic oscillation around threshold for aerobic durability and clearance
- under: `90-95% FTP`
- over: `100-105% FTP`
- oscillation duration: `3-6 min`
- progression: more oscillations or more total time before intensity change

`Sweet Spot`
- purpose: increase sustainable power and fatigue resistance
- intensity: `90-93% FTP` unless QUALITY intent and zone-model allowance justify another position inside the legal band
- interval length: `8-20 min`
- target TiZ: `40-60 min`
- progression: extend interval length, then total TiZ, then small intensity step only after volume stabilizes

`Threshold`
- purpose: improve lactate clearance and race-pace durability
- intensity: `95-100% FTP` unless QUALITY intent and zone-model allowance justify another legal placement
- interval length: `6-15 min`
- progression: increase total time at intensity before intensity change; keep recovery short
- threshold requires activation unless explicitly forbidden upstream

`VO2max` short dense 2:1
- purpose: maximize dense VO2 kinetics work with incomplete recovery
- work:recovery ratio must stay `2:1`
- common formats: `20/10`, `30/15`, `40/20`
- work intensity: `110-120% FTP`
- recovery intensity: `45-60% FTP`
- work duration: `20-40s`
- target TiZ: `18-40 min`
- progression: repetitions -> phases -> work duration -> intensity
- short VO2max requires activation

`VO2max` long intervals
- purpose: central VO2 stimulus with lower neuromuscular escalation
- interval duration: `4-6 min`
- intensity: `108-112% FTP`
- active recovery: `2-3 min @ 50-60% FTP`
- repetitions: `4-6`
- target TiZ: `16-30 min`
- progression: repetitions -> interval length -> intensity
- long VO2max requires activation

`K3`
- purpose: force endurance at sub-threshold intensity
- low cadence, seated
- intensity: `85-90% FTP`
- cadence: `50-60 rpm`
- interval length: `6-10 min`
- progression: duration first, intervals second, no intensity spikes
- K3 must remain seated in character and must not borrow VO2max/threshold recovery dynamics

Canonical minimal examples:

`Endurance / Z2`
```text
Main Set
- 2h 68%-72% 85-90rpm
```

`Sweet Spot`
```text
Warmup
- 10m ramp 50%-75% 85rpm

#### Activation
3x
- 20s 120% 95rpm
- 40s 60% 85rpm

Main Set
4x
- 12m 90% 85-90rpm
- 3m 60% 85rpm

Cooldown
- 8m ramp 60%-45% 80rpm
```

`Threshold`
```text
Warmup
- 8m ramp 50%-75% 85rpm

#### Activation
3x
- 20s 120% 95rpm
- 40s 60% 85rpm

Main Set
3x
- 10m 95% 85-90rpm
- 3m 60% 85rpm

Cooldown
- 10m ramp 60%-45% 80rpm
```

`Tempo / Over-Under`
```text
Warmup
- 8m ramp 50%-75% 85rpm

Main Set
4x
- 3m 95% 85-90rpm
- 1m 105% 90rpm

Cooldown
- 10m ramp 60%-45% 80rpm
```

`VO2max` short dense 2:1
```text
Warmup
- 10m ramp 50%-75% 85-90rpm

#### Activation
3x
- 20s 120% 95rpm
- 40s 60% 85rpm

Main Set
13x
- 30s 115% 92-95rpm
- 15s 50% 85rpm

- 3m 55% 85rpm

13x
- 30s 115% 92-95rpm
- 15s 50% 85rpm

Cooldown
- 8m ramp 60%-45% 80-85rpm
```

`VO2max` long
```text
Warmup
- 8m ramp 50%-75% 85rpm

#### Activation
3x
- 20s 120% 95rpm
- 40s 60% 85rpm

Main Set
5x
- 5m 110% 92-95rpm
- 2m 55% 85rpm

Cooldown
- 10m ramp 60%-45% 80rpm
```

`K3`
```text
Warmup
- 10m ramp 50%-75% 85rpm

Main Set
4x
- 8m 88% 55rpm
- 3m 55% 85rpm

Cooldown
- 8m ramp 60%-45% 80rpm
```

Example usage rules:
- keep examples as structural templates, not fixed prescriptions
- adapt repetitions, interval length, and exact %FTP only inside the legal family/domain range
- if upstream context demands a shortened or lighter version, reduce volume before changing family identity
- do not splice two canonical families into one workout unless the policy explicitly supports that structure
- if a workout cannot be represented cleanly in the project subset, do not approximate it with illegal shorthand or mixed-target syntax

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
- keep workout text within the project subset even when the wider Intervals EBNF would permit more tokens

Positive operating guidance:
- Use the active task, injected context, and configured skill role to choose the smallest coherent contribution.
- Read the available evidence, check the governing constraints, and explain the decision path in direct operational language.
- Produce actionable content that helps the next task continue without recomputing or guessing.
- Include required facts, assumptions, warnings, and trace cues when they are available.
- Return a concise result that supports the task expected_output and preserves the authoritative runtime context.

Positive execution pattern:
- Build workout text from the allowed subset, selected day role, active duration, load intent, and export constraints.
- Choose one canonical workout family that matches the intended domain, load modality, and day role before writing steps.
- Use QUALITY intent and workout-family ranges to place %FTP targets without redefining the domain.
- Choose warm-up, main-set, aerobic add-on, and cooldown wording that matches the planned purpose and available time.
- Keep each workout structurally recognizable as its chosen family.
- Include clear syntax decisions and export-safe structure so the reviewer can validate the workout without guessing.
- Produce concise workout-authoring guidance that helps the Week Plan writer emit valid workout text.

Retrieval policy:
- Prefer injected day-role, load-intent, and deterministic week execution context first.
- Use `workspace_get_week_calendar_context` and `workspace_get_phase_execution_context` for exact authoritative week values when direct retrieval is still needed.
- Use `workspace_get_latest` for latest authoritative planning artefacts and runtime snapshots.
- Use `workspace_get_input` only for athlete-managed inputs.

Output format:
- Return the task expected_output with workout construction decisions, syntax checks, and export-safety findings separated clearly.
- Include day role, duration, load intent, allowed intensity domain, and any syntax or recovery constraints that govern the workout.
- Keep recommendations actionable and compatible with downstream workout export.
