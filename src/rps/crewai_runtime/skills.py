"""CrewAI skill configuration and prompt rendering helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import CrewAIConfigBundle

JsonMap = dict[str, Any]

OPERATIONAL_CREW_SKILLS: tuple[str, ...] = (
    "skills/shared/runtime-boundaries",
    "skills/shared/resolved-context-consumption",
    "skills/shared/traceability-and-naming",
    "skills/shared/replan-instruction-authoring",
)


def resolve_agent_skill_profile(
    bundle: CrewAIConfigBundle,
    *,
    agent_name: str,
    crew_name: str | None = None,
) -> JsonMap:
    """Resolve crew-level operational skills plus the one method skill for an agent."""

    config = bundle.skills
    crew_paths: list[str] = []
    if crew_name:
        crew_cfg = (config.get("crews") or {}).get(crew_name) or {}
        crew_paths = [str(item) for item in (crew_cfg.get("skills") or []) if isinstance(item, str)]

    agent_cfg = (config.get("agents") or {}).get(agent_name) or {}
    agent_skill = agent_cfg.get("skill")
    agent_skill_path = str(agent_skill) if isinstance(agent_skill, str) and agent_skill else ""

    paths = [*crew_paths]
    if agent_skill_path:
        paths.append(agent_skill_path)

    return {
        "paths": paths,
        "crew_skills": crew_paths,
        "agent_skill": agent_skill_path,
    }


def build_crewai_skill_kwargs(*, root: Path, profile: JsonMap) -> JsonMap:
    """Return CrewAI skill kwargs using local directory paths."""

    paths = [str((root / path).resolve()) for path in (profile.get("paths") or [])]
    return {"skills": paths} if paths else {}


def render_skill_prompt_block(*, root: Path, profile: JsonMap) -> str:
    """Render SKILL.md bodies as a deterministic prompt block.

    Keep the compatibility layer aligned with CrewAI's normal skill behavior:
    the active skill body is injected, while `references/` remain optional support material.
    """

    skill_paths = [str(path) for path in (profile.get("paths") or [])]
    if not skill_paths:
        return ""

    chunks: list[str] = ["Activated skills (methodology and guidance):"]
    for skill_path in skill_paths:
        skill_dir = (root / skill_path).resolve()
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            raise FileNotFoundError(f"Configured skill missing SKILL.md: {skill_md}")
        skill_text = skill_md.read_text(encoding="utf-8").strip()
        chunks.append(f'{skill_path}/SKILL.md:\n"""\n{skill_text}\n"""')

    return "\n\n".join(chunks)
