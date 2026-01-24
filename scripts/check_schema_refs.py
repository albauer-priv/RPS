"""Check local schema directory for missing $ref targets."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SYS_PATH = str(ROOT / "src")
if SYS_PATH not in sys.path:
    # Allow running this script directly without installing the package.
    sys.path.insert(0, SYS_PATH)

from app.core.config import load_env_file  # noqa: E402
from script_logging import configure_logging  # noqa: E402

load_env_file(ROOT / ".env")
logger = configure_logging(ROOT, Path(__file__).stem)

schema_dir = Path("schemas")
refs = set()


def collect_refs(node) -> None:
    """Recursively collect $ref values from a JSON schema node."""
    if isinstance(node, dict):
        ref_value = node.get("$ref")
        if isinstance(ref_value, str):
            refs.add(ref_value)
        for value in node.values():
            collect_refs(value)
    elif isinstance(node, list):
        for value in node:
            collect_refs(value)


for path in schema_dir.glob("*.json"):
    raw = json.loads(path.read_text(encoding="utf-8"))
    collect_refs(raw)

refs = {ref.split("#", 1)[0] for ref in refs if not ref.startswith("#")}

missing = []
for ref in sorted(refs):
    if not (schema_dir / ref).exists():
        missing.append(ref)

print(f"Referenced schemas: {len(refs)}")
print(f"Missing schemas: {len(missing)}")
for ref in missing:
    print(f"  - {ref}")

logger.info("Referenced schemas=%d missing=%d", len(refs), len(missing))
if missing:
    logger.warning("Missing schema refs: %s", ", ".join(missing))
