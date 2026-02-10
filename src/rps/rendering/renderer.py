"""Render JSON artifacts to human-readable Markdown sidecars."""

from __future__ import annotations

import json
import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from rps.workspace.schema_registry import SchemaRegistry, validate_or_raise

REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_DIR = Path(__file__).parent / "templates"

RENDERERS = {
    "SEASON_PLAN": "season_plan.md.j2",
    "PHASE_GUARDRAILS": "phase_guardrails.md.j2",
    "PHASE_STRUCTURE": "phase_structure.md.j2",
    "PHASE_PREVIEW": "phase_preview.md.j2",
    "PHASE_FEED_FORWARD": "phase_feed_forward.md.j2",
    "SEASON_PHASE_FEED_FORWARD": "season_phase_feed_forward.md.j2",
    "DES_ANALYSIS_REPORT": "des_analysis_report.md.j2",
    "ACTIVITIES_ACTUAL": "activities_actual.md.j2",
    "ACTIVITIES_TREND": "activities_trend.md.j2",
    "ZONE_MODEL": "zone_model.md.j2",
    "WEEK_PLAN": "week_plan.md.j2",
    "KPI_PROFILE": "kpi_profile.md.j2",
    "AVAILABILITY": "availability.md.j2",
    "WELLNESS": "wellness.md.j2",
}

SCHEMA_FILES = {
    "SEASON_PLAN": "season_plan.schema.json",
    "PHASE_GUARDRAILS": "phase_guardrails.schema.json",
    "PHASE_STRUCTURE": "phase_structure.schema.json",
    "PHASE_PREVIEW": "phase_preview.schema.json",
    "PHASE_FEED_FORWARD": "phase_feed_forward.schema.json",
    "SEASON_PHASE_FEED_FORWARD": "season_phase_feed_forward.schema.json",
    "DES_ANALYSIS_REPORT": "des_analysis_report.schema.json",
    "ACTIVITIES_ACTUAL": "activities_actual.schema.json",
    "ACTIVITIES_TREND": "activities_trend.schema.json",
    "ZONE_MODEL": "zone_model.schema.json",
    "WEEK_PLAN": "week_plan.schema.json",
    "KPI_PROFILE": "kpi_profile.schema.json",
    "AVAILABILITY": "availability.schema.json",
    "WELLNESS": "wellness.schema.json",
}

SELF_CHECK_LABELS = {
    "planning_horizon_is_at_least_8_weeks": "Planning horizon is >=8 weeks",
    "every_phase_defines_weekly_kj_corridor": "Every phase defines a weekly kJ corridor",
    "every_phase_includes_kj_per_kg_guardrails_and_reference_mass": (
        "Every phase includes kJ/kg guardrails and a reference mass window"
    ),
    "every_phase_maps_to_cycle_and_deload_intent": "Every phase maps to a cycle and declares deload intent",
    "every_phase_includes_narrative_and_metabolic_focus": "Every phase includes a narrative and metabolic focus",
    "every_phase_includes_evaluation_focus_and_exit_assumptions": (
        "Every phase includes evaluation focus and exit assumptions"
    ),
    "season_load_envelope_and_assumptions_documented": (
        "Season load envelope and explicit assumptions are documented"
    ),
    "principles_and_scientific_foundation_documented": (
        "Principles and scientific foundation are documented"
    ),
    "allowed_forbidden_domains_listed": "Allowed / forbidden domains are explicitly listed",
    "no_phase_or_week_planning_content": "No phase or week planning content exists",
    "header_includes_implements_iso_week_range_trace": (
        "Header includes Implements, ISO-Week-Range, and Trace-Upstream"
    ),
}


