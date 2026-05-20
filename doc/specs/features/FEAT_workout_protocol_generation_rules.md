---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-20
Owner: Planning / Workouts
---
# FEAT: Workout Protocol Generation Rules

* **ID:** FEAT_workout_protocol_generation_rules
* **Status:** Implemented
* **Owner/Area:** Week Planning / Workout Generation
* **Last-Updated:** 2026-05-20
* **Related:** [FEAT_protocol_driven_workout_engine.md](/Users/alexander/RPS/doc/specs/features/FEAT_protocol_driven_workout_engine.md), [ADR-052-protocol-driven-week-workout-generation.md](/Users/alexander/RPS/doc/adr/ADR-052-protocol-driven-week-workout-generation.md)

---

## 1) Context / Problem

**Current behavior**

* Week planning already uses a deterministic protocol registry and a code-owned workout renderer.
* Prior-week `WEEK_PLAN` state is already inferred and reused for some protocol progression decisions.
* The solver already supports classic intervals, microburst sets, over/unders, strength endurance, long steady, and fatigue-finish patterns.

**Problem**

* Progression rules, TiZ counting semantics, and session caps were only partially explicit in config and only partially enforced in code.
* The intended progression paths such as `4x10 -> 4x12 -> 4x15 -> 5x12` or `3x10x30/15 -> 3x13x30/15 -> 4x10x30/15` were not yet the canonical documented contract for the solver.
* Week-density semantics were still too implicit, especially for `K3`, which must count as a true quality stimulus.

**Constraints**

* Scope is week planning only.
* Progression truth in v1 comes from the previous persisted `WEEK_PLAN`, not from completed-session execution data.
* Export remains constrained to the RPS Intervals subset:
  * no nested loops
  * cadence on every step
  * canonical section ordering
  * no `freeride`

---

## 2) Goals & Non-Goals

**Goals**

* [x] Define a canonical workout-generation contract for week planning.
* [x] Define supported domains, protocol classes, progression rules, TiZ semantics, and caps.
* [x] Define prior-week progression reuse from the previous `WEEK_PLAN`.
* [x] Define Z2 add-on rules and week-density rules.
* [x] Implement solver behavior directly against these documented rules.

**Non-Goals**

* [x] No completed-session truth integration in this feature.
* [x] No support for `freeride`.
* [x] No expansion of the Intervals subset grammar.

---

## 3) Proposed Behavior

**User/System behavior**

* Week planning chooses a configured workout protocol, not a free-authored workout text.
* The solver generates one concrete workout instance from:
  * protocol config
  * week context
  * prior planned progression state
  * duration/kJ target
* Progression follows documented protocol-specific rules before intensity changes are considered.
* If a target would exceed documented hard caps, the solver clamps or downshifts deterministically instead of silently overbuilding.

**UI impact**

* UI affected: No direct new page flow.
* Existing Plan/Week/Workouts views continue to consume `WEEK_PLAN` and rendered `workout_text`.

**Non-UI behavior**

* Components involved:
  * `config/planning/week_workout_protocols.yaml`
  * `rps.planning.week_engine`
  * `rps.workouts.progression_history`
  * `rps.workouts.protocol_solver`
  * `rps.workouts.generator`
* Contracts touched:
  * internal workout blueprint semantics
  * prior-week progression inference
  * protocol config semantics

---

## 4) Implementation Analysis

**Components / Modules**

* `week_workout_protocols.yaml`: canonical protocol metadata and progression semantics.
* `week_engine.py`: protocol selection, prior-state matching, quality-density enforcement, TiZ target estimation.
* `progression_history.py`: extract protocol signatures from prior canonical `WEEK_PLAN`.
* `protocol_solver.py`: deterministic protocol-specific progression and cap enforcement.
* `generator.py`: render solved internal structure to canonical Intervals subset text.

**Data flow**

* Inputs:
  * `SEASON_PLAN`
  * `PHASE_GUARDRAILS`
  * `PHASE_STRUCTURE`
  * `AVAILABILITY`
  * `ZONE_MODEL`
  * previous `WEEK_PLAN`
* Processing:
  * select legal protocol
  * infer previous progression signature
  * estimate primary TiZ target
  * solve concrete structure using protocol rules
  * optionally append Z2 add-on
  * render canonical workout text
