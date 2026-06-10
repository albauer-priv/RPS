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


class EvidenceSummaryCardModel(StrictOutputModel):
    """Compact registry-safe summary card for one evidence source."""

    focus: str
    main_takeaway: str
    main_limit: str


class EvidenceRelevanceAssessmentModel(StrictOutputModel):
    """Structured RPS-specific relevance classification for one source."""

    overall_relevance: Literal["high", "medium", "low", "reject"]
    relevance_rationale: str
    rps_domains_supported: list[
        Literal[
            "durability",
            "fatigue_resistance",
            "pacing",
            "fueling",
            "taper",
            "progression",
            "intensity_distribution",
            "masters",
            "brevet_ultra",
            "coaching_translation",
        ]
    ] = Field(default_factory=list)
    target_audiences_supported: list[
        Literal[
            "season_planning",
            "phase_planning",
            "week_planning",
            "coach_chat",
            "athlete_education",
            "background_knowledge",
        ]
    ] = Field(default_factory=list)
    best_use_mode: Literal["core_scientific_support", "applied_translation", "background_only", "reject"]
    activation_recommendation: Literal["activate", "hold", "reject"]


class EvidenceBriefSectionsModel(StrictOutputModel):
    """Rendered markdown-brief sections emitted by the evidence curation agent."""

    why_this_source_matters_for_rps: str
    research_question_or_purpose: str
    study_type: str
    population_or_context: str
    what_was_actually_examined: str
    core_concepts: list[str] = Field(default_factory=list)
    key_takeaways: list[str] = Field(default_factory=list)
    important_findings: list[str] = Field(default_factory=list)
    practical_implications_for_rps: list[str] = Field(default_factory=list)
    what_this_source_does_not_justify: list[str] = Field(default_factory=list)
    limits_and_transfer_boundaries: list[str] = Field(default_factory=list)
    allowed_uses_in_rps: list[str] = Field(default_factory=list)
    evidence_posture: str
    source_material_basis: str


class EvidenceCurationModel(StrictOutputModel):
    """Structured curation payload for the evidence library pipeline."""

    question_or_focus: str
    population_or_scope: str
    study_type: Literal[
        "systematic_review",
        "narrative_review",
        "meta_analysis",
        "rct",
        "cohort",
        "cross_sectional",
        "case_study",
        "methods_paper",
        "consensus_statement",
        "book",
        "podcast",
        "blog",
        "whitepaper",
        "practitioner_article",
        "other",
    ]
    what_was_examined: list[str] = Field(default_factory=list)
    core_concepts: list[str] = Field(default_factory=list)
    key_takeaways: list[str] = Field(default_factory=list)
    important_findings: list[str] = Field(default_factory=list)
    practical_implications: list[str] = Field(default_factory=list)
    what_this_does_not_justify: list[str] = Field(default_factory=list)
    important_limits: list[str] = Field(default_factory=list)
    allowed_uses: list[
        Literal[
            "durability_definition",
            "durability_rationale",
            "planning_justification",
            "taper_support",
            "fueling_guidance",
            "intensity_distribution_context",
            "coaching_translation",
            "background_only",
        ]
    ] = Field(default_factory=list)
    evidence_posture: Literal[
        "fulltext_curated",
        "oa_excerpt_curated",
        "abstract_curated",
        "metadata_only_not_activatable",
    ]
    relevance_assessment: EvidenceRelevanceAssessmentModel
    summary_card: EvidenceSummaryCardModel
    brief_sections: EvidenceBriefSectionsModel


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


class ArtifactTraceReferenceModel(StrictOutputModel):
    """Canonical trace reference persisted inside artifact metadata."""

    artifact: str
    version: str
    schema_version: str
    version_key: str
    run_id: str


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
    trace_upstream: list[ArtifactTraceReferenceModel] = Field(default_factory=list)
    trace_data: list[ArtifactTraceReferenceModel] = Field(default_factory=list)
    trace_events: list[ArtifactTraceReferenceModel] = Field(default_factory=list)
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
    season_archetype: str | None = None
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


