"""Typed operation models aligned with CrewAI task outputs."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class TurnModeModel(BaseModel):
    """Manager output for routing one conversational planning turn."""

    mode: Literal["analyze", "recommend", "create_preview", "resolve_pending"]
    rationale: str | None = None


class WeekContextAssessmentModel(BaseModel):
    """Structured read-only summary of the selected week context."""

    summary: str
    key_constraints: list[str] = Field(default_factory=list)
    completed_vs_planned: list[str] = Field(default_factory=list)
    likely_change_request: bool = False


class CoachingRecommendationModel(BaseModel):
    """Structured coaching guidance for advisory-only turns."""

    recommendation: str
    rationale: list[str] = Field(default_factory=list)
    preview_recommended: bool = False


class AdjustmentIntentModel(BaseModel):
    """Structured change intent before preview creation."""

    summary: str
    message_for_preview: str
    recommended_tool: str = "preview_scoped_week_replan"
    constraints_to_preserve: list[str] = Field(default_factory=list)


class PendingResolutionResultModel(BaseModel):
    """Structured result for pending preview inspection/apply/discard turns."""

    action: str
    ok: bool
    summary: str
    requires_confirmation: bool | None = None
    warnings: list[str] = Field(default_factory=list)


class ArtifactWriteModel(BaseModel):
    """One artifact write or rebuild produced by an apply operation."""

    artifact_type: str
    version_key: str | None = None
    path: str | None = None
    run_id: str | None = None


class ArtifactEnvelopeMetaModel(BaseModel):
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
    temporal_scope: dict[str, Any] | None = None
    trace_upstream: list[dict[str, Any]] = Field(default_factory=list)
    trace_data: list[dict[str, Any]] = Field(default_factory=list)
    trace_events: list[dict[str, Any]] = Field(default_factory=list)
    data_confidence: str | None = None
    notes: str | None = None
    version_key: str | None = None


class ArtifactEnvelopeModel(BaseModel):
    """Generic full artifact envelope model for persisted CrewAI tasks."""

    meta: ArtifactEnvelopeMetaModel
    data: dict[str, Any]


class SeasonEventAnchorModel(BaseModel):
    """Internal season draft for event priority and anchor handling."""

    primary_a_events: list[str] = Field(default_factory=list)
    supporting_b_events: list[str] = Field(default_factory=list)
    contextual_c_events: list[str] = Field(default_factory=list)
    anchor_rationale: list[str] = Field(default_factory=list)
    constrained_time_window: bool = False


class SeasonMacrocycleDraftModel(BaseModel):
    """Internal season draft for macrocycle and cadence layout."""

    deload_cadence: str | None = None
    phase_length_weeks: int | None = None
    macrocycle_order: list[str] = Field(default_factory=list)
    reverse_planning_notes: list[str] = Field(default_factory=list)
    event_window_implications: list[str] = Field(default_factory=list)


class SeasonPlanAuditModel(BaseModel):
    """Internal audit result for season-plan authority checks."""

    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommended_adjustments: list[str] = Field(default_factory=list)
    macrocycle_coherence_ok: bool = True
    cadence_authority_ok: bool = True


class ConstraintAuditModel(BaseModel):
    """Internal audit result for constraint propagation and consistency."""

    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommended_adjustments: list[str] = Field(default_factory=list)
    applied_sources: list[str] = Field(default_factory=list)


class LoadGovernanceAuditModel(BaseModel):
    """Internal audit result for corridor and durability governance."""

    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommended_adjustments: list[str] = Field(default_factory=list)
    cadence_authority_preserved: bool = True
    durability_first_respected: bool = True


class PhaseGuardrailsPayloadModel(BaseModel):
    """Internal phase draft for guardrails payload content."""

    phase_summary: dict[str, Any] = Field(default_factory=dict)
    load_guardrails: dict[str, Any] = Field(default_factory=dict)
    allowed_forbidden_semantics: dict[str, Any] = Field(default_factory=dict)
    events_constraints: dict[str, Any] = Field(default_factory=dict)
    execution_non_negotiables: dict[str, Any] = Field(default_factory=dict)


class PhaseStructurePayloadModel(BaseModel):
    """Internal phase draft for structural execution guidance."""

    upstream_intent: dict[str, Any] = Field(default_factory=dict)
    load_ranges: dict[str, Any] = Field(default_factory=dict)
    execution_principles: dict[str, Any] = Field(default_factory=dict)
    structural_phase_elements: dict[str, Any] = Field(default_factory=dict)
    week_skeleton_logic: dict[str, Any] = Field(default_factory=dict)
    adaptation_rules: list[str] = Field(default_factory=list)


class PhasePreviewPayloadModel(BaseModel):
    """Internal phase draft for preview-only narrative output."""

    phase_intent_summary: dict[str, Any] = Field(default_factory=dict)
    feel_overview: dict[str, Any] = Field(default_factory=dict)
    weekly_agenda_preview: list[dict[str, Any]] = Field(default_factory=list)
    week_to_week_narrative: dict[str, Any] = Field(default_factory=dict)
    deviation_rules: list[str] = Field(default_factory=list)


class PhaseBundleDecisionModel(BaseModel):
    """Internal manager summary for a full phase bundle."""

    cadence_source: str | None = None
    cadence_application_notes: list[str] = Field(default_factory=list)
    override_rationale: list[str] = Field(default_factory=list)


class PhaseBundleModel(BaseModel):
    """Internal season-authorized phase bundle before deterministic split."""

    phase_range: str
    phase_id: str | None = None
    phase_type: str | None = None
    cadence_source: str | None = None
    guardrails: PhaseGuardrailsPayloadModel
    structure: PhaseStructurePayloadModel
    preview: PhasePreviewPayloadModel
    guardrails_document: dict[str, Any] | None = None
    structure_document: dict[str, Any] | None = None
    preview_document: dict[str, Any] | None = None
    constraint_audit: ConstraintAuditModel
    load_governance_audit: LoadGovernanceAuditModel
    warnings: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    decision_summary: PhaseBundleDecisionModel




class CoachPreviewSummaryModel(BaseModel):
    """Strict preview summary model for conversational preview specialist output."""

    operation: str
    ok: bool
    requires_confirmation: bool = True
    summary: str
    warnings: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    affected_artifacts: list[str] = Field(default_factory=list)
    downstream_recomputations: list[str] = Field(default_factory=list)


class CoachOperationPreviewModel(BaseModel):
    """Structured preview for a pending coach operation."""

    operation: str
    ok: bool
    requires_confirmation: bool = True
    summary: str
    warnings: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    affected_artifacts: list[str] = Field(default_factory=list)
    downstream_recomputations: list[str] = Field(default_factory=list)
    document: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CoachOperationApplyResultModel(BaseModel):
    """Structured apply result for coach-triggered operations."""

    operation: str
    ok: bool
    summary: str
    artifact_writes: list[ArtifactWriteModel] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
