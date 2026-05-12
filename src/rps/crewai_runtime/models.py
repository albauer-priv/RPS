"""Typed operation models aligned with future CrewAI task outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


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
