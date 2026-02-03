"""Sync local manifests to OpenAI hosted vector stores.

Deprecated: Vector store sync now runs automatically in the Streamlit UI
(background task). Use this CLI only for manual recovery or headless ops.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SYS_PATH = str(ROOT / "src")
if SYS_PATH not in sys.path:
    # Allow running this script directly without installing the package.
    sys.path.insert(0, SYS_PATH)

from rps.core.config import load_env_file  # noqa: E402
from rps.openai.vectorstores import iter_manifest_paths, load_manifest, sync_manifest  # noqa: E402
from rps.openai.vectorstore_state import DEFAULT_STATE_PATH, load_state, write_state  # noqa: E402
from script_logging import configure_logging  # noqa: E402


def select_manifests(args: argparse.Namespace) -> list[Path]:
    """Resolve the manifest paths based on CLI arguments."""
    if args.manifest:
        return [Path(args.manifest).resolve()]

    knowledge_root = (ROOT / args.knowledge_root).resolve()
    unified = knowledge_root / "all_agents" / "manifest.yaml"
    if unified.exists():
        return [unified]
    manifests = iter_manifest_paths(knowledge_root)
    if not args.agent:
        return manifests

    selected: list[Path] = []
    for manifest_path in manifests:
        manifest = load_manifest(manifest_path)
        if manifest.agent == args.agent or manifest_path.parent.name == args.agent:
            selected.append(manifest_path)
    return selected


def main() -> None:
    """Sync local manifest sources to OpenAI vector stores."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--knowledge-root", default="knowledge")
    parser.add_argument("--manifest", help="Path to a single manifest.yaml")
    parser.add_argument("--agent", help="Sync only a single agent")
    parser.add_argument("--delete-removed", action="store_true")
    parser.add_argument("--prune", action="store_true", help="Alias for --delete-removed")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete all files from the vector store before syncing",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH)
    args = parser.parse_args()

    load_env_file(ROOT / ".env")
    logger = configure_logging(ROOT, Path(__file__).stem)

    manifests = select_manifests(args)
    if not manifests:
        print("No manifests found.")
        logger.warning("No manifests found for sync")
        return

    delete_removed = args.delete_removed or args.prune
    state = load_state(args.state)

    for manifest_path in manifests:
        logger.info("Sync manifest %s", manifest_path)
        stats = sync_manifest(
            manifest_path=manifest_path,
            delete_removed=delete_removed,
            dry_run=args.dry_run,
            reset=args.reset,
            progress=True,
            state=None if args.dry_run else state,
        )
        print(
            f"{manifest_path}: added={stats['added']} "
            f"updated={stats['updated']} removed={stats['removed']} "
            f"skipped={stats['skipped']}"
        )
        logger.info(
            "Sync stats manifest=%s added=%s updated=%s removed=%s skipped=%s dry_run=%s reset=%s",
            manifest_path,
            stats["added"],
            stats["updated"],
            stats["removed"],
            stats["skipped"],
            args.dry_run,
            args.reset,
        )

    if not args.dry_run:
        write_state(args.state, state)
        print(f"State updated: {args.state}")


if __name__ == "__main__":
    main()
