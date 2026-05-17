---
Version: 1.0
Status: Updated
Last-Updated: 2026-05-16
Owner: Architecture
---
# CrewAI Migration Audit

## 1. Executive Summary

The CrewAI runtime is structurally sound: Season, Phase, Week, and Report use explicit planning, review, and writer stages. The migration gaps were concentrated in high-authority details from the old system: scenario-selection routing, load calculation, S5 phase-band derivation, season cadence/deload checks, and report advisory boundaries.

Migration maturity after this hardening: **freigabefähig mit Auflagen**. Remaining risk is mostly end-to-end model behavior and live CrewAI smoke validation.

## 2. Audit des Ist-Zustands

| Bereich | Bewertung | Befund | Risiko | Maßnahme |
|---|---:|---|---|---|
| Crews | gut | Planning/Review/Writer split exists | More moving parts | Keep structure |
| Agents | gut | Specialist roles are clearly cut | Some old method details were too soft | Harden skills |
| Tasks | mittel | Scenario Selection reused scenario task | Wrong artifact framing | Dedicated task |
| Skills | mittel | Most logic migrated, load details compressed | Prompt-only load math | Code-owned S5 + skill updates |
| Knowledge | gut | Factual bundles separated from skills | Superseded docs could compete | Keep old prose as evidence/reference |
| Rechenlogik | kritisch | S5 was not fully deterministic in runtime | Non-reproducible phase bands | Add `rps.planning.load_bands` |
| Guardrails | mittel | Structural checks existed | Missing semantic checks | Add task guardrails |
| Output-Qualität | mittel | Writers serialize envelopes | Bad bands could pass if schema-valid | Add semantic checks |

## 3. Mapping Altsystem → CrewAI

| Altes Artefakt | Wichtige Regel/Logik | Zielkomponente neu | Status | Kommentar |
|---|---|---|---:|---|
| `season_scenario.md` | exactly three advisory scenarios | `season_scenarios` task + `skills/season/scenario-generation` | vollständig übernommen | Scenario task remains advisory |
| `season_scenario.md` | no weekly kJ corridors in scenarios | scenario skill/guardrail | übernommen | Selection split fixed |
| `season_planner.md` | phase count and cadence are binding | season synthesis/audit skills + guardrails | teilweise übernommen | Guardrail checks shape; model still authors content |
| `season_planner.md` | load corridors from LoadEstimationSpec | `src/rps/planning/load_bands.py` + season load context | übernommen | Code-owned capacity/S5 |
| `phase_architect.md` | S5 ladder for weekly bands | `derive_phase_s5_band` | übernommen | Full fallback ladder implemented |
| `week_planner.md` | week load must stay in active band | week guardrail + week skill | übernommen | Week task checks summary corridor |
| `workout_builder.md` | export is validation/conversion only | local workout export code | übernommen | Remains deterministic, not LLM |
| `performance_analysis.md` | DES diagnostic-only | `des_diagnostic_only` guardrail + report skill | übernommen | No direct plan changes |
| `progressive_overload_policy.md` | 2:1 / 3:1 / 2:1:1 cadence | season/phase/week skills | übernommen | No new cycle enum |
| `load_estimation_spec.md` | `planned_kJ` vs `planned_weekly_load_kj` | code + skills | übernommen | Terminology kept |

## 4. Gap-Analyse

### 4.1 Fehlende Inhalte

* Dedicated Scenario Selection task was missing.
* Code-owned availability capacity and S5 phase-band derivation were missing.
* Semantic guardrails for Season/Phase/Week/Report were incomplete.

### 4.2 Falsch platzierte Inhalte

* Exact load math was too dependent on prompt/skill prose.
* Workout export correctly belongs in deterministic code, not a CrewAI agent.

### 4.3 Zu unpräzise übertragene Inhalte

* Cadence/deload rules needed stronger Season audit language.
* Week reconciliation needed stronger no-intensity-inflation language.

### 4.4 Widersprüche

* Old documents mention specificity/taper concepts, but current schema supports only `Base | Build | Peak | Transition`. Resolution: keep schema values; express taper intent inside existing fields.

### 4.5 Risiken bei Rechenvorschriften und Algorithmen

* S5 must not be prompt-only.
* KPI escalation depends on available KPI band data; unavailable levels are traced as non-applicable.

### 4.6 Fehlende Guardrails oder Qualitätssicherungen

* Added scenario-selection shape, season cycle/cadence, phase S5 shape, week corridor/exportability, and DES advisory-only checks.

## 5. Angepasste Zielarchitektur

### 5.1 Crews

* `season_scenario`: receives deterministic event horizon and cadence options; produces three advisory scenarios.
* `season_planning`: receives deterministic load capacity, selected-scenario structure, and phase-slot skeleton; produces candidate Season bundle.
* `season_review`: checks cadence, cycle, and governance realism.
* `season_writer`: serializes only approved Season envelope.
* `phase_planning`: receives deterministic Phase Execution Context and S5 bands and must use them for exact-range outputs.
* `phase_review`: checks load compression, exact week coverage, and S5 coherence.
* `week_planning`: receives active S5/phase band plus deterministic Mon-Sun calendar/availability matrix as execution target.
* `week_review`: checks load and workout syntax before writer handoff.
* `report_planning/review/writer`: receives deterministic report evidence versions and stays advisory-only.
* `coach`: receives deterministic selected-week operation boundaries and remains preview-first.

### 5.2 Agents

