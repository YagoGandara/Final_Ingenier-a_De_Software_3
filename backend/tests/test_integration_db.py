import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db import SessionLocal, engine
from app.models import Base


@pytest.fixture(autouse=True, scope="module")
def setup_db():
    """
    Test de integración: usa la DB real (SQLite) y el stack real de FastAPI.
    Crea las tablas y limpia antes y después de correr los tests.
    """
    # Crear tablas si no existen
    Base.metadata.create_all(bind=engine)

    # Limpiar antes
    db = SessionLocal()
    try:
        # Best effort: si la tabla no existe o cambia el modelo, no rompemos el test
        try:
            db.execute("DELETE FROM todos")
            db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()

    yield

    # Limpieza final (best effort)
    db = SessionLocal()
    try:
        try:
            db.execute("DELETE FROM todos")
            db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


@pytest.mark.integration
def test_list_todos_integration_uses_real_db(setup_db):
    """
    Llama a /todos y verifica que responda 200.
    Esto atraviesa FastAPI + capa de acceso a datos + SQLite real.
    No asumimos un shape específico del JSON para no atarnos al contrato.
    """
    client = TestClient(app)

    resp_list = client.get("/todos")
    assert resp_list.status_code == 200


@pytest.mark.integration
def test_health_and_ready_uses_real_db(setup_db):
    """
    Valida que /readyz toque la DB real y responda 200,
    y que /healthz también responda 200.
    Acepta respuestas del tipo {'app': 'ok', 'db': 'ok'} u otras variantes.
    """
    client = TestClient(app)

    # /readyz chequea DB + app
    resp_ready = client.get("/readyz")
    assert resp_ready.status_code == 200
    data_ready = resp_ready.json()

    # Debe ser un dict no vacío y todos los valores en 'ok'
    assert isinstance(data_ready, dict)
    assert data_ready  # no vacío
    assert all(value == "ok" for value in data_ready.values())

    # /healthz también debería responder OK
    resp_health = client.get("/healthz")
    assert resp_health.status_code == 200
