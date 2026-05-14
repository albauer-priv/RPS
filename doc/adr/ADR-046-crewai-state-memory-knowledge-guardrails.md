---
Version: 1.0
Status: Accepted
Last-Updated: 2026-05-14
Owner: ADR
---
# ADR-046: CrewAI State, Memory, Knowledge, and Guardrail Separation

## Context

RPS used CrewAI runtime wiring, but its runtime policy remained mixed:
- static references were injected inline with prompts
- hard runtime instructions lived in the same injection layer
- mandatory-output docs carried both contract framing and output-validation burden
- outer flow state was too thin for reliable persistence/resume reasoning

CrewAI now provides separate primitives for:
- flow state persistence via `@persist`
- static retrieval via `knowledge_sources`
- memory via `Memory(...)`
- output validation via `output_pydantic`, `output_json`, and task guardrails

RPS needs to adopt these mechanisms without weakening the existing authoritative artifact boundary.

## Decision

RPS separates CrewAI runtime policy into five explicit tracks:
1. Flow state + flow persistence
2. Crew/agent memory
3. Static knowledge sources
4. Prompt injection for runtime instructions and residual contracts only
5. Structured output + task guardrails

### Rules

* Authoritative truth remains in validated workspace artifacts.
* CrewAI Memory and Knowledge are assistive only.
* Static domain references move to CrewAI knowledge-source config.
* Prompt injection remains for:
  * authority boundaries
  * runtime operational instructions
  * retained mandatory-output contracts where structured output is still unsafe
* Internal specialist tasks should prefer `output_pydantic` plus function guardrails.
* Persisted artifact tasks may retain prompt-level mandatory-output docs if their schema shape is not yet safe for strict structured output.

## Consequences

### Positive

* Architecture becomes explicit about which mechanism solves which problem.
* Static knowledge can be reduced without weakening runtime instruction fidelity.
* Guardrails shift validation burden from prose to code where possible.
* Flow persistence policy is visible and testable.

### Negative

* Runtime now has more config files and helper layers.
* Mixed-mode artifact families remain until their output models are safe for strict structured output.
* Memory/knowledge storage introduces another operational surface that must be documented.

## Alternatives Considered

### 1. Keep monolithic prompt injection
Rejected because it continues to mix static references, runtime rules, and validation into one opaque mechanism.

### 2. Force all tasks to strict structured output immediately
Rejected because artifact families with open-ended schema sections have already shown strict-schema failures and would regress reliability.

## Implementation Notes

* `config/crewai/flow_persistence.yaml` controls which flows are marked persistent.
* `config/crewai/memory_policy.yaml` controls crew shared memory and agent-scoped views.
* `config/crewai/knowledge_sources.yaml` maps static references into CrewAI knowledge profiles.
* `config/crewai/task_policies.yaml` controls output mode and task guardrails.
* `build_contract_injection_block(...)` narrows prompt injection to explicit contracts/instructions.

## Related

* `doc/specs/features/FEAT_crewai_state_memory_knowledge_prompt_cutover.md`
* `doc/architecture/crewai_flows.md`
