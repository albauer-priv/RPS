from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_evidence_curation_active_files_block_tag_leakage_for_metadata_only() -> None:
    skill = _read("skills/evidence/source-curation/SKILL.md")
    prompt = _read("prompts/agents/evidence_curation_specialist.md")
    tasks = _read("config/crewai/tasks.yaml")

    assert "Discovery tags are routing metadata, not evidence" in prompt
    assert "Discovery tags are not evidence and must not be echoed as findings" in _read("src/rps/evidence/curation.py")
    assert "Do not turn discovery tags into findings" in skill
    assert "Title paraphrases are not empirical findings" in prompt
    assert "do not mirror routing tags or title paraphrases as if they were empirical findings" in tasks


def test_evidence_curation_active_files_define_metadata_only_output_contract() -> None:
    skill = _read("skills/evidence/source-curation/SKILL.md")
    prompt = _read("prompts/agents/evidence_curation_specialist.md")
    tasks = _read("config/crewai/tasks.yaml")

    assert "Treat the source as an identification card" in skill
    assert "state explicitly that no extractable findings are available from the package" in prompt
    assert "keep `allowed_uses` at `background_only`" in prompt
    assert "`important_findings` should usually say that no extractable findings" in skill
    assert "Off-domain metadata-only sources should normally be `reject` or tightly bounded `background_only`" in tasks


def test_evidence_curation_active_files_define_abstract_only_output_contract() -> None:
    skill = _read("skills/evidence/source-curation/SKILL.md")
    prompt = _read("prompts/agents/evidence_curation_specialist.md")
    tasks = _read("config/crewai/tasks.yaml")

    assert "Treat the abstract as a constrained evidence window" in skill
    assert "prefer phrasing such as `the abstract reports`" in prompt
    assert "do not mix `background_only` with stronger allowed uses" in prompt
    assert "avoid direct imperative coaching language unless framed as abstract-supported guidance" in tasks
