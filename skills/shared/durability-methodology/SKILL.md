---
name: durability-methodology
description: Durability-first planning and coaching method for RPS endurance planning.
metadata:
  author: rps
  version: "6.0"
---
Use durability as the primary planning objective.

Definitions:
- `durability`: preservation of usable submaximal performance over long durations under accumulated work, not just fresh peak ability
- `repeatability`: ability to reproduce the next load step or the next week without hidden recovery debt
- `recovery protection`: preserved non-training days, recovery spacing, and removal of lower-priority stress before removing recovery structure
- `authority level`: the active planning layer in control of the current decision, such as Season, Phase, Week, or Coach advisory context

Authority / injected sources:
- deterministic load bands, week roles, legality, event hierarchy, and availability limits come from the active injected runtime context; this skill does not replace them
- curated durability evidence sources under `references/` are justification material only, never authority over active plan guardrails or deterministic planning constraints
- historical migration audits, superseded prose, and decommissioned bibliography files are not operative runtime sources for this skill

Scope and non-scope:
- In scope:
  - durability-first decision framing
  - repeatability-first overload logic
  - recovery-protection prioritization
  - explanation of why a more repeatable option is preferred
- Out of scope:
  - deterministic load math
  - schema or metadata decisions
  - inventing legality or overriding active plan constraints
  - treating evidence citations as permission to break deterministic governance

Durability model:
- durability means maintaining submaximal performance over long durations with limited physiological, biomechanical, and mental decay
- fresh peak metrics such as FTP or VO2max are not sufficient durability evidence
- durability claims require defined energetic preload and interpretation relative to work performed
- useful signals include delayed fatigue onset, reduced drift, stable pacing, stable heart rate, and stable RPE under prolonged work

Decision hierarchy:
1. Preserve sustainable weekly and seasonal repeatability.
2. Protect recovery structure before cosmetic symmetry or catch-up behavior.
3. Increase load mainly through durable volume/work expansion, not reckless intensity stacking.
4. Prefer conservative continuity over heroic compensation after missed sessions.
5. When in doubt, choose the option the athlete can likely repeat next week.

Operational rules:
- treat missed sessions as lost load, not debt to be repaid later in the week
- use kJ/work expansion first; increase intensity density only after stable tolerance exists
- progress at most one overload axis per step: kJ/time, frequency, density/complexity, or intensity
- use intensity as the last overload lever and only when quality and recovery are stable
- keep recovery as an explicit performance variable, not a passive leftover
- when a plan is compressed, shorten lower-priority stress before removing recovery protection
- if fatigue, logistics, or execution quality deteriorate, stabilize first and only then rebuild
- simulation of monotony, sleep deprivation, night riding, cold, or rain is dosed; it is not maximal by default
- masters or reduced-recovery profiles require larger recovery windows, lower intensity density, and stronger quality/consistency protection

Event and macrocycle implications:
- an `A` event is a true peak target and deserves explicit peak-window and taper logic
- keep a `B` event as local structure support while preserving the primary peak for the `A` event
- keep a `C` event inside season-wide durability logic as a training event
- if two `A` events exist, use an explicit multi-peak strategy; never blend them implicitly into one unresolved fatigue wave

Hard rules:
- use the planned recovery-preserving structure after missed sessions
- distribute remaining load only when the plan remains recovery-coherent
- keep overload visible by separating intensity density from long-session dominance
- recovery protection outranks perfect corridor centering
- if a choice conflicts with durability, choose the more repeatable option

Required checks before returning:
- recommendation or plan still fits the current authority level
- proposed change does not create hidden overload via intensity density
- the plan can survive a small execution miss without collapsing
- athlete guidance remains consistency-first and fatigue-aware

Output expectation:
- Return direct operational guidance that helps the active layer choose the more repeatable option.
- When multiple options remain valid, explain the durability-first preference in one or two concrete decision sentences.
- If deterministic constraints or legality already decide the issue, support that outcome instead of reopening it.

Evidence-use boundary:
- Reference priority for explanation and lookup:
  1. `references/durability_reference_table_core.md`
  2. `references/durability_reference_table_applied.md`
- `references/library/core_studies.yaml` and `references/library/applied_sources.yaml` are the canonical local evidence library. The markdown tables are generated from that library.
- `references/evidence_library_manifest.md`, `references/durability_reference_table_core.md`, and `references/durability_reference_table_applied.md` are justification sources, not decision authority.
- Prefer verified peer-reviewed and primary-source-backed references when explaining durability-first choices.
- Use practitioner sources only for implementation/practice translation while keeping thresholds and active plan governance from authoritative RPS context.
- Decommissioned bibliography files are not operative lookup inputs.
- If a source-backed answer needs web research, search by exact author/title from the canonical library first.
- Verify only against primary sources: PubMed, DOI/Crossref, official publisher/journal landing pages, NIH/PMC, or official OA repositories.
- If a locator is uncertain, omit it instead of inventing PMID, DOI, URL, journal, or year details.
