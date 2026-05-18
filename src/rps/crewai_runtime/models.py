"""Typed operation models aligned with CrewAI task outputs."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictOutputModel(BaseModel):
    """Closed base model for CrewAI structured outputs."""

    model_config = ConfigDict(extra="forbid")


class TurnModeModel(StrictOutputModel):
    """Manager output for routing one conversational planning turn."""

    mode: Literal["analyze", "recommend", "create_preview", "resolve_pending"]
    rationale: str | None = None


class PlanningDraftModel(StrictOutputModel):
    """Generic structured planning draft for internal specialist outputs."""

    summary: str = ""
    details: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class WeekContextAssessmentModel(StrictOutputModel):
    """Structured read-only summary of the selected week context."""

    summary: str
    key_constraints: list[str] = Field(default_factory=list)
    completed_vs_planned: list[str] = Field(default_factory=list)
    likely_change_request: bool = False


class CoachingRecommendationModel(StrictOutputModel):
    """Structured coaching guidance for advisory-only turns."""

    recommendation: str
    rationale: list[str] = Field(default_factory=list)
    preview_recommended: bool = False


class AdjustmentIntentModel(StrictOutputModel):
    """Structured change intent before preview creation."""

    summary: str
    message_for_preview: str
    recommended_tool: str = "preview_scoped_week_replan"
    constraints_to_preserve: list[str] = Field(default_factory=list)


class PendingResolutionResultModel(StrictOutputModel):
    """Structured result for pending preview inspection/apply/discard turns."""

    action: str
    ok: bool
    summary: str
    requires_confirmation: bool | None = None
    warnings: list[str] = Field(default_factory=list)


class ArtifactWriteModel(StrictOutputModel):
    """One artifact write or rebuild produced by an apply operation."""

    artifact_type: str
    version_key: str | None = None
    path: str | None = None
    run_id: str | None = None


class ArtifactEnvelopeMetaModel(StrictOutputModel):
    """Generic full-envelope meta model for persisted CrewAI task outputs."""

    artifact_type: str
    schema_id: str
    schema_version: str | None = None
    version: str | None = None
    authority: str | None = None
    owner_agent: str | None = None
    run_id: str | None = None
    created_at: str | None = None
    scope: str | None = None
    iso_week: str | None = None
    iso_week_range: str | None = None
    temporal_scope: list[str] = Field(default_factory=list)
    trace_upstream: list[str] = Field(default_factory=list)
    trace_data: list[str] = Field(default_factory=list)
    trace_events: list[str] = Field(default_factory=list)
    data_confidence: str | None = None
    notes: str | None = None
    version_key: str | None = None


class ArtifactEnvelopeModel(StrictOutputModel):
    """Generic full artifact envelope model for persisted CrewAI tasks."""

    meta: ArtifactEnvelopeMetaModel
    data: dict[str, Any] = Field(default_factory=dict, json_schema_extra={"additionalProperties": False})


class SeasonEventAnchorModel(StrictOutputModel):
    """Internal season draft for event priority and anchor handling."""

    primary_a_events: list[str] = Field(default_factory=list)
    supporting_b_events: list[str] = Field(default_factory=list)
    contextual_c_events: list[str] = Field(default_factory=list)
    anchor_rationale: list[str] = Field(default_factory=list)
    constrained_time_window: bool = False


class SeasonMacrocycleDraftModel(StrictOutputModel):
    """Internal season draft for macrocycle and cadence layout."""

    deload_cadence: str | None = None
    phase_length_weeks: int | None = None
    macrocycle_order: list[str] = Field(default_factory=list)
    reverse_planning_notes: list[str] = Field(default_factory=list)
    event_window_implications: list[str] = Field(default_factory=list)


class SeasonPlanAuditModel(StrictOutputModel):
    """Internal audit result for season-plan authority checks."""

    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommended_adjustments: list[str] = Field(default_factory=list)
    macrocycle_coherence_ok: bool = True
    cadence_authority_ok: bool = True


class ReplanInstructionModel(StrictOutputModel):
    """Structured replan instruction emitted by review crews."""

    target_specialists: list[str] = Field(default_factory=list)
    issues_to_fix: list[str] = Field(default_factory=list)
    must_preserve: list[str] = Field(default_factory=list)
    priority_order: list[str] = Field(default_factory=list)
    max_scope_of_change: str | None = None


class SeasonPlanBundleModel(StrictOutputModel):
    """Internal season planning bundle before review and writing."""

    context_summary: list[str] = Field(default_factory=list)
    scenario_interpretation: list[str] = Field(default_factory=list)
    event_priority: SeasonEventAnchorModel
    peak_window: list[str] = Field(default_factory=list)
    macrocycle: SeasonMacrocycleDraftModel
    constraints: list[ConstraintAuditModel] = Field(default_factory=list)
    load_governance: list[LoadGovernanceAuditModel] = Field(default_factory=list)
    decision_summary: list[str] = Field(default_factory=list)
    candidate_document_summary: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)


class SeasonReviewDecisionModel(StrictOutputModel):
    """Holistic season review decision before writer handoff."""

    status: Literal["approved", "replan_required", "rejected"]
    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    replan_instructions: list[ReplanInstructionModel] = Field(default_factory=list)
    writer_ready_summary: str = ""


class ConstraintAuditModel(StrictOutputModel):
    """Internal audit result for constraint propagation and consistency."""

    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommended_adjustments: list[str] = Field(default_factory=list)
    applied_sources: list[str] = Field(default_factory=list)


class LoadGovernanceAuditModel(StrictOutputModel):
    """Internal audit result for corridor and durability governance."""

    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommended_adjustments: list[str] = Field(default_factory=list)
    cadence_authority_preserved: bool = True
    durability_first_respected: bool = True


class PhaseGuardrailsPayloadModel(StrictOutputModel):
    """Internal phase draft for guardrails payload content."""

    phase_summary: list[str] = Field(default_factory=list)
    load_guardrails: list[str] = Field(default_factory=list)
    allowed_forbidden_semantics: list[str] = Field(default_factory=list)
    events_constraints: list[str] = Field(default_factory=list)
    execution_non_negotiables: list[str] = Field(default_factory=list)


class PhaseStructurePayloadModel(StrictOutputModel):
    """Internal phase draft for structural execution guidance."""

    upstream_intent: list[str] = Field(default_factory=list)
    load_ranges: list[str] = Field(default_factory=list)
    execution_principles: list[str] = Field(default_factory=list)
    structural_phase_elements: list[str] = Field(default_factory=list)
    week_skeleton_logic: list[str] = Field(default_factory=list)
    adaptation_rules: list[str] = Field(default_factory=list)


class PhasePreviewPayloadModel(StrictOutputModel):
    """Internal phase draft for preview-only narrative output."""

    phase_intent_summary: list[str] = Field(default_factory=list)
    feel_overview: list[str] = Field(default_factory=list)
    weekly_agenda_preview: list[str] = Field(default_factory=list)
    week_to_week_narrative: list[str] = Field(default_factory=list)
    deviation_rules: list[str] = Field(default_factory=list)


class PhaseBundleDecisionModel(StrictOutputModel):
    """Internal manager summary for a full phase bundle."""

    cadence_source: str | None = None
    cadence_application_notes: list[str] = Field(default_factory=list)
    override_rationale: list[str] = Field(default_factory=list)


class PhaseBundleModel(StrictOutputModel):
    """Internal season-authorized phase bundle before deterministic split."""

    phase_range: str
    phase_id: str | None = None
    phase_type: str | None = None
    cadence_source: str | None = None
    guardrails: PhaseGuardrailsPayloadModel
    structure: PhaseStructurePayloadModel
    preview: PhasePreviewPayloadModel
    guardrails_document_summary: list[str] = Field(default_factory=list)
    structure_document_summary: list[str] = Field(default_factory=list)
    preview_document_summary: list[str] = Field(default_factory=list)
    constraint_audit: ConstraintAuditModel
    load_governance_audit: LoadGovernanceAuditModel
    warnings: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    decision_summary: PhaseBundleDecisionModel


class PhaseReviewDecisionModel(StrictOutputModel):
    """Holistic phase review decision before writer handoff."""

    status: Literal["approved", "replan_required", "rejected"]
    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    replan_instructions: list[ReplanInstructionModel] = Field(default_factory=list)
    writer_ready_summary: str = ""


class WeekPlanBundleModel(StrictOutputModel):
    """Internal week planning bundle before review and writing."""

    context_summary: WeekContextAssessmentModel | None = None
    constraint_summary: list[str] = Field(default_factory=list)
    load_target_summary: list[str] = Field(default_factory=list)
    revision_summary: list[str] = Field(default_factory=list)
    workout_authoring_summary: list[str] = Field(default_factory=list)
    candidate_document_summary: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)


class WeekReviewDecisionModel(StrictOutputModel):
    """Holistic week review decision before writer handoff."""

    status: Literal["approved", "replan_required", "rejected"]
    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    replan_instructions: list[ReplanInstructionModel] = Field(default_factory=list)
    writer_ready_summary: str = ""


class DESAnalysisBundleModel(StrictOutputModel):
    """Internal advisory analysis bundle before review and writing."""

    context_summary: list[str] = Field(default_factory=list)
    diagnostic_summary: list[str] = Field(default_factory=list)
    candidate_document_summary: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)


class ReportReviewDecisionModel(StrictOutputModel):
    """Holistic report review decision before writer handoff."""

    status: Literal["approved", "replan_required", "rejected"]
    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    replan_instructions: list[ReplanInstructionModel] = Field(default_factory=list)
    writer_ready_summary: str = ""




class CoachPreviewSummaryModel(StrictOutputModel):
    """Strict preview summary model for conversational preview specialist output."""

    operation: str
    ok: bool
    requires_confirmation: bool = True
    summary: str
    warnings: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    affected_artifacts: list[str] = Field(default_factory=list)
    downstream_recomputations: list[str] = Field(default_factory=list)


class CoachOperationPreviewModel(StrictOutputModel):
    """Structured preview for a pending coach operation."""

    operation: str
    ok: bool
    requires_confirmation: bool = True
    summary: str
    warnings: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    affected_artifacts: list[str] = Field(default_factory=list)
    downstream_recomputations: list[str] = Field(default_factory=list)
    document: Any = None
    metadata: dict[str, Any] = Field(default_factory=dict, json_schema_extra={"additionalProperties": False})


class CoachOperationApplyResultModel(StrictOutputModel):
    """Structured apply result for coach-triggered operations."""

    operation: str
    ok: bool
    summary: str
    artifact_writes: list[ArtifactWriteModel] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict, json_schema_extra={"additionalProperties": False})
