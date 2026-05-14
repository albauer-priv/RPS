from rps.crewai_runtime.coach_chat import CoachTool, SpecialistToolsets, build_runtime_profile


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
