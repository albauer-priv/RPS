import json
from pathlib import Path

from rps.ui.performance_corridors import (
    normalize_iso_label,
    phase_guardrails_by_week,
    planned_weekly_kj_by_week,
    sorted_labels,
    trim_past_labels,
    week_plan_corridor_by_week,
)
from rps.workspace.iso_helpers import IsoWeek
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_phase_guardrails_by_week_uses_latest_version_per_week(tmp_path):
    store = LocalArtifactStore(root=tmp_path)
    athlete_id = "test_athlete"
    store.ensure_workspace(athlete_id)

    older_payload = {
        "meta": {
            "created_at": "2026-04-24T12:00:00Z",
        },
        "data": {
            "load_guardrails": {
                "weekly_kj_bands": [
                    {"week": "2026-17", "band": {"min": 7000, "max": 8200}},
                    {"week": "2026-18", "band": {"min": 7100, "max": 8300}},
                ]
            }
        },
    }
    newer_payload = {
        "meta": {
            "created_at": "2026-04-24T16:00:00Z",
        },
        "data": {
            "load_guardrails": {
                "weekly_kj_bands": [
                    {"week": "2026-17", "band": {"min": 7200, "max": 8600}},
                ]
            }
        },
    }

    _write_json(
        store.versioned_path(athlete_id, ArtifactType.PHASE_GUARDRAILS, "2026-17--2026-19__20260424_120000"),
        older_payload,
    )
    _write_json(
        store.versioned_path(athlete_id, ArtifactType.PHASE_GUARDRAILS, "2026-17--2026-19__20260424_160000"),
        newer_payload,
    )

    corridor = phase_guardrails_by_week(store, athlete_id)

    assert corridor["2026-17"] == {"min": 7200, "max": 8600}
    assert corridor["2026-18"] == {"min": 7100, "max": 8300}


def test_phase_guardrails_by_week_handles_missing_created_at(tmp_path):
    store = LocalArtifactStore(root=tmp_path)
    athlete_id = "test_athlete"
    store.ensure_workspace(athlete_id)

    _write_json(
        store.versioned_path(athlete_id, ArtifactType.PHASE_GUARDRAILS, "2026-17--2026-19__20260424_120000"),
        {
            "meta": {},
            "data": {
                "load_guardrails": {
                    "weekly_kj_bands": [
                        {"week": "2026-17", "band": {"min": 7000, "max": 8200}},
                    ]
                }
            },
        },
    )
    _write_json(
        store.versioned_path(athlete_id, ArtifactType.PHASE_GUARDRAILS, "2026-17--2026-19__20260424_160000"),
        {
            "meta": {"created_at": "2026-04-24T16:00:00Z"},
            "data": {
                "load_guardrails": {
                    "weekly_kj_bands": [
                        {"week": "2026-17", "band": {"min": 7200, "max": 8600}},
                    ]
                }
            },
        },
    )

    corridor = phase_guardrails_by_week(store, athlete_id)

    assert corridor["2026-17"] == {"min": 7200, "max": 8600}


def test_sorted_labels_includes_all_series_not_only_season():
    labels = sorted_labels(
        {"2026-W17": {"min": 7600, "max": 9000}},
        {"2026-18": {"min": 7200, "max": 8600}},
        {},
        {"2026-W19": 7800.0},
        {"2026-20": 7900.0},
    )

    assert labels == ["2026-W17", "2026-W18", "2026-W19", "2026-W20"]


def test_normalize_iso_label_accepts_both_week_formats():
    assert normalize_iso_label("2026-17") == "2026-W17"
    assert normalize_iso_label("2026-W17") == "2026-W17"


