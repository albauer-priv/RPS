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

Canonical phase semantics:
- Read inherited `phase_type`, `phase_intent`, and `build_subtype` as binding upstream semantics.
- Use canonical `phase_type` values only:
  - `TRANSITION`, `PREPARATION`, `BASE`, `BUILD`, `PEAK`, `TAPER`, `RACE`
- Use canonical `phase_intent` values only:
  - `transition_recovery`, `preparation_re_entry`, `shortened_re_entry`
  - `general_base`, `aerobic_base`, `strength_endurance_base`, `sweet_spot_base`
  - `vo2_build`, `threshold_build`, `sst_build`, `durability_build`, `specificity_build`, `vlamax_lowering`
  - `peak_sharpening`, `taper_freshening`, `race_execution`
- For `BUILD`, `build_subtype` is required and must equal `phase_intent`.
- Restrict planning semantics to the canonical values listed above.

| Phase type | Phase intent | Build subtype | Planner purpose | Allowed intensity domains | Optional / conditional | Default avoid | Allowed load modalities | Semantic notes |
|---|---|---|---|---|---|---|---|---|
| `TRANSITION` | `transition_recovery` | `null` | reduce accumulated fatigue and restore freshness without building new load | `RECOVERY`, `ENDURANCE` | very light activation only if clearly useful | `SWEET_SPOT`, `THRESHOLD`, `VO2MAX` | `NONE` | Recovery-first phase. |
| `PREPARATION` | `preparation_re_entry` | `null` | restore training rhythm and structural readiness before full base work | `ENDURANCE` | very light `TEMPO` only if continuity is stable | `SWEET_SPOT`, `THRESHOLD`, `VO2MAX` | `NONE`, `K3` | Re-entry before full base. |
| `BASE` | `shortened_re_entry` | `null` | compressed re-entry with recovery protection and controlled continuity rebuild | `ENDURANCE` | very light `TEMPO` only if recovery is stable and re-entry is controlled | `SWEET_SPOT`, `THRESHOLD`, `VO2MAX` | `NONE`, `K3` | Compressed re-entry block. |
| `BASE` | `general_base` | `null` | build broad aerobic base and repeatable training continuity without a narrow specialty focus | `ENDURANCE`, `TEMPO` | `SWEET_SPOT` when recovery is stable or time budget is tight | frequent `THRESHOLD`, much `VO2MAX` | `NONE`, `K3` | General base with controlled pressure work. |
| `BASE` | `aerobic_base` | `null` | prioritize low-intensity aerobic development, routine, and low-risk load tolerance | `ENDURANCE` | very light `TEMPO` only if clearly justified | `THRESHOLD`, `VO2MAX`, frequent `SWEET_SPOT` | `NONE`, `K3` | Early groundwork and low density. |
| `BASE` | `strength_endurance_base` | `null` | develop torque, musculoskeletal robustness, and force endurance under controlled load | `ENDURANCE`, `TEMPO` | limited `SWEET_SPOT` only if structurally coherent | `THRESHOLD`, repeated `VO2MAX` | `NONE`, `K3` | Torque/structure-oriented base. |
| `BASE` | `sweet_spot_base` | `null` | raise sustainable sub-threshold capacity while preserving base continuity | `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | controlled SST only | frequent `THRESHOLD`, much `VO2MAX` | `NONE`, `K3` | Sustainable-power base. |
| `BUILD` | `vo2_build` | `vo2_build` | raise aerobic ceiling as the primary build objective | `ENDURANCE`, `VO2MAX` | sparse `TEMPO`/`SWEET_SPOT` support only | chronic threshold accumulation | `NONE` | Ceiling-oriented build. |
| `BUILD` | `threshold_build` | `threshold_build` | improve sustained threshold power and clearance under repeatable structure | `ENDURANCE`, `TEMPO`, `THRESHOLD` | `SWEET_SPOT` support | broad VO2 escalation | `NONE`, `K3` | Sustained-power build. |
| `BUILD` | `sst_build` | `sst_build` | expand extensive sub-threshold capacity without tipping into broad high-intensity load | `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | targeted `THRESHOLD` only if justified | random HI density | `NONE`, `K3` | Extensive sub-threshold build. |
| `BUILD` | `durability_build` | `durability_build` | improve fatigue resistance, hard-late stability, and long-duration output under preload | `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | targeted `THRESHOLD`; rare `VO2MAX` maintenance only | high HI density | `NONE`, `K3` | Hard-late, B2B, preload, long-ride kJ. |
| `BUILD` | `specificity_build` | `specificity_build` | train event-near demands through pacing, fueling, terrain, cadence, and logistics specificity | `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | targeted `THRESHOLD`; sparse VO2 maintenance only when explicitly useful | broad new VO2 loading | `NONE`, `K3` | Event-near specificity without taper semantics. |
| `BUILD` | `vlamax_lowering` | `vlamax_lowering` | reduce glycolytic contribution and improve metabolic efficiency for long steady work | `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | targeted threshold only if coherent | anaerobic / VO2-heavy escalation | `NONE`, `K3` | Efficiency-oriented build. |
| `PEAK` | `peak_sharpening` | `null` | preserve readiness and sharpen event-specific execution without adding heavy new load | `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | short primers/openers only if already proven | new VO2 blocks, heavy threshold accumulation | `NONE`, `K3` | Event-near sharpening and specificity. |
| `TAPER` | `taper_freshening` | `null` | reduce fatigue while preserving feel, timing, and event readiness | `RECOVERY`, `ENDURANCE` | short `TEMPO` or `SWEET_SPOT` primers; rare short `VO2MAX` opener if already known to work | new stimuli, long hard time-in-zone | `NONE` | Freshness first. |
| `RACE` | `race_execution` | `null` | execute the event block with pacing, fueling, logistics, and recovery control | `RECOVERY`, `ENDURANCE`, `TEMPO` | short openers only if tied to event execution | new accumulation blocks | `NONE` | Event execution window. |

Reading rules:
- `allowed_intensity_domains` are permissions, not obligations.
- In `Transition`, `TEMPO` and `SWEET_SPOT` are conditional bridge tools, not default build work.
- `K3` appears only under `allowed_load_modalities`, not as an intensity domain.
- In `Peak`, `SWEET_SPOT` is low-dose maintenance/sharpening only.
- `sst_build` and `durability_build` may share the same intensity domains, but must differ through fatigue context, B2B, hard-late, preload, and long-ride kJ.
- `vo2_build` does not mean `VO2MAX` must appear every week.
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
