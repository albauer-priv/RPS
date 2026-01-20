"""Schema registry and validation helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


@dataclass(frozen=True)
class SchemaRef:
    """Points to a root schema file within the schema directory."""

    schema_file: str


class SchemaRegistry:
    """Loads all schemas from a folder and supports $ref resolution."""

    def __init__(self, schema_dir: Path):
        """Initialize a registry backed by all JSON schemas in schema_dir."""
        self.schema_dir = schema_dir.resolve()
        if not self.schema_dir.exists():
            raise FileNotFoundError(f"Schema directory not found: {self.schema_dir}")

        self._registry: Registry = Registry()
        self._load_all()

    def _load_all(self) -> None:
        """Load and register all JSON schema files in the directory."""
        for path in self.schema_dir.glob("*.json"):
            raw = json.loads(path.read_text(encoding="utf-8"))
            schema_id = raw.get("$id", path.name)
            self._registry = self._registry.with_resource(
                schema_id,
                Resource.from_contents(raw),
            )

    def get_schema(self, schema_file: str) -> dict[str, Any]:
        """Load a schema by filename."""
        path = self.schema_dir / schema_file
        if not path.exists():
            raise FileNotFoundError(f"Schema file not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def validator_for(self, schema_file: str) -> Draft202012Validator:
        """Return a Draft2020-12 validator for a schema file."""
        schema = self.get_schema(schema_file)
        return Draft202012Validator(schema, registry=self._registry)


class SchemaValidationError(ValueError):
    """Raised when schema validation fails with one or more errors."""

    def __init__(self, message: str, errors: list[str]):
        """Initialize with a message and a list of schema errors."""
        super().__init__(message)
        self.errors = errors


def validate_or_raise(validator: Draft202012Validator, instance: dict[str, Any]) -> None:
    """Validate instance and raise with a readable error list on failure."""
    errors: list[str] = []
    for err in sorted(validator.iter_errors(instance), key=str):
        loc = ".".join([str(item) for item in err.path]) or "<root>"
        errors.append(f"{loc}: {err.message}")

    if errors:
        raise SchemaValidationError("Schema validation failed", errors)
