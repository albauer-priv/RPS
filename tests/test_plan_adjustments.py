"""Tests for input-driven plan adjustment suggestions (FEAT_plan_adjustments)."""

from __future__ import annotations

from pathlib import Path

import pytest

from rps.orchestrator.plan_adjustments import (
    INPUT_PLAN_DEPS,
    get_adjustment_suggestions,
)
from rps.workspace.index_manager import WorkspaceIndexManager
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType, Authority

ATHLETE = "test_athlete"

TS_OLD = "2026-01-01T10:00:00+00:00"
TS_NEW = "2026-01-02T10:00:00+00:00"


def _make_store(root: Path) -> LocalArtifactStore:
    return LocalArtifactStore(root=root)


def _save_artifact(store: LocalArtifactStore, athlete_id: str, artifact_type: ArtifactType) -> None:
    store.save_version(
        athlete_id,
        artifact_type,
        "v_test",
        {"dummy": True},
        authority=Authority.BINDING,
        producer_agent="test",
        run_id="run_test",
        update_latest=True,
    )


def _patch_index_created_at(
    root: Path,
    athlete_id: str,
    artifact_type: ArtifactType,
    created_at: str,
) -> None:
    """Overwrite the `created_at` in index.json for the latest record of the given artifact."""
    mgr = WorkspaceIndexManager(root=root, athlete_id=athlete_id)
    index = mgr.load()
    artefacts = index.get("artefacts")
    assert isinstance(artefacts, dict), "artefacts missing"
    entry = artefacts.get(artifact_type.value)
    assert isinstance(entry, dict), f"{artifact_type.value} entry missing"
    latest = entry.get("latest")
    assert isinstance(latest, dict), f"{artifact_type.value} latest missing"
    latest["created_at"] = created_at
    versions = entry.get("versions", {})
    if isinstance(versions, dict):
        for _vk, record in versions.items():
            if isinstance(record, dict):
                record["created_at"] = created_at
    mgr.save(index)


def _load_index(root: Path, athlete_id: str) -> dict:
    mgr = WorkspaceIndexManager(root=root, athlete_id=athlete_id)
    return mgr.load()


# ---------------------------------------------------------------------------
# One suggestion per dependency row when input is newer than plan
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "input_type,plan_type,scope",
    [(row[0], row[2], row[4]) for row in INPUT_PLAN_DEPS],
)
def test_suggestion_when_input_newer(
    tmp_path: Path,
    input_type: ArtifactType,
    plan_type: ArtifactType,
    scope: str,
) -> None:
    store = _make_store(tmp_path)
    _save_artifact(store, ATHLETE, input_type)
    _save_artifact(store, ATHLETE, plan_type)
    _patch_index_created_at(tmp_path, ATHLETE, input_type, TS_NEW)
    _patch_index_created_at(tmp_path, ATHLETE, plan_type, TS_OLD)
    index = _load_index(tmp_path, ATHLETE)
    suggestions = get_adjustment_suggestions(index, store, ATHLETE)
    assert any(s.scope == scope for s in suggestions), f"Expected scope {scope!r} in suggestions"


@pytest.mark.parametrize(
    "input_type,plan_type,scope",
    [(row[0], row[2], row[4]) for row in INPUT_PLAN_DEPS],
)
def test_no_suggestion_when_input_older(
    tmp_path: Path,
    input_type: ArtifactType,
    plan_type: ArtifactType,
    scope: str,
) -> None:
    store = _make_store(tmp_path)
    _save_artifact(store, ATHLETE, input_type)
    _save_artifact(store, ATHLETE, plan_type)
    _patch_index_created_at(tmp_path, ATHLETE, input_type, TS_OLD)
    _patch_index_created_at(tmp_path, ATHLETE, plan_type, TS_NEW)
    index = _load_index(tmp_path, ATHLETE)
    suggestions = get_adjustment_suggestions(index, store, ATHLETE)
    assert not any(s.scope == scope for s in suggestions), f"Unexpected scope {scope!r}"


