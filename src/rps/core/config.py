"""Configuration helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import re


@dataclass(frozen=True)
class Settings:
    """LLM connection settings sourced from the environment."""

    openai_api_key: str
    openai_org_id: str | None
    openai_project_id: str | None
    openai_base_url: str | None


@dataclass(frozen=True)
class AppSettings:
    """Application-level runtime settings for storage and prompts."""

    openai_model: str
    openai_model_overrides: dict[str, str]
    openai_temperature: float | None
    openai_temperature_overrides: dict[str, float]
    openai_reasoning_effort: str | None
    openai_reasoning_summary: str | None
    openai_reasoning_effort_overrides: dict[str, str]
    openai_reasoning_summary_overrides: dict[str, str]
    workspace_root: Path
    schema_dir: Path
    prompts_dir: Path
    vs_state_path: Path
    file_search_max_results: int

    def model_for_agent(self, agent_name: str) -> str:
        """Return the model override for an agent, or the default model."""
        key = normalize_agent_name(agent_name)
        return self.openai_model_overrides.get(key, self.openai_model)

    def temperature_for_agent(self, agent_name: str) -> float | None:
        """Return the temperature override for an agent, or the default temperature."""
        key = normalize_agent_name(agent_name)
        return self.openai_temperature_overrides.get(key, self.openai_temperature)

    def reasoning_effort_for_agent(self, agent_name: str) -> str | None:
        """Return the reasoning effort override for an agent, or the default."""
        key = normalize_agent_name(agent_name)
        return self.openai_reasoning_effort_overrides.get(key, self.openai_reasoning_effort)

    def reasoning_summary_for_agent(self, agent_name: str) -> str | None:
        """Return the reasoning summary override for an agent, or the default."""
        key = normalize_agent_name(agent_name)
        return self.openai_reasoning_summary_overrides.get(key, self.openai_reasoning_summary)


def normalize_agent_name(value: str) -> str:
    """Normalize an agent name for env key mapping."""
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return cleaned.lower()


def _parse_float(value: str | None) -> float | None:
    """Parse a float from env, returning None on invalid input."""
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_int(value: str | None) -> int | None:
    """Parse an int from env, returning None on invalid input."""
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


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
        if not key:
            continue
        current = os.environ.get(key)
        if current is None or current == "":
            os.environ[key] = value


def load_settings() -> Settings:
    """Return LLM connection settings, raising if required values are missing."""
    api_key = os.getenv("RPS_LLM_API_KEY")
    if not api_key:
        raise RuntimeError("RPS_LLM_API_KEY is required")

    return Settings(
        openai_api_key=api_key,
        openai_org_id=os.getenv("RPS_LLM_ORG_ID"),
        openai_project_id=os.getenv("RPS_LLM_PROJECT_ID"),
        openai_base_url=os.getenv("RPS_LLM_BASE_URL"),
    )


def load_app_settings() -> AppSettings:
    """Return application runtime settings with sensible defaults."""
    overrides: dict[str, str] = {}
    for key, value in os.environ.items():
        if not key.startswith("RPS_LLM_MODEL_") or key == "RPS_LLM_MODEL":
            continue
        if not value:
            continue
        agent_key = normalize_agent_name(key[len("RPS_LLM_MODEL_"):])
        if agent_key:
            overrides[agent_key] = value

    temp_overrides: dict[str, float] = {}
    for key, value in os.environ.items():
        if not key.startswith("RPS_LLM_TEMPERATURE_") or key == "RPS_LLM_TEMPERATURE":
            continue
        parsed = _parse_float(value)
        if parsed is None:
            continue
        agent_key = normalize_agent_name(key[len("RPS_LLM_TEMPERATURE_"):])
        if agent_key:
            temp_overrides[agent_key] = parsed

    reasoning_effort_overrides: dict[str, str] = {}
    for key, value in os.environ.items():
        if not key.startswith("RPS_LLM_REASONING_EFFORT_") or key == "RPS_LLM_REASONING_EFFORT":
            continue
        if not value:
            continue
        agent_key = normalize_agent_name(key[len("RPS_LLM_REASONING_EFFORT_"):])
        if agent_key:
            reasoning_effort_overrides[agent_key] = value

    reasoning_summary_overrides: dict[str, str] = {}
    for key, value in os.environ.items():
        if not key.startswith("RPS_LLM_REASONING_SUMMARY_") or key == "RPS_LLM_REASONING_SUMMARY":
            continue
        if not value:
            continue
        agent_key = normalize_agent_name(key[len("RPS_LLM_REASONING_SUMMARY_"):])
        if agent_key:
            reasoning_summary_overrides[agent_key] = value

    return AppSettings(
        openai_model=os.getenv("RPS_LLM_MODEL", "gpt-4.1"),
        openai_model_overrides=overrides,
        openai_temperature=_parse_float(os.getenv("RPS_LLM_TEMPERATURE")),
        openai_temperature_overrides=temp_overrides,
        openai_reasoning_effort=os.getenv("RPS_LLM_REASONING_EFFORT"),
        openai_reasoning_summary=os.getenv("RPS_LLM_REASONING_SUMMARY"),
        openai_reasoning_effort_overrides=reasoning_effort_overrides,
        openai_reasoning_summary_overrides=reasoning_summary_overrides,
        workspace_root=Path(os.getenv("ATHLETE_WORKSPACE_ROOT", "var/athletes")),
        schema_dir=Path(os.getenv("SCHEMA_DIR", "schemas")),
        prompts_dir=Path(os.getenv("PROMPTS_DIR", "prompts")),
        vs_state_path=Path(os.getenv("VECTORSTORE_STATE_PATH", ".cache/vectorstores_state.json")),
        file_search_max_results=_parse_int(os.getenv("RPS_LLM_FILE_SEARCH_MAX_RESULTS")) or 20,
    )
