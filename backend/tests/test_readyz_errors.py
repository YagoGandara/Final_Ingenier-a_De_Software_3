# backend/tests/test_readyz_errors.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_readyz_returns_503_when_db_fails(monkeypatch):
    def fake_get_db():
        class Dummy:
            def execute(self, *_args, **_kwargs):
                raise RuntimeError("boom")
        yield Dummy()

    from app.main import get_db  # o donde esté definido
    app.dependency_overrides[get_db] = fake_get_db

    resp = client.get("/readyz")
    assert resp.status_code == 503
    assert resp.json()["detail"] == "db not ready"

    app.dependency_overrides.clear()
