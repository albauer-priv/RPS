"""Bundle JSON schemas by resolving local file references."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import jsonref


@dataclass(frozen=True)
class SchemaBundler:
    """Resolve local schema references into a single JSON schema object."""
    schema_dir: Path

    def load_raw(self, schema_file: str) -> dict[str, Any]:
        """Load a schema file from disk without resolving references."""
        path = (self.schema_dir / schema_file).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Schema not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    @lru_cache(maxsize=256)
    def bundle(self, schema_file: str) -> dict[str, Any]:
        """Return a fully resolved schema with $ref replaced."""
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

        return json.loads(json.dumps(bundled, default=_to_builtin))
