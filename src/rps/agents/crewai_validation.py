"""Contract validation and canonical meta normalization for CrewAI planning bundles."""

from __future__ import annotations

from typing import Any

from rps.agents.output_normalization import (
    normalize_workout_inline_loop_headers,
    normalize_workout_percent_ranges,
)
from rps.agents.runtime import AgentRuntime
from rps.crewai_runtime.guardrails import (
    season_bundle_matches_contract,
    season_bundle_review_readiness,
    week_bundle_review_readiness,
)
from rps.crewai_runtime.guardrails_phase import (
    phase_bundle_matches_context,
    phase_bundle_review_readiness,
    phase_week_role_load_coherence,
)
from rps.crewai_runtime.telemetry import emit_runtime_event
from rps.workspace.artifact_metadata import CANONICAL_OWNER_BY_ARTIFACT
from rps.workspace.types import ArtifactType

JsonMap = dict[str, Any]


def _raise_normalized_contract_failure(*, name: str, reason: object) -> None:
    """Raise a stable runtime error for normalized contract failures."""

    raise RuntimeError(f"{name}: {reason}")


def _validate_normalized_season_bundle(planning_bundle: JsonMap, *, runtime: AgentRuntime, athlete_id: str, run_id: str) -> JsonMap:
    """Validate the normalized season bundle before review/writer handoff."""

    checks = (
        ("season_bundle_matches_contract", season_bundle_matches_contract),
        ("season_bundle_review_readiness", season_bundle_review_readiness),
    )
    for name, fn in checks:
        ok, payload_or_reason = fn(planning_bundle)
        if ok:
            continue
        emit_runtime_event(
            root=runtime.workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            event_type="SEASON_BUNDLE_NORMALIZED_CONTRACT_FAILED",
            crew="season_planning",
            task="season_plan_finalize",
            component="crew:season_plan_finalize",
            reason=f"{name}: {payload_or_reason}",
        )
        _raise_normalized_contract_failure(name=name, reason=payload_or_reason)
    return planning_bundle


def _validate_normalized_phase_bundle(planning_bundle: JsonMap, *, runtime: AgentRuntime, athlete_id: str, run_id: str) -> JsonMap:
    """Validate the normalized phase bundle before review/writer handoff."""

    checks = (
        ("phase_bundle_matches_context", phase_bundle_matches_context),
        ("phase_week_role_load_coherence", phase_week_role_load_coherence),
        ("phase_bundle_review_readiness", phase_bundle_review_readiness),
    )
    for name, fn in checks:
        ok, payload_or_reason = fn(planning_bundle)
        if ok:
            continue
        emit_runtime_event(
            root=runtime.workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            event_type="PHASE_BUNDLE_NORMALIZED_CONTRACT_FAILED",
            crew="phase_planning",
            task="phase_bundle_finalize",
            component="crew:phase_bundle_finalize",
            reason=f"{name}: {payload_or_reason}",
        )
        _raise_normalized_contract_failure(name=name, reason=payload_or_reason)
    return planning_bundle


def _validate_normalized_week_bundle(planning_bundle: JsonMap, *, runtime: AgentRuntime, athlete_id: str, run_id: str) -> JsonMap:
    """Validate the week bundle before review/writer handoff."""

    checks = (("week_bundle_review_readiness", week_bundle_review_readiness),)
    for name, fn in checks:
        ok, payload_or_reason = fn(planning_bundle)
        if ok:
            continue
        emit_runtime_event(
            root=runtime.workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            event_type="WEEK_BUNDLE_NORMALIZED_CONTRACT_FAILED",
            crew="week_planning",
            task="week_plan_finalize",
            component="crew:week_plan_finalize",
            reason=f"{name}: {payload_or_reason}",
        )
        _raise_normalized_contract_failure(name=name, reason=payload_or_reason)
    return planning_bundle


def _normalize_artifact_meta(document: JsonMap, artifact_type: ArtifactType) -> JsonMap:
    """Apply canonical meta ownership for persisted artifact envelopes."""

    if not isinstance(document, dict):
        return document
    meta = document.get("meta")
    if not isinstance(meta, dict):
        return document
    meta.setdefault("authority", "Binding")
    owner = CANONICAL_OWNER_BY_ARTIFACT.get(artifact_type)
    if owner:
        meta["owner_agent"] = owner
    document["meta"] = meta
    return document


def _normalize_week_plan_meta(document: JsonMap) -> JsonMap:
    """Coerce WEEK_PLAN header constants to the canonical schema values."""

    if not isinstance(document, dict):
        return document
    meta = document.get("meta")
    if not isinstance(meta, dict):
        return document
    meta["artifact_type"] = "WEEK_PLAN"
    meta["schema_id"] = "WeekPlanInterface"
    meta["schema_version"] = "1.2"
    meta["authority"] = "Binding"
    meta["owner_agent"] = "Week-Artifact-Writer"
    if "notes" not in meta or meta.get("notes") is None:
        meta["notes"] = ""
    document["meta"] = meta
    data = document.get("data")
    if isinstance(data, dict):
        workouts = data.get("workouts")
        if isinstance(workouts, list):
            for workout in workouts:
                if not isinstance(workout, dict):
                    continue
                workout_text = workout.get("workout_text")
                if isinstance(workout_text, str):
                    workout["workout_text"] = normalize_workout_inline_loop_headers(
                        normalize_workout_percent_ranges(workout_text)
                    )
            data["workouts"] = workouts
        document["data"] = data
    return document


def _normalize_des_analysis_report(document: JsonMap) -> JsonMap:
    """Coerce DES analysis report constants to the canonical schema values."""

    if not isinstance(document, dict):
        return document
    meta = document.get("meta")
    if isinstance(meta, dict):
        meta["artifact_type"] = "DES_ANALYSIS_REPORT"
        meta["schema_id"] = "DESAnalysisInterface"
        meta["schema_version"] = "1.1"
        meta["authority"] = "Binding"
        meta["owner_agent"] = CANONICAL_OWNER_BY_ARTIFACT[ArtifactType.DES_ANALYSIS_REPORT]
        if "notes" not in meta or meta.get("notes") is None:
            meta["notes"] = ""
        document["meta"] = meta
    data = document.get("data")
    if isinstance(data, dict):
        rec = data.get("recommendation")
        if isinstance(rec, dict):
            rec["type"] = "advisory"
            rec["scope"] = "Season-Planner"
            data["recommendation"] = rec
        document["data"] = data
    return document
