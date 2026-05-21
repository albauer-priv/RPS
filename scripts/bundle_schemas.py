#!/usr/bin/env python3
"""Bundle JSON schemas by resolving $ref into standalone files."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from rps.core.config import load_env_file  # noqa: E402
from rps.schemas.bundler import SchemaBundler  # noqa: E402
from scripts.generate_artifact_models import write_generated_models  # noqa: E402
from scripts.script_logging import configure_logging  # noqa: E402


def main() -> int:
    """Bundle all specs/schemas/ into canonical and output-safe schema targets."""
    load_env_file(ROOT / ".env")
    logger = configure_logging(ROOT, Path(__file__).stem)
    schema_dir = ROOT / "specs" / "schemas"
    output_dir = ROOT / "specs" / "knowledge" / "_shared" / "sources" / "schemas" / "bundled"
    output_output_dir = (
        ROOT / "specs" / "knowledge" / "_shared" / "sources" / "schemas" / "bundled_output"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    output_output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Bundling schemas from %s to %s and %s", schema_dir, output_dir, output_output_dir)
    bundler = SchemaBundler(schema_dir)
    schema_paths = sorted(schema_dir.glob("*.schema.json"))
    logger.info("Found %d schema files", len(schema_paths))
    for schema_path in schema_paths:
        bundled = bundler.bundle(schema_path.name)
        bundled_output = bundler.bundle_output(schema_path.name)
        out_path = output_dir / schema_path.name
        out_output_path = output_output_dir / schema_path.name
        out_path.write_text(
            json.dumps(bundled, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        out_output_path.write_text(
            json.dumps(bundled_output, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        logger.debug("Bundled %s -> %s", schema_path.name, out_path)
        logger.debug("Bundled output %s -> %s", schema_path.name, out_output_path)
        print(f"Bundled: {schema_path.name} -> {out_path}")
        print(f"Bundled output: {schema_path.name} -> {out_output_path}")

    logger.info("Bundled %d schema files", len(schema_paths))
    generated = write_generated_models()
    print("Generated CrewAI artifact models")
    logger.info("Generated CrewAI artifact models (%d bytes)", len(generated))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