@pytest.mark.parametrize(
    "input_type,plan_type,scope",
    [(row[0], row[2], row[4]) for row in INPUT_PLAN_DEPS],
)
def test_no_suggestion_when_input_missing(
    tmp_path: Path,
    input_type: ArtifactType,
    plan_type: ArtifactType,
    scope: str,
) -> None:
    store = _make_store(tmp_path)
    # Only save the plan artifact, not the input
    _save_artifact(store, ATHLETE, plan_type)
    _patch_index_created_at(tmp_path, ATHLETE, plan_type, TS_OLD)
    index = _load_index(tmp_path, ATHLETE)
    suggestions = get_adjustment_suggestions(index, store, ATHLETE)
    assert not any(s.scope == scope for s in suggestions)


@pytest.mark.parametrize(
    "input_type,plan_type,scope",
    [(row[0], row[2], row[4]) for row in INPUT_PLAN_DEPS],
)
def test_no_suggestion_when_plan_missing(
    tmp_path: Path,
    input_type: ArtifactType,
    plan_type: ArtifactType,
    scope: str,
) -> None:
    store = _make_store(tmp_path)
    # Only save the input, not the plan artifact
    _save_artifact(store, ATHLETE, input_type)
    _patch_index_created_at(tmp_path, ATHLETE, input_type, TS_NEW)
    index = _load_index(tmp_path, ATHLETE)
    suggestions = get_adjustment_suggestions(index, store, ATHLETE)
    assert not any(s.scope == scope for s in suggestions)


# ---------------------------------------------------------------------------
# Scope deduplication: ATHLETE_PROFILE and PLANNING_EVENTS both map to Season Plan
# ---------------------------------------------------------------------------


def test_season_plan_scope_deduplicated(tmp_path: Path) -> None:
    """Both ATHLETE_PROFILE and PLANNING_EVENTS map to Season Plan; one suggestion expected."""
    store = _make_store(tmp_path)
    _save_artifact(store, ATHLETE, ArtifactType.ATHLETE_PROFILE)
    _save_artifact(store, ATHLETE, ArtifactType.PLANNING_EVENTS)
    _save_artifact(store, ATHLETE, ArtifactType.SEASON_PLAN)
    _patch_index_created_at(tmp_path, ATHLETE, ArtifactType.ATHLETE_PROFILE, TS_NEW)
    _patch_index_created_at(tmp_path, ATHLETE, ArtifactType.PLANNING_EVENTS, TS_NEW)
    _patch_index_created_at(tmp_path, ATHLETE, ArtifactType.SEASON_PLAN, TS_OLD)
    index = _load_index(tmp_path, ATHLETE)
    suggestions = get_adjustment_suggestions(index, store, ATHLETE)
    season_plan_suggestions = [s for s in suggestions if s.scope == "Season Plan"]
    assert len(season_plan_suggestions) == 1


def test_season_plan_scope_keeps_most_recent_input(tmp_path: Path) -> None:
    """When both inputs map to Season Plan, the newer one is shown."""
    store = _make_store(tmp_path)
    _save_artifact(store, ATHLETE, ArtifactType.ATHLETE_PROFILE)
    _save_artifact(store, ATHLETE, ArtifactType.PLANNING_EVENTS)
    _save_artifact(store, ATHLETE, ArtifactType.SEASON_PLAN)
    _patch_index_created_at(tmp_path, ATHLETE, ArtifactType.ATHLETE_PROFILE, "2026-01-05T10:00:00+00:00")
    _patch_index_created_at(tmp_path, ATHLETE, ArtifactType.PLANNING_EVENTS, "2026-01-03T10:00:00+00:00")
    _patch_index_created_at(tmp_path, ATHLETE, ArtifactType.SEASON_PLAN, TS_OLD)
    index = _load_index(tmp_path, ATHLETE)
    suggestions = get_adjustment_suggestions(index, store, ATHLETE)
    sp = next(s for s in suggestions if s.scope == "Season Plan")
    assert sp.input_artifact_type == ArtifactType.ATHLETE_PROFILE