class SeasonPhaseSemanticContractModel(StrictOutputModel):
    """Structured method contract that the Season writer must serialize, not infer."""

    methodology_family: str
    threshold_role: str
    event_load_policy: str
    taper_policy: str
    writer_semantic_notes: list[str] = Field(default_factory=list)


class ShortenedPhaseEntryModel(StrictOutputModel):
    """One shortened-phase summary entry carried in the selected scenario contract."""

    len: int = Field(ge=1)
    count: int = Field(ge=1)


class SelectedScenarioContractModel(StrictOutputModel):
    """Canonical full selected-scenario contract carried by Season and Phase runtime."""

    selected_scenario_id: Literal["A", "B", "C"]
    scenario_name: str
    selection_source: Literal["user", "system"]
    selection_rationale: str = ""
    load_posture: str
    recovery_margin: str
    fatigue_exposure: str
    specificity_density: str
    load_philosophy: str
    risk_profile: str
    best_suited_if: str
    key_differences: str
    main_payoff: str
    main_cost: str
    constraint_summary: list[str] = Field(default_factory=list)
    event_alignment_notes: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    kpi_guardrail_notes: list[str] = Field(default_factory=list)
    decision_notes: list[str] = Field(default_factory=list)
    season_archetype: str
    allowed_intensity_domains: list[str] = Field(default_factory=list)
    forbidden_intensity_domains: list[str] = Field(default_factory=list)
    deload_cadence: str
    phase_length_weeks: int = Field(ge=1)
    phase_count_expected: int = Field(ge=1)
    full_phases: int = Field(ge=0)
    shortened_phases: list[ShortenedPhaseEntryModel] = Field(default_factory=list)
    max_shortened_phases: int = Field(ge=0)
    shortening_budget_weeks: int = Field(ge=0)


class SeasonLoadEnvelopeRangeModel(StrictOutputModel):
    """Weighted expected weekly kJ range for the season bundle."""

    min: int
    max: int


class SeasonLoadEnvelopeModel(StrictOutputModel):
    """Deterministic season load-envelope handoff for the writer."""

    expected_average_weekly_kj_range: SeasonLoadEnvelopeRangeModel
    expected_high_load_weeks_count: int | None = None
    expected_deload_or_low_load_weeks_count: int | None = None


class RoleWeekLoadBandModel(StrictOutputModel):
    """Structured exact role-week load band authority."""

    week: str
    role: str
    band: SeasonLoadEnvelopeRangeModel


class SeasonPhaseBlueprintModel(StrictOutputModel):
    """Internal phase blueprint preserving selected-scenario cadence semantics."""

    phase_id: str
    iso_week_range: str
    scenario_cadence: str
    phase_type: str | None = None
    phase_intent: str | None = None
    build_subtype: str | None = None
    phase_taxonomy_version: str | None = None
    season_phase_role: str | None = None
    cadence_week_roles: list[str] = Field(default_factory=list)
    event_constraints: list[str] = Field(default_factory=list)
    load_corridor_min: int | None = None
    load_corridor_max: int | None = None
    availability_cap_kj: int | None = None
    baseline_load_kj: int | None = None
    role_week_load_bands: list[RoleWeekLoadBandModel | str] = Field(default_factory=list)
    progression_trace: list[str] = Field(default_factory=list)
    load_feasibility_status: str | None = None
    taper_intent: str | None = None
    allowed_domains: list[str] = Field(default_factory=list)
    forbidden_domains: list[str] = Field(default_factory=list)
    semantic_contract: SeasonPhaseSemanticContractModel | None = None
    warnings: list[str] = Field(default_factory=list)


