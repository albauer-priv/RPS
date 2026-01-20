"""Configuration helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    """OpenAI connection settings sourced from the environment."""

    openai_api_key: str
    openai_org_id: str | None
    openai_project_id: str | None
    openai_base_url: str | None


@dataclass(frozen=True)
class AppSettings:
    """Application-level runtime settings for storage and prompts."""

    openai_model: str
    workspace_root: Path
    schema_dir: Path
    prompts_dir: Path
    vs_state_path: Path
    shared_vs_name: str


def load_env_file(path: str | Path) -> None:
    """Load a simple KEY=VALUE env file into the process environment."""
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_settings() -> Settings:
    """Return OpenAI connection settings, raising if required values are missing."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required")

    return Settings(
        openai_api_key=api_key,
        openai_org_id=os.getenv("OPENAI_ORG_ID"),
        openai_project_id=os.getenv("OPENAI_PROJECT_ID"),
        openai_base_url=os.getenv("OPENAI_BASE_URL"),
    )


def load_app_settings() -> AppSettings:
    """Return application runtime settings with sensible defaults."""
    return AppSettings(
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1"),
        workspace_root=Path(os.getenv("ATHLETE_WORKSPACE_ROOT", "var/athletes")),
        schema_dir=Path(os.getenv("SCHEMA_DIR", "schemas")),
        prompts_dir=Path(os.getenv("PROMPTS_DIR", "prompts")),
        vs_state_path=Path(os.getenv("VECTORSTORE_STATE_PATH", ".cache/vectorstores_state.json")),
        shared_vs_name=os.getenv("SHARED_VECTORSTORE_NAME", "vs_shared_training"),
    )
