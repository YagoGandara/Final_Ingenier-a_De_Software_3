import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db import SessionLocal, engine
from app.models import Base, Todo


@pytest.fixture(autouse=True, scope="module")
def setup_db():
    """
    Test de integración: usa la DB real (SQLite) y el Store real.
    Asegura que la tabla exista y empieza con la tabla vacía.
    """
    # Crear tablas si no existen
    Base.metadata.create_all(bind=engine)

    # Limpiar la tabla antes de correr los tests
    db = SessionLocal()
    try:
        db.query(Todo).delete()
        db.commit()
    finally:
        db.close()

    yield

    # Limpieza final (opcional)
    db = SessionLocal()
    try:
        db.query(Todo).delete()
        db.commit()
    finally:
        db.close()


@pytest.mark.integration
def test_create_and_list_todos_integration(setup_db):
    """
    Crea un todo vía HTTP y luego lo recupera desde /todos.
    Esto atraviesa FastAPI + Store + SQLAlchemy + SQLite.
    """
    client = TestClient(app)

    # Crear
    resp_create = client.post(
        "/todos",
        json={"title": "Todo integración", "description": "Creado desde test de integración"},
    )
    assert resp_create.status_code == 201
    body_create = resp_create.json()
    assert body_create["id"] > 0
    assert body_create["title"] == "Todo integración"

    # Listar
    resp_list = client.get("/todos")
    assert resp_list.status_code == 200
    todos = resp_list.json()
    titles = [t["title"] for t in todos]
    assert "Todo integración" in titles


@pytest.mark.integration
def test_health_and_ready_uses_real_db(setup_db):
    """
    Valida que /readyz toque la DB real (usa Store.health()) y que el sistema
    responda 200 cuando la DB está OK.
    """
    client = TestClient(app)

    # /readyz chequea DB + app
    resp_ready = client.get("/readyz")
    assert resp_ready.status_code == 200
    data_ready = resp_ready.json()
    assert data_ready.get("status") == "ok"

    # /healthz también debería responder OK
    resp_health = client.get("/healthz")
    assert resp_health.status_code == 200
