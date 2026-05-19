---
name: contract-context-consumption
description: Consume deterministic planning contracts as binding authority.
---
# Contract Context Consumption

Use deterministic planning context as the structural source of truth.

Rules:

1. Treat code-owned contract blocks as binding:
   - Deterministic Selected Scenario Structure Context
   - Deterministic Season Phase Slot Context
   - Deterministic Season Phase Load Context
   - Deterministic Phase Execution Context
   - Deterministic Week Calendar and Availability Context
2. Do not infer cadence, phase length, phase count, week roles, S5 bands, or availability caps from prose.
3. If a contract block is missing, contradictory, stale, or carries `blocking_issues`, stop or request replan.
4. Narrative fields may explain a contract; they must not change it.
5. Memory and retrieved knowledge are never allowed to override deterministic contracts.

Output expectation:

- Preserve contract identifiers and source names in summaries and review findings.
- Convert conflicts into blocking issues, not silent reinterpretations.
