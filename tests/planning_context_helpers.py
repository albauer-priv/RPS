import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from rps.workspace.index_exact import IndexExactQuery
from rps.workspace.iso_helpers import IsoWeek, previous_iso_week
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType


def seed_previous_week_planning_evidence(
    store: LocalArtifactStore,
    athlete_id: str,
    *,
    target_year: int,
    target_week: int,
) -> None:
    evidence_week = previous_iso_week(IsoWeek(target_year, target_week))
    version_key = f"{evidence_week.year:04d}-{evidence_week.week:02d}"
    store.save_document(
        athlete_id,
        ArtifactType.HISTORICAL_BASELINE,
        "baseline",
        {
            "data": {
                "metrics": {"kj_per_year": 120000, "kj_per_activity": 650, "long_ride_tolerance_kj": 2200},
                "source": {"source_type": "test", "range": "3y"},
            }
        },
        producer_agent="test",
        run_id="historical-baseline",
        update_latest=True,
    )
    store.save_document(
        athlete_id,
        ArtifactType.ACTIVITIES_ACTUAL,
        version_key,
        {"data": {"activities": []}},
        producer_agent="test",
        run_id=f"activities-actual-{version_key}",
        update_latest=True,
    )
    store.save_document(
        athlete_id,
        ArtifactType.ACTIVITIES_TREND,
        version_key,
        {
            "data": {
                "weekly_trends": [
                    {
                        "year": evidence_week.year,
                        "iso_week": evidence_week.week,
                        "weekly_aggregates": {"activity_count": 4, "moving_time": "10:30", "work_kj": 6400},
                        "intensity_load_metrics": {"durability_index": 0.91},
                    }
                ]
            }
        },
        producer_agent="test",
        run_id=f"activities-trend-{version_key}",
        update_latest=True,
    )


def write_minimal_scenario_chain(
    store: LocalArtifactStore,
    athlete_id: str,
    *,
    version_key: str = "2026-12",
    horizon_weeks: int = 3,
    cadence: str = "2:1",
    selected_scenario_id: str = "A",
) -> None:
    phase_length = {"2:1": 3, "3:1": 4, "2:1:1": 4}[cadence]
    phase_count = (horizon_weeks + phase_length - 1) // phase_length
    shortened_len = horizon_weeks - ((phase_count - 1) * phase_length)
    shortened = [{"len": shortened_len, "count": 1}] if shortened_len < phase_length else []
    full_phases = phase_count - len(shortened)
    store.save_document(
        athlete_id,
        ArtifactType.SEASON_SCENARIOS,
        version_key,
        {
            "meta": {
                "artifact_type": "SEASON_SCENARIOS",
                "version_key": version_key,
                "run_id": f"store_scenarios_{version_key}",
            },
            "data": {
                "planning_horizon_weeks": horizon_weeks,
                "scenarios": [
                    {
                        "scenario_id": selected_scenario_id,
                        "name": "Minimal contract scenario",
                        "load_philosophy": "balanced_progressive",
                        "risk_profile": "medium",
                        "best_suited_if": "stable recovery",
                        "key_differences": "Balances continuity and progression.",
                        "main_payoff": "Repeatable load progression.",
                        "main_cost": "Less conservative than scenario A.",
                        "scenario_guidance": {
                            "deload_cadence": cadence,
                            "phase_length_weeks": phase_length,
                            "phase_count_expected": phase_count,
                            "max_shortened_phases": len(shortened),
                            "shortening_budget_weeks": 0 if not shortened else phase_length - shortened_len,
                            "phase_plan_summary": {
                                "full_phases": full_phases,
                                "shortened_phases": shortened,
                            },
                            "recovery_margin": "medium",
                            "fatigue_exposure": "moderate",
                            "specificity_density": "controlled",
                            "constraint_summary": ["Preserve continuity and legal intensity domains."],
                            "intensity_guidance": {
                                "allowed_domains": ["ENDURANCE", "TEMPO"],
                                "avoid_domains": ["VO2MAX"],
                            },
                            "event_alignment_notes": ["Test scenario anchor."],
                            "risk_flags": [],
                            "kpi_guardrail_notes": ["Stay repeatable."],
                            "decision_notes": ["Selected for testing."],
                        },
                    }
                ],
            },
        },
        producer_agent="test",
        run_id=f"store_scenarios_{version_key}",
        update_latest=True,
    )
    scenarios_doc = store.load_latest(athlete_id, ArtifactType.SEASON_SCENARIOS)
    scenarios_meta = scenarios_doc.get("meta", {}) if isinstance(scenarios_doc, dict) else {}
    actual_scenarios_version = scenarios_meta.get("version_key", version_key)
    actual_scenarios_run_id = scenarios_meta.get("run_id", f"store_scenarios_{version_key}")
    existing_selection: dict[str, object] = {}
    try:
        loaded = store.load_latest(athlete_id, ArtifactType.SEASON_SCENARIO_SELECTION)
        if isinstance(loaded, dict):
            existing_selection = loaded
    except Exception:
        existing_selection = {}
    selection_data = existing_selection.get("data")
    if not isinstance(selection_data, dict):
        selection_data = {}
    selection_data["selected_scenario_id"] = selected_scenario_id
    selection_data["season_scenarios_ref"] = actual_scenarios_version
    selection_data.setdefault("selection_source", "user")
    selection_data.setdefault("selection_rationale", "Test selection")
    selection_data.setdefault("notes", ["Selected in test helper."])
    selection_data.setdefault("kpi_moving_time_rate_guidance_selection", None)
    store.save_document(
        athlete_id,
        ArtifactType.SEASON_SCENARIO_SELECTION,
        version_key,
        {
            "meta": {
                "artifact_type": "SEASON_SCENARIO_SELECTION",
                "version_key": version_key,
                "run_id": f"store_selection_{version_key}",
                "trace_upstream": [
                    {
                        "artifact": "SEASON_SCENARIOS",
                        "version": actual_scenarios_version,
                        "version_key": actual_scenarios_version,
                        "run_id": actual_scenarios_run_id,
                    }
                ],
            },
            "data": selection_data,
        },
        producer_agent="test",
        run_id=f"store_selection_{version_key}",
        update_latest=True,
    )
    if not store.latest_exists(athlete_id, ArtifactType.ZONE_MODEL):
        store.save_document(
            athlete_id,
            ArtifactType.ZONE_MODEL,
            "zone_model",
            {
                "data": {
                    "model_metadata": {"ftp_watts": 300},
                    "zones": [
                        {
                            "zone_id": "Z2",
                            "name": "Endurance",
                            "ftp_percent_range": {"min": 56, "max": 75},
                            "typical_if": 0.66,
                        }
                    ],
                }
            },
            producer_agent="test",
            run_id="store_zone_model",
            update_latest=True,
        )


