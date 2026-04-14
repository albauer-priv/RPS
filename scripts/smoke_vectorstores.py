#!/usr/bin/env python3
"""Smoke test for local vector store retrieval."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from script_logging import configure_logging  # noqa: E402

from rps.openai.vectorstore_state import (  # noqa: E402
    DEFAULT_STATE_PATH,
    load_state,
    load_vectorstore_id,
    write_state,
)
from rps.openai.vectorstores import compute_manifest_hash, sync_manifest  # noqa: E402
from rps.vectorstores.qdrant_local import (  # noqa: E402
    embed_texts,
    get_qdrant_client,
    resolve_embedding_config,
    search_points,
)
from scripts.data_pipeline.common import load_env  # noqa: E402


def _default_max_results() -> int:
    raw = os.getenv("RPS_LLM_FILE_SEARCH_MAX_RESULTS", "").strip()
    if not raw:
        return 3
    try:
        return int(raw)
    except ValueError:
        return 3


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the smoke test."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--store",
        default="vs_rps_all_agents",
        help="Vector store name to query (default: vs_rps_all_agents).",
    )
    parser.add_argument("--question", default="List a document filename from the agent store.")
    parser.add_argument("--max-results", type=int, default=_default_max_results())
    return parser.parse_args()


def main() -> int:
    """Run a simple retrieval request to verify vector stores."""
    load_env()
    logger = configure_logging(ROOT, Path(__file__).stem)
    args = parse_args()

    api_key_set = bool(os.getenv("RPS_LLM_API_KEY"))
    project_id_set = bool(os.getenv("RPS_LLM_PROJECT_ID"))
    org_id_set = bool(os.getenv("RPS_LLM_ORG_ID"))
    print(
        "LLM env preflight: RPS_LLM_API_KEY={} RPS_LLM_PROJECT_ID={} RPS_LLM_ORG_ID={}".format(
            "set" if api_key_set else "missing",
            "set" if project_id_set else "missing",
            "set" if org_id_set else "missing",
        )
    )

    try:
        store_id = load_vectorstore_id(args.store)
    except KeyError:
        store_id = args.store
    logger.info("Smoke test store=%s store_id=%s", args.store, store_id)

    client = get_qdrant_client()
    config = resolve_embedding_config()
    vector = embed_texts([args.question], config)[0]

    manifest_path = ROOT / "specs" / "knowledge" / "all_agents" / "manifest.yaml"

    def _sync_collection() -> str:
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")
        state = load_state()
        logger.warning("Collection missing; running local sync from %s", manifest_path)
        stats = sync_manifest(
            manifest_path=manifest_path,
            delete_removed=True,
            reset=True,
            progress=True,
            state=state,
            client=client,
        )
        state_entry = state.setdefault("vectorstores", {}).setdefault(args.store, {})
        state_entry["manifest_hash"] = compute_manifest_hash(manifest_path)
        write_state(DEFAULT_STATE_PATH, state)
        updated_id = load_vectorstore_id(args.store)
        logger.info("Sync complete; store_id=%s (stats=%s)", updated_id, stats)
        return updated_id

    def _collection_exists(collection_name: str) -> bool:
        try:
            if hasattr(client, "get_collection"):
                client.get_collection(collection_name)
                return True
            if hasattr(client, "get_collections"):
                collections = client.get_collections()
                items = collections.collections if hasattr(collections, "collections") else collections
                return any(getattr(item, "name", None) == collection_name for item in items or [])
        except ValueError:
            return False
        return False

    if not _collection_exists(store_id):
        store_id = _sync_collection()

    try:
        results = search_points(
            client,
            collection_name=store_id,
            query_vector=vector,
            limit=args.max_results,
            with_payload=True,
        )
    except ValueError as exc:
        if "Collection" not in str(exc):
            raise
        store_id = _sync_collection()
        results = search_points(
            client,
            collection_name=store_id,
            query_vector=vector,
            limit=args.max_results,
            with_payload=True,
        )
    logger.info("Results: %d", len(results))
    for idx, result in enumerate(results, start=1):
        payload = result.payload or {}
        logger.info("%d) score=%.4f source=%s", idx, result.score, payload.get("source_path"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