class SeasonPhaseDraftBlueprintModel(StrictOutputModel):
    """Raw LLM-authored season phase blueprint before deterministic normalization."""

    phase_id: str
    iso_week_range: str
    scenario_cadence: str
    phase_type: str | None = None
    phase_intent: str | None = None
    build_subtype: str | None = None
    phase_taxonomy_version: str | None = None
    season_phase_role: str | None = None
    cadence_week_roles: list[str] = Field(default_factory=list)
    event_constraints: list[str] = Field(default_factory=list)
    load_corridor_min: int | None = None
    load_corridor_max: int | None = None
    availability_cap_kj: int | None = None
    baseline_load_kj: int | None = None
    role_week_load_bands: list[RoleWeekLoadBandModel | str] = Field(default_factory=list)
    progression_trace: list[str] = Field(default_factory=list)
    load_feasibility_status: str | None = None
    taper_intent: str | None = None
    allowed_domains: list[str] = Field(default_factory=list)
    forbidden_domains: list[str] = Field(default_factory=list)
    semantic_contract: SeasonPhaseSemanticContractModel | None = None
    warnings: list[str] = Field(default_factory=list)


class ReplanInstructionModel(StrictOutputModel):
    """Structured replan instruction emitted by review crews."""

    target_specialists: list[str] = Field(default_factory=list)
    issues_to_fix: list[str] = Field(default_factory=list)
    must_preserve: list[str] = Field(default_factory=list)
    priority_order: list[str] = Field(default_factory=list)
    max_scope_of_change: str | None = None


class SeasonPlanBundleModel(StrictOutputModel):
    """Internal season planning bundle before review and writing."""

    selected_scenario_contract: SelectedScenarioContractModel | None = None
    context_summary: list[str] = Field(default_factory=list)
    scenario_interpretation: list[str] = Field(default_factory=list)
    event_priority: SeasonEventAnchorModel
    peak_window: list[str] = Field(default_factory=list)
    macrocycle: SeasonMacrocycleDraftModel
    constraints: list[ConstraintAuditModel] = Field(default_factory=list)
    load_governance: list[LoadGovernanceAuditModel] = Field(default_factory=list)
    phase_blueprints: list[SeasonPhaseBlueprintModel] = Field(default_factory=list)
    season_load_envelope: SeasonLoadEnvelopeModel | None = None
    season_semantic_notes: list[str] = Field(default_factory=list)
    decision_summary: list[str] = Field(default_factory=list)
    candidate_document_summary: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)


class SeasonPlanDraftBundleModel(StrictOutputModel):
    """Raw LLM-authored season plan bundle before deterministic normalization."""

    selected_scenario_contract: SelectedScenarioContractModel | None = None
    context_summary: list[str] = Field(default_factory=list)
    scenario_interpretation: list[str] = Field(default_factory=list)
    event_priority: SeasonEventAnchorModel
    peak_window: list[str] = Field(default_factory=list)
    macrocycle: SeasonMacrocycleDraftModel
    constraints: list[ConstraintAuditModel] = Field(default_factory=list)
    load_governance: list[LoadGovernanceAuditModel] = Field(default_factory=list)
    phase_blueprints: list[SeasonPhaseDraftBlueprintModel] = Field(default_factory=list)
    season_load_envelope: SeasonLoadEnvelopeModel | None = None
    season_semantic_notes: list[str] = Field(default_factory=list)
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


class PhasePersistedLoadBandModel(StrictOutputModel):
    """Structured persisted load band with deterministic notes."""

    min: int | float
    max: int | float
    notes: str | None = None


class PhaseWeeklyKjBandModel(StrictOutputModel):
    """One persisted weekly kJ band row for phase artifacts."""

    week: str
    band: PhasePersistedLoadBandModel


class PhaseSummaryModel(StrictOutputModel):
    """Structured summary block used by PHASE_GUARDRAILS and preview intent summaries."""

    primary_objective: str | None = None
    secondary_objectives: list[str] = Field(default_factory=list)
    non_negotiables: list[str] = Field(default_factory=list)
    key_risks_warnings: list[str] = Field(default_factory=list)


class PhaseQualityDensityModel(StrictOutputModel):
    """Structured quality-density and intensity handling semantics."""

    quality_intent: str | None = None
    max_quality_days_per_week: int | None = None
    forbidden_intensity_domains: list[str] = Field(default_factory=list)


