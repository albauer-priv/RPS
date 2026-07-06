from rps.planning.deterministic_context import _resolve_phase_execution_roles
from rps.workspace.iso_helpers import IsoWeek


def test_resolve_phase_execution_roles_prefers_active_slot_values() -> None:
    resolution = _resolve_phase_execution_roles(
        weeks=[IsoWeek(2026, 12), IsoWeek(2026, 13), IsoWeek(2026, 14)],
        active_slot={
            "scenario_cadence": "2:1",
            "cadence_week_roles": ["LOAD_1", "LOAD_2", "DELOAD"],
        },
        phase_raw={},
    )

    assert resolution.scenario_cadence == "2:1"
    assert resolution.cadence_week_roles == ("LOAD_1", "LOAD_2", "DELOAD")
    assert resolution.week_role_by_iso_week == {
        "2026-12": "LOAD_1",
        "2026-13": "LOAD_2",
        "2026-14": "DELOAD",
    }
    assert resolution.blocking_issues == ()
    assert resolution.used_fallbacks == ()


def test_resolve_phase_execution_roles_falls_back_to_phase_raw_and_pattern() -> None:
    resolution = _resolve_phase_execution_roles(
        weeks=[IsoWeek(2026, 12), IsoWeek(2026, 13), IsoWeek(2026, 14)],
        active_slot={},
        phase_raw={"scenario_cadence": "2:1"},
    )

    assert resolution.scenario_cadence == "2:1"
    assert resolution.cadence_week_roles == ("LOAD_1", "LOAD_2", "DELOAD")
    assert resolution.used_fallbacks == (
        "scenario_cadence_from_phase_raw",
        "cadence_week_roles_from_cadence_pattern",
    )
    assert resolution.blocking_issues == ()


def test_resolve_phase_execution_roles_falls_back_to_phase_raw_roles() -> None:
    resolution = _resolve_phase_execution_roles(
        weeks=[IsoWeek(2026, 12), IsoWeek(2026, 13), IsoWeek(2026, 14)],
        active_slot={},
        phase_raw={
            "deload_cadence": "2:1",
            "cadence_week_roles": ["LOAD_1", "LOAD_2", "DELOAD"],
        },
    )

    assert resolution.scenario_cadence == "2:1"
    assert resolution.cadence_week_roles == ("LOAD_1", "LOAD_2", "DELOAD")
    assert resolution.used_fallbacks == (
        "scenario_cadence_from_phase_raw",
        "cadence_week_roles_from_phase_raw",
    )
    assert resolution.blocking_issues == ()


def test_resolve_phase_execution_roles_reports_unsupported_cadence() -> None:
    resolution = _resolve_phase_execution_roles(
        weeks=[IsoWeek(2026, 12), IsoWeek(2026, 13), IsoWeek(2026, 14)],
        active_slot={},
        phase_raw={"scenario_cadence": "9:9"},
    )

    assert resolution.scenario_cadence == "9:9"
    assert resolution.cadence_week_roles == ()
    assert resolution.used_fallbacks == ("scenario_cadence_from_phase_raw",)
    assert resolution.blocking_issues == (
        "phase cadence week roles do not cover every phase week.",
        "scenario cadence is unsupported for deterministic phase roles.",
    )


def test_resolve_phase_execution_roles_reports_role_count_mismatch() -> None:
    resolution = _resolve_phase_execution_roles(
        weeks=[IsoWeek(2026, 12), IsoWeek(2026, 13), IsoWeek(2026, 14)],
        active_slot={
            "scenario_cadence": "2:1",
            "cadence_week_roles": ["LOAD_1", "LOAD_2"],
        },
        phase_raw={},
    )

    assert resolution.scenario_cadence == "2:1"
    assert resolution.cadence_week_roles == ("LOAD_1", "LOAD_2")
    assert resolution.week_role_by_iso_week == {
        "2026-12": "LOAD_1",
        "2026-13": "LOAD_2",
    }
    assert resolution.used_fallbacks == ()
    assert resolution.blocking_issues == (
        "phase cadence week roles do not cover every phase week.",
    )