from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_season_skills_preserve_inherited_cadence_semantics() -> None:
    synthesis = _read("skills/season/plan-synthesis/SKILL.md")
    audit = _read("skills/season/audit/SKILL.md")

    assert "inherited Scenario authority" in synthesis
    assert "must not replace it" in audit or "different cadence than the selected Scenario" in audit
    assert "MINI_RESET" in synthesis or "mini-reset" in synthesis
    assert "RELOAD" in synthesis or "reload" in synthesis


def test_season_skills_preserve_durability_without_intensity_free_collapse() -> None:
    macrocycle = _read("skills/season/macrocycle-architecture/SKILL.md")
    governance = _read("skills/season/governance-review/SKILL.md")

    assert "durability-first is not intensity-free" in macrocycle
    assert "RECOVERY" in governance
    assert "dominant `ENDURANCE`" in governance
    assert "`B` events receive only rehearsal" in governance
