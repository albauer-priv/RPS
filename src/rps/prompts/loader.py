"""Prompt loading helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_PROMPTS_DIR = Path("prompts")


def load_prompt(path: Path) -> str:
    """Read a prompt file from disk."""
    return path.read_text(encoding="utf-8")


def agent_system_prompt(agent_name: str, prompts_dir: Path = DEFAULT_PROMPTS_DIR) -> str:
    """Combine shared system prompt and the agent-specific prompt."""
    system_path = prompts_dir / "shared" / "system.md"
    agent_path = prompts_dir / "agents" / f"{agent_name}.md"

    system_prompt = load_prompt(system_path)
    agent_prompt = load_prompt(agent_path)
    return f"{system_prompt}\n\n{agent_prompt}"


@dataclass(frozen=True)
class PromptLoader:
    """Prompt loader that validates prompt files exist."""
    prompts_dir: Path = DEFAULT_PROMPTS_DIR

    def _read(self, path: Path) -> str:
        """Read a prompt file, raising if it is missing."""
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")
        return path.read_text(encoding="utf-8")

    def system_prompt(self) -> str:
        """Return the shared system prompt."""
        return self._read(self.prompts_dir / "shared" / "system.md")

    def agent_prompt(self, agent_name: str) -> str:
        """Return the agent-specific prompt."""
        return self._read(self.prompts_dir / "agents" / f"{agent_name}.md")

    def combined_system_prompt(self, agent_name: str) -> str:
        """Return the combined shared + agent prompt."""
        return f"{self.system_prompt()}\n\n{self.agent_prompt(agent_name)}"