class PhaseAllowedForbiddenSemanticsModel(StrictOutputModel):
    """Structured legality block for phase guardrails."""

    allowed_day_roles: list[str] = Field(default_factory=list)
    forbidden_day_roles: list[str] = Field(default_factory=list)
    allowed_intensity_domains: list[str] = Field(default_factory=list)
    forbidden_intensity_domains: list[str] = Field(default_factory=list)
    allowed_load_modalities: list[str] = Field(default_factory=list)
    forbidden_load_modalities: list[str] = Field(default_factory=list)
    quality_density: PhaseQualityDensityModel = Field(default_factory=PhaseQualityDensityModel)


class PhaseEventConstraintModel(StrictOutputModel):
    """Structured event constraint row for phase guardrails."""

    date: str | None = None
    week: str | None = None
    type: str | None = None
    constraint: str | None = None


class PhaseEventsConstraintsModel(StrictOutputModel):
    """Structured events and logistics constraints for phase guardrails."""

    events: list[PhaseEventConstraintModel] = Field(default_factory=list)
    logistics_time_constraints: list[str] = Field(default_factory=list)


class PhaseExecutionNonNegotiablesModel(StrictOutputModel):
    """Structured non-negotiables for phase guardrails."""

    recovery_protection_rules: str | None = None
    long_endurance_anchor_protection: str | None = None
    minimum_recovery_opportunities: str | None = None
    no_catch_up_rule: str | None = None


class PhaseLoadGuardrailsModel(StrictOutputModel):
    """Structured load guardrails for phase guardrails payloads."""

    weekly_kj_bands: list[PhaseWeeklyKjBandModel] = Field(default_factory=list)
    confidence_assumptions: list[str] = Field(default_factory=list)


class PhaseGuardrailsPayloadModel(StrictOutputModel):
    """Internal phase draft for guardrails payload content."""

    inherited_scenario_contract: SelectedScenarioContractModel | None = None
    phase_summary: PhaseSummaryModel = Field(default_factory=PhaseSummaryModel)
    phase_intent: str | None = None
    load_guardrails: PhaseLoadGuardrailsModel = Field(default_factory=PhaseLoadGuardrailsModel)
    allowed_forbidden_semantics: PhaseAllowedForbiddenSemanticsModel = Field(
        default_factory=PhaseAllowedForbiddenSemanticsModel
    )
    events_constraints: PhaseEventsConstraintsModel = Field(default_factory=PhaseEventsConstraintsModel)
    execution_non_negotiables: PhaseExecutionNonNegotiablesModel = Field(
        default_factory=PhaseExecutionNonNegotiablesModel
    )


class PhaseUpstreamIntentModel(StrictOutputModel):
    """Structured upstream phase intent block for phase structure."""

    phase_intent: str | None = None
    phase_taxonomy_version: str | None = None
    phase_type: str | None = None
    build_subtype: str | None = None
    primary_objective: str | None = None
    phase_status: str | None = None
    non_negotiables: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    key_risks_warnings: list[str] = Field(default_factory=list)


class PhaseLoadRangesModel(StrictOutputModel):
    """Structured load ranges block for phase structure."""

    weekly_kj_bands: list[PhaseWeeklyKjBandModel] = Field(default_factory=list)
    source: str | None = None


class PhaseRecoveryProtectionModel(StrictOutputModel):
    """Structured recovery-protection block for phase structure."""

    fixed_non_training_days: list[str] = Field(default_factory=list)


class PhaseExecutionPrinciplesModel(StrictOutputModel):
    """Structured execution-principles block for phase structure."""

    load_intensity_handling: PhaseQualityDensityModel = Field(default_factory=PhaseQualityDensityModel)
    recovery_protection: PhaseRecoveryProtectionModel = Field(default_factory=PhaseRecoveryProtectionModel)
    consistency_over_optimization: str | None = None
    phase_role: str | None = None


class PhaseStructuralElementsModel(StrictOutputModel):
    """Structured structural legality block for phase structure."""

    allowed_day_roles: list[str] = Field(default_factory=list)
    allowed_intensity_domains: list[str] = Field(default_factory=list)
    allowed_load_modalities: list[str] = Field(default_factory=list)


