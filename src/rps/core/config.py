"""Minimal application configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_GROQ_BASE_URL_MARKER = "api.groq.com"
_DEFAULT_GROQ_MODEL = "groq/openai/gpt-oss-20b"
_DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"
_DEFAULT_GROQ_MAX_COMPLETION_TOKENS = 2048


@dataclass(frozen=True)
class Settings:
    """Provider connection settings sourced from the environment."""

    openai_api_key: str
    openai_org_id: str | None
    openai_project_id: str | None
    openai_base_url: str | None


@dataclass(frozen=True)
class AppSettings:
    """Minimal app-level defaults plus local path settings."""

    openai_model: str
    openai_temperature: float | None
    openai_reasoning_effort: str | None
    openai_reasoning_summary: str | None
    openai_max_completion_tokens: int | None
    workspace_root: Path
    schema_dir: Path
    prompts_dir: Path

    def model_for_agent(self, _agent_name: str) -> str:
        """Return the global app default model."""

        return self.openai_model

    def temperature_for_agent(self, _agent_name: str) -> float | None:
        """Return the global app default temperature."""

        return self.openai_temperature

    def reasoning_effort_for_agent(self, _agent_name: str) -> str | None:
        """Return the global app default reasoning effort."""

        return self.openai_reasoning_effort

    def reasoning_summary_for_agent(self, _agent_name: str) -> str | None:
        """Return the global app default reasoning summary."""

        return self.openai_reasoning_summary

    def max_completion_tokens_for_agent(self, _agent_name: str) -> int | None:
        """Return the global app default max completion tokens."""

        return self.openai_max_completion_tokens

    def planning_enabled_for_crew(self, _crew_name: str, default_enabled: bool = False) -> bool:
        """Return the provided crew default unchanged.

        Crew-planning policy is owned by runtime profiles and provider helpers,
        not by app-level settings.
        """

        return default_enabled

    def planning_model_for_crew(self, _crew_name: str, default_model: str | None = None) -> str | None:
        """Return the provided planning-model default unchanged."""

        return default_model


def _parse_float(value: str | None) -> float | None:
    """Parse a float from env, returning ``None`` on invalid input."""

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
    """Parse an int from env, returning ``None`` on invalid input."""

    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _default_model(base_url: str | None) -> str:
    """Return the global default model for the active provider."""

    if base_url and _GROQ_BASE_URL_MARKER in base_url:
        return _DEFAULT_GROQ_MODEL
    return _DEFAULT_OPENAI_MODEL


def _default_max_completion_tokens(base_url: str | None) -> int | None:
    """Return the global default max completion tokens for the active provider."""

    if base_url and _GROQ_BASE_URL_MARKER in base_url:
        return _DEFAULT_GROQ_MAX_COMPLETION_TOKENS
    return None


def load_env_file(path: str | Path) -> None:
    """Load a simple ``KEY=VALUE`` env file into the process environment."""

    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
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
    """Return provider connection settings, raising if required values are missing."""

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
    """Return minimal application runtime settings with sensible defaults."""

    base_url = os.getenv("RPS_LLM_BASE_URL")
    default_model = os.getenv("RPS_LLM_MODEL") or _default_model(base_url)
    default_max_completion = _parse_int(os.getenv("RPS_LLM_MAX_COMPLETION_TOKENS"))
    if default_max_completion is None:
        default_max_completion = _default_max_completion_tokens(base_url)

    return AppSettings(
        openai_model=default_model,
        openai_temperature=_parse_float(os.getenv("RPS_LLM_TEMPERATURE")),
        openai_reasoning_effort=os.getenv("RPS_LLM_REASONING_EFFORT"),
        openai_reasoning_summary=os.getenv("RPS_LLM_REASONING_SUMMARY"),
        openai_max_completion_tokens=default_max_completion,
        workspace_root=Path(os.getenv("ATHLETE_WORKSPACE_ROOT", "runtime/athletes")),
        schema_dir=Path(os.getenv("SCHEMA_DIR", "specs/schemas")),
        prompts_dir=Path(os.getenv("PROMPTS_DIR", "prompts")),
    )
