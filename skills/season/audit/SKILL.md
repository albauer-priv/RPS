---
name: audit
description: Audit season bundles for macrocycle coherence, taper validity, and durability-first governance.
metadata:
  author: rps
  version: "5.1"
---
Audit the candidate season bundle holistically.

Checklist:
- each target macrocycle ends in either one `A` event or one explicit `A`-event peak cluster
- every `A` event is classifiable as primary, secondary, equal-priority, or cluster-member
- every taper behavior serves an `A` event and remains inside a schema-valid `Peak` cycle
- `B` and `C` events fit without breaking macrocycle structure
- recovery and transition phases are explicitly planned
- peak logic is consistent with event spacing
- load governance remains sustainable and durability-first
- progressive-overload semantics are explicit, not only implied by cadence labels
- phase ISO-week coverage is gap-free and overlap-free
- phase count, phase lengths, and cadence semantics match the selected Scenario and deterministic phase-slot context
- every phase blueprint preserves injected `cadence_week_roles`
- every phase has stable `phase_id`, schema-valid `cycle`, explicit `deload`, and cadence-based `deload_rationale`
- corridors above injected availability capacity are either rejected or escalated with explicit replan rationale
- final `A` event taper load is meaningfully lower than Build/Re-entry unless an explicit review rationale explains why not
- `B` event handling is rehearsal/minor adjustment only and never an independent full taper or peak
- season-level intensity authority comes from the selected scenario and season contracts, not from a narrower downstream phase example
- later Base/Build/rehearsal phases may preserve `TEMPO` or other scenario-permitted quality semantics; do not require every phase to do so

Block approval when:
- event hierarchy is contradictory
- multi-`A` spacing requires a peak cluster or downgrade, but the bundle still implies separate overlapping macrocycles
- a clustered-event plan tries to use repeated independent tapers
- a second peak is implied without an explicit multi-peak model
- season progression requires repeated catch-up or hidden overload
- Season Plan implies a different cadence than the selected Scenario
- deterministic phase-slot `blocking_issues` are present and unresolved
- `2:1:1` is inherited but mini-reset/reload semantics are missing from phase blueprint or final phase rationale
- `3:1` or `2:1` is inherited but the corresponding build/deload semantics are not visible in phase blueprint meaning
- corridors copy availability capacity across unrelated phases instead of expressing progression, re-entry, rehearsal, or taper intent
- durability-first is collapsed into intensity-free planning without `RECOVERY`/dominant `ENDURANCE` plus scenario-permitted targeted quality semantics
- all phases collapse to `ENDURANCE only` even though the selected scenario permits broader season intensity domains
- selected scenario has `season_archetype: ceiling_first_durability` but early Base phases use `aerobic_base` intent only (missing `vo2_base` / `vo2_build`) — unless deterministic phase-slot context explicitly shortened or excluded them
- `ceiling_first_durability` archetype is present but `vlamax_lowering` / `durability_build` / `specificity_build` Build phases are absent without explicit horizon rationale
- missed-load compensation or hidden catch-up behavior appears in season reasoning
- a phase cycle is outside `Base | Build | Peak | Transition`
- deload rationale is missing where deload intent is present
- phase coverage has gaps, overlaps, or ambiguous week ownership
- an `A` event lacks coherent `Peak`/`Transition` handling
- `self_check.every_phase_maps_to_cycle_and_deload_intent` is true while cycle/cadence/deload evidence is missing

Do NOT raise a blocking_issue for:
- a re-entry corridor above a recent disrupted week's actual load — when `W_prev_actual < BL_kJ × 0.85`
  the disrupted-week rule applies; a corridor at `BL_kJ × 0.85–1.05` is valid re-entry
- `RELOAD → TAPER` phase adjacency — flag as structural **warning** and recommend restructuring
  the preceding phase's final week to `MINI_RESET` or `DELOAD`; only block if the taper window
  itself is shorter than the minimum effective window (2–3 weeks including event week for events
  > 12 hours) — see `macrocycle_and_peak_window_rules.md`
- a domain coherence narrative note (a forbidden domain mentioned in phase prose) — that is a
  finalize-pass coherence warning, not a macrocycle audit blocker
- objective mismatch between athlete goal and highest in-horizon A event — warn but do not block

Output format:
- Return the task expected_output as a structured review contribution.
- Include approved findings, blocking issues, warnings, and required adjustments in separate fields or clearly separated sections.
- Tie each issue to the relevant context, policy, phase/week range, load band, or artifact field.
