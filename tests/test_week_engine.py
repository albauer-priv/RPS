from __future__ import annotations

from pathlib import Path

import pytest

from rps.planning.week_engine import execute_week_engine, load_week_workout_family_config
from rps.planning.week_selection_rules import (
    best_matching_rule,
    load_week_workout_selection_rule_config,
    matching_rules,
)
from rps.workouts.validator import validate_week_plan_exportability
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.schema_registry import SchemaRegistry, validate_or_raise
from rps.workspace.types import ArtifactType


def _seed_week_workspace(
    root: Path,
    athlete_id: str = "test_athlete",
    *,
    phase_intent: str = "shortened_re_entry",
    week_role: str = "SHORTENED_RE_ENTRY",
    phase_type: str = "BASE",
    allowed_domains: list[str] | None = None,
) -> LocalArtifactStore:
    store = LocalArtifactStore(root=root)
    store.ensure_workspace(athlete_id)
    domains = allowed_domains or ["ENDURANCE", "TEMPO", "SWEET_SPOT"]
    store.save_document(
        athlete_id,
        ArtifactType.SEASON_PLAN,
        "2026-21",
        {
            "meta": {"artifact_type": "SEASON_PLAN", "schema_id": "SeasonPlanInterface", "iso_week_range": "2026-21--2026-23"},
            "data": {
                "body_metadata": {
                    "phase_taxonomy_version": "canonical_phase_taxonomy_v1",
                },
                "phases": [
                    {
                        "phase_id": "P01",
                        "phase_name": "Shortened Re-Entry",
                        "phase_type": phase_type,
                        "phase_intent": phase_intent,
                        "build_subtype": None,
                        "iso_week_range": "2026-21--2026-23",
                    }
                ]
            },
        },
        producer_agent="test",
        run_id="seed",
        update_latest=True,
    )
    phase_guardrails = {
        "meta": {"artifact_type": "PHASE_GUARDRAILS", "schema_id": "PhaseGuardrailsInterface", "iso_week_range": "2026-21--2026-23"},
        "data": {
            "body_metadata": {
                "phase_type": phase_type,
                "phase_intent": phase_intent,
                "build_subtype": None,
                "phase_taxonomy_version": "canonical_phase_taxonomy_v1",
            },
            "load_guardrails": {
                "weekly_kj_bands": [
                    {"week": "2026-21", "band": {"min": 7329, "max": 8372, "notes": "binding"}},
                    {"week": "2026-22", "band": {"min": 7329, "max": 8372, "notes": "binding"}},
                    {"week": "2026-23", "band": {"min": 7329, "max": 8372, "notes": "binding"}},
                ]
            },
            "allowed_forbidden_semantics": {
                "allowed_day_roles": ["REST", "RECOVERY", "ENDURANCE", "QUALITY", "OPTIONAL", "OFF_BIKE"],
                "forbidden_day_roles": [],
                "allowed_intensity_domains": domains,
                "forbidden_intensity_domains": ["RECOVERY", "THRESHOLD", "VO2MAX"],
                "allowed_load_modalities": ["NONE", "K3"],
                "quality_density": {"max_quality_days_per_week": 2},
            },
        },
    }
    phase_structure = {
        "meta": {"artifact_type": "PHASE_STRUCTURE", "schema_id": "PhaseStructureInterface", "iso_week_range": "2026-21--2026-23"},
        "data": {
            "execution_principles": {
                "phase_role": phase_type,
                "load_intensity_handling": {"load_modality_constraints": ["NONE"]},
            },
            "upstream_intent": {
                "phase_type": phase_type,
                "phase_intent": phase_intent,
                "build_subtype": None,
                "phase_taxonomy_version": "canonical_phase_taxonomy_v1",
            },
            "week_skeleton_logic": {
                "week_roles": {
                    "week_roles": [
                        {"week": "2026-21", "role": week_role},
                        {"week": "2026-22", "role": "SHORTENED_CONSOLIDATION"},
                        {"week": "2026-23", "role": "SHORTENED_MINI_RESET"},
                    ]
                },
                "mandatory_elements": {"recovery_opportunities_min": 2, "endurance_anchor_required": True},
            },
        },
    }
    phase_preview = {
        "meta": {"artifact_type": "PHASE_PREVIEW", "schema_id": "PhasePreviewInterface", "iso_week_range": "2026-21--2026-23"},
        "data": {
            "phase_intent_summary": {
                "phase_type": phase_type,
                "phase_intent": phase_intent,
                "build_subtype": None,
                "phase_taxonomy_version": "canonical_phase_taxonomy_v1",
            },
            "weekly_agenda_preview": [
                {
                    "week": "2026-21",
                    "days": [
                        {"day_of_week": "Mon", "day_role": "REST", "intensity_domain": "NONE", "load_modality": "NONE"},
                        {"day_of_week": "Tue", "day_role": "QUALITY", "intensity_domain": "ENDURANCE", "load_modality": "NONE"},
                        {"day_of_week": "Wed", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE"},
                        {"day_of_week": "Thu", "day_role": "QUALITY", "intensity_domain": "TEMPO", "load_modality": "NONE"},
                        {"day_of_week": "Fri", "day_role": "REST", "intensity_domain": "NONE", "load_modality": "NONE"},
                        {"day_of_week": "Sat", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE"},
                        {"day_of_week": "Sun", "day_role": "ENDURANCE", "intensity_domain": "SWEET_SPOT", "load_modality": "NONE"},
                    ],
                }
            ]
        },
    }
    availability = {
        "meta": {"artifact_type": "AVAILABILITY", "schema_id": "AvailabilityInterface"},
        "data": {
            "fixed_rest_days": ["Mon", "Fri"],
            "availability_table": [
                {"day": "Mon", "hours_min": 0.0, "hours_typical": 0.0, "hours_max": 0.0},
                {"day": "Tue", "hours_min": 1.5, "hours_typical": 2.0, "hours_max": 2.5},
                {"day": "Wed", "hours_min": 1.5, "hours_typical": 2.0, "hours_max": 2.5},
                {"day": "Thu", "hours_min": 1.5, "hours_typical": 2.0, "hours_max": 2.5},
                {"day": "Fri", "hours_min": 0.0, "hours_typical": 0.0, "hours_max": 0.0},
                {"day": "Sat", "hours_min": 3.0, "hours_typical": 4.0, "hours_max": 5.0},
                {"day": "Sun", "hours_min": 3.0, "hours_typical": 4.0, "hours_max": 5.0},
            ],
        },
    }
    zone_model = {
        "meta": {"artifact_type": "ZONE_MODEL", "schema_id": "ZoneModelInterface"},
        "data": {
            "model_metadata": {"ftp_watts": 300},
            "zones": [
                {"zone_id": "Z2", "typical_if": 0.68},
                {"zone_id": "Z3", "typical_if": 0.83},
                {"zone_id": "SS", "typical_if": 0.92},
            ],
        },
    }
    athlete_profile = {
        "meta": {"artifact_type": "ATHLETE_PROFILE", "schema_id": "AthleteProfileInterface"},
        "data": {"profile": {"endurance_anchor_w": 210}},
    }
    for artifact_type, version_key, payload in (
        (ArtifactType.PHASE_GUARDRAILS, "2026-21--2026-23", phase_guardrails),
        (ArtifactType.PHASE_STRUCTURE, "2026-21--2026-23", phase_structure),
        (ArtifactType.PHASE_PREVIEW, "2026-21--2026-23", phase_preview),
        (ArtifactType.AVAILABILITY, "20260316_000000", availability),
        (ArtifactType.ZONE_MODEL, "20260520_000000", zone_model),
        (ArtifactType.ATHLETE_PROFILE, "20260315_000000", athlete_profile),
    ):
        store.save_document(
            athlete_id,
            artifact_type,
            version_key,
            payload,
            producer_agent="test",
            run_id="seed",
            update_latest=True,
        )
    return store


def _seed_previous_week_plan(store: LocalArtifactStore, athlete_id: str = "test_athlete") -> None:
    store.save_document(
        athlete_id,
        ArtifactType.WEEK_PLAN,
        "2026-20",
        {
            "meta": {"artifact_type": "WEEK_PLAN", "schema_id": "WeekPlanInterface", "iso_week": "2026-20"},
            "data": {
                "week_summary": {"planned_weekly_load_kj": 7200},
                "agenda": [
                    {"day": "Mon", "date": "2026-05-11", "day_role": "REST", "planned_duration": "00:00", "planned_kj": 0, "workout_id": None},
                    {"day": "Tue", "date": "2026-05-12", "day_role": "QUALITY", "planned_duration": "01:38", "planned_kj": 1100, "workout_id": "2026-20-TUE-QUALITY"},
                    {"day": "Wed", "date": "2026-05-13", "day_role": "RECOVERY", "planned_duration": "01:00", "planned_kj": 500, "workout_id": "2026-20-WED-REC"},
                    {"day": "Thu", "date": "2026-05-14", "day_role": "ENDURANCE", "planned_duration": "01:30", "planned_kj": 800, "workout_id": "2026-20-THU-END"},
                    {"day": "Fri", "date": "2026-05-15", "day_role": "REST", "planned_duration": "00:00", "planned_kj": 0, "workout_id": None},
                    {"day": "Sat", "date": "2026-05-16", "day_role": "ENDURANCE", "planned_duration": "03:30", "planned_kj": 2600, "workout_id": "2026-20-SAT-END"},
                    {"day": "Sun", "date": "2026-05-17", "day_role": "ENDURANCE", "planned_duration": "01:20", "planned_kj": 700, "workout_id": "2026-20-SUN-END"},
                ],
                "workouts": [
                    {
                        "workout_id": "2026-20-TUE-QUALITY",
                        "title": "Tempo Intervals",
                        "notes": "Deterministic Tempo Classic workout generated from the approved week blueprint.",
                        "date": "2026-05-12",
                        "start": "00:00",
                        "duration": "01:38:00",
                        "workout_text": "Warmup\n- 10m ramp 50%-75% 85-95rpm\n\nMain Set\n4x\n- 10m 82%-88% 90-95rpm\n- 6m 60%-65% 85-90rpm\n\nCooldown\n- 8m ramp 60%-45% 80-85rpm",
                    }
                ],
            },
        },
        producer_agent="test",
        run_id="seed_prev",
        update_latest=True,
    )


def test_load_week_workout_family_config_rejects_unknown_addon_policy(tmp_path: Path) -> None:
    config_dir = tmp_path / "config" / "planning"
    config_dir.mkdir(parents=True)
    (config_dir / "week_workout_protocols.yaml").write_text(
        "addon_policies:\n"
        "  NONE:\n"
        "    target_domain: null\n"
        "protocols:\n"
        "  BAD:\n"
        "    intensity_domain: ENDURANCE\n"
        "    load_modality: NONE\n"
        "    protocol_type: LONG_STEADY\n"
        "    protocol_variant: BAD\n"
        "    allowed_day_roles: [ENDURANCE]\n"
        "    allowed_phase_intents: ['*']\n"
        "    allowed_week_roles: ['*']\n"
        "    tags: []\n"
        "    primary_axis: duration\n"
        "    secondary_axis: none\n"
        "    addon_policy: MISSING\n"
        "selection_policy:\n"
        "  by_day_role:\n"
        "    ENDURANCE: [BAD]\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown add-on policy"):
        load_week_workout_family_config(tmp_path)


def test_execute_week_engine_preview_generates_valid_exportable_week_plan(tmp_path: Path) -> None:
    _seed_week_workspace(tmp_path)

    result = execute_week_engine(
        repo_root=Path.cwd(),
        schema_dir=Path("specs/schemas"),
        workspace_root=tmp_path,
        athlete_id="test_athlete",
        run_id="preview_run",
        target_year=2026,
        target_week=21,
        preview_only=True,
    )

    assert result["ok"] is True
    document = result["document"]
    validate_week_plan_exportability(document)
    total = document["data"]["week_summary"]["planned_weekly_load_kj"]
    assert 7329 <= total <= 8372
    rendered = "\n".join(workout["workout_text"] for workout in document["data"]["workouts"])
    assert "- 3x " not in rendered
    workout_ids = {workout["workout_id"]: workout for workout in result["details"]["planning_bundle"]["workout_blueprints"]}
    assert workout_ids["2026-21-WED-REC"]["protocol_type"] == "LONG_STEADY"
    assert workout_ids["2026-21-WED-REC"]["protocol_variant"] == "ENDURANCE_LOW"


def test_execute_week_engine_persists_week_plan_without_crewai_week_crews(tmp_path: Path) -> None:
    store = _seed_week_workspace(tmp_path)

    result = execute_week_engine(
        repo_root=Path.cwd(),
        schema_dir=Path("specs/schemas"),
        workspace_root=tmp_path,
        athlete_id="test_athlete",
        run_id="persist_run",
        target_year=2026,
        target_week=21,
        user_message="increase load and use tempo",
        preview_only=False,
    )

    assert result["ok"] is True
    version = store.resolve_week_version_key("test_athlete", ArtifactType.WEEK_PLAN, "2026-21")
    assert isinstance(version, str)
    assert version.startswith("2026-21")
    saved = store.load_version("test_athlete", ArtifactType.WEEK_PLAN, version)
    assert saved["data"]["week_summary"]["planned_weekly_load_kj"] >= 7329
    rendered = "\n".join(workout["workout_text"] for workout in saved["data"]["workouts"])
    assert "- 3x " not in rendered
    audit_version = store.resolve_week_version_key("test_athlete", ArtifactType.WEEK_WORKOUT_SELECTION_AUDIT, "2026-21")
    assert isinstance(audit_version, str)
    audit = store.load_version("test_athlete", ArtifactType.WEEK_WORKOUT_SELECTION_AUDIT, audit_version)
    audit_meta = audit.get("meta")
    if isinstance(audit_meta, dict):
        audit_meta.pop("version_key", None)
    validate_or_raise(SchemaRegistry(Path("specs/schemas")).validator_for("week_workout_selection_audit.schema.json"), audit)
    assert audit["data"]["rows"]
    csv_path = store.versioned_path("test_athlete", ArtifactType.WEEK_WORKOUT_SELECTION_AUDIT, audit_version).with_suffix(".csv")
    assert csv_path.exists()
    assert "protocol_variant" in csv_path.read_text(encoding="utf-8")


def test_execute_week_engine_reuses_previous_week_progression_signature(tmp_path: Path) -> None:
    _seed_week_workspace(tmp_path)
    store = LocalArtifactStore(root=tmp_path)
    _seed_previous_week_plan(store)

    result = execute_week_engine(
        repo_root=Path.cwd(),
        schema_dir=Path("specs/schemas"),
        workspace_root=tmp_path,
        athlete_id="test_athlete",
        run_id="progression_run",
        target_year=2026,
        target_week=21,
        preview_only=True,
    )

    assert result["ok"] is True
    workout_ids = {workout["workout_id"]: workout for workout in result["details"]["planning_bundle"]["workout_blueprints"]}
    tempo = workout_ids["2026-21-TUE-QUALITY"]
    previous = tempo["progression_state"]["previous_signature"]
    assert previous["protocol_type"] == "CLASSIC_INTERVALS"
    assert previous["set_count"] == 4
    assert previous["work_duration_minutes"] == 10


def test_execute_week_engine_falls_back_cleanly_without_previous_week_signature(tmp_path: Path) -> None:
    _seed_week_workspace(tmp_path)

    result = execute_week_engine(
        repo_root=Path.cwd(),
        schema_dir=Path("specs/schemas"),
        workspace_root=tmp_path,
        athlete_id="test_athlete",
        run_id="no_prev_run",
        target_year=2026,
        target_week=21,
        preview_only=True,
    )

    assert result["ok"] is True
    workout_ids = {workout["workout_id"]: workout for workout in result["details"]["planning_bundle"]["workout_blueprints"]}
    assert workout_ids["2026-21-TUE-QUALITY"]["progression_state"]["previous_signature"] == {}


def test_execute_week_engine_counts_quality_cost_and_downshifts_sat_endurance(tmp_path: Path) -> None:
    _seed_week_workspace(
        tmp_path,
        phase_intent="specificity_build",
        week_role="SPECIFICITY_BUILD",
        allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
    )

    result = execute_week_engine(
        repo_root=Path.cwd(),
        schema_dir=Path("specs/schemas"),
        workspace_root=tmp_path,
        athlete_id="test_athlete",
        run_id="density_run",
        target_year=2026,
        target_week=21,
        preview_only=True,
    )

    assert result["ok"] is True
    workout_ids = {workout["workout_id"]: workout for workout in result["details"]["planning_bundle"]["workout_blueprints"]}
    assert workout_ids["2026-21-TUE-QUALITY"]["progression_state"]["quality_cost"] == "true_quality"
    assert workout_ids["2026-21-THU-QUALITY"]["progression_state"]["quality_cost"] == "true_quality"
    assert workout_ids["2026-21-SAT-END"]["protocol_variant"] == "ENDURANCE_LONG_STEADY"


def test_execute_week_engine_shortened_reentry_defaults_to_one_quality_day_and_warns_on_modality_mismatch(tmp_path: Path) -> None:
    _seed_week_workspace(tmp_path)
    store = LocalArtifactStore(root=tmp_path)
    _seed_previous_week_plan(store)

    result = execute_week_engine(
        repo_root=Path.cwd(),
        schema_dir=Path("specs/schemas"),
        workspace_root=tmp_path,
        athlete_id="test_athlete",
        run_id="reentry_shape_run",
        target_year=2026,
        target_week=21,
        preview_only=True,
    )

    assert result["ok"] is True
    warnings = result["details"]["planning_bundle"]["warnings"]
    assert any("reentry_week_shape" in item for item in warnings)
    assert any("load_modality_constraint_mismatch" in item for item in warnings)
    assert any("phase_preview_alignment" in item for item in warnings)
    blueprints = {item["workout_id"]: item for item in result["details"]["planning_bundle"]["workout_blueprints"]}
    assert blueprints["2026-21-TUE-QUALITY"]["protocol_variant"] == "TEMPO_CLASSIC"
    assert "2026-21-THU-QUALITY" not in blueprints
    assert blueprints["2026-21-THU-END"]["protocol_variant"] == "ENDURANCE_STEADY"
    assert blueprints["2026-21-THU-END"]["selection_rule_row_ids"]
    audit_rows = result["details"]["selection_audit"]["rows"]
    thu_rows = [row for row in audit_rows if row["day"] == "Thu" and row["day_role"] == "ENDURANCE"]
    assert any(row["review_bucket"] == "SOLL" for row in thu_rows if row["selected"] is True)
    assert any(row["protocol_variant"] == "ENDURANCE_LONG_STEADY" and row["selected"] is False for row in thu_rows)
    assert any(row["selected"] is True and row["protocol_variant"] == "ENDURANCE_STEADY" for row in thu_rows)
    workouts = {item["workout_id"]: item for item in result["document"]["data"]["workouts"]}
    tue = workouts["2026-21-TUE-QUALITY"]["workout_text"]
    thu = workouts["2026-21-THU-END"]["workout_text"]
    assert "82%-88%" in tue
    assert "68%-72%" in thu
    assert tue != thu


def test_execute_week_engine_specificity_build_keeps_vo2_as_nur_wenn(tmp_path: Path) -> None:
    _seed_week_workspace(
        tmp_path,
        phase_intent="specificity_build",
        week_role="SPECIFICITY_BUILD",
        phase_type="BUILD",
        allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD", "VO2MAX"],
    )

    result = execute_week_engine(
        repo_root=Path.cwd(),
        schema_dir=Path("specs/schemas"),
        workspace_root=tmp_path,
        athlete_id="test_athlete",
        run_id="specificity_bucket_run",
        target_year=2026,
        target_week=21,
        preview_only=True,
    )

    assert result["ok"] is True
    blueprints = {item["workout_id"]: item for item in result["details"]["planning_bundle"]["workout_blueprints"]}
    selected_quality = [item for item in blueprints.values() if item["day_role"] == "QUALITY"]
    assert selected_quality
    assert all(item["protocol_variant"] != "VO2_LONG_INTERVALS" for item in selected_quality)
    audit_rows = result["details"]["selection_audit"]["rows"]
    vo2_rows = [
        row for row in audit_rows
        if row["day_role"] == "QUALITY" and row["protocol_variant"] == "VO2_LONG_INTERVALS"
    ]
    assert vo2_rows
    assert all(row["review_bucket"] == "NUR_WENN" for row in vo2_rows)
    assert any(row["selected"] is False for row in vo2_rows)


def test_selection_rule_overlaps_resolve_deterministically() -> None:
    config = load_week_workout_selection_rule_config(Path.cwd())
    rows = matching_rules(
        config.rules,
        protocol_variant="TEMPO_CLASSIC",
        protocol_type="CLASSIC_INTERVALS",
        intensity_domain="TEMPO",
        load_modality="NONE",
        season_archetype="none",
        phase_type="BASE",
        phase_intent="shortened_re_entry",
        week_role="SHORTENED_RE_ENTRY",
        day_role="QUALITY",
    )
    best = best_matching_rule(rows)
    assert best is not None
    assert best.row_id == "REENTRY-TUE-TEMPO-PRIMARY"
