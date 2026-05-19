---
name: intensity-distribution
description: Shape phase-appropriate intensity and density inside established guardrails using KPI signal effects only as informational guidance.
metadata:
  author: rps
  version: "4.0"
---
Shape phase intensity at the phase level, not at workout-detail level.

Method:
1. Start from phase objective, active cycle type, and approved load/cadence guardrails.
2. Use KPI signal effects as informational mapping only. They explain what different workout classes are good at while progression, deloads, gates, and overrides remain governed by active artifacts.
3. Express intensity through allowed and suppressed domains, quality-density intent, and phase emphasis.
4. Keep durability and energetic tolerance above intensity ambition.

KPI-informed mapping rules:
- VO2max interval types mainly support VO2 TiZ and fresh FIR, not durability.
- Sweet spot and tempo mainly support FTP durability, EF stability, and sub-threshold economy.
- Endurance fatigue-finish and back-to-back load mainly inform durability, sustained power drop, HR drift, and BBR.
- Recovery supports recovery only; it is not a performance KPI session.
- K3 is economy/torque-adjacent support, not a VO2 or durability diagnostic by itself.

Phase-level usage rules:
- intensity density is subordinate to corridor realism and cadence safety
- use quality support for clean adaptive stimulus while keeping low-load weeks recovery-coherent
- durability-oriented phases bias toward endurance/tempo stability over high-intensity density
- event-specific weeks may allow tighter emphasis, but not outside agenda semantics and recovery protection
- Base/general build is usually LIT-dominant and pyramidal-leaning: high low intensity, dosed tempo/sweet spot, little high intensity
- Build/performance sharpening is usually more polarized: LIT remains high, moderate density is capped, and high-intensity quality appears only when recovered
- moderate work is a budget, not a default; reduce it when it degrades high-intensity quality or low-intensity consistency
- place high-intensity work only when freshness supports clean repeat quality and weekly kJ still leaves recovery margin
- near the A event, specificity rises through event-like duration, pace stability, fueling stability, back-to-back or hard-late relevance, not random extra moderate work

Phase intent and intensity semantics:
- Use only schema-valid cycles: `Base`, `Build`, `Peak`, `Transition`.
- Do not invent new cycle values such as `Specificity` or `Taper`.
- Represent finer planning intent through phase intent semantics inside the active cycle.

