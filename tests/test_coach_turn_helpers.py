from rps.crewai_runtime.coach_chat import (
    CoachTool,
    SpecialistToolsets,
    _coach_reply_style_issues,
    build_runtime_profile,
)


def _tool(name: str) -> CoachTool:
    return CoachTool(
        name=name,
        description=name,
        parameters={"type": "object", "properties": {}, "required": []},
        handler=lambda **_: "{}",
    )


def test_runtime_profile_assigns_tools_per_specialist() -> None:
    toolsets = SpecialistToolsets(
        context=[_tool("read_current_plan_context"), _tool("list_current_week_plan_workouts")],
        recommendation=[],
        preview=[_tool("preview_scoped_week_replan")],
        pending=[_tool("show_pending_coach_operation"), _tool("apply_pending_coach_operation")],
    )

    profile = build_runtime_profile(surface_name="coach", toolsets=toolsets)

    assert profile["knowledge_modes"]["week_recommendation_specialist"] == "coach"
    assert profile["tool_names"]["week_context_specialist"] == [
        "read_current_plan_context",
        "list_current_week_plan_workouts",
    ]
    assert profile["tool_names"]["week_recommendation_specialist"] == []
    assert profile["tool_names"]["week_revision_specialist"] == ["preview_scoped_week_replan"]
    assert profile["tool_names"]["pending_resolution_specialist"] == [
        "show_pending_coach_operation",
        "apply_pending_coach_operation",
    ]


def test_coach_reply_style_flags_task_runner_output() -> None:
    reply = """
Sofort: Temperatur messen
Was: Miss jetzt deine Temperatur.
Prüfen: Kalender öffnen.
DONE: Temperaturwert notiert.
READY
"""

    issues = _coach_reply_style_issues(reply)

    assert "repeated_done_markers" in issues or "task_checklist_labels" in issues
    assert any("DONE" in issue or "READY" in issue for issue in issues)


def test_coach_reply_style_accepts_conversational_answer() -> None:
    reply = (
        "Nicht nachholen. Diese Woche zählt Erholung mehr als kosmetische kJ. "
        "Bleib im aktiven Band, streiche zusätzliche Intensität und kürze bei Krankheit. "
        "Der nächste sichere Schritt ist: heute nur Symptome prüfen und keine Extra-Session planen."
    )

    assert _coach_reply_style_issues(reply) == []
