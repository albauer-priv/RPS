# 50 — Change Impact Checklist

## When touching `config/crewai/*.yaml`

Check:

- top-level authority ownership
- task / agent / skill mapping
- runtime profiles / policy alignment
- memory policy impact
- task output modes and guardrails

## When touching `prompts/agents/*.md`

Check:

- active-layer self-contained rules
- variable authority compliance
- planning vs review vs writer ownership
- mandatory output / tool load order

## When touching `skills/**/SKILL.md`

Check:

- one-method-skill rule
- no domain-method leakage into crew-level helpers
- references are actionable and locally usable

## When touching `src/rps/agents/**` or `src/rps/crewai_runtime/**`

Check:

- Flow-first orchestration boundaries
- telemetry and guardrails
- contract truth and traceability
- runtime memory constraints

## When touching `specs/schemas/**`

Check:

- strict required-property expectations
- schema bundling
- generated models if applicable
- validation coverage

## When touching UI pages

Check:

- no direct agent calls
- Streamlit rerun/worker safety
- AppTest coverage