---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-21
Owner: Planning / Workouts
---
# Week Workout Selection Audit Guide

This guide explains how weekly workout combinations are chosen and how an external reviewer can audit that choice.

## What is selected deterministically

The system does not let an LLM decide:

* which workout types are legal in a week
* whether duplicate workouts should be avoided
* whether K3 counts as quality
* whether a phase-specific week should be conservative or dense

Those decisions come from:

* season and phase artefacts
* canonical phase semantics (`phase_type`, `phase_intent`, `build_subtype`)
* configured workout protocols
* a flat selector-rule table
* deterministic scoring and tie-break rules

## What “good weekly combination” means

A good week is not just a set of individually legal workouts. The combination also has to make sense together.

Examples:

* `shortened_re_entry` defaults to one true quality day, one long Z2 anchor, and lighter endurance support unless a stronger second stimulus is explicitly justified
* `shortened_re_entry` should not default to two identical upper-tempo quality days
* `durability_build` should lean toward long endurance anchors and durability-specific quality
* `specificity_build` should stay focused on event-near structure instead of broad mixed density
* `peak_sharpening` should be narrower and more specific
* `taper_freshening` should preserve freshness rather than create new fatigue
* `K3` is treated as a real stimulus, not as free filler

## How duplicate and monotony avoidance works

The selector scores candidates with explicit penalties when a later workout would repeat:

* the same protocol variant
* the same stimulus class
* the same monotony group
* a disfavored pairing after an earlier selected protocol

That means the system can prefer:

* `Tempo + Sweet Spot`
over
* `Tempo + the same Tempo again`

when the phase context says the second choice is more appropriate.

For re-entry weeks this now also means:

* a second true quality day is not the default
* non-anchor endurance support days should not silently become long-anchor workouts
* a repeated `Tempo Classic` row only wins as an explicit damped fallback

## How phase and season semantics shape the choice

The selector is downstream of season and phase.

Inputs include:

* season archetype
* `phase_type`
* `phase_intent`
* `build_subtype` for `BUILD` phases
* week role
* allowed and forbidden intensity domains
* allowed load modalities
* weekly quality cap
* preview hints

So a `BASE / shortened_re_entry` week and a `BUILD / specificity_build` week do not score the same candidate set the same way.

The semantic responsibilities are:

* `phase_type` = macro-period container
* `phase_intent` = primary method purpose of the phase
* `build_subtype` = explicit selector key for `BUILD` phases

That means:

* `vo2_build` should prefer VO2-focused combinations
* `threshold_build` should prefer threshold / over-under combinations
* `sst_build` should prefer extensive sub-threshold combinations with density control
* `durability_build` should prefer fatigue-resistant combinations
* `specificity_build` should prefer event-near combinations
* `peak_sharpening`, `taper_freshening`, and `race_execution` should progressively narrow density

## What gets written for audit

Every generated `WEEK_PLAN` also gets:

* a JSON audit artefact with one row per evaluated candidate/day combination
* a CSV sidecar with the same rows

Each row shows:

* which candidate was considered
* whether it was legal
* which selector rule row matched
* which `phase_type`, `phase_intent`, and `build_subtype` were active
* which review bucket applied (`SOLL`, `KANN`, `NUR_WENN`, `VERMEIDEN`)
* which bonuses and penalties were applied
* the final score
* whether it was selected
* the final reason text

That lets an external reviewer answer:

* why this workout was chosen
* why another legal workout was not chosen
* whether the week respected the active phase semantics such as `shortened_re_entry`, `vo2_build`, `specificity_build`, or `peak_sharpening`

## How to review a week externally

1. Open the `WEEK_PLAN`
2. Open the matching `WEEK_WORKOUT_SELECTION_AUDIT`
3. If needed, open the CSV sidecar
4. Check:
   * source artefact versions
   * active `phase_type`, `phase_intent`, and `build_subtype`
   * allowed domains/modalities
   * selected protocol variants
   * penalties for duplicates or monotony
   * preview-alignment bonuses
   * warnings about modality mismatch or week-shape drift

If the audit rows do not justify the final weekly combination clearly, that is a quality issue and should be treated as a selector defect.
