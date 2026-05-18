from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_crewai_skills.py"
_SPEC = importlib.util.spec_from_file_location("validate_crewai_skills", _SCRIPT_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)

main = _MODULE.main
validate_configured_skills = _MODULE.validate_configured_skills
validate_skill_dir = _MODULE.validate_skill_dir


def _write_skill(root: Path, path: str, body: str) -> Path:
    skill_dir = root / path
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")
    return skill_dir


def test_validate_configured_skills_rejects_external_reference(tmp_path: Path) -> None:
    (tmp_path / "config" / "crewai").mkdir(parents=True)
    (tmp_path / "config" / "crewai" / "skills.yaml").write_text(
        """
crews: {}
agents:
  coach:
    skill: skills/conversation/example
""",
        encoding="utf-8",
    )
    _write_skill(
        tmp_path,
        "skills/conversation/example",
        """---
name: example
description: Example.
---
Use this method and return a compact Output.

Read `../shared/reference.md`.
""",
    )

    issues = validate_configured_skills(tmp_path)

    assert any(issue.severity == "ERROR" and "inside the skill package" in issue.message for issue in issues)


def test_validate_skill_warns_for_missing_positive_output_format(tmp_path: Path) -> None:
    skill_dir = _write_skill(
        tmp_path,
        "skills/week/example",
        """---
name: example
description: Example.
---
Do not do this. Never do that. Avoid everything.
""",
    )

    issues = validate_skill_dir(skill_dir, root=tmp_path)

    assert any(issue.severity == "WARN" and "positive actions" in issue.message for issue in issues)
    assert any(issue.severity == "WARN" and "Output" in issue.message for issue in issues)
    assert any(issue.severity == "WARN" and "positively" in issue.message for issue in issues)


def test_validate_skill_accepts_local_reference_and_output_format(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skills/week/example"
    (skill_dir / "references").mkdir(parents=True)
    (skill_dir / "references" / "method.md").write_text("details", encoding="utf-8")
    (skill_dir / "SKILL.md").write_text(
        """---
name: example
description: Example.
---
Use `references/method.md`.

Method:
- Read the context.
- Produce the plan.

Output format:
- Return status, rationale, and next action.
""",
        encoding="utf-8",
    )

    issues = validate_skill_dir(skill_dir, root=tmp_path)

    assert not [issue for issue in issues if issue.severity == "ERROR"]
    assert not [issue for issue in issues if issue.severity == "WARN"]


def test_cli_fail_on_warnings_returns_nonzero(tmp_path: Path) -> None:
    (tmp_path / "config" / "crewai").mkdir(parents=True)
    (tmp_path / "config" / "crewai" / "skills.yaml").write_text(
        """
crews: {}
agents:
  coach:
    skill: skills/conversation/example
""",
        encoding="utf-8",
    )
    _write_skill(
        tmp_path,
        "skills/conversation/example",
        """---
name: example
description: Example.
---
Use the context.
""",
    )

    assert main(["--root", str(tmp_path)]) == 0
    assert main(["--root", str(tmp_path), "--fail-on-warnings"]) == 1
