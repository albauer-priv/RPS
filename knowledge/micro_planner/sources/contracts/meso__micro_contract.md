---
Type: Contract
Contract-Name: meso__micro
Version: 1.3
Status: Active

Scope: Shared
Authority: Binding

From-Agent: Meso-Architect
To-Agent: Micro-Planner

Dependencies:
  - ID: BlockGovernanceInterface
    Version: 1.0
  - ID: BlockFeedForwardInterface
    Version: 1.0
  - ID: BlockExecutionArchInterface
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

# Contract: Meso-Architect -> Micro-Planner (v1.3)

## 1) Purpose (Binding)
Define the strict execution relationship between Meso-Architect governance
and Micro-Planner weekly execution.

## 2) Producer Responsibilities (Meso-Architect)
- OWNS block-level intent, objectives, and weekly kJ corridors.
- OWNS QUALITY density and permissions.
- OWNS domain/modality allow/forbid sets.
- OWNS structural block architecture.
- OWNS in-block delta overrides (Feed Forward).
- MUST validate all output JSON before release.

## 3) Consumer Responsibilities (Micro-Planner)
- MUST validate all input JSON before use and STOP on invalid artefacts.
- MUST execute strictly within governance.
- MUST respect weekly kJ corridors.
- MUST respect block-level non-negotiables, including fixed rest days derived from the Season Brief availability table.
- MUST NOT compensate missed load.
- MUST NOT introduce progression or deload logic.
- MUST NOT reinterpret intent or objectives.
- MUST NOT create or modify macro/block artefacts.
- MUST produce exactly one `workouts_plan_yyyy-ww.json` per run, validated.

## 4) Artefacts and Schemas (Binding)

### Inputs (Micro-Planner consumes)
- `block_governance_*` -> `block_governance.schema.json` (required)
- `block_feed_forward_*` -> `block_feed_forward.schema.json` (binding if present)
- `block_execution_arch_*` -> `block_execution_arch.schema.json` (read-only)
- `activities_actual_*` -> `activities_actual.schema.json` (informational)
- `activities_trend_*` -> `activities_trend.schema.json` (informational)
- `events.md` (informational, no schema)

### Outputs (Micro-Planner produces)
- `workouts_plan_yyyy-ww.json` -> `workouts_plan.schema.json`

## 5) Governance Hierarchy (Binding)
Conflicts are resolved in this order:
1. Principles
2. Macro-Planner artefacts (`macro_overview_*`)
3. Meso-Architect baseline governance (`block_governance_*`)
4. Meso-Architect delta overrides (`block_feed_forward_*`)
5. Micro-Planner execution artefacts
6. Data and context (informational only)

## 6) Feed Forward Application (Binding)
- Feed Forward artefacts ALWAYS originate from Meso-Architect.
- Micro-Planner MUST NOT stack, merge, or reinterpret Feed Forwards.
- If multiple Feed Forwards exist, only the latest valid artefact applies.
- Conflicts -> STOP and escalate.

## 7) Constraints / Forbidden (Binding)
- `events.md` MAY explain deviations but MUST NOT mandate load changes.
- Informational inputs NEVER mandate action.
- The Micro-Planner MUST NOT create, modify, or extend:
  - `block_governance_*`
  - `block_feed_forward_*`
  - `block_execution_arch_*`
  - any macro or block artefacts

## 8) Error Handling & STOP Rules
- No valid `block_governance_yyyy-ww--yyyy-ww+3.json` exists -> STOP.
- Feed Forward is ambiguous or malformed -> STOP.
- Execution would violate kJ corridors -> STOP.
- Structural architecture is infeasible to execute -> STOP.

## 9) Traceability
- Outputs MUST reference applied `block_governance` filename + version.
- Outputs MUST reference applied `block_feed_forward` filename + version (if any).

## 10) Precedence
- If there is a conflict between this contract and other documents, this contract wins.