def test_trim_past_labels_limits_history_but_keeps_future():
    labels = [
        "2026-W03",
        "2026-W04",
        "2026-W05",
        "2026-W06",
        "2026-W07",
        "2026-W08",
        "2026-W09",
        "2026-W10",
        "2026-W11",
        "2026-W12",
        "2026-W13",
        "2026-W14",
        "2026-W15",
        "2026-W16",
        "2026-W17",
        "2026-W18",
        "2026-W19",
    ]

    trimmed = trim_past_labels(labels, IsoWeek(2026, 17), 12)

    assert trimmed == [
        "2026-W06",
        "2026-W07",
        "2026-W08",
        "2026-W09",
        "2026-W10",
        "2026-W11",
        "2026-W12",
        "2026-W13",
        "2026-W14",
        "2026-W15",
        "2026-W16",
        "2026-W17",
        "2026-W18",
        "2026-W19",
    ]


def test_week_plan_helpers_use_latest_version_per_week(tmp_path):
    store = LocalArtifactStore(root=tmp_path)
    athlete_id = "test_athlete"
    store.ensure_workspace(athlete_id)

    _write_json(
        store.versioned_path(athlete_id, ArtifactType.WEEK_PLAN, "2026-17__20260424_120000"),
        {
            "meta": {"iso_week": "2026-17", "created_at": "2026-04-24T12:00:00Z"},
            "data": {
                "week_summary": {
                    "weekly_load_corridor_kj": {"min": 7000, "max": 8200},
                    "planned_weekly_load_kj": 7600,
                }
            },
        },
    )
    _write_json(
        store.versioned_path(athlete_id, ArtifactType.WEEK_PLAN, "2026-17__20260424_160000"),
        {
            "meta": {"iso_week": "2026-W17", "created_at": "2026-04-24T16:00:00Z"},
            "data": {
                "week_summary": {
                    "weekly_load_corridor_kj": {"min": 7200, "max": 8600},
                    "planned_weekly_load_kj": 7800,
                }
            },
        },
    )
    _write_json(
        store.versioned_path(athlete_id, ArtifactType.WEEK_PLAN, "2026-18__20260424_160000"),
        {
            "meta": {"iso_week": "2026-18", "created_at": "2026-04-24T16:00:00Z"},
            "data": {
                "week_summary": {
                    "weekly_load_corridor_kj": {"min": 7100, "max": 8400},
                    "planned_weekly_load_kj": 7750,
                }
            },
        },
    )

    corridors = week_plan_corridor_by_week(store, athlete_id)
    planned = planned_weekly_kj_by_week(store, athlete_id)

    assert corridors["2026-W17"] == {"min": 7200, "max": 8600}
    assert planned["2026-W17"] == 7800.0
    assert corridors["2026-W18"] == {"min": 7100, "max": 8400}
    assert planned["2026-W18"] == 7750.0


def test_week_plan_helpers_handle_missing_created_at(tmp_path):
    store = LocalArtifactStore(root=tmp_path)
    athlete_id = "test_athlete"
    store.ensure_workspace(athlete_id)

    _write_json(
        store.versioned_path(athlete_id, ArtifactType.WEEK_PLAN, "2026-17__20260424_120000"),
        {
            "meta": {"iso_week": "2026-17"},
            "data": {
                "week_summary": {
                    "weekly_load_corridor_kj": {"min": 7000, "max": 8200},
                    "planned_weekly_load_kj": 7600,
                }
            },
        },
    )
    _write_json(
        store.versioned_path(athlete_id, ArtifactType.WEEK_PLAN, "2026-17__20260424_160000"),
        {
            "meta": {"iso_week": "2026-17", "created_at": "2026-04-24T16:00:00Z"},
            "data": {
                "week_summary": {
                    "weekly_load_corridor_kj": {"min": 7200, "max": 8600},
                    "planned_weekly_load_kj": 7800,
                }
            },
        },
    )

    corridors = week_plan_corridor_by_week(store, athlete_id)
    planned = planned_weekly_kj_by_week(store, athlete_id)

    assert corridors["2026-W17"] == {"min": 7200, "max": 8600}
    assert planned["2026-W17"] == 7800.0