def load_json(path: Path):
    """Load JSON from disk."""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def fmt_number(value):
    """Format numeric values for display."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def fmt_range(range_obj):
    """Format min/max ranges for display."""
    if not range_obj:
        return "N/A"
    min_val = range_obj.get("min")
    max_val = range_obj.get("max")
    if min_val is None or max_val is None:
        return "N/A"
    return f"{fmt_number(min_val)}-{fmt_number(max_val)}"


def fmt_date_range(range_obj):
    """Format date ranges for display."""
    if not range_obj:
        return "N/A"
    start = range_obj.get("from") or range_obj.get("start")
    end = range_obj.get("to") or range_obj.get("end")
    if not start or not end:
        return "N/A"
    return f"{start} to {end}"


def fmt_bool(value):
    """Format booleans as Yes/No."""
    return "Yes" if value else "No"


def fmt_bool_upper(value):
    """Format booleans as TRUE/FALSE."""
    if value is True:
        return "TRUE"
    if value is False:
        return "FALSE"
    return ""


def join_or_na(items):
    """Join list values or return N/A."""
    if not items:
        return "N/A"
    return ", ".join(items)


def format_trace_list(entries):
    """Format trace entries for rendering."""
    if not entries:
        return ["N/A"]
    formatted = []
    for entry in entries:
        if isinstance(entry, str):
            formatted.append(entry)
            continue
        if not isinstance(entry, dict):
            continue
        text = entry.get("artifact") or ""
        version = entry.get("version")
        run_id = entry.get("run_id")
        if version:
            text += f"@{version}"
        if run_id:
            text += f"#{run_id}"
        if text:
            formatted.append(text)
    return formatted or ["N/A"]


def validate_document(doc, artifact_type, schema_dir):
    """Validate a document against its schema."""
    schema_file = SCHEMA_FILES.get(artifact_type)
    if not schema_file:
        raise ValueError(f"No schema mapping for {artifact_type}.")

    registry = SchemaRegistry(schema_dir)
    validator = registry.validator_for(schema_file)
    validate_or_raise(validator, doc)


def build_season_plan_context(doc):
    """Build context for season plan rendering."""
    meta = doc.get("meta", {})
    data = doc.get("data", {})

    body = data.get("body_metadata", {})
    season_intent = data.get("season_intent_principles", {})

    phases = []
    for phase in data.get("phases", []):
        overview = phase.get("overview", {})
        weekly_kj = phase.get("weekly_load_corridor", {}).get("weekly_kj")
        semantics = phase.get("allowed_forbidden_semantics", {})
        phases.append(
            {
                "phase_id": phase.get("phase_id", ""),
                "name": phase.get("name", ""),
                "date_range": fmt_date_range(phase.get("date_range")),
                "iso_week_range": phase.get("iso_week_range", ""),
                "cycle": phase.get("cycle", ""),
                "deload": fmt_bool(phase.get("deload")),
                "deload_rationale": phase.get("deload_rationale"),
                "narrative": phase.get("narrative", ""),
                "overview": {
                    "core_focus_and_characteristics": overview.get(
                        "core_focus_and_characteristics", []
                    ),
                    "phase_goals_primary": overview.get("phase_goals", {}).get("primary", ""),
                    "phase_goals_secondary": overview.get("phase_goals", {}).get("secondary"),
                    "metabolic_focus": overview.get("metabolic_focus", ""),
                    "expected_adaptations": overview.get("expected_adaptations", []),
                    "evaluation_focus": overview.get("evaluation_focus", []),
                    "phase_exit_assumptions": overview.get("phase_exit_assumptions", []),
                    "typical_duration_intensity_pattern": overview.get(
                        "typical_duration_intensity_pattern", ""
                    ),
                    "non_negotiables": overview.get("non_negotiables", []),
                },
                "weekly_kj": weekly_kj or {},
                "allowed_intensity_domains": semantics.get("allowed_intensity_domains", []),
                "allowed_load_modalities": semantics.get("allowed_load_modalities", []),
                "forbidden_intensity_domains": semantics.get("forbidden_intensity_domains", []),
                "structural_emphasis": {
                    "typical_focus": phase.get("structural_emphasis", {}).get("typical_focus", ""),
                    "not_emphasized": phase.get("structural_emphasis", {}).get("not_emphasized", ""),
                },
                "events_constraints": phase.get("events_constraints", []),
            }
        )

    self_check = []
    for key, label in SELF_CHECK_LABELS.items():
        self_check.append(
            {
                "label": label,
                "value": bool(data.get("self_check", {}).get(key)),
            }
        )

    context = {
        "meta": meta,
        "trace_upstream": format_trace_list(meta.get("trace_upstream")),
        "trace_data": format_trace_list(meta.get("trace_data")),
        "trace_events": format_trace_list(meta.get("trace_events")),
        "body_metadata": {
            "planning_horizon_weeks": body.get("planning_horizon_weeks"),
            "kpi_profile_ref": body.get("kpi_profile_ref"),
            "athlete_profile_ref": body.get("athlete_profile_ref"),
            "body_mass_kg": body.get("body_mass_kg"),
            "moving_time_rate_guidance": {
                "segment": (body.get("moving_time_rate_guidance") or {}).get("segment"),
                "w_per_kg": fmt_range(
                    (body.get("moving_time_rate_guidance") or {}).get("w_per_kg")
                ),
                "kj_per_kg_per_hour": fmt_range(
                    (body.get("moving_time_rate_guidance") or {}).get(
                        "kj_per_kg_per_hour"
                    )
                ),
                "notes": (body.get("moving_time_rate_guidance") or {}).get("notes"),
            },
        },
        "season_intent": {
            "season_objective": season_intent.get("season_objective"),
            "success_definition": season_intent.get("success_definition"),
            "non_negotiable_principles": season_intent.get("non_negotiable_principles", []),
            "kj_corridor_design_notes": season_intent.get("kJ_corridor_design_notes", []),
        },
        "phases": phases,
        "global_constraints": {
            "availability_assumptions": data.get("global_constraints", {}).get(
                "availability_assumptions", []
            ),
            "planned_event_windows": data.get("global_constraints", {}).get(
                "planned_event_windows", []
            ),
            "risk_constraints": data.get("global_constraints", {}).get("risk_constraints", []),
        },
        "season_load_envelope": {
            "expected_average_weekly_kj_range": fmt_range(
                data.get("season_load_envelope", {}).get("expected_average_weekly_kj_range")
            ),
            "expected_high_load_weeks_count": data.get("season_load_envelope", {}).get(
                "expected_high_load_weeks_count"
            ),
            "expected_deload_or_low_load_weeks_count": data.get("season_load_envelope", {}).get(
                "expected_deload_or_low_load_weeks_count"
            ),
        },
        "assumptions_unknowns": {
            "assumptions": data.get("assumptions_unknowns", {}).get("assumptions", []),
            "uncertainties": data.get("assumptions_unknowns", {}).get("uncertainties", []),
            "revisit_items": data.get("assumptions_unknowns", {}).get("revisit_items", []),
        },
        "phase_transitions_guardrails": {
            "expected_progression": data.get("phase_transitions_guardrails", {}).get(
                "expected_progression"
            ),
            "conservative_triggers": data.get("phase_transitions_guardrails", {}).get(
                "conservative_triggers", []
            ),
            "absolute_no_go_rules": data.get("phase_transitions_guardrails", {}).get(
                "absolute_no_go_rules", []
            ),
        },
        "principles_scientific_foundation": {
            "principle_applications": data.get("principles_scientific_foundation", {}).get(
                "principle_applications", []
            ),
            "scientific_foundation": data.get("principles_scientific_foundation", {}).get(
                "scientific_foundation", {}
            ),
        },
        "explicit_forbidden_content": data.get("explicit_forbidden_content", []),
        "self_check": self_check,
    }
    return context


def build_phase_guardrails_context(doc):
    """Build context for phase guardrails rendering."""
    meta = doc.get("meta", {})
    data = doc.get("data", {})
    body_metadata = data.get("body_metadata", {})
    phase_summary = data.get("phase_summary", {})
    load_guardrails = data.get("load_guardrails", {})
    confidence_assumptions = load_guardrails.get("confidence_assumptions", {})
    semantics = data.get("allowed_forbidden_semantics", {})
    quality_density = semantics.get("quality_density", {})
    execution_non_negotiables = data.get("execution_non_negotiables", {})
    escalation_change_control = data.get("escalation_change_control", {})
    required_response = escalation_change_control.get("required_response", {})
    self_check = data.get("self_check", {})

    def weekly_band_rows(entries):
        """Normalize weekly load band entries into row-friendly data."""
        rows = []
        for entry in entries or []:
            band = entry.get("band", {})
            rows.append(
                {
                    "week": entry.get("week", ""),
                    "min": fmt_number(band.get("min")),
                    "max": fmt_number(band.get("max")),
                    "notes": band.get("notes", ""),
                }
            )
        return rows

    events = []
    for event in data.get("events_constraints", {}).get("events", []):
        events.append(
            {
                "date": event.get("date", ""),
                "week": event.get("week", ""),
                "type": event.get("type", ""),
                "constraint": event.get("constraint", ""),
            }
        )

    context = {
        "meta": meta,
        "trace_upstream": format_trace_list(meta.get("trace_upstream")),
        "trace_data": format_trace_list(meta.get("trace_data")),
        "trace_events": format_trace_list(meta.get("trace_events")),
        "body_metadata": {
            "phase_id": body_metadata.get("phase_id", ""),
            "phase_type": body_metadata.get("phase_type", ""),
            "phase_status": body_metadata.get("phase_status", ""),
            "change_type": body_metadata.get("change_type", ""),
            "derived_from": body_metadata.get("derived_from"),
            "upstream_inputs": body_metadata.get("upstream_inputs", []),
        },
        "phase_summary": {
            "primary_objective": phase_summary.get("primary_objective", ""),
            "secondary_objectives": phase_summary.get("secondary_objectives", []),
            "key_risks_warnings": phase_summary.get("key_risks_warnings", []),
            "non_negotiables": phase_summary.get("non_negotiables", []),
        },
        "weekly_kj_bands": weekly_band_rows(
            load_guardrails.get("weekly_kj_bands", [])
        ),
        "confidence_assumptions": {
            "ftp_watts_used": confidence_assumptions.get("ftp_watts_used"),
            "zone_model_version": confidence_assumptions.get("zone_model_version"),
            "kj_estimation_method": confidence_assumptions.get("kj_estimation_method"),
            "confidence": confidence_assumptions.get("confidence", {}),
        },
        "allowed_forbidden_semantics": {
            "allowed_day_roles": semantics.get("allowed_day_roles", []),
            "forbidden_day_roles": semantics.get("forbidden_day_roles", []),
            "allowed_intensity_domains": semantics.get("allowed_intensity_domains", []),
            "forbidden_intensity_domains": semantics.get("forbidden_intensity_domains", []),
            "allowed_load_modalities": semantics.get("allowed_load_modalities", []),
            "forbidden_load_modalities": semantics.get("forbidden_load_modalities", []),
            "quality_density": {
                "max_quality_days_per_week": fmt_number(
                    quality_density.get("max_quality_days_per_week")
                ),
                "quality_intent": quality_density.get("quality_intent"),
                "forbidden_patterns": quality_density.get("forbidden_patterns", []),
            },
        },
        "events": events,
        "logistics": data.get("events_constraints", {}).get(
            "logistics_time_constraints", {}
        ),
        "execution_non_negotiables": {
            "recovery_protection_rules": execution_non_negotiables.get(
                "recovery_protection_rules", ""
            ),
            "long_endurance_anchor_protection": execution_non_negotiables.get(
                "long_endurance_anchor_protection", ""
            ),
            "minimum_recovery_opportunities": execution_non_negotiables.get(
                "minimum_recovery_opportunities", ""
            ),
            "no_catch_up_rule": execution_non_negotiables.get("no_catch_up_rule", ""),
        },
        "escalation_change_control": {
            "warning_signals": escalation_change_control.get("warning_signals", []),
            "required_response": {
                "week_planner_must": required_response.get("week_planner_must", []),
                "week_planner_must_not": required_response.get(
                    "week_planner_must_not", []
                ),
                "phase_architect_decides": required_response.get(
                    "phase_architect_decides", ""
                ),
            },
        },
        "explicit_forbidden_content": data.get("explicit_forbidden_content", []),
        "self_check": {
            "weekly_kj_bands_present": bool(self_check.get("weekly_kj_bands_present")),
            "max_quality_days_specified": bool(self_check.get("max_quality_days_specified")),
            "allowed_forbidden_enums_specified": bool(
                self_check.get("allowed_forbidden_enums_specified")
            ),
            "no_week_planning_content": bool(self_check.get("no_week_planning_content")),
            "header_includes_implements_iso_week_range_trace": bool(
                self_check.get("header_includes_implements_iso_week_range_trace")
            ),
        },
    }
    return context


def build_week_plan_context(doc):
    """Build context for week plan rendering."""
    meta = doc.get("meta", {})
    data = doc.get("data", {})

    week_summary = data.get("week_summary", {})
    load_corridor = week_summary.get("weekly_load_corridor_kj", {})

    agenda_rows = []
    for row in data.get("agenda", []):
        agenda_rows.append(
            {
                "day": row.get("day", ""),
                "date": row.get("date", ""),
                "day_role": row.get("day_role", ""),
                "planned_duration": row.get("planned_duration", ""),
                "planned_kj": fmt_number(row.get("planned_kj")),
                "workout_id": row.get("workout_id") or "",
            }
        )
    day_order = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
    agenda_rows.sort(key=lambda entry: day_order.get(entry.get("day", ""), 99))

    workouts = []
    for workout in data.get("workouts", []):
        workouts.append(
            {
                "workout_id": workout.get("workout_id", ""),
                "title": workout.get("title", ""),
                "notes": workout.get("notes") or "",
                "date": workout.get("date", ""),
                "start": workout.get("start", ""),
                "duration": workout.get("duration", ""),
                "workout_text": workout.get("workout_text", ""),
            }
        )

    context = {
        "meta": meta,
        "trace_upstream": format_trace_list(meta.get("trace_upstream")),
        "trace_data": format_trace_list(meta.get("trace_data")),
        "trace_events": format_trace_list(meta.get("trace_events")),
        "week_summary": {
            "week_objective": week_summary.get("week_objective", ""),
            "weekly_load_corridor_kj": {
                "min": fmt_number(load_corridor.get("min")),
                "max": fmt_number(load_corridor.get("max")),
                "notes": load_corridor.get("notes", ""),
            },
            "planned_weekly_load_kj": fmt_number(week_summary.get("planned_weekly_load_kj")),
            "notes": week_summary.get("notes", ""),
        },
        "agenda": agenda_rows,
        "workouts": workouts,
    }
    return context


def build_phase_structure_context(doc):
    """Build context for phase structure rendering."""
    meta = doc.get("meta", {})
    data = doc.get("data", {})

    upstream_intent = data.get("upstream_intent", {})
    execution_principles = data.get("execution_principles", {})
    load_intensity = execution_principles.get("load_intensity_handling", {})
    recovery_protection = execution_principles.get("recovery_protection", {})
    consistency = execution_principles.get("consistency_over_optimization", {})
    structural = data.get("structural_phase_elements", {})
    week_skeleton = data.get("week_skeleton_logic", {})
    week_roles = week_skeleton.get("week_roles", {})
    mandatory_elements = week_skeleton.get("mandatory_elements", {})
    optional_elements = week_skeleton.get("optional_elements", {})
    quality_days = optional_elements.get("quality_days", {})
    optional_flex_days = optional_elements.get("optional_flex_days", {})
    relationships = data.get("relationships", {})
    self_check = data.get("self_check", {})

    context = {
        "meta": meta,
        "trace_upstream": format_trace_list(meta.get("trace_upstream")),
        "trace_data": format_trace_list(meta.get("trace_data")),
        "trace_events": format_trace_list(meta.get("trace_events")),
        "upstream_intent": {
            "phase_type": upstream_intent.get("phase_type", ""),
            "primary_objective": upstream_intent.get("primary_objective", ""),
            "phase_status": upstream_intent.get("phase_status", ""),
            "non_negotiables": upstream_intent.get("non_negotiables", []),
            "constraints": upstream_intent.get("constraints", []),
            "key_risks_warnings": upstream_intent.get("key_risks_warnings", []),
        },
        "execution_principles": {
            "load_intensity_handling": {
                "max_quality_days_per_week": fmt_number(
                    load_intensity.get("max_quality_days_per_week")
                ),
                "quality_intent": load_intensity.get("quality_intent"),
                "allowed_intensity_domains": load_intensity.get(
                    "allowed_intensity_domains", []
                ),
                "forbidden_intensity_domains": load_intensity.get(
                    "forbidden_intensity_domains", []
                ),
                "load_modality_constraints": load_intensity.get(
                    "load_modality_constraints", []
                ),
            },
            "recovery_protection": {
                "fixed_non_training_days": recovery_protection.get(
                    "fixed_non_training_days", []
                ),
                "mandatory_recovery_spacing_rules": recovery_protection.get(
                    "mandatory_recovery_spacing_rules", []
                ),
                "forbidden_sequences": recovery_protection.get("forbidden_sequences", []),
                "long_endurance_anchor_protection": recovery_protection.get(
                    "long_endurance_anchor_protection", ""
                ),
            },
            "consistency_over_optimization": {
                "statements": consistency.get("statements", []),
            },
        },
        "structural_phase_elements": {
            "allowed_day_roles": structural.get("allowed_day_roles", []),
            "allowed_intensity_domains": structural.get("allowed_intensity_domains", []),
            "allowed_load_modalities": structural.get("allowed_load_modalities", []),
        },
        "week_skeleton_logic": {
            "week_roles": {
                "week_roles": (
                    week_roles.get("week_roles", [])
                    if isinstance(week_roles.get("week_roles"), list)
                    else []
                ),
                "allowed_role_set": week_roles.get("allowed_role_set", []),
            },
            "mandatory_elements": {
                "recovery_opportunities_min": fmt_number(
                    mandatory_elements.get("recovery_opportunities_min")
                ),
                "endurance_anchor_required": fmt_bool(
                    mandatory_elements.get("endurance_anchor_required")
                ),
            },
            "optional_elements": {
                "quality_days": {
                    "capped_by_upstream_limits": fmt_bool(
                        quality_days.get("capped_by_upstream_limits")
                    ),
                    "never_adjacent_unless_allowed": fmt_bool(
                        quality_days.get("never_adjacent_unless_allowed")
                    ),
                },
                "optional_flex_days": {
                    "removable_without_compensation": fmt_bool(
                        optional_flex_days.get("removable_without_compensation")
                    ),
                },
            },
            "forbidden_patterns": week_skeleton.get("forbidden_patterns", []),
        },
        "adaptation_rules": data.get("adaptation_rules", []),
        "relationships": {
            "guides": relationships.get("guides", []),
            "does_not_replace": relationships.get("does_not_replace", []),
        },
        "self_check": {
            "phase_status_respected": bool(self_check.get("phase_status_respected")),
            "phase_range_covered": bool(self_check.get("phase_range_covered")),
            "week_roles_defined_for_phase_range": bool(
                self_check.get("week_roles_defined_for_phase_range")
            ),
            "no_new_decision_introduced": bool(self_check.get("no_new_decision_introduced")),
            "no_numeric_target_introduced": bool(self_check.get("no_numeric_target_introduced")),
            "no_kpi_gate_inferred": bool(self_check.get("no_kpi_gate_inferred")),
        },
    }
    return context


def build_phase_preview_context(doc):
    """Build context for phase preview rendering."""
    meta = doc.get("meta", {})
    data = doc.get("data", {})

    phase_intent_summary = data.get("phase_intent_summary", {})
    feel_overview = data.get("feel_overview", {})

    week_previews = []
    day_order = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
    for week in data.get("weekly_agenda_preview", []):
        days = []
        for day in week.get("days", []):
            days.append(
                {
                    "day_of_week": day.get("day_of_week", ""),
                    "day_role": day.get("day_role", ""),
                    "intensity_domain": day.get("intensity_domain", ""),
                    "load_modality": day.get("load_modality", ""),
                    "notes": day.get("notes", ""),
                }
            )
        days.sort(key=lambda entry: day_order.get(entry.get("day_of_week", ""), 99))
        week_previews.append(
            {
                "week": week.get("week", ""),
                "days": days,
            }
        )

    week_to_week = data.get("week_to_week_narrative", {})
    traceability = data.get("traceability", {})

    context = {
        "meta": meta,
        "trace_upstream": format_trace_list(meta.get("trace_upstream")),
        "trace_data": format_trace_list(meta.get("trace_data")),
        "trace_events": format_trace_list(meta.get("trace_events")),
        "phase_intent_summary": {
            "phase_type": phase_intent_summary.get("phase_type", ""),
            "primary_objective": phase_intent_summary.get("primary_objective", ""),
            "non_negotiables": phase_intent_summary.get("non_negotiables", []),
            "key_risks_warnings": phase_intent_summary.get("key_risks_warnings", []),
        },
        "feel_overview": {
            "dominant_theme": feel_overview.get("dominant_theme", ""),
            "intensity_handling_conceptual": feel_overview.get(
                "intensity_handling_conceptual", ""
            ),
            "recovery_protection_conceptual": feel_overview.get(
                "recovery_protection_conceptual", ""
            ),
        },
        "weekly_agenda_preview": week_previews,
        "week_to_week_narrative": {
            "direction": week_to_week.get("direction", ""),
            "what_will_not_change": week_to_week.get("what_will_not_change", ""),
            "what_is_flexible": week_to_week.get("what_is_flexible", ""),
        },
        "deviation_rules": data.get("deviation_rules", []),
        "traceability": {
            "derived_from": traceability.get("derived_from", []),
            "conflict_resolution": traceability.get("conflict_resolution", []),
        },
    }
    return context


def build_phase_feed_forward_context(doc):
    """Build context for phase feed forward rendering."""
    meta = doc.get("meta", {})
    data = doc.get("data", {})

    body_metadata = data.get("body_metadata", {})
    reason_context = data.get("reason_context", {})
    delta_load_guardrails = data.get("delta_load_guardrails", {})
    semantic_overrides = data.get("temporary_semantic_overrides", {})
    intensity_override = semantic_overrides.get("intensity_domain", {})
    modality_override = semantic_overrides.get("load_modality", {})
    quality_override = semantic_overrides.get("quality_density_override", {})
    non_negotiables = data.get("temporary_non_negotiables", {})
    self_check = data.get("self_check", {})

    def delta_rows(entries):
        """Normalize delta rows for reporting."""
        rows = []
        for entry in entries or []:
            band = entry.get("band", {})
            rows.append(
                {
                    "week": entry.get("week", ""),
                    "min": fmt_number(band.get("min")),
                    "max": fmt_number(band.get("max")),
                    "rationale": entry.get("rationale", ""),
                    "notes": entry.get("notes", ""),
                }
            )
        return rows

    context = {
        "meta": meta,
        "trace_upstream": format_trace_list(meta.get("trace_upstream")),
        "trace_data": format_trace_list(meta.get("trace_data")),
        "trace_events": format_trace_list(meta.get("trace_events")),
        "body_metadata": {
            "applies_to_weeks": body_metadata.get("applies_to_weeks", []),
            "valid_until": body_metadata.get("valid_until", ""),
            "change_type": body_metadata.get("change_type", ""),
            "derived_from": body_metadata.get("derived_from", ""),
            "upstream_triggers": body_metadata.get("upstream_triggers", []),
        },
        "reason_context": {
            "trigger_summary": reason_context.get("trigger_summary", ""),
            "observed_risk_deviation": reason_context.get("observed_risk_deviation", ""),
            "intent_of_adjustment": reason_context.get("intent_of_adjustment", ""),
        },
        "delta_load_guardrails": {
            "adjusted_weekly_kj_bands": delta_rows(
                delta_load_guardrails.get("adjusted_weekly_kj_bands", [])
            ),
        },
        "temporary_semantic_overrides": {
            "intensity_domain": {
                "newly_forbidden": intensity_override.get("newly_forbidden", []),
                "newly_allowed": intensity_override.get("newly_allowed", []),
            },
            "load_modality": {
                "newly_forbidden": modality_override.get("newly_forbidden", []),
                "newly_allowed": modality_override.get("newly_allowed", []),
            },
            "quality_density_override": {
                "max_quality_days_per_week": fmt_number(
                    quality_override.get("max_quality_days_per_week")
                ),
                "additional_forbidden_patterns": quality_override.get(
                    "additional_forbidden_patterns", []
                ),
            },
        },
        "temporary_non_negotiables": {
            "recovery_protection_changes": non_negotiables.get(
                "recovery_protection_changes", ""
            ),
            "anchor_protection_changes": non_negotiables.get(
                "anchor_protection_changes", ""
            ),
            "explicit_expiry_condition": non_negotiables.get("explicit_expiry_condition"),
        },
        "week_planner_operating_rules": data.get("week_planner_operating_rules", []),
        "explicit_forbidden_content": data.get("explicit_forbidden_content", []),
        "self_check": {
            "applies_to_weeks_specified": bool(
                self_check.get("applies_to_weeks_specified")
            ),
            "valid_until_defined": bool(self_check.get("valid_until_defined")),
            "only_deltas_vs_baseline_included": bool(
                self_check.get("only_deltas_vs_baseline_included")
            ),
            "no_week_content_present": bool(self_check.get("no_week_content_present")),
        },
    }
    return context


def build_season_phase_feed_forward_context(doc):
    """Build context for season phase feed-forward rendering."""
    meta = doc.get("meta", {})
    data = doc.get("data", {})

    source_context = data.get("source_context", {})
    decision_summary = data.get("decision_summary", {})
    phase_adjustment = data.get("phase_adjustment")

    context = {
        "meta": meta,
        "trace_upstream": format_trace_list(meta.get("trace_upstream")),
        "trace_data": format_trace_list(meta.get("trace_data")),
        "trace_events": format_trace_list(meta.get("trace_events")),
        "source_context": {
            "season_plan_ref": source_context.get("season_plan_ref", ""),
            "des_analysis_report_ref": source_context.get("des_analysis_report_ref", ""),
            "affected_phase_id": source_context.get("affected_phase_id", ""),
        },
        "decision_summary": {
            "conclusion": decision_summary.get("conclusion", ""),
            "rationale": decision_summary.get("rationale", []),
        },
        "phase_adjustment": phase_adjustment,
        "explicit_non_actions": data.get("explicit_non_actions", []),
    }
    return context


def build_des_analysis_report_context(doc):
    """Build context for des analysis report rendering."""
    meta = doc.get("meta", {})
    data = doc.get("data", {})

    summary_meta = data.get("summary_meta", {})
    kpi_summary = data.get("kpi_summary", {})
    weekly_analysis = data.get("weekly_analysis", {})
    trend_analysis = data.get("trend_analysis", {})
    recommendation = data.get("recommendation", {})
    narrative_report = data.get("narrative_report", {})

    def kpi_entry(entry):
        """Normalize KPI entry fields for rendering."""
        if not entry:
            return {}
        evidence = entry.get("evidence_window", {})
        return {
            "status": entry.get("status", ""),
            "confidence": entry.get("confidence", ""),
            "evidence_weeks": evidence.get("weeks"),
            "delta_vs_baseline": entry.get("delta_vs_baseline", ""),
        }

    context = {
        "meta": meta,
        "summary_meta": {
            "year": summary_meta.get("year"),
            "iso_week": summary_meta.get("iso_week"),
            "run_id": summary_meta.get("run_id", ""),
        },
        "kpi_summary": {
            "durability": kpi_entry(kpi_summary.get("durability")),
            "fatigue_resistance": kpi_entry(kpi_summary.get("fatigue_resistance")),
            "fueling_stability": kpi_entry(kpi_summary.get("fueling_stability")),
        },
        "weekly_analysis": {
            "context": {
                "phase_week": weekly_analysis.get("context", {}).get("phase_week"),
                "phase_focus": weekly_analysis.get("context", {}).get("phase_focus", ""),
            },
            "signals": weekly_analysis.get("signals", []),
            "interpretation": {
                "summary": weekly_analysis.get("interpretation", {}).get("summary", ""),
            },
        },
        "trend_analysis": {
            "horizon_weeks": trend_analysis.get("horizon_weeks"),
            "observations": trend_analysis.get("observations", []),
        },
        "recommendation": {
            "type": recommendation.get("type", ""),
            "scope": recommendation.get("scope", ""),
            "urgency": recommendation.get("urgency", ""),
            "rationale": recommendation.get("rationale", []),
            "suggested_considerations": recommendation.get("suggested_considerations", []),
            "explicitly_not": recommendation.get("explicitly_not", []),
        },
        "narrative_report": {
            "overview_current_status": narrative_report.get("overview_current_status", ""),
            "detailed_analysis_last_week": narrative_report.get(
                "detailed_analysis_last_week", ""
            ),
            "trend_analysis_within_phase": narrative_report.get(
                "trend_analysis_within_phase", ""
            ),
            "trend_analysis_season": narrative_report.get("trend_analysis_season", ""),
            "interpretation_recommendation": narrative_report.get(
                "interpretation_recommendation", ""
            ),
        },
    }
    return context


def build_activities_actual_context(doc):
    """Build context for activities actual rendering."""
    meta = doc.get("meta", {})
    data = doc.get("data", {})
    activities = data.get("activities", [])

    column_specs = [
        ("ISO Year", "base", "iso_year"),
        ("ISO Week", "base", "iso_week"),
        ("Day", "base", "day"),
        ("Day of Week", "base", "day_of_week"),
        ("Activity ID", "base", "activity_id"),
        ("Start Time (Local)", "base", "start_time_local"),
        ("Type", "base", "type"),
        ("Moving Time (hh:mm:ss)", "base", "moving_time"),
        ("Distance (km)", "base", "distance_km"),
        ("Work (kJ)", "base", "work_kj"),
        ("Load (TSS)", "base", "load_tss"),
        ("NP (W)", "base", "normalized_power_w"),
        ("Avg Power (W)", "metric", "avg_power_w"),
        ("Peak Power (W)", "metric", "peak_power_w"),
        ("Intensity Factor (IF)", "base", "intensity_factor"),
        ("Variability Index (VI)", "metric", "variability_index_vi"),
        ("Efficiency Factor (EF)", "metric", "efficiency_factor_ef"),
        ("Durability Index (DI)", "metric", "durability_index_di"),
        ("Functional Intensity Ratio (FIR)", "metric", "functional_intensity_ratio_fir"),
        ("Polarization Index", "metric", "polarization_index"),
        ("VO2/FTP (MMP 300s (W) / FTP Estimated (W))", "metric", "vo2_ftp_mmp_300s_w_ftp_estimated_w"),
        ("W′ Drop (%)", "metric", "w_drop"),
        ("Work > FTP (kJ)", "metric", "work_ftp_kj"),
        ("Decoupling (%)", "metric", "decoupling"),
        ("Avg HR (bpm)", "base", "avg_hr_bpm"),
        ("Max HR (bpm)", "base", "max_hr_bpm"),
        ("Power TiZ Z1 (hh:mm:ss)", "base", "power_tiz_z1"),
        ("Power TiZ Z2 (hh:mm:ss)", "base", "power_tiz_z2"),
        ("Power TiZ Z3 (hh:mm:ss)", "base", "power_tiz_z3"),
        ("Power TiZ Z4 (hh:mm:ss)", "base", "power_tiz_z4"),
        ("Power TiZ Z5 (hh:mm:ss)", "base", "power_tiz_z5"),
        ("Power TiZ Z6 (hh:mm:ss)", "base", "power_tiz_z6"),
        ("Power TiZ Z7 (hh:mm:ss)", "base", "power_tiz_z7"),
        ("HR TiZ Z1 (hh:mm:ss)", "base", "hr_tiz_z1"),
        ("HR TiZ Z2 (hh:mm:ss)", "base", "hr_tiz_z2"),
        ("HR TiZ Z3 (hh:mm:ss)", "base", "hr_tiz_z3"),
        ("HR TiZ Z4 (hh:mm:ss)", "base", "hr_tiz_z4"),
        ("HR TiZ Z5 (hh:mm:ss)", "base", "hr_tiz_z5"),
        ("HR TiZ Z6 (hh:mm:ss)", "base", "hr_tiz_z6"),
        ("HR TiZ Z7 (hh:mm:ss)", "base", "hr_tiz_z7"),
        ("Sweet Spot TiZ (hh:mm:ss)", "base", "sweet_spot_tiz"),
        ("Power TiZ Share Z2 (%)", "metric", "power_tiz_share_z2"),
        ("VO2Max TiZ Eff (hh:mm:ss)", "metric", "vo2max_tiz_eff_hh_mm_ss"),
        ("VO2Max Power TiZ (hh:mm:ss)", "metric", "vo2max_power_tiz_hh_mm_ss"),
        ("VO2Max HR TiZ (hh:mm:ss)", "metric", "vo2max_hr_tiz_hh_mm_ss"),
        ("Flag Long Ride >=150min (bool)", "flag", "flag_long_ride_150min_bool"),
        ("Flag Long Ride >=180min (bool)", "flag", "flag_long_ride_180min_bool"),
        ("Flag Long Ride >=240min (bool)", "flag", "flag_long_ride_240min_bool"),
        ("Flag IF <= 0.75 (bool)", "flag", "flag_if_0_75_bool"),
        ("Flag IF <= 0.80 (bool)", "flag", "flag_if_0_80_bool"),
        ("Flag Z2 Share >= 60% (bool)", "flag", "flag_z2_share_60_bool"),
        ("Flag Z2 Share >= 70% (bool)", "flag", "flag_z2_share_70_bool"),
        ("Flag Drift Valid (Z2 >= 90min) (bool)", "flag", "flag_drift_valid_z2_90min_bool"),
        ("Flag DES Long Base Candidate (bool)", "flag", "flag_des_long_base_candidate_bool"),
        ("Flag DES Long Build Candidate (bool)", "flag", "flag_des_long_build_candidate_bool"),
        ("Flag Brevet Long Candidate (bool)", "flag", "flag_brevet_long_candidate_bool"),
        ("MMP 5s (W)", "metric", "mmp_5s_w"),
        ("MMP 30s (W)", "metric", "mmp_30s_w"),
        ("MMP 60s (W)", "metric", "mmp_60s_w"),
        ("MMP 120s (W)", "metric", "mmp_120s_w"),
        ("MMP 300s (W)", "metric", "mmp_300s_w"),
        ("MMP 600s (W)", "metric", "mmp_600s_w"),
        ("MMP 1200s (W)", "metric", "mmp_1200s_w"),
        ("MMP 3600s (W)", "metric", "mmp_3600s_w"),
        ("MMP 5400s (W)", "metric", "mmp_5400s_w"),
        ("MMP 7200s (W)", "metric", "mmp_7200s_w"),
        ("MMP 9000s (W)", "metric", "mmp_9000s_w"),
        ("MMP 10800s (W)", "metric", "mmp_10800s_w"),
        ("MMP 14400s (W)", "metric", "mmp_14400s_w"),
        ("MMP 18000s (W)", "metric", "mmp_18000s_w"),
        ("MMP 21600s (W)", "metric", "mmp_21600s_w"),
    ]

    columns = []
    for label, source, key in column_specs:
        if source == "metric":
            columns.append({"label": label, "key": f"metric:{key}"})
        elif source == "flag":
            columns.append({"label": label, "key": f"flag:{key}"})
        else:
            columns.append({"label": label, "key": key})

    rows = []
    for activity in activities:
        flags = activity.get("flags") or {}
        metrics = activity.get("metrics") or {}
        row = {}
        for column in columns:
            key = column["key"]
            if key.startswith("flag:"):
                value = flags.get(key.split(":", 1)[1])
                row[key] = fmt_bool_upper(value)
            elif key.startswith("metric:"):
                value = metrics.get(key.split(":", 1)[1])
                row[key] = "" if value is None else str(value)
            else:
                value = activity.get(key)
                row[key] = "" if value is None else fmt_number(value)
        rows.append(row)

    context = {
        "meta": meta,
        "trace_upstream": format_trace_list(meta.get("trace_upstream")),
        "trace_data": format_trace_list(meta.get("trace_data")),
        "trace_events": format_trace_list(meta.get("trace_events")),
        "columns": columns,
        "rows": rows,
        "notes": data.get("notes"),
    }
    return context


def build_activities_trend_context(doc):
    """Build context for activities trend rendering."""
    meta = doc.get("meta", {})
    data = doc.get("data", {})
    weekly_trends = data.get("weekly_trends", [])

    column_specs = [
        ("Year", "base", "year"),
        ("ISO Week", "base", "iso_week"),
        ("Period", "base", "period"),
        ("# Activities", "weekly", "activity_count"),
        ("Moving Time (h:mm)", "weekly", "moving_time"),
        ("Distance (km)", "weekly", "distance_km"),
        ("Load (TSS)", "weekly", "load_tss"),
        ("Work (kJ)", "weekly", "work_kj"),
        ("Normalized Power (NP) (W)", "intensity", "normalized_power_w"),
        ("Intensity Factor (IF)", "intensity", "intensity_factor"),
        ("Decoupling (%)", "intensity", "decoupling_percent"),
        ("Durability Index (DI)", "intensity", "durability_index"),
        ("Efficiency Factor (EF)", "intensity", "efficiency_factor"),
        ("Functional Intensity Ratio (FIR) (MMP 5'/ MMP 20')", "intensity", "functional_intensity_ratio"),
        ("FTP Estimated (W)", "intensity", "ftp_estimated_w"),
        ("VO2/FTP (MMP 300s (W) / FTP Estimated (W))", "intensity", "vo2_ftp"),
        ("TSB (today)", "static", "tsb_today"),
        ("Adherence (%)", "distribution", "adherence_percent"),
        ("Z1 + Z2 Time (%)", "distribution", "z1_z2_time_percent"),
        ("Z5 Time (%)", "distribution", "z5_time_percent"),
        ("Power TiZ Z1 (hh:mm:ss)", "power_tiz", "z1"),
        ("Power TiZ Z2 (hh:mm:ss)", "power_tiz", "z2"),
        ("Power TiZ Z3 (hh:mm:ss)", "power_tiz", "z3"),
        ("Power TiZ Z4 (hh:mm:ss)", "power_tiz", "z4"),
        ("Power TiZ Z5 (hh:mm:ss)", "power_tiz", "z5"),
        ("Power TiZ Z6 (hh:mm:ss)", "power_tiz", "z6"),
        ("Power TiZ Z7 (hh:mm:ss)", "power_tiz", "z7"),
        ("HR TiZ Z1 (hh:mm:ss)", "hr_tiz", "z1"),
        ("HR TiZ Z2 (hh:mm:ss)", "hr_tiz", "z2"),
        ("HR TiZ Z3 (hh:mm:ss)", "hr_tiz", "z3"),
        ("HR TiZ Z4 (hh:mm:ss)", "hr_tiz", "z4"),
        ("HR TiZ Z5 (hh:mm:ss)", "hr_tiz", "z5"),
        ("HR TiZ Z6 (hh:mm:ss)", "hr_tiz", "z6"),
        ("HR TiZ Z7 (hh:mm:ss)", "hr_tiz", "z7"),
        ("Z2 Share (Power) (%)", "distribution", "z2_share_power_percent"),
        ("Sweet Spot TiZ (hh:mm:ss)", "optional_tiz", "sweet_spot"),
        ("VO2Max Power TiZ (hh:mm:ss)", "optional_tiz", "vo2max_power"),
        ("VO2Max HR TiZ (hh:mm:ss)", "optional_tiz", "vo2max_hr"),
        ("VO2Max TiZ Eff (hh:mm:ss)", "optional_tiz", "vo2max_tiz_efficiency"),
        ("MMP 60s (W)", "peak", "mmp_60s"),
        ("MMP 180s (W)", "peak", "mmp_180s"),
        ("MMP 300s (W)", "peak", "mmp_300s"),
        ("MMP 600s (W)", "peak", "mmp_600s"),
        ("MMP 1200s (W)", "peak", "mmp_1200s"),
        ("MMP 1800s (W)", "peak", "mmp_1800s"),
        ("MMP 3600s (W)", "peak", "mmp_3600s"),
        ("MMP 5400s (W)", "peak", "mmp_5400s"),
        ("MMP 7200s (W)", "peak", "mmp_7200s"),
        ("MMP 9000s (W)", "peak", "mmp_9000s"),
        ("MMP 10800s (W)", "peak", "mmp_10800s"),
        ("MMP 14400s (W)", "peak", "mmp_14400s"),
        ("MMP 18000s (W)", "peak", "mmp_18000s"),
        ("MMP 21600s (W)", "peak", "mmp_21600s"),
        ("Back-to-Back Z2 Days", "distribution", "back_to_back_z2_days_count"),
        ("Weekly Moving Time Total (min)", "static", "weekly_moving_time_total_min"),
        ("Weekly Z2 Time Total (min)", "static", "weekly_z2_time_total_min"),
        ("Weekly Z2 Share (%)", "static", "weekly_z2_share"),
        ("Weekly Moving Time Max (min)", "static", "weekly_moving_time_max_min"),
        ("Weekly Z2 Time Max (min)", "static", "weekly_z2_time_max_min"),
        ("Weekly Moving Time >=150min Sum (min)", "static", "weekly_moving_time_150min_sum_min"),
        ("Weekly Moving Time >=180min Sum (min)", "static", "weekly_moving_time_180min_sum_min"),
        ("Weekly Moving Time >=240min Sum (min)", "static", "weekly_moving_time_240min_sum_min"),
        ("Weekly Z2 Time >=150min Sum (min)", "static", "weekly_z2_time_150min_sum_min"),
        ("Weekly Z2 Time >=180min Sum (min)", "static", "weekly_z2_time_180min_sum_min"),
        ("Weekly Z2 Time >=240min Sum (min)", "static", "weekly_z2_time_240min_sum_min"),
        ("Weekly Moving Time DES Base Sum (min)", "static", "weekly_moving_time_des_base_sum_min"),
        ("Weekly Moving Time DES Build Sum (min)", "static", "weekly_moving_time_des_build_sum_min"),
        ("Weekly Z2 Time DES Base Sum (min)", "static", "weekly_z2_time_des_base_sum_min"),
        ("Weekly Z2 Time DES Build Sum (min)", "static", "weekly_z2_time_des_build_sum_min"),
        ("Count Flag Long Ride >=150min (count)", "flag_count", "long_ride_150min"),
        ("Count Flag Long Ride >=180min (count)", "flag_count", "long_ride_180min"),
        ("Count Flag Long Ride >=240min (count)", "flag_count", "long_ride_240min"),
        ("Count Flag IF <= 0.75 (count)", "flag_count", "if_at_or_below_0_75"),
        ("Count Flag IF <= 0.80 (count)", "flag_count", "if_at_or_below_0_80"),
        ("Count Flag Z2 Share >= 60% (count)", "flag_count", "z2_share_at_or_above_60"),
        ("Count Flag Z2 Share >= 70% (count)", "flag_count", "z2_share_at_or_above_70"),
        ("Count Flag Drift Valid (Z2 >= 90min) (count)", "flag_count", "drift_valid_z2_90min"),
        ("Count Flag DES Long Base Candidate (count)", "flag_count", "des_long_base_candidate"),
        ("Count Flag DES Long Build Candidate (count)", "flag_count", "des_long_build_candidate"),
        ("Count Flag Brevet Long Candidate (count)", "flag_count", "brevet_long_candidate"),
        ("Any Flag Long Ride >=150min (bool)", "flag_any", "long_ride_150min"),
        ("Any Flag Long Ride >=180min (bool)", "flag_any", "long_ride_180min"),
        ("Any Flag Long Ride >=240min (bool)", "flag_any", "long_ride_240min"),
        ("Any Flag IF <= 0.75 (bool)", "flag_any", "if_at_or_below_0_75"),
        ("Any Flag IF <= 0.80 (bool)", "flag_any", "if_at_or_below_0_80"),
        ("Any Flag Z2 Share >= 60% (bool)", "flag_any", "z2_share_at_or_above_60"),
        ("Any Flag Z2 Share >= 70% (bool)", "flag_any", "z2_share_at_or_above_70"),
        ("Any Flag Drift Valid (Z2 >= 90min) (bool)", "flag_any", "drift_valid_z2_90min"),
        ("Any Flag DES Long Base Candidate (bool)", "flag_any", "des_long_base_candidate"),
        ("Any Flag DES Long Build Candidate (bool)", "flag_any", "des_long_build_candidate"),
        ("Any Flag Brevet Long Candidate (bool)", "flag_any", "brevet_long_candidate"),
    ]

    columns = []
    for label, source, key in column_specs:
        if source == "weekly":
            columns.append({"label": label, "key": f"weekly:{key}"})
        elif source == "intensity":
            columns.append({"label": label, "key": f"intensity:{key}"})
        elif source == "power_tiz":
            columns.append({"label": label, "key": f"power_tiz:{key}"})
        elif source == "hr_tiz":
            columns.append({"label": label, "key": f"hr_tiz:{key}"})
        elif source == "optional_tiz":
            columns.append({"label": label, "key": f"optional_tiz:{key}"})
        elif source == "distribution":
            columns.append({"label": label, "key": f"distribution:{key}"})
        elif source == "peak":
            columns.append({"label": label, "key": f"peak:{key}"})
        elif source == "flag_count":
            columns.append({"label": label, "key": f"flag_count:{key}"})
        elif source == "flag_any":
            columns.append({"label": label, "key": f"flag_any:{key}"})
        elif source == "static":
            columns.append({"label": label, "key": f"static:{key}"})
        else:
            columns.append({"label": label, "key": key})

    rows = []
    for trend in weekly_trends:
        weekly = trend.get("weekly_aggregates", {})
        intensity = trend.get("intensity_load_metrics", {})
        power_tiz = trend.get("power_tiz", {})
        hr_tiz = trend.get("hr_tiz", {})
        optional_tiz = trend.get("optional_tiz") or {}
        distribution = trend.get("distribution_metrics") or {}
        peak = trend.get("peak_metrics") or {}
        flag_counts = trend.get("flag_counts") or {}
        flag_any = trend.get("flag_any") or {}
        metrics = trend.get("metrics") or {}

        row = {}
        for column in columns:
            key = column["key"]
            if key == "period":
                row[key] = fmt_date_range(trend.get("period"))
            elif key.startswith("weekly:"):
                value = weekly.get(key.split(":", 1)[1])
                row[key] = "" if value is None else fmt_number(value)
            elif key.startswith("intensity:"):
                value = intensity.get(key.split(":", 1)[1])
                row[key] = "" if value is None else fmt_number(value)
            elif key.startswith("power_tiz:"):
                value = power_tiz.get(key.split(":", 1)[1])
                row[key] = "" if value is None else str(value or "")
            elif key.startswith("hr_tiz:"):
                value = hr_tiz.get(key.split(":", 1)[1])
                row[key] = "" if value is None else str(value or "")
            elif key.startswith("optional_tiz:"):
                value = optional_tiz.get(key.split(":", 1)[1])
                row[key] = "" if value is None else str(value)
            elif key.startswith("distribution:"):
                value = distribution.get(key.split(":", 1)[1])
                row[key] = "" if value is None else fmt_number(value)
            elif key.startswith("peak:"):
                value = peak.get(key.split(":", 1)[1])
                row[key] = "" if value is None else fmt_number(value)
            elif key.startswith("flag_count:"):
                value = flag_counts.get(key.split(":", 1)[1])
                row[key] = "" if value is None else fmt_number(value)
            elif key.startswith("flag_any:"):
                value = flag_any.get(key.split(":", 1)[1])
                row[key] = fmt_bool_upper(value)
            elif key.startswith("static:"):
                value = metrics.get(key.split(":", 1)[1])
                row[key] = "" if value is None else fmt_number(value)
            else:
                row[key] = fmt_number(trend.get(key))
        rows.append(row)

    context = {
        "meta": meta,
        "trace_upstream": format_trace_list(meta.get("trace_upstream")),
        "trace_data": format_trace_list(meta.get("trace_data")),
        "trace_events": format_trace_list(meta.get("trace_events")),
        "columns": columns,
        "rows": rows,
        "notes": data.get("notes"),
    }
    return context


def build_zone_model_context(doc):
    """Build context for zone model rendering."""
    meta = doc.get("meta", {})
    data = doc.get("data", {})

    model_metadata = data.get("model_metadata", {})
    ftp_watts = model_metadata.get("ftp_watts")

    def format_range(range_obj, suffix):
        """Format a numeric range with a suffix."""
        if not range_obj:
            return "N/A"
        min_val = range_obj.get("min")
        max_val = range_obj.get("max")
        if min_val is None or max_val is None:
            return "N/A"
        return f"{fmt_number(min_val)}-{fmt_number(max_val)} {suffix}"

    zone_order = {"Z1": 0, "Z2": 1, "Z3": 2, "SS": 3, "Z4": 4, "Z5": 5, "Z6": 6, "Z7": 7}
    zones = []
    for zone in data.get("zones", []):
        percent_range = zone.get("ftp_percent_range", {})
        watt_range = zone.get("watt_range", {})
        zones.append(
            {
                "zone_id": zone.get("zone_id", ""),
                "name": zone.get("name", ""),
                "percent_range": format_range(percent_range, "%"),
                "watt_range": format_range(watt_range, "W"),
                "typical_if": "" if zone.get("typical_if") is None else fmt_number(zone.get("typical_if")),
                "training_intent": zone.get("training_intent", ""),
            }
        )
    zones.sort(key=lambda entry: zone_order.get(entry.get("zone_id"), 99))

    examples = []
    for example in data.get("examples", []):
        examples.append(
            {
                "workout_name": example.get("workout_name", ""),
                "structure": example.get("structure", ""),
                "duration": example.get("duration", ""),
                "if_adj": "" if example.get("if_adj") is None else fmt_number(example.get("if_adj")),
            }
        )

    z2_np_example = ""
    z2_zone = next((zone for zone in zones if zone.get("zone_id") == "Z2"), None)
    if z2_zone and ftp_watts is not None and z2_zone.get("typical_if"):
        try:
            z2_if = float(z2_zone["typical_if"])
            z2_np_example = fmt_number(z2_if * float(ftp_watts))
        except ValueError:
            z2_np_example = ""

    context = {
        "meta": meta,
        "trace_upstream": format_trace_list(meta.get("trace_upstream")),
        "trace_data": format_trace_list(meta.get("trace_data")),
        "trace_events": format_trace_list(meta.get("trace_events")),
        "model_metadata": {
            "valid_from": model_metadata.get("valid_from", ""),
            "ftp_watts": fmt_number(ftp_watts),
            "purpose": model_metadata.get("purpose", ""),
            "filename": model_metadata.get("filename", ""),
        },
        "zones": zones,
        "examples": examples,
        "versioning_usage": data.get("versioning_usage", []),
        "z2_np_example": z2_np_example,
    }
    return context


def build_kpi_profile_context(doc):
    """Build context for kpi profile rendering."""
    meta = doc.get("meta", {})
    data = doc.get("data", {})

    def text_or_na(value):
        """Return a text value or N/A."""
        if value is None or value == "":
            return "N/A"
        return str(value)

    def number_or_na(value):
        """Return a numeric value or N/A."""
        if value is None:
            return "N/A"
        return fmt_number(value)

    def range_or_na(value):
        """Return a formatted range or N/A."""
        return fmt_range(value)

    def threshold_row(label, threshold):
        """Normalize a threshold row for KPI tables."""
        threshold = threshold or {}
        return {
            "label": label,
            "green": text_or_na(threshold.get("green")),
            "yellow": text_or_na(threshold.get("yellow")),
            "red": text_or_na(threshold.get("red")),
            "context": threshold.get("context") or "",
            "notes": threshold.get("notes") or "",
        }

    def progression_row(label, limit):
        """Normalize a progression limit row for KPI tables."""
        limit = limit or {}
        return {
            "label": label,
            "allowed": text_or_na(limit.get("allowed")),
            "warning": text_or_na(limit.get("warning")),
            "stop": text_or_na(limit.get("stop")),
        }

    profile_metadata = data.get("profile_metadata", {})
    energetic_load = data.get("energetic_load_targets", {})
    progression_limits = energetic_load.get("progression_limits", {})
    durability = data.get("durability", {})
    multi_day = data.get("multi_day_durability", {})
    fueling = data.get("fueling_stability", {})
    efficiency = data.get("efficiency_drift", {})
    intensity = data.get("intensity_control", {})
    recovery = data.get("recovery_tolerability", {})
    traceability = data.get("traceability", {})

    context = {
        "meta": {
            "artifact_type": meta.get("artifact_type", ""),
            "schema_id": meta.get("schema_id", ""),
            "schema_version": meta.get("schema_version", ""),
            "version": meta.get("version", ""),
            "created_at": meta.get("created_at", ""),
            "owner_agent": meta.get("owner_agent", ""),
            "authority": meta.get("authority", ""),
            "run_id": meta.get("run_id", ""),
            "data_confidence": meta.get("data_confidence", ""),
            "scope": meta.get("scope", ""),
        },
        "trace_upstream": format_trace_list(meta.get("trace_upstream")),
        "trace_data": format_trace_list(meta.get("trace_data")),
        "trace_events": format_trace_list(meta.get("trace_events")),
        "profile_metadata": {
            "profile_id": profile_metadata.get("profile_id", ""),
            "event_type": profile_metadata.get("event_type", ""),
            "distance_range": profile_metadata.get("distance_range", ""),
            "athlete_class": profile_metadata.get("athlete_class", ""),
            "primary_objective": profile_metadata.get("primary_objective", ""),
        },
        "energetic_load_targets": {
            "weekly_load_kj": threshold_row("kJ / week", energetic_load.get("weekly_load_kj")),
            "progression_limits": [
                progression_row(
                    "Weekly kJ increase",
                    progression_limits.get("weekly_kj_increase"),
                ),
                progression_row(
                    "Long ride kJ increase",
                    progression_limits.get("long_ride_kj_increase"),
                ),
            ],
        },
        "durability": {
            "energetic_preload": {
                "single_ride_kj": number_or_na(
                    (durability.get("energetic_preload") or {}).get("single_ride_kj")
                ),
                "back_to_back_kj": number_or_na(
                    (durability.get("energetic_preload") or {}).get("back_to_back_kj")
                ),
                "derived_from": (durability.get("energetic_preload") or {}).get(
                    "derived_from"
                ),
            },
            "moving_time_rate_guidance": {
                "derived_from": (durability.get("moving_time_rate_guidance") or {}).get(
                    "derived_from"
                ),
                "notes": (durability.get("moving_time_rate_guidance") or {}).get("notes"),
                "bands": [
                    {
                        "segment": entry.get("segment"),
                        "w_per_kg": range_or_na(entry.get("w_per_kg")),
                        "kj_per_kg_per_hour": range_or_na(
                            entry.get("kj_per_kg_per_hour")
                        ),
                        "basis": entry.get("basis"),
                    }
                    for entry in (
                        (durability.get("moving_time_rate_guidance") or {}).get(
                            "bands",
                            [],
                        )
                    )
                ],
            },
            "kpis": [
                threshold_row(
                    "Durability Index (DI)",
                    (durability.get("kpis") or {}).get("durability_index"),
                ),
                threshold_row(
                    "Sustained Power Drop (3h vs 1h)",
                    (durability.get("kpis") or {}).get(
                        "sustained_power_drop_3h_vs_1h_percent"
                    ),
                ),
                threshold_row(
                    "Back-to-Back Ratio (BBR)",
                    (durability.get("kpis") or {}).get("back_to_back_ratio"),
                ),
                threshold_row(
                    "FIR (5'/20')",
                    (durability.get("kpis") or {}).get("fir_5min_20min"),
                ),
            ],
        },
        "multi_day_durability": {
            "applies_to": multi_day.get("applies_to") or [],
            "evaluation_window": multi_day.get("evaluation_window") or "N/A",
            "purpose": multi_day.get("purpose") or "N/A",
            "dominance_rule": multi_day.get("dominance_rule") or "N/A",
            "kpis": [
                threshold_row(
                    "BBR Trend (Day n vs Day n-1)",
                    (multi_day.get("kpis") or {}).get("bbr_trend_day_n_vs_day_n_minus_1"),
                ),
                threshold_row(
                    "IF Stability (Delta day-to-day)",
                    (multi_day.get("kpis") or {}).get("if_stability_delta_day_to_day"),
                ),
                threshold_row(
                    "HR Drift Trend",
                    (multi_day.get("kpis") or {}).get("hr_drift_trend"),
                ),
            ],
        },
        "fueling_stability": {
            "validity_requirement": fueling.get("validity_requirement") or "N/A",
            "purpose": fueling.get("purpose") or "N/A",
            "interpretation_rule": fueling.get("interpretation_rule") or "N/A",
            "kpis": [
                threshold_row(
                    "IF Decline under Preload",
                    (fueling.get("kpis") or {}).get("if_decline_under_preload"),
                ),
                threshold_row(
                    "HR Drift under Preload",
                    (fueling.get("kpis") or {}).get("hr_drift_under_preload"),
                ),
                threshold_row(
                    "Decoupling under Preload",
                    (fueling.get("kpis") or {}).get("decoupling_under_preload"),
                ),
            ],
        },
        "efficiency_drift": {
            "kpis": [
                threshold_row(
                    "Pa:Hr (Z2 >= 90 min)",
                    (efficiency.get("kpis") or {}).get("pa_hr_z2_90min"),
                ),
                threshold_row(
                    "HR Drift (Race Pace)",
                    (efficiency.get("kpis") or {}).get("hr_drift_race_pace"),
                ),
                threshold_row(
                    "EF trend",
                    (efficiency.get("kpis") or {}).get("ef_trend"),
                ),
            ],
        },
        "intensity_control": {
            "kpis": [
                threshold_row(
                    "VO2 TiZ / week",
                    (intensity.get("kpis") or {}).get("vo2_tiz_per_week"),
                ),
                threshold_row(
                    "SWEET_SPOT TiZ / week",
                    (intensity.get("kpis") or {}).get("sst_tiz_per_week"),
                ),
            ],
        },
        "recovery_tolerability": {
            "kpis": [
                threshold_row(
                    "TSB (Sun)",
                    (recovery.get("kpis") or {}).get("tsb_sun"),
                ),
                threshold_row(
                    "Subjective fatigue",
                    (recovery.get("kpis") or {}).get("subjective_fatigue"),
                ),
            ],
        },
        "decision_rules": {
            "green": (data.get("decision_rules") or {}).get("green") or "N/A",
            "yellow": (data.get("decision_rules") or {}).get("yellow") or "N/A",
            "red": (data.get("decision_rules") or {}).get("red") or "N/A",
        },
        "traceability": {
            "requirements": traceability.get("requirements") or [],
        },
    }
    return context


def build_availability_context(doc):
    """Build context for availability rendering."""
    meta = doc.get("meta", {})
    data = doc.get("data", {})

    weekly_hours = data.get("weekly_hours") or {}
    availability_table = []
    for row in data.get("availability_table", []):
        availability_table.append(
            {
                "weekday": row.get("weekday", ""),
                "hours_min": fmt_number(row.get("hours_min")),
                "hours_typical": fmt_number(row.get("hours_typical")),
                "hours_max": fmt_number(row.get("hours_max")),
                "indoor_possible": row.get("indoor_possible"),
                "travel_risk": row.get("travel_risk"),
                "locked": row.get("locked"),
            }
        )

    context = {
        "meta": meta,
        "trace_upstream": format_trace_list(meta.get("trace_upstream")),
        "trace_data": format_trace_list(meta.get("trace_data")),
        "trace_events": format_trace_list(meta.get("trace_events")),
        "data": {
            "weekly_hours": {
                "min": fmt_number(weekly_hours.get("min")),
                "typical": fmt_number(weekly_hours.get("typical")),
                "max": fmt_number(weekly_hours.get("max")),
            }
            if weekly_hours
            else None,
            "availability_table": availability_table,
            "fixed_rest_days": data.get("fixed_rest_days", []),
            "notes": data.get("notes", ""),
        },
    }
    return context


def build_wellness_context(doc):
    """Build context for wellness rendering."""
    meta = doc.get("meta", {})
    data = doc.get("data", {})

    entries = list(data.get("entries") or [])
    entries.sort(key=lambda row: row.get("date") or "")

    context = {
        "meta": meta,
        "trace_upstream": format_trace_list(meta.get("trace_upstream")),
        "trace_data": format_trace_list(meta.get("trace_data")),
        "trace_events": format_trace_list(meta.get("trace_events")),
        "data": {
            "body_mass_kg": data.get("body_mass_kg"),
            "entries": entries,
            "notes": data.get("notes", ""),
        },
    }
    return context


def render_season_plan(doc, template_dir: Path):
    """Render season plan using a Jinja template."""
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["join_or_na"] = join_or_na
    template = env.get_template(RENDERERS["SEASON_PLAN"])
    context = build_season_plan_context(doc)
    return template.render(**context)


def render_phase_guardrails(doc, template_dir: Path):
    """Render phase guardrails using a Jinja template."""
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["join_or_na"] = join_or_na
    template = env.get_template(RENDERERS["PHASE_GUARDRAILS"])
    context = build_phase_guardrails_context(doc)
    return template.render(**context)


def render_week_plan(doc, template_dir: Path):
    """Render week plan using a Jinja template."""
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["join_or_na"] = join_or_na
    template = env.get_template(RENDERERS["WEEK_PLAN"])
    context = build_week_plan_context(doc)
    return template.render(**context)


def render_phase_structure(doc, template_dir: Path):
    """Render phase structure using a Jinja template."""
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["join_or_na"] = join_or_na
    template = env.get_template(RENDERERS["PHASE_STRUCTURE"])
    context = build_phase_structure_context(doc)
    return template.render(**context)


def render_phase_preview(doc, template_dir: Path):
    """Render phase preview using a Jinja template."""
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["join_or_na"] = join_or_na
    template = env.get_template(RENDERERS["PHASE_PREVIEW"])
    context = build_phase_preview_context(doc)
    return template.render(**context)


def render_phase_feed_forward(doc, template_dir: Path):
    """Render phase feed forward using a Jinja template."""
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["join_or_na"] = join_or_na
    template = env.get_template(RENDERERS["PHASE_FEED_FORWARD"])
    context = build_phase_feed_forward_context(doc)
    return template.render(**context)


def render_season_phase_feed_forward(doc, template_dir: Path):
    """Render season phase feed forward using a Jinja template."""
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["join_or_na"] = join_or_na
    template = env.get_template(RENDERERS["SEASON_PHASE_FEED_FORWARD"])
    context = build_season_phase_feed_forward_context(doc)
    return template.render(**context)


def render_des_analysis_report(doc, template_dir: Path):
    """Render des analysis report using a Jinja template."""
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["join_or_na"] = join_or_na
    template = env.get_template(RENDERERS["DES_ANALYSIS_REPORT"])
    context = build_des_analysis_report_context(doc)
    return template.render(**context)


def render_activities_actual(doc, template_dir: Path):
    """Render activities actual using a Jinja template."""
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(RENDERERS["ACTIVITIES_ACTUAL"])
    context = build_activities_actual_context(doc)
    return template.render(**context)


def render_activities_trend(doc, template_dir: Path):
    """Render activities trend using a Jinja template."""
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(RENDERERS["ACTIVITIES_TREND"])
    context = build_activities_trend_context(doc)
    return template.render(**context)


def render_zone_model(doc, template_dir: Path):
    """Render zone model using a Jinja template."""
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(RENDERERS["ZONE_MODEL"])
    context = build_zone_model_context(doc)
    return template.render(**context)


def render_kpi_profile(doc, template_dir: Path):
    """Render kpi profile using a Jinja template."""
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["join_or_na"] = join_or_na
    template = env.get_template(RENDERERS["KPI_PROFILE"])
    context = build_kpi_profile_context(doc)
    return template.render(**context)


def render_availability(doc, template_dir: Path):
    """Render availability using a Jinja template."""
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(RENDERERS["AVAILABILITY"])
    context = build_availability_context(doc)
    return template.render(**context)


def render_wellness(doc, template_dir: Path):
    """Render wellness using a Jinja template."""
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(RENDERERS["WELLNESS"])
    context = build_wellness_context(doc)
    return template.render(**context)


def render_json_sidecar(
    input_path: Path,
    output_path: Path | None = None,
    *,
    schema_dir: Path | None = None,
    validate: bool = False,
    athlete_id: str | None = None,
) -> Path | None:
    """Render a JSON artefact to a Markdown sidecar.

    Args:
        input_path: Path to the JSON artefact.
        output_path: Optional output path for the rendered Markdown.
        schema_dir: Optional schema directory for validation.
        validate: Whether to validate before rendering.
        athlete_id: Optional athlete id to resolve rendered output location.

    Returns:
        Path to the rendered Markdown sidecar, or None if nothing was rendered.
    """
    if not input_path.exists():
        return None

    doc = load_json(input_path)
    if isinstance(doc, list):
        return None

    meta = doc.get("meta", {})
    artifact_type = meta.get("artifact_type")
    if not artifact_type:
        return None

    if artifact_type not in RENDERERS:
        return None

    resolved_schema_dir = Path(
        schema_dir
        or os.getenv("SCHEMA_DIR", str(REPO_ROOT / "specs/schemas"))
    ).resolve()
    if validate:
        validate_document(doc, artifact_type, resolved_schema_dir)

    template_dir = TEMPLATE_DIR
    if artifact_type == "SEASON_PLAN":
        rendered = render_season_plan(doc, template_dir)
    elif artifact_type == "PHASE_GUARDRAILS":
        rendered = render_phase_guardrails(doc, template_dir)
    elif artifact_type == "PHASE_STRUCTURE":
        rendered = render_phase_structure(doc, template_dir)
    elif artifact_type == "PHASE_PREVIEW":
        rendered = render_phase_preview(doc, template_dir)
    elif artifact_type == "PHASE_FEED_FORWARD":
        rendered = render_phase_feed_forward(doc, template_dir)
    elif artifact_type == "SEASON_PHASE_FEED_FORWARD":
        rendered = render_season_phase_feed_forward(doc, template_dir)
    elif artifact_type == "DES_ANALYSIS_REPORT":
        rendered = render_des_analysis_report(doc, template_dir)
    elif artifact_type == "ACTIVITIES_ACTUAL":
        rendered = render_activities_actual(doc, template_dir)
    elif artifact_type == "ACTIVITIES_TREND":
        rendered = render_activities_trend(doc, template_dir)
    elif artifact_type == "ZONE_MODEL":
        rendered = render_zone_model(doc, template_dir)
    elif artifact_type == "WEEK_PLAN":
        rendered = render_week_plan(doc, template_dir)
    elif artifact_type == "KPI_PROFILE":
        rendered = render_kpi_profile(doc, template_dir)
    elif artifact_type == "AVAILABILITY":
        rendered = render_availability(doc, template_dir)
    elif artifact_type == "WELLNESS":
        rendered = render_wellness(doc, template_dir)
    else:
        return None

    if output_path is None:
        resolved_athlete_id = athlete_id or os.getenv("ATHLETE_ID")
        if resolved_athlete_id:
            out_dir = REPO_ROOT / "var" / "athletes" / resolved_athlete_id / "rendered"
            out_dir.mkdir(parents=True, exist_ok=True)
            output_path = out_dir / f"{input_path.stem}.md"
        else:
            output_path = input_path.with_suffix(".md")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    return output_path