# ---------------------------------------------------------------------------
# Sort order: Season Plan > Phase > Week Plan
# ---------------------------------------------------------------------------


def test_suggestions_sorted_by_priority(tmp_path: Path) -> None:
    store = _make_store(tmp_path)
    for artifact_type in [
        ArtifactType.ATHLETE_PROFILE,
        ArtifactType.AVAILABILITY,
        ArtifactType.LOGISTICS,
        ArtifactType.SEASON_PLAN,
        ArtifactType.PHASE_GUARDRAILS,
        ArtifactType.WEEK_PLAN,
    ]:
        _save_artifact(store, ATHLETE, artifact_type)
        _patch_index_created_at(tmp_path, ATHLETE, artifact_type, TS_OLD)

    # Make all inputs newer than all plan artifacts
    _patch_index_created_at(tmp_path, ATHLETE, ArtifactType.ATHLETE_PROFILE, TS_NEW)
    _patch_index_created_at(tmp_path, ATHLETE, ArtifactType.AVAILABILITY, TS_NEW)
    _patch_index_created_at(tmp_path, ATHLETE, ArtifactType.LOGISTICS, TS_NEW)

    index = _load_index(tmp_path, ATHLETE)
    suggestions = get_adjustment_suggestions(index, store, ATHLETE)
    scopes = [s.scope for s in suggestions]
    assert scopes == sorted(scopes, key=lambda x: -{"Season Plan": 3, "Phase": 2, "Week Plan": 1}.get(x, 0))


# ---------------------------------------------------------------------------
# No suggestions when nothing is stale
# ---------------------------------------------------------------------------


def test_no_suggestions_all_current(tmp_path: Path) -> None:
    store = _make_store(tmp_path)
    for artifact_type in [
        ArtifactType.ATHLETE_PROFILE,
        ArtifactType.PLANNING_EVENTS,
        ArtifactType.AVAILABILITY,
        ArtifactType.LOGISTICS,
        ArtifactType.SEASON_PLAN,
        ArtifactType.PHASE_GUARDRAILS,
        ArtifactType.WEEK_PLAN,
    ]:
        _save_artifact(store, ATHLETE, artifact_type)
        _patch_index_created_at(tmp_path, ATHLETE, artifact_type, TS_OLD)
    # All inputs are old, all plan artifacts are new
    for plan_type in [ArtifactType.SEASON_PLAN, ArtifactType.PHASE_GUARDRAILS, ArtifactType.WEEK_PLAN]:
        _patch_index_created_at(tmp_path, ATHLETE, plan_type, TS_NEW)
    index = _load_index(tmp_path, ATHLETE)
    suggestions = get_adjustment_suggestions(index, store, ATHLETE)
    assert suggestions == []


# ---------------------------------------------------------------------------
# Suggestion fields are correctly populated
# ---------------------------------------------------------------------------


def test_suggestion_fields(tmp_path: Path) -> None:
    store = _make_store(tmp_path)
    _save_artifact(store, ATHLETE, ArtifactType.AVAILABILITY)
    _save_artifact(store, ATHLETE, ArtifactType.PHASE_GUARDRAILS)
    _patch_index_created_at(tmp_path, ATHLETE, ArtifactType.AVAILABILITY, TS_NEW)
    _patch_index_created_at(tmp_path, ATHLETE, ArtifactType.PHASE_GUARDRAILS, TS_OLD)
    index = _load_index(tmp_path, ATHLETE)
    suggestions = get_adjustment_suggestions(index, store, ATHLETE)
    assert len(suggestions) == 1
    s = suggestions[0]
    assert s.input_artifact_type == ArtifactType.AVAILABILITY
    assert s.input_label == "Availability"
    assert s.plan_artifact_type == ArtifactType.PHASE_GUARDRAILS
    assert s.plan_label == "Phase"
    assert s.scope == "Phase"
    assert s.input_created_at == TS_NEW
    assert s.plan_created_at == TS_OLD