def write_minimal_availability(store: LocalArtifactStore, athlete_id: str) -> None:
    store.latest_path(athlete_id, ArtifactType.AVAILABILITY).write_text(
        json.dumps(
            {
                "data": {
                    "weekly_hours": {"min": 10.5, "typical": 14.0, "max": 17.5},
                    "fixed_rest_days": ["Mon", "Fri"],
                    "availability_table": [],
                    "source_type": "manual",
                    "source_ref": "test",
                    "notes": "",
                }
            }
        ),
        encoding="utf-8",
    )
    if not store.latest_exists(athlete_id, ArtifactType.ZONE_MODEL):
        store.save_document(
            athlete_id,
            ArtifactType.ZONE_MODEL,
            "zone_model",
            {
                "data": {
                    "model_metadata": {"ftp_watts": 300},
                    "zones": [
                        {
                            "zone_id": "Z2",
                            "name": "Endurance",
                            "ftp_percent_range": {"min": 56, "max": 75},
                            "typical_if": 0.66,
                        }
                    ],
                }
            },
            producer_agent="test",
            run_id="store_zone_model",
            update_latest=True,
        )


def seed_minimal_phase_test_context(
    store: LocalArtifactStore,
    athlete_id: str,
    *,
    target_year: int,
    target_week: int,
) -> None:
    seed_previous_week_planning_evidence(store, athlete_id, target_year=target_year, target_week=target_week)
    store.save_document(
        athlete_id,
        ArtifactType.KPI_PROFILE,
        "sample_profile",
        {"data": {}},
        producer_agent="test",
        run_id="store_kpi_profile",
        update_latest=True,
    )
    store.latest_path(athlete_id, ArtifactType.PLANNING_EVENTS).write_text(
        json.dumps({"data": {"events": []}}),
        encoding="utf-8",
    )
    store.latest_path(athlete_id, ArtifactType.LOGISTICS).write_text(
        json.dumps({"data": {"events": []}}),
        encoding="utf-8",
    )


def mock_previous_week_report_gate(
    monkeypatch: pytest.MonkeyPatch,
    *,
    evidence_week: IsoWeek = IsoWeek(2026, 11),
) -> None:
    monkeypatch.setattr(
        "rps.orchestrator.plan_week._ensure_previous_week_report",
        lambda *_args, **_kwargs: (
            SimpleNamespace(
                evidence_week=evidence_week,
                activities_actual_version=f"{evidence_week.year:04d}-{evidence_week.week:02d}",
                activities_trend_version=f"{evidence_week.year:04d}-{evidence_week.week:02d}",
                des_analysis_report_version=f"{evidence_week.year:04d}-{evidence_week.week:02d}",
            ),
            {},
            None,
            None,
        ),
    )


