# RPS Skill Layer Architecture — Periodization & Load Methodology

Overview of how the planning methodology is distributed across shared and layer-specific skills.
This document reflects the state as of v0.37.31.

---

## Three-foundation model

| Foundation | Skill | Covers | Does NOT cover |
|---|---|---|---|
| WHY | `skills/shared/durability-methodology` | Durability-first philosophy, repeatability principle, evidence library manifest | Phase structure, load numbers |
| WHAT | `skills/shared/periodization-methodology` | Phase semantics, backward planning from A event, event hierarchy, taper week content | Load math, cadence selection, kJ bands |
| HOW (load) | `skills/shared/load-estimation-core` | kJ estimation math, IF_ref_load | Training structure, periodization |

All season and phase planning agents receive all three foundations through the crew skill context.

---

## Skill layer map

```
INPUTS
├── planning_events (A/B/C, date, distance, priority)
├── athlete_profile (FTP, CTL, kJ/kg, goals, risks)
├── availability (h/week, rest days, indoor/outdoor)
├── logistics (travel, work, weather)
├── historical_baseline (recent 6–8 weeks kJ, Z2%, DI)
└── season_scenario (cadence, archetype, domains)

SHARED FOUNDATION (all agents in season + phase crews)
├── durability-methodology v6.0 ......... WHY  (durability-first, repeatability)
├── periodization-methodology v1.0 ...... WHAT (phase semantics, backward planning, taper)
├── load-estimation-core v8.0 ........... HOW  (kJ math, IF_ref_load)
├── domain-glossary v1.0 ................ vocabulary
├── traceability-and-naming v2.2 ........ traceability
└── runtime-boundaries v2.0 ............. authority boundaries

SEASON LAYER
├── context-analysis v3.0 ............... planning horizon, events, availability, logistics
├── event-priority-anchoring v4.0 ....... A/B/C classification, conflict hierarchy, peak windows
├── historical-context v1.0 ............. recent load history interpretation
├── evidence-alignment v1.0 ............. season-level evidence → planning implications
├── kpi-guidance v1.0 ................... KPI interpretation
├── scenario-generation v4.3 ............ 3 scenarios with cadence, archetype, domains
├── scenario-interpretation v3.0 ........ binds selected scenario as planning authority
├── constraint-synthesis v3.1 ........... event/athlete/availability/logistics constraints (*)
├── macrocycle-architecture v5.3 ........ BACKWARD PLANNING from A event, taper override (**)
├── load-governance v8.0 ................ kJ corridors, ramp +5/8/12/18%, cadence selection
├── plan-synthesis v3.0 ................. combines specialist outputs
├── governance-review v1.0 .............. corridor realism review
├── audit v5.0 .......................... macrocycle coherence audit
├── review-decision v2.0 ................ approve / reject / replan
├── feed-forward v2.0 ................... season → phase guidance
└── artifact-writing v3.1 ............... serializes final artifact

  (*) constraint-synthesis v3.1: patched (v0.37.28) for B+A co-residence, RELOAD-in-Peak,
      and MINI_RESET-before-A-event; references periodization-methodology as methodological basis
  (**) macrocycle-architecture v5.3: patched (v0.37.28–v0.37.30) with backward-planning
       algorithm, taper week content rules, and cadence-override section

↓ (phase slots · cycle-type · kJ-bands · events in phase · taper windows · feed-forward)

PHASE LAYER
├── context-analysis v3.0 ............... reads phase-range authority, feed-forward
├── evidence-alignment v1.0 ............. phase-level evidence
├── guardrails-authoring v9.0 ........... exact weekly kJ bands (BL_kJ, DL_kJ, RE_kJ)
├── cadence-recovery v6.0 ............... 2:1 / 3:1 / 2:1:1, deload, re-entry
├── event-integration v1.0 .............. B/C events → week roles (***) 
├── structure-authoring v4.0 ............ week roles + skeleton; taper_freshening (****)
├── intensity-distribution v4.0 ......... intensity and density shaping
├── execution-rules v2.0 ................ included/excluded session semantics
├── load-governance-audit v4.0 .......... audits phase load governance
├── constraint-audit v2.0 ............... constraint compliance
├── structure-review v1.0 ............... structural consistency
├── bundle-synthesis v2.0 ............... synthesizes phase bundle
├── review-decision v2.0 ................ approve / reject / replan
├── feed-forward v2.0 ................... phase → week guidance
└── artifact-writing v3.1 ............... serializes final artifact

  (***) event-integration v1.0: updated (v0.37.31) to reference periodization-methodology
        for B/C event treatment semantics
  (****) structure-authoring v4.0: updated (v0.37.31) taper_freshening rule to reference
         periodization-methodology for taper week content (volume/intensity/frequency)

↓ (week roles · kJ band · intensity domains · taper flag · phase constraints)

WEEK LAYER
├── load-estimation-week ................ kJ targets per week
├── recommendation-and-adjustment ........ recommendations + micro-adjustments
├── evidence-alignment (week) ........... week-level evidence
└── artifact-writing .................... serializes week artifact
```

---

## Progressive overload coverage

Progressive overload (load ramp, cadence, recovery) is FULLY covered in operational skills:

| Rule | Covered in |
|---|---|
| Ramp rate +5/8/12/18% | `load-governance` v8.0 |
| Exact kJ bands per week | `guardrails-authoring` v9.0 |
| 2:1 / 3:1 / 2:1:1 cadence | `cadence-recovery` v6.0 |
| BL_kJ baseline, DL_kJ deload, RE_kJ re-entry | `cadence-recovery` v6.0 |
| Load math, IF_ref_load | `load-estimation-core` v8.0 |

`periodization-methodology` does NOT redefine any of these — it defines structure and semantics only.

---

## Legacy / superseded

| File | Superseded by |
|---|---|
| `specs/knowledge/_shared/sources/policies/progressive_overload_policy.md` | load-governance + cadence-recovery |
| `specs/knowledge/_shared/sources/specs/season_cycle_enum_spec.md` | macrocycle-architecture + periodization-methodology |

---

## Evidence cross-reference

| Evidence ID | Location | Used for |
|---|---|---|
| `tap_core_001` (Bosquet 2007) | taper_and_peaking_evidence.md | Volume −41–60%, intensity MAINTAIN rule |
| `tap_core_002` (Mujika 2003 = dur_core_012) | taper_and_peaking_evidence.md | Frequency ≥80%, taper definition |
| `tap_applied_001` (Friel 2018 = dur_core_017) | taper_and_peaking_evidence.md | Backward planning, B event as rehearsal |
| `tap_applied_002` (Gallagher 2024) | taper_and_peaking_evidence.md | B+A same phase, fitness held in taper |
| `tap_applied_003` (TORQ 2022) | taper_and_peaking_evidence.md | Volume-first reduction framework |