class PhaseWeekRoleEntryModel(StrictOutputModel):
    """One week-role row inside the shared phase skeleton."""

    week: str
    role: str


class PhaseWeekRolesModel(StrictOutputModel):
    """Wrapper for structured week-role rows."""

    week_roles: list[PhaseWeekRoleEntryModel] = Field(default_factory=list)


class PhaseWeekSkeletonLogicModel(StrictOutputModel):
    """Structured week-skeleton logic for phase structure."""

    week_roles: PhaseWeekRolesModel = Field(default_factory=PhaseWeekRolesModel)
    mandatory_elements: list[str] = Field(default_factory=list)
    optional_elements: list[str] = Field(default_factory=list)
    forbidden_patterns: list[str] = Field(default_factory=list)


class PhaseStructurePayloadModel(StrictOutputModel):
    """Internal phase draft for structural execution guidance."""

    inherited_scenario_contract: SelectedScenarioContractModel | None = None
    upstream_intent: PhaseUpstreamIntentModel = Field(default_factory=PhaseUpstreamIntentModel)
    phase_intent: str | None = None
    load_ranges: PhaseLoadRangesModel = Field(default_factory=PhaseLoadRangesModel)
    execution_principles: PhaseExecutionPrinciplesModel = Field(default_factory=PhaseExecutionPrinciplesModel)
    structural_phase_elements: PhaseStructuralElementsModel = Field(default_factory=PhaseStructuralElementsModel)
    week_skeleton_logic: PhaseWeekSkeletonLogicModel = Field(default_factory=PhaseWeekSkeletonLogicModel)
    adaptation_rules: list[str] = Field(default_factory=list)


class PhasePreviewAgendaDayModel(StrictOutputModel):
    """One day row inside the structured phase preview agenda."""

    day_of_week: str
    day_role: str
    intensity_domain: str
    load_modality: str
    notes: str | None = None


class PhasePreviewWeekAgendaModel(StrictOutputModel):
    """One structured phase preview week with exact day rows."""

    week: str
    days: list[PhasePreviewAgendaDayModel] = Field(default_factory=list)


class PhaseIntentSummaryModel(StrictOutputModel):
    """Structured phase intent summary for preview payloads."""

    phase_type: str | None = None
    phase_intent: str | None = None
    build_subtype: str | None = None
    phase_taxonomy_version: str | None = None
    primary_objective: str | None = None
    non_negotiables: list[str] = Field(default_factory=list)
    key_risks_warnings: list[str] = Field(default_factory=list)


class PhaseFeelOverviewModel(StrictOutputModel):
    """Structured high-level feel summary for preview payloads."""

    dominant_theme: str | None = None
    intensity_handling_conceptual: str | None = None
    recovery_protection_conceptual: str | None = None


class PhaseWeekToWeekNarrativeModel(StrictOutputModel):
    """Structured explanation of fixed versus flexible preview semantics."""

    direction: str | None = None
    what_will_not_change: str | None = None
    what_is_flexible: str | None = None


class PhasePreviewPayloadModel(StrictOutputModel):
    """Internal phase draft for preview-only narrative output."""

    phase_intent_summary: PhaseIntentSummaryModel = Field(default_factory=PhaseIntentSummaryModel)
    phase_intent: str | None = None
    feel_overview: PhaseFeelOverviewModel = Field(default_factory=PhaseFeelOverviewModel)
    weekly_agenda_preview: list[PhasePreviewWeekAgendaModel] = Field(default_factory=list)
    week_to_week_narrative: PhaseWeekToWeekNarrativeModel = Field(default_factory=PhaseWeekToWeekNarrativeModel)
    deviation_rules: list[str] = Field(default_factory=list)


class PhaseBundleDecisionModel(StrictOutputModel):
    """Internal manager summary for a full phase bundle."""

    cadence_source: str | None = None
    cadence_application_notes: list[str] = Field(default_factory=list)
    override_rationale: list[str] = Field(default_factory=list)


