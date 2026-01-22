---
Type: Template
Template-For: MACRO_OVERVIEW
Template-ID: MacroOverviewTemplate
Version: 1.1

Scope: Agent
Authority: Binding
Implements:
  Interface-ID: MacroOverviewInterface
  Version: 1.0

Owner-Agent: Macro-Planner
Dependencies:
  - Specification-ID: AgendaEnumSpec
    Version: 1.0
  - Specification-ID: LoadEstimationSpec
    Version: 1.0
Notes: >
  Schema-aligned blueprint for MACRO_OVERVIEW. Replace every <!--- FILL --->
  marker with concrete values before output.
---

# Macro Overview Template (Envelope)

Use this JSON envelope shape for `MACRO_OVERVIEW`. Fill all markers.

```json
{
  "meta": {
    "artifact_type": "MACRO_OVERVIEW",
    "schema_id": "MacroOverviewInterface",
    "schema_version": "1.0",
    "version": "1.0",
    "authority": "Binding",
    "owner_agent": "Macro-Planner",
    "run_id": "<!--- FILL --->",
    "created_at": "<!--- FILL --->",
    "scope": "Macro",
    "iso_week": "<!--- FILL --->",
    "iso_week_range": "<!--- FILL --->",
    "temporal_scope": {
      "from": "<!--- FILL --->",
      "to": "<!--- FILL --->"
    },
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
    "body_metadata": {
      "planning_horizon_weeks": 8,
      "season_brief_ref": "<!--- FILL --->",
      "kpi_profile_ref": "<!--- FILL --->",
      "body_mass_kg": 0,
      "reference_mass_window_kg": { "min": 0, "max": 0 },
      "moving_time_rate_guidance": {
        "segment": "<!--- FILL --->",
        "w_per_kg": { "min": 0, "max": 0 },
        "kj_per_kg_per_hour": { "min": 0, "max": 0 },
        "notes": "<!--- FILL --->"
      },
      "athlete_profile_ref": "<!--- FILL --->"
    },
    "macro_intent_principles": {
      "season_objective": "<!--- FILL --->",
      "success_definition": "event-focused",
      "non_negotiable_principles": ["<!--- FILL --->"],
      "kJ_corridor_design_notes": ["<!--- FILL --->"]
    },
    "phases": [
      {
        "phase_id": "<!--- FILL --->",
        "name": "<!--- FILL --->",
        "date_range": { "from": "<!--- FILL --->", "to": "<!--- FILL --->" },
        "iso_week_range": { "from": "<!--- FILL --->", "to": "<!--- FILL --->" },
        "cycle": "Base",
        "deload": false,
        "deload_rationale": "<!--- FILL --->",
        "reference_mass_window_kg": { "min": 0, "max": 0 },
        "narrative": "<!--- FILL --->",
        "overview": {
          "core_focus_and_characteristics": ["<!--- FILL --->"],
          "phase_goals": {
            "primary": "<!--- FILL --->",
            "secondary": "<!--- FILL --->"
          },
          "metabolic_focus": "<!--- FILL --->",
          "expected_adaptations": ["<!--- FILL --->"],
          "evaluation_focus": ["<!--- FILL --->"],
          "phase_exit_assumptions": ["<!--- FILL --->"],
          "typical_duration_intensity_pattern": "<!--- FILL --->",
          "non_negotiables": ["<!--- FILL --->"]
        },
        "weekly_load_corridor": {
          "weekly_kj": { "min": 0, "max": 0, "notes": "<!--- FILL --->", "per_kg": { "min": 0, "max": 0 } },
          "weekly_tss": { "min": 0, "max": 0, "notes": "<!--- FILL --->" }
        },
        "allowed_forbidden_semantics": {
          "allowed_intensity_domains": ["ENDURANCE"],
          "allowed_load_modalities": ["NONE"],
          "forbidden_intensity_domains": ["VO2MAX"]
        },
        "structural_emphasis": {
          "typical_focus": "<!--- FILL --->",
          "not_emphasized": "<!--- FILL --->"
        },
        "events_constraints": [],
        "deload_rationale": "<!--- FILL --->"
      }
    ],
    "global_constraints": {
      "availability_assumptions": ["<!--- FILL --->"],
      "risk_constraints": ["<!--- FILL --->"],
      "planned_event_windows": ["<!--- FILL --->"],
      "recovery_protection": {
        "fixed_rest_days": ["Mon"],
        "notes": ["<!--- FILL --->"]
      }
    },
    "season_load_envelope": {
      "expected_average_weekly_kj_range": { "min": 0, "max": 0 },
      "expected_high_load_weeks_count": 0,
      "expected_deload_or_low_load_weeks_count": 0
    },
    "assumptions_unknowns": {
      "assumptions": ["<!--- FILL --->"],
      "uncertainties": ["<!--- FILL --->"],
      "revisit_items": ["<!--- FILL --->"]
    },
    "phase_transitions_guardrails": {
      "expected_progression": "<!--- FILL --->",
      "conservative_triggers": ["<!--- FILL --->"],
      "absolute_no_go_rules": ["<!--- FILL --->"]
    },
    "justification": {
      "summary": "<!--- FILL --->",
      "citations": [
        {
          "source_type": "principles",
          "source_id": "<!--- FILL --->",
          "section": "<!--- FILL --->",
          "rationale": "<!--- FILL --->"
        }
      ],
      "phase_justifications": [
        {
          "phase_id": "<!--- FILL --->",
          "intensity_distribution": "<!--- FILL --->",
          "overload_pattern": "<!--- FILL --->",
          "kJ_first_statement": "<!--- FILL --->",
          "citations": ["<!--- FILL --->"]
        }
      ]
    },
    "principles_scientific_foundation": {
      "principle_applications": [
        { "principle": "<!--- FILL --->", "influence": "<!--- FILL --->" }
      ],
      "scientific_foundation": {
        "publications": [
          { "authors": "<!--- FILL --->", "year": 2000, "title": "<!--- FILL --->", "link": "<!--- FILL --->" }
        ],
        "plan_alignment_check": "<!--- FILL --->",
        "rationale": "<!--- FILL --->"
      }
    },
    "explicit_forbidden_content": [
      "block definitions (4-week plans)",
      "weekly schedules",
      "day-by-day structure",
      "workouts or interval prescriptions",
      "numeric progression rules",
      "daily or session-level kJ/TSS targets"
    ],
    "self_check": {
      "planning_horizon_is_at_least_8_weeks": true,
      "every_phase_defines_weekly_kj_corridor": true,
      "every_phase_includes_kj_per_kg_guardrails_and_reference_mass": true,
      "every_phase_maps_to_cycle_and_deload_intent": true,
      "every_phase_includes_narrative_and_metabolic_focus": true,
      "every_phase_includes_evaluation_focus_and_exit_assumptions": true,
      "season_load_envelope_and_assumptions_documented": true,
      "principles_and_scientific_foundation_documented": true,
      "allowed_forbidden_domains_listed": true,
      "no_meso_or_micro_planning_content": true,
      "header_includes_implements_iso_week_range_trace": true
    }
  }
}
```
