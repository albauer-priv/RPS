#!/usr/bin/env python3
"""Generate CrewAI artifact output models from canonical JSON schema files."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

SCHEMA_DIR = ROOT / "specs" / "schemas"
TASKS_CONFIG = ROOT / "config" / "crewai" / "tasks.yaml"
OUTPUT_FILE = ROOT / "src" / "rps" / "crewai_runtime" / "generated_artifact_models.py"


def _class_name_from_schema(schema: dict[str, Any], schema_file: str) -> str:
    title = str(schema.get("title") or "")
    raw = title or schema_file.removesuffix(".schema.json")
    parts = re.split(r"[^A-Za-z0-9]+|_", raw)
    name = "".join(part[:1].upper() + part[1:] for part in parts if part)
    if not name.endswith("Model"):
        name += "Model"
    if not name[:1].isalpha():
        name = f"Artifact{name}"
    return name


def _artifact_type_from_schema(schema: dict[str, Any]) -> str | None:
    meta = schema.get("properties", {}).get("meta")
    if not isinstance(meta, dict):
        return None
    artifact_type = meta.get("properties", {}).get("artifact_type")
    if isinstance(artifact_type, dict):
        const = artifact_type.get("const")
        if isinstance(const, str) and const:
            return const
    return None


def _load_task_schema_mapping(schema_files: set[str]) -> dict[str, str]:
    if not TASKS_CONFIG.exists():
        return {}
    raw = yaml.safe_load(TASKS_CONFIG.read_text(encoding="utf-8")) or {}
    tasks = raw.get("tasks") if isinstance(raw, dict) else None
    if not isinstance(tasks, dict):
        return {}
    mapping: dict[str, str] = {}
    for task_name, task_config in tasks.items():
        if not isinstance(task_name, str) or not isinstance(task_config, dict):
            continue
        if task_config.get("output") != "artifact_envelope":
            continue
        schema_file = f"{task_name}.schema.json"
        if schema_file in schema_files:
            mapping[task_name] = schema_file
    return mapping


def generate() -> str:
    schema_paths = sorted(SCHEMA_DIR.glob("*.schema.json"))
    schema_rows: list[tuple[str, str, str | None]] = []
    for schema_path in schema_paths:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        if not isinstance(schema.get("properties"), dict):
            continue
        properties = schema["properties"]
        if "meta" not in properties or "data" not in properties:
            continue
        schema_rows.append(
            (
                schema_path.name,
                _class_name_from_schema(schema, schema_path.name),
                _artifact_type_from_schema(schema),
            )
        )

    schema_files = {schema_file for schema_file, _, _ in schema_rows}
    task_schema_mapping = _load_task_schema_mapping(schema_files)
    class_by_schema = {schema_file: class_name for schema_file, class_name, _ in schema_rows}

    lines: list[str] = [
        '"""Generated CrewAI artifact output models. Do not edit by hand."""',
        "",
        "from __future__ import annotations",
        "",
        "from typing import Any",
        "",
        "from rps.crewai_runtime.models import ArtifactEnvelopeModel",
        "from rps.crewai_runtime.schema_backed_models import JsonSchemaArtifactModel",
        "",
        "",
    ]
    for schema_file, class_name, _artifact_type in schema_rows:
        lines.extend(
            [
                f"class {class_name}(JsonSchemaArtifactModel):",
                f'    """Schema-backed model for `{schema_file}`."""',
                "",
                f'    __schema_file__ = "{schema_file}"',
                "",
                "",
            ]
        )

    lines.append("ARTIFACT_MODEL_BY_SCHEMA_FILE: dict[str, type[JsonSchemaArtifactModel]] = {")
    for schema_file, class_name, _artifact_type in schema_rows:
        lines.append(f'    "{schema_file}": {class_name},')
    lines.append("}")
    lines.append("")

    lines.append("ARTIFACT_MODEL_BY_TYPE: dict[str, type[JsonSchemaArtifactModel]] = {")
    for _schema_file, class_name, artifact_type in schema_rows:
        if artifact_type:
            lines.append(f'    "{artifact_type}": {class_name},')
    lines.append("}")
    lines.append("")

    lines.append("ARTIFACT_MODEL_BY_TASK_NAME: dict[str, type[JsonSchemaArtifactModel]] = {")
    for task_name, schema_file in sorted(task_schema_mapping.items()):
        class_name = class_by_schema[schema_file]
        lines.append(f'    "{task_name}": {class_name},')
    lines.append("}")
    lines.append("")

    lines.extend(
        [
            "def artifact_model_for_schema_file(schema_file: str | None) -> type[Any]:",
            '    """Return the generated artifact model for a schema file, or the generic fallback."""',
            "",
            "    if schema_file and schema_file in ARTIFACT_MODEL_BY_SCHEMA_FILE:",
            "        return ARTIFACT_MODEL_BY_SCHEMA_FILE[schema_file]",
            "    return ArtifactEnvelopeModel",
            "",
            "",
            "def artifact_model_for_task_name(task_name: str | None) -> type[Any]:",
            '    """Return the generated artifact model for a CrewAI task name, or the generic fallback."""',
            "",
            "    if task_name and task_name in ARTIFACT_MODEL_BY_TASK_NAME:",
            "        return ARTIFACT_MODEL_BY_TASK_NAME[task_name]",
            "    return ArtifactEnvelopeModel",
            "",
        ]
    )
    return "\n".join(lines)


def write_generated_models() -> str:
    """Write generated artifact models and return the rendered source."""

    rendered = generate()
    OUTPUT_FILE.write_text(rendered, encoding="utf-8")
    return rendered


def main() -> int:
    write_generated_models()
    print(f"Generated CrewAI artifact models -> {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
