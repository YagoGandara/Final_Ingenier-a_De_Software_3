# backend/tests/test_readyz_errors.py
from fastapi.testclient import TestClient
import app.main as main_module

client = TestClient(main_module.app)


def test_readyz_returns_503_when_db_fails(monkeypatch):
    """
    Fuerza que /readyz falle simulando que la SessionLocal levanta una excepción.
    Así cubrimos la rama de error (status 503).
    """

    class DummyContext:
        def __enter__(self):
            # cualquier excepción sirve, va al except Exception
            raise Exception("db down")

        def __exit__(self, exc_type, exc, tb):
            # no manejamos la excepción
            return False

    def fake_session_local():
        # readyz hace: with SessionLocal() as db: ...
        return DummyContext()

    # Parcheamos la SessionLocal que usa readyz internamente
    monkeypatch.setattr(main_module, "SessionLocal", fake_session_local)

    resp = client.get("/readyz")
    assert resp.status_code == 503
    data = resp.json()
    assert data["db"] == "down"
    assert "error" in data