def write_contract_phase_docs(
    store: LocalArtifactStore,
    athlete_id: str,
    *,
    phase_range: str = "2026-11--2026-13",
    weeks: tuple[str, ...] = ("2026-11", "2026-12", "2026-13"),
) -> None:
    roles = ["LOAD_1", "LOAD_2", "DELOAD"][: len(weeks)]
    bands = [
        {"week": week, "band": {"min": 1000 + idx * 100, "max": 2000 + idx * 100, "notes": "Contract band"}}
        for idx, week in enumerate(weeks)
    ]
    store.save_document(
        athlete_id,
        ArtifactType.PHASE_GUARDRAILS,
        phase_range,
        {
            "meta": {"artifact_type": "PHASE_GUARDRAILS", "iso_week_range": phase_range},
            "data": {
                "load_guardrails": {"weekly_kj_bands": bands},
                "allowed_forbidden_semantics": {
                    "allowed_day_roles": ["REST", "RECOVERY", "ENDURANCE", "QUALITY"],
                    "forbidden_day_roles": [],
                    "allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO"],
                    "forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
                    "allowed_load_modalities": ["NONE"],
                    "quality_density": {"max_quality_days_per_week": 1},
                },
            },
        },
        producer_agent="phase_architect",
        run_id=f"store_phase_guardrails_{phase_range}",
        update_latest=True,
    )
    store.save_document(
        athlete_id,
        ArtifactType.PHASE_STRUCTURE,
        phase_range,
        {
            "meta": {"artifact_type": "PHASE_STRUCTURE", "iso_week_range": phase_range},
            "data": {
                "execution_principles": {
                    "phase_role": "Base",
                    "recovery_protection": {"fixed_non_training_days": ["Mon", "Fri"]},
                    "load_intensity_handling": {"max_quality_days_per_week": 1},
                },
                "week_skeleton_logic": {
                    "week_roles": {
                        "week_roles": [
                            {"week": week, "role": role}
                            for week, role in zip(weeks, roles, strict=False)
                        ],
                        "allowed_role_set": roles,
                    }
                },
                "load_ranges": {
                    "weekly_kj_bands": bands,
                    "source": "phase_guardrails_latest.json",
                },
            },
        },
        producer_agent="phase_architect",
        run_id=f"store_phase_structure_{phase_range}",
        update_latest=True,
    )
    store.save_document(
        athlete_id,
        ArtifactType.PHASE_PREVIEW,
        phase_range,
        {"meta": {"artifact_type": "PHASE_PREVIEW", "iso_week_range": phase_range}, "data": {}},
        producer_agent="phase_architect",
        run_id=f"store_phase_preview_{phase_range}",
        update_latest=True,
    )


def patch_plan_week_exact_query(
    monkeypatch: pytest.MonkeyPatch,
    *,
    root: Path,
    athlete_id: str,
) -> None:
    class _BoundExactQuery:
        def __init__(self, *args, **kwargs) -> None:
            self._delegate = IndexExactQuery(root=root, athlete_id=athlete_id)
            self._index_manager = self._delegate._index_manager

        def has_exact_range(self, artifact_type: str, expected_range) -> bool:
            return self._delegate.has_exact_range(artifact_type, expected_range)

        def best_exact_range_version(self, artifact_type: str, expected_range) -> str | None:
            return self._delegate.best_exact_range_version(artifact_type, expected_range)

    monkeypatch.setattr("rps.orchestrator.plan_week.IndexExactQuery", _BoundExactQuery)


def season_plan_stub_payload(
    *,
    phase_range: str = "2026-11--2026-13",
    weeks: tuple[str, ...] = ("2026-11", "2026-12", "2026-13"),
) -> dict[str, object]:
    roles = ["LOAD_1", "LOAD_2", "DELOAD"][: len(weeks)]
    return {
        "meta": {"iso_week_range": phase_range},
        "data": {
            "phases": [
                {
                    "phase_id": "P01",
                    "id": "P01",
                    "name": "Base 1",
                    "cycle": "Base",
                    "phase_type": "BASE",
                    "phase_intent": "shortened_re_entry",
                    "build_subtype": None,
                    "scenario_cadence": "2:1:1",
                    "cadence_week_roles": roles,
                    "iso_week_range": phase_range,
                    "role_week_load_bands": [
                        {
                            "week": week,
                            "role": role,
                            "band": {"min": 1000 + idx * 100, "max": 2000 + idx * 100},
                        }
                        for idx, (week, role) in enumerate(zip(weeks, roles, strict=False))
                    ],
                    "allowed_forbidden_semantics": {
                        "allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO"],
                        "forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
                        "allowed_load_modalities": ["NONE"],
                    },
                    "overview": {"phase_goals": {"primary": "Protect continuity."}},
                }
            ]
        },
    }
