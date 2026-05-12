---
Version: 1.0
Status: Accepted
Last-Updated: 2026-05-12
Owner: Coach / Runtime
---
# ADR-033: Coach CrewAI Decoupling and Direct Provider Config

## Context

After the Python 3.13 / CrewAI activation baseline work, two visible legacy dependencies remained:

* the `Coach` page still depended on `rps.ui.rps_chatbot`
* the CrewAI backend still read provider settings indirectly from the legacy LiteLLM client object

That left the most visible conversational surface and part of the CrewAI execution path tied to the old stack.

## Decision

1. The `Coach` page will no longer use `rps.ui.rps_chatbot`.
2. Coach conversation turns will run through a dedicated CrewAI turn runner with Streamlit-native chat rendering.
3. CrewAI provider configuration will be resolved directly from `RPS_LLM_*` environment variables in a dedicated module.
4. The CrewAI persisted-artefact backend will use this provider config instead of reading from `LiteLLMClient.config`.
5. Pending operation preview/apply semantics remain unchanged.

## Consequences

### Positive

* The active Coach surface is no longer on the old chatbot runtime.
* CrewAI has a direct provider configuration path.
* Remaining LiteLLM exit work becomes narrower and more mechanical.

### Negative

* Two chat/runtime implementations coexist temporarily in the repo:
  * new Coach path
  * old `rps_chatbot` path for any remaining legacy consumers

### Follow-up

* Remove remaining product/runtime uses of LiteLLM and the old chat/runtime helpers.
