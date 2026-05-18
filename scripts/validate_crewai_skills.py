"""Validate CrewAI skill packages referenced by RPS runtime config."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
LOCAL_RESOURCE_PREFIXES = ("references/", "scripts/", "assets/")
FORBIDDEN_REPO_PREFIXES = (
    "../",
    "skills/",
    "specs/knowledge/",
    "doc/",
    "config/",
    "prompts/",
    "/",
)
OUTPUT_SECTION_PATTERN = re.compile(
    r"(?im)^(?:#{1,3}\s*)?(ausgabe|output|expected output|output format|answer format|antwortformat|antwortstruktur|"
    r"ergebnisformat|prüfergebnis|response format|result format|deliverable|format)\b"
)
POSITIVE_TERMS = (
    "answer",
    "arbeite",
    "beschreibe",
    "build",
    "check",
    "choose",
    "create",
    "draft",
    "emit",
    "explain",
    "gib",
    "include",
    "leite",
    "liefere",
    "nimm",
    "priorisiere",
    "produce",
    "prüfe",
    "return",
    "schreibe",
    "set",
    "summarize",
    "use",
    "verwende",
    "wähle",
)
NEGATIVE_TERMS = (
    "avoid",
    "block",
    "darf nicht",
    "do not",
    "don't",
    "forbidden",
    "kein",
    "keine",
    "never",
    "nicht",
    "no ",
    "not ",
    "verboten",
    "vermeide",
)
EXPLICIT_NEGATIVE_PATTERN = re.compile(
    r"(?im)(\bdo not\b|\bdon't\b|\bnever\b|\bavoid\b|\bmust not\b|\bforbidden\b|"
    r"\bdarf nicht\b|\bsoll nicht\b|\bvermeide\b|^- no\b)"
)


@dataclass(frozen=True)
class SkillIssue:
    """One validation finding for a CrewAI skill package."""

    severity: str
    path: str
    message: str


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a mapping.")
    return data


def configured_skill_paths(root: Path) -> list[Path]:
    """Return unique skill package directories referenced by config/crewai/skills.yaml."""

    config = _load_yaml(root / "config" / "crewai" / "skills.yaml")
    paths: set[str] = set()
    for crew_def in (config.get("crews") or {}).values():
        if isinstance(crew_def, dict):
            paths.update(str(item) for item in (crew_def.get("skills") or []))
    for agent_def in (config.get("agents") or {}).values():
        if isinstance(agent_def, dict) and isinstance(agent_def.get("skill"), str):
            paths.add(str(agent_def["skill"]))
    return [root / item for item in sorted(paths)]


def _skill_name(skill_md: Path) -> str | None:
    """Extract the frontmatter `name:` value from a SKILL.md file."""

    for line in skill_md.read_text(encoding="utf-8").splitlines():
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip('"').strip("'")
    return None


def _candidate_path_tokens(text: str) -> list[str]:
    """Return inline-code and Markdown-link targets that look path-like."""

    tokens: list[str] = []
    tokens.extend(match.group(1).strip() for match in re.finditer(r"`([^`]+)`", text))
    tokens.extend(match.group(1).strip() for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text))
    return [
        token
        for token in tokens
        if any(marker in token for marker in (*LOCAL_RESOURCE_PREFIXES, *FORBIDDEN_REPO_PREFIXES))
    ]


def _count_terms(text: str, terms: tuple[str, ...]) -> int:
    lowered = text.lower()
    return sum(lowered.count(term) for term in terms)


def _has_output_format(text: str) -> bool:
    return bool(OUTPUT_SECTION_PATTERN.search(text)) or "task expected_output" in text.lower()


def _is_guardrail_like(skill_dir: Path) -> bool:
    name = skill_dir.name.lower()
    return any(marker in name for marker in ("guardrail", "syntax", "audit", "review", "constraint"))


def validate_skill_dir(skill_dir: Path, *, root: Path) -> list[SkillIssue]:
    """Validate one CrewAI skill package directory."""

    rel = str(skill_dir.relative_to(root)) if skill_dir.is_relative_to(root) else str(skill_dir)
    issues: list[SkillIssue] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_dir.exists():
        return [SkillIssue("ERROR", rel, "Configured skill directory does not exist.")]
    if not skill_md.exists():
        return [SkillIssue("ERROR", rel, "Configured skill directory is missing SKILL.md.")]

    text = skill_md.read_text(encoding="utf-8")
    name = _skill_name(skill_md)
    if name != skill_dir.name:
        issues.append(
            SkillIssue(
                "ERROR",
                str(skill_md.relative_to(root)),
                f"Skill frontmatter name must match directory name: expected {skill_dir.name!r}, got {name!r}.",
            )
        )

    for token in _candidate_path_tokens(text):
        if token.startswith(("http://", "https://", "mailto:")):
            continue
        if token.startswith(FORBIDDEN_REPO_PREFIXES):
            issues.append(
                SkillIssue(
                    "ERROR",
                    str(skill_md.relative_to(root)),
                    f"Reference must stay inside the skill package, got {token!r}.",
                )
            )
            continue
        if token.startswith(LOCAL_RESOURCE_PREFIXES):
            target = (skill_dir / token).resolve()
            try:
                target.relative_to(skill_dir.resolve())
            except ValueError:
                issues.append(
                    SkillIssue(
                        "ERROR",
                        str(skill_md.relative_to(root)),
                        f"Local reference escapes the skill package: {token!r}.",
                    )
                )
                continue
            if not target.exists():
                issues.append(
                    SkillIssue(
                        "ERROR",
                        str(skill_md.relative_to(root)),
                        f"Local reference does not exist: {token!r}.",
                    )
                )

    positive_count = _count_terms(text, POSITIVE_TERMS)
    negative_count = _count_terms(text, NEGATIVE_TERMS)
    if EXPLICIT_NEGATIVE_PATTERN.search(text):
        issues.append(
            SkillIssue(
                "WARN",
                str(skill_md.relative_to(root)),
                "Skill should express operating guidance positively; rewrite explicit don't/never/no-style rules as desired behavior.",
            )
        )
    if positive_count == 0:
        issues.append(
            SkillIssue(
                "WARN",
                str(skill_md.relative_to(root)),
                "Skill should describe positive actions the agent should perform.",
            )
        )
    elif negative_count >= 8 and negative_count > positive_count:
        severity = "INFO" if _is_guardrail_like(skill_dir) else "WARN"
        issues.append(
            SkillIssue(
                severity,
                str(skill_md.relative_to(root)),
                "Negative constraints outweigh positive operating instructions; add positive behavior guidance.",
            )
        )

    if not _has_output_format(text):
        issues.append(
            SkillIssue(
                "WARN",
                str(skill_md.relative_to(root)),
                "Skill should include an explicit Output/Antwortformat section or reference the task expected_output.",
            )
        )
    return issues


def validate_configured_skills(root: Path) -> list[SkillIssue]:
    """Validate all configured CrewAI skills."""

    issues: list[SkillIssue] = []
    for skill_dir in configured_skill_paths(root):
        issues.extend(validate_skill_dir(skill_dir, root=root))
    return issues


def _print_issues(issues: list[SkillIssue]) -> None:
    for issue in issues:
        print(f"{issue.severity}: {issue.path}: {issue.message}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root.")
    parser.add_argument(
        "--fail-on-warnings",
        action="store_true",
        help="Return non-zero for WARN findings in addition to ERROR findings.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    issues = validate_configured_skills(root)
    _print_issues(issues)
    error_count = sum(1 for issue in issues if issue.severity == "ERROR")
    warning_count = sum(1 for issue in issues if issue.severity == "WARN")
    info_count = sum(1 for issue in issues if issue.severity == "INFO")
    print(
        f"Validated {len(configured_skill_paths(root))} configured CrewAI skills: "
        f"{error_count} errors, {warning_count} warnings, {info_count} info."
    )
    if error_count or (args.fail_on_warnings and warning_count):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
