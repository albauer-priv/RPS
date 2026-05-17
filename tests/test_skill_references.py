import re
from pathlib import Path

SKILLS_ROOT = Path("skills")
LOCAL_RESOURCE_PREFIXES = ("references/", "scripts/", "assets/")
FORBIDDEN_SKILL_PATH_PREFIXES = (
    "../",
    "skills/",
    "specs/knowledge/",
    "doc/",
    "config/",
    "prompts/",
)


def _skill_name(skill_md: Path) -> str:
    for line in skill_md.read_text(encoding="utf-8").splitlines():
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip('"').strip("'")
    raise AssertionError(f"Missing skill name in {skill_md}")


def _candidate_path_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    tokens.extend(match.group(1).strip() for match in re.finditer(r"`([^`]+)`", text))
    tokens.extend(match.group(1).strip() for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text))
    return [token for token in tokens if any(marker in token for marker in (*LOCAL_RESOURCE_PREFIXES, *FORBIDDEN_SKILL_PATH_PREFIXES))]


def test_skill_names_match_directory_names() -> None:
    for skill_md in sorted(SKILLS_ROOT.glob("**/SKILL.md")):
        assert _skill_name(skill_md) == skill_md.parent.name


def test_skill_references_are_local_to_skill_directory() -> None:
    failures: list[str] = []
    for skill_md in sorted(SKILLS_ROOT.glob("**/SKILL.md")):
        skill_dir = skill_md.parent
        for token in _candidate_path_tokens(skill_md.read_text(encoding="utf-8")):
            if token.startswith(FORBIDDEN_SKILL_PATH_PREFIXES):
                failures.append(f"{skill_md}: cross-skill or repo path is not allowed: {token}")
                continue
            if token.startswith(LOCAL_RESOURCE_PREFIXES):
                target = skill_dir / token
                if not target.exists():
                    failures.append(f"{skill_md}: local skill reference does not exist: {token}")
    assert not failures, "\n".join(failures)


def test_runtime_does_not_manually_render_skill_bodies() -> None:
    forbidden = "render_" + "skill_prompt_block"
    runtime_files = [
        Path("src/rps/agents/crewai_backend.py"),
        Path("src/rps/crewai_runtime/coach_chat.py"),
        Path("src/rps/crewai_runtime/bindings.py"),
        Path("src/rps/crewai_runtime/skills.py"),
    ]
    failures = [str(path) for path in runtime_files if forbidden in path.read_text(encoding="utf-8")]
    assert not failures