class PhaseWeekBlueprintModel(StrictOutputModel):
    """Internal phase week blueprint tying phase role, week role, and S5 band."""

    week: str
    phase_role: str | None = None
    phase_intent: str | None = None
    week_role: str
    s5_band_min: int | None = None
    s5_band_max: int | None = None
    role_progression_band: str | None = None
    allowed_domains: list[str] = Field(default_factory=list)
    event_implication: str | None = None
    warnings: list[str] = Field(default_factory=list)


class PhaseWeekDraftBlueprintModel(StrictOutputModel):
    """Raw LLM-authored phase week blueprint before deterministic normalization."""

    week: str
    phase_role: str | None = None
    phase_intent: str | None = None
    week_role: str
    s5_band_min: int | None = None
    s5_band_max: int | None = None
    role_progression_band: str | None = None
    allowed_domains: list[str] = Field(default_factory=list)
    event_implication: str | None = None
    warnings: list[str] = Field(default_factory=list)


class PhaseBundleModel(StrictOutputModel):
    """Internal season-authorized phase bundle before deterministic split."""

    phase_range: str
    phase_id: str | None = None
    phase_type: str | None = None
    phase_intent: str | None = None
    build_subtype: str | None = None
    cadence_source: str | None = None
    week_blueprints: list[PhaseWeekBlueprintModel] = Field(default_factory=list)
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


class PhaseDraftBundleModel(StrictOutputModel):
    """Raw LLM-authored phase bundle before deterministic normalization."""

    phase_range: str
    phase_id: str | None = None
    phase_type: str | None = None
    phase_intent: str | None = None
    build_subtype: str | None = None
    cadence_source: str | None = None
    week_blueprints: list[PhaseWeekDraftBlueprintModel] = Field(default_factory=list)
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


class WeekDayBlueprintModel(StrictOutputModel):
    """Internal day-level week execution blueprint before WEEK_PLAN writing."""

    day: Literal["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    date: str
    fixed_rest_day: bool = False
    availability_cap_minutes: int | None = None
    phase_role: str | None = None
    phase_intent: str | None = None
    phase_week_role: str | None = None
    day_role: str
    intended_domain: str | None = None
    planned_duration_minutes: int = 0
    planned_kj: int = 0
    workout_id: str | None = None
    event_implication: str | None = None
    warnings: list[str] = Field(default_factory=list)


class WeekWorkoutBlueprintModel(StrictOutputModel):
    """Internal workout blueprint for role-aware authoring and syntax review."""

    workout_id: str
    date: str
    phase_intent: str | None = None
    day_role: str
    intensity_domain: str | None = None
    workout_family: str | None = None
    family_variant: str | None = None
    protocol_type: str | None = None
    protocol_variant: str | None = None
    load_modality: str | None = None
    stimulus_class: str | None = None
    monotony_group: str | None = None
    selection_score: float | None = None
    selection_rule_row_ids: list[str] = Field(default_factory=list)
    generator_profile: str | None = None
    addon_policy: str | None = None
    primary_tiz_target_min: int | None = None
    target_kj: int | None = None
    progression_state: dict[str, Any] = Field(default_factory=dict, json_schema_extra={"additionalProperties": False})
    selection_reason: str | None = None
    activation_required: bool | None = None
    low_end_endurance: bool = False
    progression_parameters: dict[str, Any] = Field(default_factory=dict, json_schema_extra={"additionalProperties": False})
    phase_legality_status: Literal["unknown", "legal", "illegal"] = "unknown"
    planned_duration_minutes: int
    planned_kj: int
    required_sections: list[str] = Field(default_factory=list)
    syntax_profile: str = "RPS_INTERVALS_CYCLING_SUBSET"
    exportability_status: Literal["pending", "valid", "invalid"] = "pending"
    warnings: list[str] = Field(default_factory=list)


class WeekPlanBundleModel(StrictOutputModel):
    """Internal week planning bundle before review and writing."""

    context_summary: WeekContextAssessmentModel | None = None
    day_blueprints: list[WeekDayBlueprintModel] = Field(default_factory=list)
    workout_blueprints: list[WeekWorkoutBlueprintModel] = Field(default_factory=list)
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
