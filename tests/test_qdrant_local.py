from rps.vectorstores import qdrant_local


def test_get_qdrant_client_reuses_same_path(monkeypatch):
    created = []

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            created.append((args, kwargs))

    qdrant_local._build_qdrant_client.cache_clear()
    monkeypatch.setattr(qdrant_local, "QdrantClient", _FakeClient)
    monkeypatch.setenv("RPS_LLM_VECTORSTORE_PATH", ".cache/qdrant")

    client_a = qdrant_local.get_qdrant_client()
    client_b = qdrant_local.get_qdrant_client()

    assert client_a is client_b
    assert len(created) == 1
