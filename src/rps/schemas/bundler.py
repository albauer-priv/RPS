"""Bundle JSON schemas by resolving local file references."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonref


@dataclass(frozen=True)
class SchemaBundler:
    """Resolve local schema references into a single JSON schema object."""
    schema_dir: Path
    _bundle_cache: dict[str, dict[str, Any]] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )

    def load_raw(self, schema_file: str) -> dict[str, Any]:
        """Load a schema file from disk without resolving references."""
        path = (self.schema_dir / schema_file).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Schema not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def bundle(self, schema_file: str) -> dict[str, Any]:
        """Return a fully resolved schema with $ref replaced."""
        cached = self._bundle_cache.get(schema_file)
        if cached is not None:
            return cached

        root = self.load_raw(schema_file)

        def loader(uri: str):
            """Resolve a schema reference relative to the schema directory."""
            path = (self.schema_dir / uri).resolve()
            if not path.exists():
                raise FileNotFoundError(f"Missing referenced schema file: {path}")
            return json.loads(path.read_text(encoding="utf-8"))

        bundled = jsonref.JsonRef.replace_refs(root, loader=loader)

        def _to_builtin(obj: Any) -> Any:
            if isinstance(obj, jsonref.JsonRef):
                return dict(obj)
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        resolved = json.loads(json.dumps(bundled, default=_to_builtin))
        bundled_schema = self._strip_schema_ids(resolved, keep_root_id=True)
        self._bundle_cache[schema_file] = bundled_schema
        return bundled_schema

    def _strip_schema_ids(self, schema: Any, *, keep_root_id: bool) -> Any:
        """Remove nested $id values to avoid duplicate canonical URIs in bundled schemas."""
        if isinstance(schema, dict):
            result = {}
            for key, value in schema.items():
                if key == "$id" and not keep_root_id:
                    continue
                result[key] = self._strip_schema_ids(value, keep_root_id=False)
            return result
        if isinstance(schema, list):
            return [self._strip_schema_ids(item, keep_root_id=False) for item in schema]
        return schema
