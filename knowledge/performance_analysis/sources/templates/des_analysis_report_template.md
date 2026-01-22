---
Type: Template
Template-For: DES_ANALYSIS_REPORT
Template-ID: DESAnalysisReportTemplate
Version: 1.0

Scope: Agent
Authority: Binding
Implements:
  Interface-ID: DESAnalysisInterface
  Version: 1.1

Owner-Agent: Performance-Analyst
Notes: >
  Schema-aligned blueprint for DES_ANALYSIS_REPORT. Replace every <!--- FILL --->
  marker with concrete values before output.
---

# DES Analysis Report Template (Envelope)

```json
{
  "meta": {
    "artifact_type": "DES_ANALYSIS_REPORT",
    "schema_id": "DESAnalysisInterface",
    "schema_version": "1.1",
    "version": "1.0",
    "authority": "Binding",
    "owner_agent": "Performance-Analyst",
    "run_id": "<!--- FILL --->",
    "created_at": "<!--- FILL --->",
    "scope": "Analysis",
    "iso_week": "<!--- FILL --->",
    "trace_upstream": [
      {
        "artifact": "<!--- FILL --->",
        "version": "<!--- FILL --->",
        "run_id": "<!--- FILL --->"
      }
    ],
    "trace_data": [],
    "trace_events": [],
    "notes": "<!--- FILL --->"
  },
  "data": {
    "summary_meta": {
      "year": 2000,
      "iso_week": 1,
      "run_id": "<!--- FILL --->"
    },
    "kpi_summary": {
      "durability": {
        "status": "green",
        "confidence": "high",
        "evidence_window": { "weeks": 1 },
        "delta_vs_baseline": "<!--- FILL --->"
      },
      "fatigue_resistance": {
        "status": "green",
        "confidence": "high",
        "evidence_window": { "weeks": 1 },
        "delta_vs_baseline": "<!--- FILL --->"
      },
      "fueling_stability": {
        "status": "green",
        "confidence": "high",
        "evidence_window": { "weeks": 1 },
        "delta_vs_baseline": "<!--- FILL --->"
      }
    },
    "weekly_analysis": {
      "context": {
        "block_week": 1,
        "block_focus": "<!--- FILL --->"
      },
      "signals": [
        { "metric": "<!--- FILL --->", "observation": "<!--- FILL --->", "confidence": "medium" }
      ],
      "interpretation": {
        "summary": "<!--- FILL --->"
      }
    },
    "trend_analysis": {
      "horizon_weeks": 1,
      "observations": [
        { "metric": "<!--- FILL --->", "trend": "stable", "interpretation": "<!--- FILL --->" }
      ]
    },
    "recommendation": {
      "type": "advisory",
      "scope": "Macro-Planner",
      "urgency": "low",
      "rationale": ["<!--- FILL --->"],
      "suggested_considerations": ["<!--- FILL --->"],
      "explicitly_not": ["direct_block_change", "weekly_intervention"]
    },
    "narrative_report": {
      "overview_current_status": "<!--- FILL --->",
      "detailed_analysis_last_week": "<!--- FILL --->",
      "trend_analysis_within_block": "<!--- FILL --->",
      "trend_analysis_macro": "<!--- FILL --->",
      "interpretation_recommendation": "<!--- FILL --->"
    }
  }
}
```
