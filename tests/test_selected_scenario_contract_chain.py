from pathlib import Path


def test_active_files_frontload_selected_and_inherited_posture() -> None:
    season_prompt = Path("prompts/agents/season_plan_manager.md").read_text(encoding="utf-8")
    phase_prompt = Path("prompts/agents/phase_bundle_manager.md").read_text(encoding="utf-8")
    week_prompt = Path("prompts/agents/week_planner.md").read_text(encoding="utf-8")
    season_skill = Path("skills/season/plan-synthesis/SKILL.md").read_text(encoding="utf-8")
    phase_skill = Path("skills/phase/bundle-synthesis/SKILL.md").read_text(encoding="utf-8")
    week_skill = Path("skills/week/plan-synthesis/SKILL.md").read_text(encoding="utf-8")

    assert "selected_scenario_contract" in season_prompt
    assert "selected_scenario_contract" in season_skill
    assert "inherited scenario contract" in phase_prompt.lower()
    assert "inherited_scenario_contract" in phase_skill
    assert "inherited_planning_posture" in week_prompt
    assert "inherited_planning_posture" in week_skill


def test_review_and_writer_files_state_contract_preservation() -> None:
    season_review = Path("prompts/agents/season_review_manager.md").read_text(encoding="utf-8")
    phase_review = Path("prompts/agents/phase_review_manager.md").read_text(encoding="utf-8")
    week_review = Path("prompts/agents/week_review_manager.md").read_text(encoding="utf-8")
    season_writer = Path("prompts/agents/season_artifact_writer.md").read_text(encoding="utf-8")
    phase_writer = Path("prompts/agents/phase_artifact_writer.md").read_text(encoding="utf-8")

    assert "selected scenario contract" in season_review.lower()
    assert "inherited scenario contract" in phase_review.lower()
    assert "inherited_planning_posture" in week_review
    assert "`selected_scenario_contract`" in season_writer
    assert "`inherited_scenario_contract`" in phase_writer


def test_task_descriptions_reference_selected_or_inherited_posture() -> None:
    tasks = Path("config/crewai/tasks.yaml").read_text(encoding="utf-8")

    assert "selected_scenario_contract" in tasks
    assert "inherited scenario contract" in tasks.lower()
    assert "inherited_planning_posture" in tasks
