---
Type: Contract
Contract-Name: phase__week
Version: 1.3
Status: Active

Scope: Shared
Authority: Binding

From-Agent: Phase-Architect
To-Agent: Week-Planner

Dependencies:
  - ID: PhaseGuardrailsInterface
    Version: 1.0
  - ID: PhaseFeedForwardInterface
    Version: 1.0
  - ID: PhaseStructureInterface
    Version: 1.0
  - ID: AgendaEnumSpec
    Version: 1.2
  - ID: LoadEstimationSpec
    Version: 1.0
  - ID: TraceabilitySpec
    Version: 1.0
  - ID: FileNamingSpec
    Version: 1.0
---

# Contract: Phase-Architect -> Week-Planner (v1.3)

## 1) Purpose (Binding)
Define the strict execution relationship between Phase-Architect governance
and Week-Planner weekly execution.

## 2) Producer Responsibilities (Phase-Architect)
- OWNS phase-level intent, objectives, and weekly kJ corridors.
- OWNS QUALITY density and permissions.
- OWNS domain/modality allow/forbid sets.
- OWNS structural phase architecture.
- OWNS in-phase delta overrides (Feed Forward).
- MUST validate all output JSON before release.

## 3) Consumer Responsibilities (Week-Planner)
- MUST validate all input JSON before use and STOP on invalid artefacts.
- MUST execute strictly within governance.
- MUST respect weekly kJ corridors.
- MUST respect phase-level non-negotiables, including fixed rest days from the Availability artefact.
- MUST NOT compensate missed load.
- MUST NOT introduce progression or deload logic.
- MUST NOT reinterpret intent or objectives.
- MUST NOT create or modify season/phase artefacts.
- MUST produce exactly one `week_plan_yyyy-ww.json` per run, validated.

## 4) Artefacts and Schemas (Binding)

### Inputs (Week-Planner consumes)
- `phase_guardrails_*` -> `phase_guardrails.schema.json` (required)
- `phase_feed_forward_*` -> `phase_feed_forward.schema.json` (binding if present)
- `phase_structure_*` -> `phase_structure.schema.json` (read-only)
- `activities_actual_*` -> `activities_actual.schema.json` (informational)
- `activities_trend_*` -> `activities_trend.schema.json` (informational)
- `logistics` (context only; no training authority)

### Outputs (Week-Planner produces)
- `week_plan_yyyy-ww.json` -> `week_plan.schema.json`

## 5) Governance Hierarchy (Binding)
Conflicts are resolved in this order:
1. Principles
2. Season-Planner artefacts (`season_plan_*`)
3. Phase-Architect baseline governance (`phase_guardrails_*`)
4. Phase-Architect delta overrides (`phase_feed_forward_*`)
5. Week-Planner execution artefacts
6. Data and context (informational only)

## 6) Feed Forward Application (Binding)
- Feed Forward artefacts ALWAYS originate from Phase-Architect.
- Week-Planner MUST NOT stack, merge, or reinterpret Feed Forwards.
- If multiple Feed Forwards exist, only the latest valid artefact applies.
- Conflicts -> STOP and escalate.

## 7) Constraints / Forbidden (Binding)
- `logistics` MAY explain deviations but MUST NOT mandate load changes.
- Informational inputs NEVER mandate action.
- The Week-Planner MUST NOT create, modify, or extend:
  - `phase_guardrails_*`
  - `phase_feed_forward_*`
  - `phase_structure_*`
  - any season or phase artefacts

## 8) Error Handling & STOP Rules
- No valid `phase_guardrails_yyyy-ww--yyyy-ww.json` exists -> STOP.
- Feed Forward is ambiguous or malformed -> STOP.
- Execution would violate kJ corridors -> STOP.
- Structural architecture is infeasible to execute -> STOP.

## 9) Traceability
- Outputs MUST reference applied `phase_guardrails` filename + version.
- Outputs MUST reference applied `phase_feed_forward` filename + version (if any).

## 10) Precedence
- If there is a conflict between this contract and other documents, this contract wins.
