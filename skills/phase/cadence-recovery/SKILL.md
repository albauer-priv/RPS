---
name: cadence-recovery
description: Apply season-owned cadence, deload, and re-entry rules inside an exact phase range.
metadata:
  author: rps
  version: "6.0"
---
Apply cadence as a constrained translation problem.

Definitions:
- `BL_kJ`: baseline weekly governance-load anchor for the exact phase range
- `prior_week_kJ`: previous comparable build-week governance load in the active cadence interpretation
- `DL_kJ`: deload governance-load target
- `RE_kJ`: re-entry governance-load target
- `MR_kJ`: mini-reset governance-load target
- `W1_kJ`, `W2_kJ`, `W3_kJ`, `W4_kJ`: cadence-step governance-load targets inside the exact phase range
- `BL_kJ_next`: conservative next-baseline anchor after a finished cadence cycle
- `week_role`: inherited exact-week cadence role from deterministic phase execution context
- `phase_role`: deterministic phase role for the active exact range
- `planned_weekly_load_kj`: governance load metric used for phase/weekly bands

Authority / injected sources:
- `week_role`, exact phase range, and cadence family come from `Deterministic Phase Execution Context`
- baseline context should come from deterministic baseline or recent-history inputs already prepared for this layer; if baseline is absent, this layer must mark it low-confidence rather than inventing it from prose
- this layer calculates overload, deload, mini-reset, reload, and re-entry semantics for the exact phase range
- this layer must not compute workout-level segment math

Method:
1. Confirm the season-compatible cadence family: `3:1`, `2:1`, or `2:1:1`.
2. Place build, deload, and mini-reset weeks so the exact phase range stays coherent.
3. Define deload magnitude and re-entry load from the selected baseline.
4. Favor the shorter fatigue wave whenever tolerance or logistics are uncertain.

Decision procedure:
1. Start with the inherited season cadence; do not invent a new family locally.
2. Determine whether the phase context still supports the nominal family:
   - stable robustness and no repeated collapse can keep `3:1`
   - fragile recovery, masters profile, or high stress should bias toward `2:1`
   - tolerance for two build weeks but not a third should bias toward `2:1:1`
3. Decide whether the nominal reset week stays mini-reset/reload or degrades to deload/re-entry.
4. Mark the resulting week semantics explicitly in the phase output.

Progression axes:
- duration / total governance work
- frequency only when exact-range structure supports it
- density / complexity
- intensity last

Progression rules:
- advance only one overload axis at a time unless an explicit bounded exception is stated
- do not use intensity first to repair a weak load step
- calculate exact-range overload and reset semantics rather than inheriting labels blindly

Selection rules:
- `2:1` for fragile recovery, life stress, masters profiles, injury/illness sensitivity, or repeated build-week collapse
- `3:1` only with stable robustness and evidence that three progressive weeks are sustainable
- `2:1:1` when two build weeks are tolerated but a full third build week is consistently too much
- if `3:1` repeatedly breaks down in week 3, shift phase interpretation toward `2:1` or `2:1:1`
- if `2:1` repeatedly over-recovers or stalls without fatigue pressure, flag whether a different cadence family would better fit the inherited season policy

Deload and re-entry:
- deload must reduce meaningful weekly load, not merely relabel intensity
- baseline-anchored deload: `DL_kJ = BL_kJ * 0.60 to 0.80`
- last-build anchored deload: `DL_kJ = prior_week_kJ * 0.55 to 0.75`
- default re-entry: `RE_kJ = BL_kJ * 0.90 to 1.00`
- high-fatigue re-entry: `RE_kJ = BL_kJ * 0.85 to 0.95`
- robust/fresh re-entry, only without spike or dominance warnings: `RE_kJ = BL_kJ * 0.95 to 1.05`
- when fatigue remains high, re-entry should be lower rather than forcing the old build target
- keep normal reload and baseline-anchored re-entry semantically distinct

Reload vs re-entry rule:
- `reload` means the athlete is returning near prior build load after only a limited reset
- `re-entry` means the athlete is returning from a true deload or unresolved fatigue and must be baseline-anchored rather than prior-build anchored
- when in doubt after poor readiness, choose `re-entry`, not `reload`

Cadence target math:
- `3:1`: `W1 = BL * 1.00-1.05`, `W2 = W1 * 1.08-1.12`, `W3 = W2 * 1.06-1.10`, then deload
- `2:1`: `W1 = BL * 1.00-1.05`, `W2 = W1 * 1.08-1.15`, then deload
- `2:1:1`: `W1 = BL * 1.00-1.05`, `W2 = W1 * 1.08-1.12`, `MR = W2 * 0.80-0.90`, `W4 = W2 * 0.95-1.05`
- if `2:1:1` fatigue is high in W2 or readiness is poor in W3, replace `MR` with true deload and treat W4 as re-entry
- after a clean `2:1:1`, update next baseline conservatively as `BL_kJ_next = mean(W2_kJ, W4_kJ)` or use rolling `CH_kJ`
- Build-entry after shortened/base/re-entry context must stay conservative and readiness-gated even if the inherited week role is nominally a load week

Cadence-specific failure handling:
- `3:1`: if W3 quality or execution repeatedly collapses, do not preserve a nominal third build week in prose; move the phase logic toward `2:1` or `2:1:1`
- `2:1`: if the deload keeps appearing unnecessary and progression still stalls, surface explicit cadence reconsideration rather than pretending the current cadence is clean
- `2:1:1`: if W3 fatigue is already too high, do not preserve mini-reset wording; write true deload semantics and baseline-anchored W4 re-entry

Hard rules:
- use the cadence allowed by season logic
- re-entry ramps gradually back toward normal build load
- deloads and mini-resets must remain visible in the phase structure
- a phase structure must show which weeks are build, deload, mini-reset, reload, or re-entry
- if policy semantics force a reload to behave like re-entry, mark it explicitly rather than hiding it behind the reload label
- use cadence logic to constrain structure while preserving explicit season authority

Output format:
- Return the active task expected_output with clear sections for facts, decision, rationale, warnings, and next action when applicable.
- Include only information needed by the active task and downstream consumer.