* Outputs:
  * `WEEK_PLAN`
  * deterministic `workout_text`
  * internal solver trace via blueprint metadata

**Schema / Artefacts**

* New persisted artefacts: none.
* Changed persisted artefacts: none required.
* Changed internal semantics:
  * `WeekWorkoutBlueprintModel.progression_state`
  * protocol config fields

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes, for persisted `WEEK_PLAN`.
* Breaking changes: none in persisted schema.
* Fallback behavior:
  * if no prior progression signature exists, use protocol defaults
  * if prior state is not parseable, continue deterministically from config minima/preferred defaults

**Conflicts with ADRs / Principles**

* No conflict with ADR-052; this feature operationalizes the existing protocol-driven direction.
* Fully aligned with `workout_policy.md` and `principles_durability_first_cycling.md`.

**Impacted areas**

* UI: no flow change, only different deterministic content.
* Pipeline/data: prior-week state is consumed more explicitly.
* Renderer: same export surface, stricter upstream inputs.
* Workspace/run-store: no new artefacts.
* Validation/tooling: tests and solver semantics must match documented progression examples.
* Deployment/config: protocol config gains explicit cap/progression fields.

**Required refactoring**

* Replace implicit solver defaults with config-driven semantics.
* Add explicit TiZ counting semantics per protocol.
* Add explicit quality-cost semantics for week-density checks.

---

## 6) Options & Recommendation

### Option A — Config-driven protocol solver

**Summary**

* Keep protocols in config and let the solver enforce progression order, TiZ semantics, and caps.

**Pros**

* Directly auditable.
* Easy to extend without changing the export surface.
* Keeps policy logic code-owned and deterministic.

**Cons**

* Requires disciplined config maintenance.
* Some protocol semantics still need protocol-specific code paths.

**Risk**

* Overly generic solver code can drift from sports-methodology intent unless examples are tested.

### Option B — Hardcode all progression ladders in Python

**Summary**

* Encode every progression path directly in code with minimal config.

**Pros**

* Simple for very small protocol libraries.

**Cons**

* Becomes opaque and hard to maintain.
* Pushes product rules back into code branches instead of keeping them reviewable in config.

### Recommendation

* Choose: Option A
* Rationale: it matches the repo’s deterministic direction and keeps workout policy reviewable, testable, and extensible.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Protocol config encodes TiZ semantics, standard caps, hard caps, quality cost, progression priorities, and redistribution thresholds where applicable.
* [x] Classic interval progression follows documented order before intensity changes:
  * `4x10 -> 4x12`
  * `4x12 -> 4x15`
  * `4x15 -> 5x12`
* [x] VO2 microburst progression follows documented order using on-time:
  * reps first
  * then sets
* [x] `K3` counts as a real quality stimulus in week composition.
* [x] Prior-week `WEEK_PLAN` signatures influence next-step generation when a protocol match exists.
* [x] Export remains valid against the RPS Intervals subset.

---

## 8) Migration / Rollout

**Migration strategy**

* No persisted artefact migration required.
* Existing previous `WEEK_PLAN` artefacts are parsed opportunistically for progression signatures.

**Rollout / gating**

* No feature flag.
* Safe rollback: revert solver/config/docs changes as one feature set.

---

## 9) Risks & Failure Modes

* Failure mode: previous `WEEK_PLAN` cannot be parsed into a usable signature
  * Detection: empty or partial `previous_signature`
  * Safe behavior: fall back to protocol defaults
  * Recovery: inspect canonical `workout_text` or refine parser coverage

* Failure mode: target TiZ exceeds hard cap
  * Detection: solver cap check
  * Safe behavior: clamp or downshift deterministically
  * Recovery: lower requested load/duration or use a different protocol

* Failure mode: week intensity density becomes illegal
  * Detection: week-engine quality-cost counting
  * Safe behavior: choose lower-cost endurance protocol instead of stacking more quality
  * Recovery: adjust selection policy or day-role allocation

---

## 10) Observability / Logging

**New/changed events**

* No new persisted event types required in this feature.
* Existing planning logs should expose:
  * chosen protocol id
  * prior signature match presence
  * primary TiZ target
  * cap clamping when applied

**Diagnostics**

