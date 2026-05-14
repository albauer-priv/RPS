---
Version: 1.0
Status: Updated
Last-Updated: 2026-05-14
Owner: Runbooks
---
# CrewAI Prompt and Guardrail Debugging

## Prompt boundary

RPS now separates:
- static knowledge -> `knowledge_sources`
- runtime/contract framing -> `build_contract_injection_block(...)`
- task output validation -> task guardrails and output-mode policy

## Task policy config

See `config/crewai/task_policies.yaml`.

Each task resolves:
- `output_mode`: `pydantic`, `json`, or `prompt_only`
- `guardrails`
- `guardrail_max_retries`

## Typical retained prompt contracts

Persisted artifact tasks may still retain `mandatory_output_*` content where strict structured output is unsafe.

## Debugging checklist

1. Inspect resolved task policy.
2. Inspect the contract-only injected prompt block.
3. Inspect the task output mode.
4. Inspect guardrail failures and retry budget.
5. Confirm guarded store validation still passes on persisted outputs.
