"""Vector store state persistence helpers."""

from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass

JsonMap = dict[str, object]
RemoteFileRecord = dict[str, object]
RemoteIndex = dict[str, RemoteFileRecord]

DEFAULT_STATE_PATH = Path("runtime/vectorstores_state.json")


def load_state(state_path: Path = DEFAULT_STATE_PATH) -> JsonMap:
    """Load the vector store sync state, returning an empty structure if missing."""
    if not state_path.exists():
        return {"vectorstores": {}}
    return json.loads(state_path.read_text(encoding="utf-8"))


def write_state(state_path: Path, state: JsonMap) -> None:
    """Persist the vector store sync state to disk."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def load_vectorstore_id(store_name: str, state_path: Path = DEFAULT_STATE_PATH) -> str:
    """Look up a vector store id by name from the state file."""
    state = load_state(state_path)
    vectorstores = state.get("vectorstores", {})
    if not isinstance(vectorstores, dict):
        vectorstores = {}
    entry = vectorstores.get(store_name)
    if not isinstance(entry, dict) or not entry.get("vector_store_id"):
        raise KeyError(f"Vector store id not found for {store_name}")
    return str(entry["vector_store_id"])


def update_state_for_store(
    state: JsonMap,
    store_name: str,
    vector_store_id: str,
    remote_index: RemoteIndex,
) -> None:
    """Update state for a store using a normalized remote index."""
    vectorstores = state.setdefault("vectorstores", {})
    if not isinstance(vectorstores, dict):
        raise TypeError("vectorstores state must be a mapping")
    entry = vectorstores.setdefault(store_name, {"files": {}})
    if not isinstance(entry, dict):
        raise TypeError(f"vectorstores[{store_name}] must be a mapping")
    entry["vector_store_id"] = vector_store_id

    files: dict[str, object] = {}
    for source_path, info in remote_index.items():
        if not info.get("managed"):
            continue
        files[source_path] = {
            "sha256": info.get("sha256"),
            "file_id": info.get("file_id"),
            "tags": info.get("tags") or [],
        }

    entry["files"] = files


@dataclass(frozen=True)
class VectorStoreResolver:
    """Load vector store IDs from the local sync state file."""
    state_path: Path = DEFAULT_STATE_PATH

    def _load(self) -> JsonMap:
        """Load the raw state JSON, raising if missing."""
        if not self.state_path.exists():
            raise FileNotFoundError(
                f"Vectorstore state file not found: {self.state_path}\n"
                f"Run the Streamlit app or sync via scripts/smoke_vectorstores.py"
            )
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def id_for_store_name(self, store_name: str) -> str:
        """Return the vector store ID for the given store name."""
        data = self._load()
        try:
            vectorstores = data.get("vectorstores", {})
            if not isinstance(vectorstores, dict):
                raise KeyError("vectorstores")
            entry = vectorstores.get(store_name)
            if not isinstance(entry, dict):
                raise KeyError(store_name)
            return str(entry["vector_store_id"])
        except KeyError as exc:
            raise KeyError(f"Vector store '{store_name}' not found in {self.state_path}") from exc
