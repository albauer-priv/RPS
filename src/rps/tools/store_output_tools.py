"""Helpers for building strict store tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from rps.agents.tasks import OutputSpec
from rps.schemas.bundler import SchemaBundler

ToolDef = dict[str, object]
StoreResult = dict[str, object]


def build_strict_store_tool(bundler: SchemaBundler, spec: OutputSpec) -> ToolDef:
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
    guard_put_validated: Callable[..., StoreResult]
