from __future__ import annotations

import pytest
from pydantic import ValidationError

from rps.crewai_runtime.generated_artifact_models import (
    SeasonScenariosModel,
    artifact_model_for_schema_file,
    artifact_model_for_task_name,
)
from rps.crewai_runtime.schema_backed_models import _normalize_schema_backed_metadata


def test_generated_artifact_model_registry_resolves_concrete_task_model() -> None:
    assert artifact_model_for_task_name("season_scenarios") is SeasonScenariosModel
    assert artifact_model_for_schema_file("season_scenarios.schema.json") is SeasonScenariosModel
    assert SeasonScenariosModel.model_json_schema()["title"] == "SeasonScenarios"


def test_generated_artifact_model_rejects_schema_invalid_payload() -> None:
    with pytest.raises(ValidationError) as exc_info:
        SeasonScenariosModel(
            meta={
                "artifact_type": "SEASON_SCENARIOS",
                "schema_id": "SeasonScenariosInterface",
                "schema_version": "1.0",
                "version": "2026-20_A01",
                "authority": "Informational",
                "owner_agent": "Season-Scenario-Agent",
                "run_id": "run-1",
                "created_at": "2026-05-17T16:07:25Z",
                "scope": "Athlete: i150546",
                "iso_week": "2026-20",
                "iso_week_range": "2026-20--2026-37",
                "temporal_scope": {"from": "2026-05-11", "to": "2026-09-13"},
                "trace_upstream": [],
                "trace_data": [],
                "trace_events": [],
                "data_confidence": "UNKNOWN",
                "notes": "",
            },
            data={"scenarios": []},
        )

    message = str(exc_info.value)
    assert "JSON schema validation failed" in message
    assert "version" in message or "scope" in message


def test_schema_backed_metadata_normalizes_operational_trace_version_keys() -> None:
    payload = {
        "meta": {
            "schema_version": "20260518_145618",
            "version": "2026-21__20260518_145618",
            "trace_upstream": [
                {"artifact": "SEASON_SCENARIOS", "version": "20260518_103858", "run_id": "run-a"},
            ],
            "trace_data": [
                {"artifact": "ATHLETE_PROFILE", "version": "20260315_091949", "run_id": "run-b"},
                {"artifact": "AVAILABILITY", "version": "1.2.0", "run_id": "run-c"},
            ],
            "trace_events": [
                {"artifact": "PLANNING_EVENTS", "version": "20260504_094650", "run_id": "run-d"},
            ],
        },
        "data": {},
    }

    normalized = _normalize_schema_backed_metadata(payload)

    assert normalized["meta"]["schema_version"] == "1.0"
    assert normalized["meta"]["version"] == "1.0"
    assert normalized["meta"]["trace_upstream"][0]["version"] == "1.0"
    assert normalized["meta"]["trace_data"][0]["version"] == "1.0"
    assert normalized["meta"]["trace_data"][1]["version"] == "1.2.0"
    assert normalized["meta"]["trace_events"][0]["version"] == "1.0"
    assert payload["meta"]["trace_data"][0]["version"] == "20260315_091949"