| Cycle | Phase intent | Existing / aligned repo term | Allowed intensity domains | Optional / conditional | Default avoid | Allowed load modalities | Semantic notes |
|---|---|---|---|---|---|---|---|
| `Transition` | `recovery_reset` | aligns with `Transition`; may include `re-entry`, `reset`, `post-event restoration` | `RECOVERY`, `ENDURANCE` | very light activation only if clearly useful | `SWEET_SPOT`, `THRESHOLD`, `VO2MAX` | `NONE` | Recovery-first phase. Restore rhythm without building structural load. |
| `Transition` | `shortened_re_entry` | `shortened_re_entry` | `ENDURANCE` | very light `TEMPO` only if recovery is stable and re-entry is clearly controlled | `SWEET_SPOT`, `THRESHOLD`, `VO2MAX` | `NONE`, `K3` | Shortened return after disruption or compressed horizon. Controlled load re-establishment, not full build logic. |
| `Transition` | `shortened_consolidation` | `shortened_consolidation` | `ENDURANCE` | selected `TEMPO` only if scenario-permitted and continuity is stable | `SWEET_SPOT`, `THRESHOLD`, `VO2MAX` | `NONE`, `K3` | Bridge phase after re-entry. Consolidate execution and preserve runway for later build phases. |
| `Transition` | `transition_consolidation` | `transition_consolidation` | `ENDURANCE` | `TEMPO`; `SWEET_SPOT` only as rare primer if scenario-permitted and recovery is coherent | `VO2MAX`, frequent `THRESHOLD`, accumulated `SWEET_SPOT` | `NONE`, `K3` | Controlled bridge phase, not hidden build work. Tempo/SST are bridge tools only, not default progression load. |
| `Base` | `foundation` | aligns with Base semantics in macrocycle architecture | `ENDURANCE` | very light `TEMPO` only if clearly justified | `THRESHOLD`, `VO2MAX`, frequent `SWEET_SPOT` | `NONE`, `K3` | Early groundwork: aerobic routine, kJ tolerance, passive structure preparation, low density. |
| `Base` | `general_build` | aligns with active Base/general-build wording | `ENDURANCE`, `TEMPO` | `SWEET_SPOT` when recovery is stable or time budget is tight | frequent `THRESHOLD`, much `VO2MAX` | `NONE`, `K3` | Later groundwork: still endurance-dominant, with first controlled pressure work. Pyramidal-leaning. |
| `Build` | `build_progression` | aligns with generic `Build` progression semantics | `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | `THRESHOLD` only if explicitly justified by scenario and recovery | high HI density, random `VO2MAX` | `NONE`, `K3` | General build progression: more structure, controlled progression, event-relevant load growth without losing durability-first control. |
| `Build` | `ceiling_support` | repo-aligned semantic only | `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | short `VO2MAX` support block only when fresh and explicitly useful | chronic `THRESHOLD` load, broad HI escalation | `NONE`, `K3` | Early/mid build where aerobic ceiling support may be useful. HI remains support capacity, not the main motor. |
| `Build` | `durability_build` | repo-aligned semantic only | `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | targeted `THRESHOLD`; rare `VO2MAX` maintenance only | high HI density | `NONE`, `K3` | Later build focused on fatigue-resistant output: hard-late, B2B, preload, long-ride kJ, and specific work under fatigue. Intensity is not the main escalation lever; fatigue-context specificity is. |
| `Build` | `b_event_rehearsal` | `b_event_rehearsal` | `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | targeted rehearsal-specific sharpening only if scenario-permitted | full taper logic, broad new HI blocks | `NONE`, `K3` | B event is rehearsal/minor adjustment only. Preserve long-build continuity and A-event runway. |
| `Peak` | `peak_preparation` | `peak_preparation` | `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | short primers/openers only if already proven | new VO2 blocks, heavy threshold accumulation, new `SWEET_SPOT` accumulation | `NONE`, `K3` | Event-near sharpening and specificity through pacing, fueling, preload, and execution realism. Sweet spot here is maintenance/sharpening only, not a new accumulation block. |
| `Peak` | `a_event_peak_taper` | `a_event_peak_taper` | `RECOVERY`, `ENDURANCE` | short `TEMPO` or `SWEET_SPOT` primers; rare short `VO2MAX` opener if already known to work | new stimuli, long hard time-in-zone | `NONE` | Dedicated A-event taper. Freshness first; maintain feel without creating fatigue debt. |

Reading rules:
- `allowed_intensity_domains` are permissions, not obligations.
- In `Transition`, `TEMPO` and `SWEET_SPOT` are conditional bridge tools, not default build work.
- `K3` appears only under `allowed_load_modalities`, not as an intensity domain.
- In `Peak`, `SWEET_SPOT` is low-dose maintenance/sharpening only.
- `build_progression` and `durability_build` may share the same intensity domains, but must differ through fatigue context, B2B, hard-late, preload, and long-ride kJ.
- `ceiling_support` does not mean `VO2MAX` must appear.
- Phase intent may narrow scenario domains, but must not exceed scenario-level allowed domains.
- Authority flows only downward:
  - `scenario.allowed_domains` = upper seasonal authority
  - `phase.allowed_domains` = narrower phase authority
  - `week.allowed_domains` = fatigue-/execution-filtered week authority

Hard rules:
- use KPI signal mapping as explanatory context rather than a decision gate
- keep workout details in downstream week/workout tasks
- keep intensity inside recovery, durability, and corridor constraints
- infer governance actions from active artifacts and review tasks

Positive operating guidance:
- Use the active task, injected context, and configured skill role to choose the smallest coherent contribution.
- Read the available evidence, check the governing constraints, and explain the decision path in direct operational language.
- Produce actionable content that helps the next task continue without recomputing or guessing.
- Include required facts, assumptions, warnings, and trace cues when they are available.
- Return a concise result that supports the task expected_output and preserves the authoritative runtime context.

Positive execution pattern:
- Choose the intensity distribution that best supports the phase role, active deload intent, available recovery, and event proximity.
- Build the distribution from allowed domains, quality-day limits, and durability-first priorities.
- Summarize the selected emphasis, explain why it fits the current phase, and include the practical boundaries for downstream week planning.
- Produce clear guidance that helps the week planner place easy, endurance, tempo, or quality work without adding hidden load.

Output format:
- Return the active task expected_output with clear sections for facts, decision, rationale, warnings, and next action when applicable.
- Include only information needed by the active task and downstream consumer.
