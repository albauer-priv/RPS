---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: Overview
---
# Recommended Models

Version: 2.0  
Status: Updated  
Last-Updated: 2026-01-20

---

## Cost-Optimized Profile (Current)

The runtime uses `OPENAI_MODEL` as the default and allows **per-agent overrides**
via `OPENAI_MODEL_<AGENT>` (see table below).

**Recommended cost-optimized defaults**

| Component / Agent | Recommended | Env Override |
| --- | --- | --- |
| Data Pipeline (scripts) | N/A | No model usage. |
| Season-Planner | gpt-4.1 | `OPENAI_MODEL_SEASON_PLANNER` |
| Phase-Architect | gpt-4.1 | `OPENAI_MODEL_PHASE_ARCHITECT` |
| Week-Planner | gpt-4.1-mini | `OPENAI_MODEL_WEEK_PLANNER` |
| Workout-Builder | gpt-4.1-mini | `OPENAI_MODEL_WORKOUT_BUILDER` |
| Performance-Analyst | gpt-4.1 | `OPENAI_MODEL_PERFORMANCE_ANALYSIS` |

Example `.env` snippet:

```
OPENAI_MODEL=gpt-4.1
OPENAI_MODEL_WEEK_PLANNER=gpt-4.1-mini
OPENAI_MODEL_WORKOUT_BUILDER=gpt-4.1-mini
```

---

## Temperature Overrides

Set a global temperature and (optionally) per-agent overrides:

```
OPENAI_TEMPERATURE=0.2
OPENAI_TEMPERATURE_SEASON_PLANNER=0.2
OPENAI_TEMPERATURE_PHASE_ARCHITECT=0.2
OPENAI_TEMPERATURE_WEEK_PLANNER=0.2
OPENAI_TEMPERATURE_WORKOUT_BUILDER=0.2
OPENAI_TEMPERATURE_PERFORMANCE_ANALYSIS=0.3
```

Lower values reduce creative variance for schema-heavy outputs.

---

## Notes

- Per-agent overrides are optional; unset values fall back to `OPENAI_MODEL` / `OPENAI_TEMPERATURE`.
- Keep heavier models for Season/Phase/Analysis if schema errors rise.
- For Season Mode A scenarios, keep `--max-num-results 1` to limit token throughput.

---

## End
