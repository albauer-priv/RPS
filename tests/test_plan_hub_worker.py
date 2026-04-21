from rps.orchestrator.plan_hub_worker import _bundled_phase_force_steps


def test_bundled_phase_force_steps_groups_remaining_phase_outputs() -> None:
    steps = [
        {"step_id": "PHASE_GUARDRAILS", "Status": "RUNNING"},
        {"step_id": "PHASE_STRUCTURE", "Status": "QUEUED"},
        {"step_id": "PHASE_PREVIEW", "Status": "QUEUED"},
        {"step_id": "WEEK_PLAN", "Status": "QUEUED"},
    ]

    assert _bundled_phase_force_steps(steps, "PHASE_GUARDRAILS") == [
        "PHASE_GUARDRAILS",
        "PHASE_STRUCTURE",
        "PHASE_PREVIEW",
    ]
    assert _bundled_phase_force_steps(steps, "PHASE_STRUCTURE") == [
        "PHASE_STRUCTURE",
        "PHASE_PREVIEW",
    ]
    assert _bundled_phase_force_steps(steps, "PHASE_PREVIEW") == ["PHASE_PREVIEW"]
