#!/usr/bin/env python3
"""Verify every JSON schema has required covering all properties."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SYS_PATH = str(ROOT / "src")
if SYS_PATH not in sys.path:
    # Allow running the script directly without installing the package.
    sys.path.insert(0, SYS_PATH)

from app.core.config import load_env_file  # noqa: E402
from script_logging import configure_logging  # noqa: E402

load_env_file(ROOT / ".env")
logger = configure_logging(ROOT, Path(__file__).stem)


def find_schema_files(root: Path) -> list[Path]:
    return sorted(root.glob("*.schema.json"))


def check_required_coverage(obj: Any, path_stack: list[str], issues: list[str]) -> None:
    if isinstance(obj, dict):
        props = obj.get("properties")
        req = obj.get("required")
        if isinstance(props, dict):
            prop_keys = set(props.keys())
            if req is None:
                issues.append(f"{'/'.join(path_stack)} :: missing required for properties {sorted(prop_keys)}")
            elif isinstance(req, list):
                missing = sorted(prop_keys - set(req))
                if missing:
                    issues.append(f"{'/'.join(path_stack)} :: required missing keys {missing}")
            else:
                issues.append(f"{'/'.join(path_stack)} :: required not list ({req})")
        for key, value in obj.items():
            check_required_coverage(value, path_stack + [str(key)], issues)
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            check_required_coverage(value, path_stack + [str(index)], issues)


def check_schema(path: Path) -> list[str]:
    try:
        data = json.loads(path.read_text())
    except Exception as exc:  # pragma: no cover - CLI visibility
        return [f"{path} :: parse_error :: {exc}"]
    issues: list[str] = []
    check_required_coverage(data, [str(path)], issues)
    return issues


def main() -> int:
    root = Path.cwd()
    schema_dirs = [
        root / "schemas",
        root / "knowledge" / "_shared" / "sources" / "schemas" / "bundled",
    ]
    files: list[Path] = []
    for directory in schema_dirs:
        if directory.exists():
            files.extend(find_schema_files(directory))

    logger.info("Checking required coverage for %d schema files", len(files))
    all_issues: list[str] = []
    for path in files:
        all_issues.extend(check_schema(path))

    if all_issues:
        logger.error("Required coverage issues=%d", len(all_issues))
        print("Schema required coverage issues found:")
        for issue in all_issues:
            print(f"- {issue}")
        return 1

    logger.info("No required coverage issues found")
    print(f"OK: {len(files)} schema files checked, no required coverage issues.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
