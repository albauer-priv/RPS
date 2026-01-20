#!/usr/bin/env python3
"""Bundle JSON schemas by resolving $ref into standalone files."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from app.schemas.bundler import SchemaBundler  # noqa: E402


def main() -> int:
    """Bundle all schemas/ into knowledge/_shared/sources/schemas/bundled/."""
    schema_dir = ROOT / "schemas"
    output_dir = ROOT / "knowledge" / "_shared" / "sources" / "schemas" / "bundled"
    output_dir.mkdir(parents=True, exist_ok=True)

    bundler = SchemaBundler(schema_dir)
    for schema_path in sorted(schema_dir.glob("*.schema.json")):
        bundled = bundler.bundle(schema_path.name)
        out_path = output_dir / schema_path.name
        out_path.write_text(
            json.dumps(bundled, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Bundled: {schema_path.name} -> {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
