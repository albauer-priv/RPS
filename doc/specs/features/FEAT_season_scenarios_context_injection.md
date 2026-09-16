---
Status: Implemented
Version: 1.0
Last-Updated: 2026-09-16
---
# FEAT_season_scenarios_context_injection

## Problem

`create_season_scenarios` pre-loads all required workspace artifacts before launching the crew
(`athlete_profile`, `planning_events`, `logistics`, `availability`, `kpi_profile`, `wellness`,
historical baseline, evidence). These are used to build summary blocks injected into `user_input`.
However the same `user_input` string also instructs the LLM:

> "Use workspace_get_input for Athlete Profile, Planning Events, and Logistics.
>  Use workspace_get_latest only for shared latest inputs Availability, KPI Profile, and Wellness."

So the LLM re-reads the same files a second time via tool calls during its run — one redundant
disk read + one LLM round-trip per tool. With guardrail retries each retry repeats these calls.

Meanwhile Season Plan, Phase, and Week tasks have already adopted the "injected context" pattern:
all workspace content is pre-loaded at the orchestrator level and passed into `user_input` /
`guardrail_runtime_context`, and task descriptions say "no workspace tools are available or needed".
Season Scenarios is the only remaining outlier.

## Goal

Move Season Scenarios onto the same injected-context pattern:

1. Serialize the pre-loaded artifacts as JSON blocks and inject them into `user_input` **before**
   the dynamic context blocks (horizon, evidence, recommendation) — maximizing the stable prefix
   OpenAI's automatic prefix caching can reuse across runs.
2. Remove the tool-call instructions from `user_input`.
3. Pass the pre-loaded artifact payloads into `guardrail_runtime_context` as `preloaded_inputs`
   so `_normalize_document` can resolve `planning_events_document` without a tool-call fallback.
4. Remove `workspace_get_input` / `workspace_get_latest` from the `season_scenarios` task in
   `tasks.yaml` and add the standard "injected context" note to the description.

## Non-Goals

- No application-level Python cache in `workspace_read_tools.py`.
- `season_scenario_selection` is not changed (short operation, minimal tool call overhead).
- No new module or ADR (continuation of the established injection pattern).

## Prompt Order for Provider Prefix Caching

```
[Agent Instructions]            ← static, always cached
[Skill Content]                 ← static, always cached
[Athlete Profile JSON]          ← semi-static (rarely changes)
[Planning Events JSON]          ← semi-static
[Logistics + Availability JSON] ← semi-static
[KPI Profile + Wellness JSON]   ← semi-static
[Season Horizon Block]          ← dynamic (per run/week)
[Cadence + Evidence Blocks]     ← dynamic
[Scenario Recommendation]       ← dynamic
[User Request + Year/Week]      ← dynamic
```

Everything up to and including the athlete inputs is a stable prefix OpenAI caches when no
input data changes between runs.

## Files Changed

- `src/rps/orchestrator/season_flow.py` — inject pre-loaded artifacts; remove tool-call instructions; add `preloaded_inputs` to `guardrail_runtime_context`
- `src/rps/agents/crewai_task_execution.py` — fallback in `_normalize_document` to `preloaded_inputs` from context when `loaded_inputs` has no `planning_events`
- `config/crewai/tasks.yaml` — remove tools from `season_scenarios`; add injection note to description
