from types import SimpleNamespace

from rps.tools import knowledge_search


def test_search_knowledge_rebuilds_missing_collection(monkeypatch):
    calls = {"search": 0, "rebuild": 0}

    monkeypatch.setattr(knowledge_search, "_resolve_collection", lambda _agent: "vs_rps_all_agents")
    monkeypatch.setattr(knowledge_search, "get_qdrant_client", lambda: object())
    monkeypatch.setattr(knowledge_search, "resolve_embedding_config", lambda: object())
    monkeypatch.setattr(knowledge_search, "embed_texts", lambda _texts, _config: [[0.1, 0.2]])

    def _fake_search_points(*_args, **_kwargs):
        calls["search"] += 1
        if calls["search"] == 1:
            raise RuntimeError("Collection vs_rps_all_agents not found")
        return [
            SimpleNamespace(
                payload={"text": "match", "source_path": "doc.md", "tags": ["spec"], "attributes": {}},
                score=0.99,
            )
        ]

    def _fake_rebuild(_agent_name):
        calls["rebuild"] += 1

    monkeypatch.setattr(knowledge_search, "search_points", _fake_search_points)
    monkeypatch.setattr(knowledge_search, "_rebuild_collection_for_agent", _fake_rebuild)

    result = knowledge_search.search_knowledge("phase_architect", "phase guardrails", max_results=5)

    assert calls["search"] == 2
    assert calls["rebuild"] == 1
    assert result[0]["text"] == "match"


def test_knowledge_store_status_for_agent_ready(monkeypatch):
    monkeypatch.setattr(knowledge_search, "_manifest_for_store", lambda _store: knowledge_search.Path("specs/knowledge/all_agents/manifest.yaml"))
    monkeypatch.setattr(knowledge_search, "load_state", lambda _path: {"vectorstores": {"vs_rps_all_agents": {"vector_store_id": "vs_rps_all_agents"}}})

    class _Client:
        def get_collection(self, name):
            assert name == "vs_rps_all_agents"
            return {"name": name}

    monkeypatch.setattr(knowledge_search, "get_qdrant_client", lambda: _Client())

    status = knowledge_search.knowledge_store_status_for_agent("phase_architect")

    assert status["ready"] is True
    assert status["collection_name"] == "vs_rps_all_agents"