* Inspect:
  * `planning_bundle.workout_blueprints[*].progression_state`
  * `planning_bundle.workout_blueprints[*].selection_reason`
  * rendered `WEEK_PLAN`

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] [doc/specs/features/FEAT_workout_protocol_generation_rules.md](/Users/alexander/RPS/doc/specs/features/FEAT_workout_protocol_generation_rules.md) — canonical implementation contract
* [x] [doc/overview/workout_generation_guide.md](/Users/alexander/RPS/doc/overview/workout_generation_guide.md) — athlete-/coach-readable overview
* [x] [CHANGELOG.md](/Users/alexander/RPS/CHANGELOG.md) — summary of solver/documentation changes

---

## 12) Link Map (no duplication; links only)

* Architecture: [doc/architecture/system_architecture.md](/Users/alexander/RPS/doc/architecture/system_architecture.md)
* Artefact flow: [doc/overview/artefact_flow.md](/Users/alexander/RPS/doc/overview/artefact_flow.md)
* Planning process: [doc/overview/how_to_plan.md](/Users/alexander/RPS/doc/overview/how_to_plan.md)
* Workout policy source: [specs/knowledge/_shared/sources/policies/workout_policy.md](/Users/alexander/RPS/specs/knowledge/_shared/sources/policies/workout_policy.md)
* Durability-first principle: [specs/knowledge/_shared/sources/principles/principles_durability_first_cycling.md](/Users/alexander/RPS/specs/knowledge/_shared/sources/principles/principles_durability_first_cycling.md)
* Intervals grammar: [specs/knowledge/_shared/sources/specs/workouts/intervals_workout_ebnf.md](/Users/alexander/RPS/specs/knowledge/_shared/sources/specs/workouts/intervals_workout_ebnf.md)
* RPS workout subset: [specs/knowledge/_shared/sources/specs/workouts/workout_syntax_and_validation.md](/Users/alexander/RPS/specs/knowledge/_shared/sources/specs/workouts/workout_syntax_and_validation.md)
* Related feature: [doc/specs/features/FEAT_protocol_driven_workout_engine.md](/Users/alexander/RPS/doc/specs/features/FEAT_protocol_driven_workout_engine.md)
* Related ADR: [doc/adr/ADR-052-protocol-driven-week-workout-generation.md](/Users/alexander/RPS/doc/adr/ADR-052-protocol-driven-week-workout-generation.md)

---

## Supported Domains and Protocol Classes

### Domains

* `ENDURANCE`
* `TEMPO`
* `SWEET_SPOT`
* `THRESHOLD`
* `VO2MAX`
* `K3` is represented via `load_modality`, not as a separate intensity domain.

### Protocol Classes

* `LONG_STEADY`
* `CLASSIC_INTERVALS`
* `OVER_UNDER_INTERVALS`
* `MICROBURST_SETS`
* `STRENGTH_ENDURANCE_INTERVALS`
* `FATIGUE_FINISH`
* `RAMP_INTERVALS`
* `DAY_TYPE_ONLY`

---

## Canonical TiZ / On-Time Semantics

* `count_tiz_as = full_work`
  * Count total time spent in work blocks.
  * Applies to `TEMPO`, `SWEET_SPOT`, `THRESHOLD`, `K3`, and most steady interval protocols.

* `count_tiz_as = on_time`
  * Count only the `on` segments of microburst work.
  * Applies to `VO2 20/10`, `30/15`, `40/20`.

* `count_tiz_as = late_segment`
  * Count only the late quality finish segment, not the preload endurance.
  * Applies to fatigue-finish / pre-fatigue durability protocols.

---

## Canonical Protocol Rules

### `CLASSIC_INTERVALS`

**Applies to**

* `TEMPO_CLASSIC_INTERVALS`
* `SWEET_SPOT_CLASSIC_INTERVALS`
* `SWEET_SPOT_EXTENSIVE`
* `THRESHOLD_CLASSIC_INTERVALS`
* `VO2_LONG_INTERVALS`

**Progression**

* `TEMPO` / `SWEET_SPOT`:
  * increase work duration first
  * redistribute to more sets when practical work duration ceiling is reached
  * intensity is not the normal progression lever
* canonical example:
  * `4x10 -> 4x12 -> 4x15 -> 5x12`

