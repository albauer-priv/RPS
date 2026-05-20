---
Version: 1.0
Status: Updated
Last-Updated: 2026-05-20
Owner: Planning / Workouts
---
# Workout Generation Guide

This guide explains how week workouts are generated, how they progress, and why some sessions are capped even if an athlete could theoretically do more.

It is written for athletes and coaches. The technical implementation contract lives in [FEAT_workout_protocol_generation_rules.md](/Users/alexander/RPS/doc/specs/features/FEAT_workout_protocol_generation_rules.md).

## What this system tries to do

The planning system does not generate random interval sessions. It chooses from a small set of workout types and then progresses them in a controlled way.

The main idea is simple:

* keep the workout type stable long enough to adapt to it
* progress with one main lever at a time
* keep intensity as the last lever
* respect the bigger week goal, not just one isolated workout

## Main workout types

### Endurance / Z2

This is the base. It builds volume, aerobic durability, and repeatability.

Typical forms:

* steady Z2
* long endurance anchor
* endurance with a late finish

What too much looks like:

* too much total duration or kJ for the week
* late quality layered onto an already dense week

### Tempo

Tempo is a durability and fatigue-resistance tool. It matters most when it stays controlled and repeatable.

Typical forms:

* `4x10`, `4x12`, `4x15`
* `2x30`, `3x30`, `2x45`
* steady tempo after endurance preload

What too much looks like:

* pushing tempo so long that it starts stealing recovery from the rest of the week

### Sweet Spot

Sweet Spot is efficient and useful, but it becomes expensive quickly if it is overused.

Typical forms:

* `3x12`
* `3x15`
* `2x20`
* `3x20`
* `2x30`

What too much looks like:

* too much total Sweet Spot time every week
* trying to solve every planning problem with more Sweet Spot

### Threshold

Threshold is more specific and narrower than Sweet Spot. It is useful, but it has to stay disciplined.

Typical forms:

* shorter classic intervals
* over-under patterns when the phase allows them

What too much looks like:

* too much threshold density in a week that already carries high volume or durability load

### VO2max

VO2max is a high-value but high-cost stimulus. In this system it is usually built around short microburst structures such as `30/15` or `40/20`.

Typical forms:

* `3x10x30/15`
* `3x13x30/15`
* `3x8x40/20`
* `3x10x40/20`

What too much looks like:

* going beyond the point where power quality, cadence, and repeatability stay stable

Important:

* for VO2 microbursts, only the hard `on` time counts as TiZ

### K3 / low cadence

K3 is not easy filler. It is a real strength-endurance stimulus with real local muscular cost.

Typical forms:

* `3x8`
* `4x8`
* `3x10`
* `4x10`
* `3x12`

What too much looks like:

* treating K3 like low-cost tempo
* stacking K3 onto an already hard week as if it did not count

## How progression works

The same workout type can evolve without becoming a different workout type.

### Tempo / Sweet Spot example

A classic progression can look like this:

* `4x10`
* `4x12`
* `4x15`
* `5x12`

The point is not to invent a new session name every time. The point is to stay in the same workout idea and progress it in a controlled way.

What changes first:

* work duration

What changes later:

* set structure

What usually changes last:

* intensity

### VO2 microburst example

A VO2 progression can look like this:

* `3x10x30/15`
* `3x13x30/15`
* `4x10x30/15`

or:

* `3x8x40/20`
* `3x10x40/20`
* `4x8x40/20`

Here the progression usually happens through:

* more reps first
* then more sets
* only later more density or a broader structural step

## Why caps exist

Caps exist because more is not automatically better. Past a certain point, a session stops being productive and starts consuming too much recovery and planning budget.

### VO2max

For `30/15` and `40/20`, count only the hard `on` time.

Typical planning ranges:

* standard: about `20-22 min` on-time
* hard upper range: about `25-30 min` on-time

### Sweet Spot

Typical planning ranges:

* standard: about `45-60 min TiZ`
* hard upper range: about `75-90 min TiZ`

### Tempo

Typical planning ranges:

* standard: about `90-120 min TiZ`
* hard upper range: about `150-180 min TiZ`

### K3

Typical planning ranges:

* standard: about `30-40 min TiZ`
* hard upper range: about `45-60 min TiZ`

## Why tempo after preload is different

Tempo done fresh is not the same as tempo done after a long endurance preload.

For brevet and durability work, tempo after preload is often more specific because it asks for steady output under fatigue, not just in a fresh state.

That is why the system supports durability-specific patterns like:

* endurance first
* then a controlled late tempo or Sweet Spot finish

## Why K3 is not free

K3 can look moderate on heart rate. That does not make it cheap.

It still costs:

* local muscular fatigue
* torque tolerance
* structural stress

So K3 counts as a real quality session in weekly composition.

## Good and bad weekly combinations

Usually good:

* `VO2 + K3 + long Z2`
* `Sweet Spot + K3 + long Z2`
* `hard-late tempo + K3 + long Z2`
* `VO2 + Tempo + long Z2`

Usually too dense:

* `VO2 + Sweet Spot + Tempo + K3` in the same week

Default logic:

* one or two real quality stimuli are usually enough
* long Z2 remains the base
* as durability load rises, intensity density should fall

## Re-entry weeks are shaped differently

In a shortened re-entry week, the system should not simply repeat the same upper-tempo session twice just because it is legal.

If the week still lands on two tempo quality days, the second one should usually be lighter or more stabilizing, for example:

* less total Tempo TiZ
* a lower Tempo target range
* a different but still legal quality flavor when the phase rules allow it

That is the difference between:

* a week that is merely valid
* and a week that actually behaves like a re-entry week

## Preview hints vs binding rules

The phase preview gives soft week-shape hints. The engine can use those hints and warn when it drifts away from them.

But the preview is not the binding contract.

Binding rules still come first from:

* phase guardrails
* phase structure
* allowed domains
* quality-density limits
* fixed recovery days

## Plain-language rules

* Progress with one main lever at a time.
* Intensity is usually the last lever.
* Long-term repeatability matters more than one heroic workout.
* Missing work is not “made up” by stacking more intensity into the next session.
* K3 counts.
* VO2 on-time is counted differently because only the hard work intervals count.
* Tempo after preload can be more specific than fresh tempo for brevet-style goals.
