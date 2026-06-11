from __future__ import annotations

from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_active_files_frontload_previous_week_evidence_alignment() -> None:
    tasks = _read("config/crewai/tasks.yaml")
    season_prompt = _read("prompts/agents/season_planner.md")
    phase_prompt = _read("prompts/agents/phase_architect.md")
    week_prompt = _read("prompts/agents/week_planner.md")

    assert "season_evidence_alignment" in tasks
    assert "phase_evidence_alignment" in tasks
    assert "week_evidence_alignment" in tasks
    assert "previous-week `DES_ANALYSIS_REPORT`" in tasks
    assert "previous-week `ACTIVITIES_ACTUAL`" in tasks or "exact previous-week `ACTIVITIES_ACTUAL`" in tasks
    assert "previous-week `ACTIVITIES_TREND`" in tasks or "exact previous-week `ACTIVITIES_TREND`" in tasks
    assert "completed week `W - 1`" in season_prompt
    assert "completed week `W - 1`" in phase_prompt
    assert "completed week `W - 1`" in week_prompt


def test_evidence_alignment_skills_exist_and_forbid_authority_override() -> None:
    for path in (
        "skills/season/evidence-alignment/SKILL.md",
        "skills/phase/evidence-alignment/SKILL.md",
        "skills/week/evidence-alignment/SKILL.md",
    ):
        text = _read(path)
        assert "previous-week" in text
        assert "do not rewrite" in text
        assert "not a late reviewer" in text
