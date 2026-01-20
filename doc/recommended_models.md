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
| Macro-Planner | gpt-4.1 | `OPENAI_MODEL_MACRO_PLANNER` |
| Meso-Architect | gpt-4.1 | `OPENAI_MODEL_MESO_ARCHITECT` |
| Micro-Planner | gpt-4.1-mini | `OPENAI_MODEL_MICRO_PLANNER` |
| Workout-Builder | gpt-4.1-mini | `OPENAI_MODEL_WORKOUT_BUILDER` |
| Performance-Analyst | gpt-4.1 | `OPENAI_MODEL_PERFORMANCE_ANALYSIS` |

Example `.env` snippet:

```
OPENAI_MODEL=gpt-4.1
OPENAI_MODEL_MICRO_PLANNER=gpt-4.1-mini
OPENAI_MODEL_WORKOUT_BUILDER=gpt-4.1-mini
```

---

## Notes

- Per-agent overrides are optional; unset values fall back to `OPENAI_MODEL`.
- Keep heavier models for Macro/Meso/Analysis if schema errors rise.

---

## End
