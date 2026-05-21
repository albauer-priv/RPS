from __future__ import annotations

from rps.workspace.phase_intents import (
    PHASE_TAXONOMY_VERSION,
    normalize_phase_semantics,
    validate_phase_semantics,
)


def test_normalize_phase_semantics_maps_legacy_build_value_with_warning() -> None:
    semantics = normalize_phase_semantics(
        phase_type="Build",
        phase_intent="general_build",
        build_subtype="general_build",
    )

    assert semantics is not None
    assert semantics.phase_type == "BUILD"
    assert semantics.phase_intent == "threshold_build"
    assert semantics.build_subtype == "threshold_build"
    assert semantics.phase_taxonomy_version == PHASE_TAXONOMY_VERSION
    assert semantics.normalization_source == "legacy_mapping"
    assert semantics.legacy_phase_intent_raw == "general_build"
    assert semantics.normalization_warning


def test_normalize_phase_semantics_fails_closed_for_unknown_legacy_value() -> None:
    semantics = normalize_phase_semantics(
        phase_type="Build",
        phase_intent="mystery_build",
        build_subtype="mystery_build",
    )

    assert semantics is None


def test_validate_phase_semantics_rejects_legacy_new_write_value() -> None:
    errors = validate_phase_semantics(
        phase_type="BASE",
        phase_intent="foundation_mode",
        build_subtype=None,
    )

    assert errors
    assert any("Unknown phase_intent" in message for message in errors)


def test_validate_phase_semantics_requires_build_subtype_for_build() -> None:
    errors = validate_phase_semantics(
        phase_type="BUILD",
        phase_intent="threshold_build",
        build_subtype=None,
    )

    assert not errors

    mismatch_errors = validate_phase_semantics(
        phase_type="BUILD",
        phase_intent="threshold_build",
        build_subtype="vo2_build",
    )

    assert mismatch_errors
    assert any("build_subtype" in message for message in mismatch_errors)
