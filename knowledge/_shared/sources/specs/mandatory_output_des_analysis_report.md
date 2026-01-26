# Mandatory Output Chapter

Purpose
This chapter defines how to produce **schema‑valid DES_ANALYSIS_REPORT JSON**.

---

## ARTIFACT: DES_ANALYSIS_REPORT

### WHICH SCHEMA TO USE AND HOW TO FIND
- Schema: `des_analysis_report.schema.json`
  - Filter: `{"type":"eq","key":"schema_id","value":"des_analysis_report.schema.json"}`
- You MUST validate output against this schema before calling `store_des_analysis_report`.

### HOW TO FILL (BINDING)

#### 1) Envelope (top‑level)
- Output MUST be a **top‑level object** with only:
  - `meta`
  - `data`

#### 2) `meta` (required fields)
- Must satisfy `artefact_meta.schema.json`.
- Required constants:
  - `artifact_type`: `"DES_ANALYSIS_REPORT"`
  - `schema_id`: `"DESAnalysisInterface"`
  - `schema_version`: `"1.1"`
  - `authority`: `"Binding"`
  - `owner_agent`: `"Performance-Analyst"`
- `iso_week` required.

#### 3) `data.summary_meta`
Required:
- `year` (int)
- `iso_week` (int)
- `run_id` (string)

#### 4) `data.kpi_summary`
Required objects:
- `durability`, `fatigue_resistance`, `fueling_stability`
Each must include:
- `status` (`green|yellow|red`)
- `confidence` (`high|medium|low`)
- `evidence_window` `{ "weeks": int >= 1 }`
- `delta_vs_baseline` (string)

#### 5) `data.weekly_analysis`
Required:
- `context.block_week` (int 1–4)
- `context.block_focus` (string)
- `signals` (array of `{metric, observation, confidence}`)
- `interpretation.summary` (string)

#### 6) `data.trend_analysis`
Required:
- `horizon_weeks` (int >= 1)
- `observations` (array of `{metric, trend, interpretation}`)
  - `trend` is `improving|stable|declining`

#### 7) `data.recommendation`
Required:
- `type`: const `advisory`
- `scope`: const `Macro-Planner`
- `urgency`: `low|medium|high`
- `rationale` (array, min 1)
- `suggested_considerations` (array, min 1)
- `explicitly_not`: array of exactly 2 items:
  - `direct_block_change`
  - `weekly_intervention`

#### 8) `data.narrative_report`
Required strings:
- `overview_current_status`
- `detailed_analysis_last_week`
- `trend_analysis_within_block`
- `trend_analysis_macro`
- `interpretation_recommendation`

#### 9) Validation & Stop (Binding)
- Use the store tool with a top-level `{ "meta": ..., "data": ... }` envelope only.
- Do NOT output raw JSON in chat; only the store tool call is allowed.
- Before output: confirm the Mandatory Output Chapter was read in full and followed exactly.
- Validate against `des_analysis_report.schema.json` before calling the store tool.
- If validation fails or any required field is missing/unknown: STOP.
- Do not use empty strings for required string fields (including citations). If required info is missing: STOP.
- Validate against schema before calling `store_des_analysis_report`.
- On any error: **STOP** and report schema errors.

---

### EXAMPLE: DES_ANALYSIS_REPORT (minimal valid)

```json
{
  "meta": {
    "artifact_type": "DES_ANALYSIS_REPORT",
    "schema_id": "DESAnalysisInterface",
    "schema_version": "1.1",
    "version": "1.0",
    "authority": "Binding",
    "owner_agent": "Performance-Analyst",
    "run_id": "example_des_report_2026_w04",
    "created_at": "2026-01-26T00:00:00Z",
    "scope": "Macro",
    "iso_week": "2026-04",
    "iso_week_range": "2026-04--2026-04",
    "temporal_scope": { "from": "2026-01-19", "to": "2026-01-25" },
    "trace_upstream": [],
    "trace_data": [],
    "trace_events": [],
    "notes": "Example only. Replace with real trace references."
  },
  "data": {
    "summary_meta": { "year": 2026, "iso_week": 4, "run_id": "example_des_report_2026_w04" },
    "kpi_summary": {
      "durability": { "status": "yellow", "confidence": "medium", "evidence_window": { "weeks": 2 }, "delta_vs_baseline": "Slightly below baseline." },
      "fatigue_resistance": { "status": "green", "confidence": "medium", "evidence_window": { "weeks": 2 }, "delta_vs_baseline": "Stable." },
      "fueling_stability": { "status": "green", "confidence": "low", "evidence_window": { "weeks": 2 }, "delta_vs_baseline": "Not evaluated." }
    },
    "weekly_analysis": {
      "context": { "block_week": 1, "block_focus": "Base" },
      "signals": [
        { "metric": "work_kj", "observation": "Below target range", "confidence": "medium" }
      ],
      "interpretation": { "summary": "Low weekly load relative to corridor." }
    },
    "trend_analysis": {
      "horizon_weeks": 4,
      "observations": [
        { "metric": "work_kj", "trend": "stable", "interpretation": "Stable recent weeks." }
      ]
    },
    "recommendation": {
      "type": "advisory",
      "scope": "Macro-Planner",
      "urgency": "medium",
      "rationale": ["Observe consistency and recovery."],
      "suggested_considerations": ["Review corridor fit for availability."],
      "explicitly_not": ["direct_block_change", "weekly_intervention"]
    },
    "narrative_report": {
      "overview_current_status": "Mixed signals, slight underload.",
      "detailed_analysis_last_week": "Last week load below corridor.",
      "trend_analysis_within_block": "Stable trend with minor fluctuations.",
      "trend_analysis_macro": "Macro trend stable.",
      "interpretation_recommendation": "Monitor and adjust only if pattern persists."
    }
  }
}
```
