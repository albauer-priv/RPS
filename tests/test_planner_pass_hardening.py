from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_finalize_files_carry_three_pass_model_and_loopback_rules() -> None:
    tasks = _read("config/crewai/tasks.yaml")
    season_prompt = _read("prompts/agents/season_plan_manager.md")
    season_skill = _read("skills/season/plan-synthesis/SKILL.md")
    phase_prompt = _read("prompts/agents/phase_bundle_manager.md")
    phase_skill = _read("skills/phase/bundle-synthesis/SKILL.md")
    week_prompt = _read("prompts/agents/week_planner.md")
    week_skill = _read("skills/week/plan-synthesis/SKILL.md")

    assert "Pass 1 - structural draft" in season_prompt
    assert "Pass 2 - semantic finalization" in season_prompt
    assert "Pass 3 - planner self-audit" in season_prompt
    assert "route back to Pass 1" in season_prompt
    assert "route back to Pass 2" in season_prompt
    assert "season_plan_finalize" in tasks
    assert "phase_bundle_finalize" in tasks
    assert "week_plan_finalize" in tasks
    assert "Pass 1 structural draft" in tasks
    assert "Pass 2 semantic finalization" in tasks
    assert "Pass 3 planner self-audit" in tasks
    assert "Pass 2-return findings" in tasks
    assert "Pass 1-return findings" in tasks
    assert "Pass 1 - structural draft" in season_skill
    assert "Pass 2 - semantic finalization" in season_skill
    assert "Pass 3 - planner self-audit" in season_skill
    assert "`constraints[]`, `load_governance[]`, and `phase_blueprints` are not part of this task's output" in season_prompt
    assert "assembled deterministically from those tasks' own typed outputs" in season_prompt
    assert "`constraints[]`, `load_governance[]`, and `phase_blueprints` are not part of the finalizer's own output" in season_skill

    assert "Pass 1 - structural draft" in phase_prompt
    assert "Pass 2 - semantic finalization" in phase_prompt
    assert "Pass 3 - planner self-audit" in phase_prompt
    assert "route back to Pass 1" in phase_prompt
    assert "route back to Pass 2" in phase_prompt
    assert "Pass 1 - structural draft" in phase_skill
    assert "Pass 2 - semantic finalization" in phase_skill
    assert "Pass 3 - planner self-audit" in phase_skill

    assert "Pass 1 - structural draft" in week_prompt
    assert "Pass 2 - semantic finalization" in week_prompt
    assert "Pass 3 - planner self-audit" in week_prompt
    assert "route back to Pass 1" in week_prompt
    assert "route back to Pass 2" in week_prompt
    assert "Pass 1 - structural draft" in week_skill
    assert "Pass 2 - semantic finalization" in week_skill
    assert "Pass 3 - planner self-audit" in week_skill


def test_review_files_are_formal_gates_with_pass_classification() -> None:
    season_prompt = _read("prompts/agents/season_review_manager.md")
    season_skill = _read("skills/season/review-decision/SKILL.md")
    phase_prompt = _read("prompts/agents/phase_review_manager.md")
    phase_skill = _read("skills/phase/review-decision/SKILL.md")
    week_prompt = _read("prompts/agents/week_review_manager.md")
    week_skill = _read("skills/week/review-decision/SKILL.md")

    for text in (season_prompt, season_skill, phase_prompt, phase_skill, week_prompt, week_skill):
        assert "formal approval gate" in text or "policy gate" in text
        assert "Pass 1 return" in text
        assert "Pass 2 return" in text
        assert "must not repair semantics itself" in text or "no semantic rewriting in review" in text

    assert "Formal review confirmation checklist" in season_prompt
    assert "Formal review confirmation checklist" in phase_prompt
    assert "Formal review confirmation checklist" in week_prompt


def test_writer_files_require_pass3_and_review_approval() -> None:
    season_prompt = _read("prompts/agents/season_artifact_writer.md")
    season_skill = _read("skills/season/artifact-writing/SKILL.md")
    phase_prompt = _read("prompts/agents/phase_artifact_writer.md")
    week_prompt = _read("prompts/agents/week_artifact_writer.md")
    week_skill = _read("skills/week/artifact-writing/SKILL.md")

    for text in (season_prompt, season_skill, phase_prompt, week_prompt, week_skill):
        assert "Pass 3 self-audit passed and Review approved" in text
        assert "Pass 1 or Pass 2 return finding" in text
        assert "must not run" in text

    assert "Copy, do not infer" in season_prompt
    assert "Stop rather than guess" in phase_prompt or "stop rather than guess" in phase_prompt
    assert "Stop when required fields are missing or contradictory" in week_prompt
