"""Schema utility helpers."""

from __future__ import annotations

from typing import Any


def is_envelope_schema(schema: dict[str, Any]) -> bool:
    """Return True if a schema represents the {meta,data} envelope shape."""
    if "allOf" in schema and isinstance(schema["allOf"], list):
        for entry in schema["allOf"]:
            if isinstance(entry, dict) and entry.get("$ref") == "artefact_envelope.schema.json":
                return True

    props = schema.get("properties", {})
    return isinstance(props, dict) and "meta" in props and "data" in props
