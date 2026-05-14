"""CrewAI skill configuration and prompt rendering helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import CrewAIConfigBundle

JsonMap = dict[str, Any]


def _bundle_skills(bundle_cfg: JsonMap, bundle_name: str) -> list[str]:
    bundles = bundle_cfg.get("bundles") or {}
    skill_bundle = bundles.get(bundle_name) or {}
    skills = skill_bundle.get("skills") or []
    return [str(item) for item in skills if isinstance(item, str)]


def resolve_agent_skill_profile(
    bundle: CrewAIConfigBundle,
    *,
    agent_name: str,
    crew_name: str | None = None,
) -> JsonMap:
    """Resolve configured skill paths for one agent, with optional crew inheritance."""

    config = bundle.skills
    paths: list[str] = []
    seen: set[str] = set()
    bundle_names: list[str] = []

    if crew_name:
        crew_cfg = (config.get("crews") or {}).get(crew_name) or {}
        for bundle_name in [str(item) for item in (crew_cfg.get("bundles") or [])]:
            bundle_names.append(bundle_name)
            for skill_path in _bundle_skills(config, bundle_name):
                if skill_path in seen:
                    continue
                seen.add(skill_path)
                paths.append(skill_path)

    agent_cfg = (config.get("agents") or {}).get(agent_name) or {}
    for bundle_name in [str(item) for item in (agent_cfg.get("bundles") or [])]:
        bundle_names.append(bundle_name)
        for skill_path in _bundle_skills(config, bundle_name):
            if skill_path in seen:
                continue
            seen.add(skill_path)
            paths.append(skill_path)

    for skill_path in [str(item) for item in (agent_cfg.get("skills") or []) if isinstance(item, str)]:
        if skill_path in seen:
            continue
        seen.add(skill_path)
        paths.append(skill_path)

    return {"paths": paths, "bundles": bundle_names}


def build_crewai_skill_kwargs(*, root: Path, profile: JsonMap) -> JsonMap:
    """Return CrewAI skill kwargs using directory paths.

    CrewAI supports passing local skill directories directly through ``skills=[...]``.
    """

    paths = [str((root / path).resolve()) for path in (profile.get("paths") or [])]
    return {"skills": paths} if paths else {}


def render_skill_prompt_block(*, root: Path, profile: JsonMap) -> str:
    """Render SKILL.md bodies as a deterministic prompt block.

    This keeps local compatibility when direct CrewAI skill execution is unavailable.
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
        chunks.append(f"{skill_path}/SKILL.md:\n\"\"\"\n{skill_md.read_text(encoding='utf-8').strip()}\n\"\"\"")
    return "\n\n".join(chunks)
