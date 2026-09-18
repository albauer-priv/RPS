# Phase Structure and Event Hierarchy

Extended reference for the general periodization methodology defined in `SKILL.md`.

---

## Phase types — operational detail

### Base
- Primary goal: raise aerobic ceiling, build durability tolerance, establish repeatability
- Load character: high volume relative to intensity; durability-first overload axis
- Intensity: `RECOVERY`, `ENDURANCE`; `TEMPO` bounded and only when recovery is stable
- Avoid: threshold or VO2-style intensity as a primary stimulus; premature specificity
- Duration: typically the longest portion of the planning horizon (weeks to months)

### Build
- Primary goal: progressive event-relevant load; fitness is transferred toward the event demands
- Load character: volume is stable or slightly decreasing; intensity density increases moderately
- Intensity: `ENDURANCE`, `TEMPO`, `SWEET_SPOT`; scenario-specific domains permitted
- Sub-types: `durability_build` (long-ride, preload, hard-late), `specificity_build`
  (pacing/fueling/terrain realism), `vo2_build` (bounded VO2-tolerance blocks)
- Avoid: simultaneous escalation of duration, density, and intensity; new milestones too close
  to the peak window

### Peak
- Primary goal: sharpen event-specific fitness and execute the taper; all taper structure is
  inside this phase
- Load character: volume drops, intensity is maintained at race-relevant levels; no new overload
- Taper: see `SKILL.md` "Taper week content" section; volume −41–60%, intensity maintained,
  frequency ≥ 80%
- The phase contains the A event week as its final anchor point
- When a B event is also in this phase (spacing ≤ 4 weeks from A event), the B event week is
  the last hard stimulus and the first taper week begins immediately after
- Cadence week roles within this phase are overridden by event-driven taper semantics

### Transition
- Primary goal: recovery, re-entry, or post-event restoration
- Load character: minimal to moderate; no meaningful overload; no specificity
- When mandatory: after an A event; at the start of the season (prep block); after illness/injury
  deload when re-entry is not yet appropriate
- Duration: scales with event severity; typically 1–3 weeks; longer for ultra events (2–4 weeks)

---

## Event hierarchy — operational detail

### A event
- Full backward-planned macrocycle with a dedicated `Peak` phase and explicit taper
- Maximum 2–3 per season; ≥ 12 weeks between consecutive A events for separate macrocycles
- Taper depth: full (2–3 weeks minimum for ultra/brevet events)
- Post-event: mandatory `Transition` before any new Build, unless the next A event is in the
  same peak cluster

### B event
- Fits inside the existing macrocycle without rebuilding around it
- Taper treatment: minor load reduction in the event week only; no independent peak
- When 2–4 weeks before an A event: becomes the **final specificity stimulus** — the B event
  week is the last full training/event week; all subsequent weeks are A-event taper
- When > 4 weeks before an A event: 3–7 day recovery window inside existing structure, then
  resume normal build
- Post-B recovery inside a Build phase: brief (3–7 days easy); no full re-entry or rebuild block
- Do not insert a new Build or reload block between the B event and A-event taper when spacing ≤ 3 weeks

### C event
- No load adjustment, no taper, no post-event recovery window
- Fits inside existing week structure as a long-ride or training event
- Note in week planning only if logistics or duration affect the training day itself

---

## Macrocycle structures

### Single A event (most common)
```
Transition/Prep → Base → Build (1–2 mesocycles) → Peak (taper + A event) → Transition
```

### Two A events with sufficient spacing (≥ 12 weeks between)
```
Base → Build → Peak (A1 + taper) → Transition → Build → Peak (A2 + taper) → Transition
```

### Two A events close together (< 12 weeks) — use A-event cluster
```
Base → Build → Peak (taper covers both A1 and A2) → Transition
```

### B event in same phase as A event (spacing ≤ 4 weeks)
```
... Build → Peak [B event (W1) | recovery (W2) | taper (W3) | A event (W4)] → Transition
```
All weeks after B event in the Peak phase = taper; the B event week is not a taper week —
it is the last hard training/event week.

---

## Phase length guidelines

| Cycle type  | Typical length     | Notes                                                  |
|-------------|--------------------|--------------------------------------------------------|
| Transition  | 1–4 weeks          | Longer after ultra/brevet events                       |
| Base        | 6–16 weeks         | At least 4 weeks needed for meaningful adaptation      |
| Build       | 4–12 weeks         | May be split into Build 1 and Build 2 mesocycles       |
| Peak        | 2–4 weeks          | Never shorten below minimum taper window               |

Minimum effective taper window (inside Peak phase):
- Events ≤ 6 hours: 7–14 days
- Events 6–12 hours: 10–14 days
- Events > 12 hours (ultra/brevet): 2–3 weeks including event week

---

## Compression rules

When the planning horizon is compressed (not enough weeks for the full Base → Build → Peak sequence):
1. Shorten `Base` first (but keep ≥ 4 weeks)
2. Shorten `Build` next (but keep ≥ 4 weeks)
3. Never shorten `Peak` below the minimum taper window
4. Never shorten the phase immediately before `Peak` if it would eliminate the final build stimulus
5. Add a `Transition` at the start to absorb the remaining horizon mismatch
