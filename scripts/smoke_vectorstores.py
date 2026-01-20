#!/usr/bin/env python3
"""Smoke test for vector store attachment and retrieval."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.data_pipeline.common import load_env  # noqa: E402
from app.openai.vectorstore_state import load_vectorstore_id  # noqa: E402


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the smoke test."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", default="micro_planner", help="Agent name for the agent store.")
    parser.add_argument("--shared", default="vs_shared_training", help="Shared store name.")
    parser.add_argument("--question", default="List a document filename from the agent store.")
    parser.add_argument("--model", default="gpt-4.1")
    parser.add_argument("--max-results", type=int, default=3)
    parser.add_argument("--force-tool", action="store_true", help="Force file_search tool usage.")
    return parser.parse_args()


def main() -> int:
    """Run a simple retrieval request to verify vector stores."""
    load_env()
    args = parse_args()

    shared_id = load_vectorstore_id(args.shared)
    agent_id = load_vectorstore_id(f"vs_{args.agent}")

    client = OpenAI()
    payload = {
        "model": args.model,
        "input": args.question,
        "tools": [
            {
                "type": "file_search",
                "vector_store_ids": [shared_id, agent_id],
                "max_num_results": args.max_results,
            }
        ],
        "include": ["file_search_call.results"],
    }
    response = None
    if args.force_tool:
        payload["tool_choice"] = {"type": "file_search"}
    try:
        response = client.responses.create(**payload)
    except Exception as exc:
        if args.force_tool:
            payload.pop("tool_choice", None)
            response = client.responses.create(**payload)
        else:
            raise exc

    found = False
    for item in response.output:
        if getattr(item, "type", None) == "file_search_call":
            found = True
            files = []
            for result in item.results:
                name = getattr(result, "filename", None) or getattr(result, "file_id", "")
                files.append(name)
            print("FILES:", files)

    if not found:
        print("WARN: No file_search_call results. Try --force-tool or a more specific question.")
    print("TEXT:", response.output_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
