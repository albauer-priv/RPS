---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-06
Owner: Overview
---
# Recommended Models

Version: 2.0  
Status: Updated  
Last-Updated: 2026-02-06

---

## Cost-Optimized Profile (Current)

The runtime uses `RPS_LLM_MODEL` as the default and allows **per-agent overrides**
via `RPS_LLM_MODEL_<AGENT>` (see table below).

**Recommended cost-optimized defaults**

| Component / Agent | Recommended | Env Override |
| --- | --- | --- |
| Data Pipeline (scripts) | N/A | No model usage. |
| Season-Planner | gpt-4.1 | `RPS_LLM_MODEL_SEASON_PLANNER` |
| Phase-Architect | gpt-4.1 | `RPS_LLM_MODEL_PHASE_ARCHITECT` |
| Week-Planner | gpt-4.1-mini | `RPS_LLM_MODEL_WEEK_PLANNER` |
| Workout-Builder | gpt-4.1-mini | `RPS_LLM_MODEL_WORKOUT_BUILDER` |
| Performance-Analyst | gpt-4.1 | `RPS_LLM_MODEL_PERFORMANCE_ANALYSIS` |

Example `.env` snippet:

```
RPS_LLM_MODEL=gpt-4.1
RPS_LLM_MODEL_WEEK_PLANNER=gpt-4.1-mini
RPS_LLM_MODEL_WORKOUT_BUILDER=gpt-4.1-mini
```

---

## Temperature Overrides

Set a global temperature and (optionally) per-agent overrides:

```
RPS_LLM_TEMPERATURE=0.2
RPS_LLM_TEMPERATURE_SEASON_PLANNER=0.2
RPS_LLM_TEMPERATURE_PHASE_ARCHITECT=0.2
RPS_LLM_TEMPERATURE_WEEK_PLANNER=0.2
RPS_LLM_TEMPERATURE_WORKOUT_BUILDER=0.2
RPS_LLM_TEMPERATURE_PERFORMANCE_ANALYSIS=0.3
```

Lower values reduce creative variance for schema-heavy outputs.

---

## Notes

- Per-agent overrides are optional; unset values fall back to `RPS_LLM_MODEL` / `RPS_LLM_TEMPERATURE`.
- Keep heavier models for Season/Phase/Analysis if schema errors rise.
- For Season Mode A scenarios, keep `--max-num-results 1` to limit token throughput.
- Set `RPS_LLM_EMBEDDING_MODEL` to match your provider’s embedding model for vectorstore sync.

---

## End