**Caps**

* `SWEET_SPOT`
  * standard cap: `45-60 min TiZ`
  * hard cap: `75-90 min TiZ`
* `TEMPO`
  * standard cap: `90-120 min TiZ`
  * hard cap: `150-180 min TiZ`
* `THRESHOLD`
  * narrower TiZ than tempo/sweet spot; intensity remains stable and recoveries stay short

### `MICROBURST_SETS`

**Applies to**

* `VO2_MICROBURST_20_10`
* `VO2_MICROBURST_30_15`
* `VO2_MICROBURST_40_20`

**Progression**

* count only on-time
* increase reps first
* then increase sets
* only later change broader structure
* intensity is last

**Canonical examples**

* `3x10x30/15 -> 3x13x30/15 -> 4x10x30/15`
* `3x8x40/20 -> 3x10x40/20 -> 4x8x40/20`

**Caps**

* standard cap: `20-22 min on-time`
* hard cap: `25-30 min on-time`

### `OVER_UNDER_INTERVALS`

**Applies to**

* `TEMPO_OVER_UNDER`

**Progression**

* oscillation count first
* under/over durations stay stable unless protocol config explicitly changes them
* threshold/tempo TiZ caps still apply

### `STRENGTH_ENDURANCE_INTERVALS`

**Applies to**

* `K3_CLASSIC_INTERVALS`

**Progression**

* increase work duration first
* then set count
* cadence stays explicitly low and stable
* K3 counts as a true quality stimulus

**Caps**

* standard cap: `30-40 min TiZ`
* hard cap: `45-60 min TiZ`

### `FATIGUE_FINISH`

**Applies to**

* `ENDURANCE_FATIGUE_FINISH`
* `ENDURANCE_PREFATIGUE_FINISH`

**Progression**

* preload and late segment are separate semantics
* late quality finish is capped explicitly
* these patterns are durability-specific overload, not generic endurance extension

**Caps**

* standard late-segment cap: `60-75 min`
* hard late-segment cap: `90 min`

---

## Prior-Week Progression Reuse

* Source of truth in v1: previous persisted `WEEK_PLAN`
* Infer from canonical `workout_text`:
  * protocol type
  * protocol variant guess
  * set count
  * reps per set
  * work duration
  * recovery duration
  * oscillation count
  * TiZ or on-time
* Matching order:
  1. protocol type
  2. protocol variant
  3. workout family + day role
* If no reliable signature exists:
  * continue from protocol defaults

---

## Z2 Add-On Rules

* Primary protocol remains the workout’s classification.
* Z2 add-on is only a duration/kJ filler.
* Add-on may only be appended when the configured add-on policy allows it.
* Add-on must not convert a quality workout into a disguised long steady session.
* Add-on does not count as a separate quality stimulus, but it still adds fatigue and total load.

---

## Week-Density Rules

* `VO2MAX`, `SWEET_SPOT`, `TEMPO`, `THRESHOLD`, and `K3` all count as real quality stimuli.
* `K3` is not free.
* Default weekly rule:
  * maximum two true quality stimuli
* When durability-specific volume or late-finish load is high:
  * downshift protocol intensity density before stacking more quality
* In `shortened_*` weeks, quality-day selection should avoid exact duplicate quality protocol variants when a legal alternative exists.
* In `shortened_re_entry`, if the second quality day still resolves to repeated `TEMPO_CLASSIC`, it must be damped to a lighter stabilization dose instead of repeating the same upper-tempo prescription unchanged.
* `PHASE_PREVIEW` remains non-binding, but drift from its week-shape hints should surface as warnings.

## Modality Consistency

* Effective allowed load modalities for week planning are the strictest consistent set available.
* If `PHASE_GUARDRAILS` and `PHASE_STRUCTURE` disagree on allowed load modalities:
  * use their intersection if non-empty
  * emit a warning
  * if the intersection is empty, fall back to `PHASE_GUARDRAILS` and emit a stronger warning

---

## Export Projection Rules

* Internal model may be richer than Intervals text.
* Export must still be:
  * canonical section order
  * flat loops only
  * no nested loops
  * cadence on every step
  * no `freeride`
* Set progression is flattened into sequential blocks where necessary.
