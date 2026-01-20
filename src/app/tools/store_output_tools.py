"""Helpers for building strict store tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.agents.tasks import OutputSpec
from app.schemas.bundler import SchemaBundler


def build_strict_store_tool(bundler: SchemaBundler, spec: OutputSpec) -> dict[str, Any]:
    """Build a strict function tool schema for storing output."""
    bundled_schema = bundler.bundle(spec.schema_file)

    if spec.envelope:
        params = bundled_schema
    else:
        params = {
            "type": "object",
            "properties": {
                "workouts": bundled_schema,
            },
            "required": ["workouts"],
            "additionalProperties": False,
        }

    return {
        "type": "function",
        "name": spec.tool_name,
        "strict": True,
        "description": f"Store validated output for task={spec.task.value}, artifact={spec.artifact_type.value}.",
        "parameters": params,
    }


@dataclass
class StoreToolContext:
    """Runtime context for saving artifacts via a guarded store."""
    athlete_id: str
    run_id: str
    producer_agent: str
    guard_put_validated: Callable[[str, Any, OutputSpec], dict[str, Any]]