* Season load/cadence agents consume `Deterministic Load Capacity Context`, including availability-capacity min/typical/max.
* Season scenario generation consumes `Deterministic Season Scenario Horizon Context` and `Deterministic Cadence Options Context`.
* Season plan synthesis consumes selected-scenario structure math and `Deterministic Season Phase Slot Context`, including total planning weeks, cadence-derived phase length, expected full phases, shortened-phase budget, phase ids, and ISO-week ranges.
* Phase guardrail/structure agents consume `Deterministic Phase Execution Context` and `deterministic_s5_bands` with min/max per ISO week once the Season corridor is known.
* Week load agent consumes the active S5/phase min/max band and `Deterministic Week Calendar and Availability Context` for corridor and day-level checks.
* Report and Coach agents consume deterministic boundary contexts for evidence versions and preview/apply semantics.
* Writers never re-plan.

### 5.3 Tasks

* `season_scenario_selection` is now a first-class persisted artifact task.
* `phase_guardrails` and `week_plan` now have semantic guardrails.

### 5.4 Skills

* Skills now state that code-owned S5 values are authoritative.
* Old cadence/load/deload logic is placed in Season/Phase/Week method skills.

### 5.5 Knowledge

* Factual interface/schema/evidence bundles remain in `knowledge_sources`.
* Superseded prose remains migration evidence or skill references, not broad runtime authority.

## 6. Direkt angepasste Artefakte

Implemented directly in:

* `src/rps/planning/load_bands.py`
* `src/rps/agents/crewai_backend.py`
* `src/rps/crewai_runtime/guardrails.py`
* `config/crewai/tasks.yaml`
* `config/crewai/task_policies.yaml`
* `skills/season/*/SKILL.md`
* `skills/phase/*/SKILL.md`
* `skills/week/*/SKILL.md`
* `tests/test_load_bands.py`
* `tests/test_crewai_runtime.py`

## 7. Änderungsdokumentation

| Änderung | Betroffenes Artefakt | Quelle im Altsystem | Begründung | Status |
|---|---|---|---|---|
| Scenario Selection task split | `tasks.yaml`, `crewai_backend.py` | `season_scenario.md` | one artifact per run | umgesetzt |
| S5 code-owned | `load_bands.py` | `load_estimation_spec.md` | deterministic governance | umgesetzt |
| Load context injection | `season_flow.py`, `plan_week.py` | old planner load gates | agents consume code truth | umgesetzt |
| Deterministic context registry | `deterministic_context.py` | old prompt calculations | centralize code-owned dates, slots, calendars, report evidence, Coach boundaries | umgesetzt |
| Season cadence hardening | Season skills | progressive overload policy | preserve old cadence | umgesetzt |
| Semantic guardrails | `guardrails.py` | old stop/review gates | fail before persistence | umgesetzt |

## 8. Rechenvorschriften

| Name | Quelle | Zweck | Umsetzung |
|---|---|---|---|
| `IF_ref_load` | LoadEstimationSpec | athlete-aware normalization | code |
| Availability feasible band | LoadEstimationSpec S4.2 | capacity in governance load | code |
| KPI capacity band | LoadEstimationSpec S4.3 | optional KPI gating | code |
| Progression band | ProgressiveOverloadPolicy | ramp bounds | code |
| S5 ladder | LoadEstimationSpec S4.5 | final phase weekly band | code |
| Week corridor check | Week planner prompt | load compliance | guardrail |

## 9. Guardrails und Qualitätssicherung

* Fachlich: cadence/deload, phase cycle enum, S5 band shape, week corridor compliance.
* Sicherheit: no raw direct DES planning action.
* Konsistenz: scenario selection cannot contain planning payloads.
* Output: artifact envelopes must include meta/data and semantic validity.
* Eskalation: guardrail retry, then run failure without persistence.

## 10. Regressionstest-Matrix

| Testfall | Input | Erwartung Altsystem | Erwartung neues System | Prüfkriterium | Status |
|---|---|---|---|---|---|
| Scenario Selection | selected `A` | selection artifact only | own task artifact | task mapping | umgesetzt |
| Availability capacity | weekly hours + FTP | load capacity bounded by time | deterministic capacity | unit test | umgesetzt |
| S5 normal | intersecting bands | fallback 0 | same | unit test | umgesetzt |
| S5 fallback | progression conflict | drop progression | fallback 1 | unit test | umgesetzt |
| Week overload | planned > corridor | stop/rework | guardrail fail | unit test | umgesetzt |
| DES action | direct phase change | forbidden | guardrail fail | unit test | umgesetzt |

## 11. Annahmen und offene Punkte

Annahmen:

* `AVAILABILITY.weekly_hours` is the numeric time source.
* `LOGISTICS` constrains interpretation but does not numerically reduce hours.
* `Specificity` and `Taper` stay out of schema cycles.

Offene Punkte:

* End-to-end CrewAI smoke should validate model behavior with live credentials.
* KPI LOW/MID/HIGH escalation can only run when the corresponding bands are available.

## 12. Finale Qualitätsfreigabe

* Fachliche Vollständigkeit: high for load/cadence migration.
* CrewAI-Strukturqualität: high.
* Übernahmegrad: high for listed old logic.
* Robustheit Rechenlogik: improved, code-owned.
* Wartbarkeit: moderate; more code paths but clearer authority.
* Testbarkeit: improved.

Finale Einschätzung: **freigabefähig mit Auflagen** pending full validation commands and live CrewAI smoke.
