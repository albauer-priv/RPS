"""OpenAI client helpers."""

from __future__ import annotations

from openai import OpenAI

from rps.core.config import load_settings


def get_client() -> OpenAI:
    """Create an OpenAI client configured from environment settings."""
    settings = load_settings()
    kwargs: dict[str, str] = {}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    if settings.openai_org_id:
        kwargs["organization"] = settings.openai_org_id
    if settings.openai_project_id:
        kwargs["project"] = settings.openai_project_id
    return OpenAI(api_key=settings.openai_api_key, **kwargs)
