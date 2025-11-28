from typing import List

import pytest
from fastapi.testclient import TestClient

from app.main import app, settings
from app.deps import get_store


class DummyTodo:
    def __init__(self, id: int, title: str, done: bool = False, description: str | None = None):
        self.id = id
        self.title = title
        self.done = done
        self.description = description


class FakeStore:
    """Store fake en memoria para no usar la DB real.

    Implementa solo lo que los endpoints necesitan: list() y add().
    Además guarda un registro de llamadas a add() para las aserciones.
    """

    def __init__(self, initial: List[DummyTodo] | None = None):
        self._todos: List[DummyTodo] = initial or []
        self.add_calls: list[dict] = []

    def list(self) -> List[DummyTodo]:
        return list(self._todos)

    def add(self, title: str, description: str | None = None) -> DummyTodo:
        new_id = (max([t.id for t in self._todos]) + 1) if self._todos else 1
        todo = DummyTodo(id=new_id, title=title, description=description, done=False)
        self._todos.append(todo)
        self.add_calls.append({"title": title, "description": description})
        return todo

    def health(self):
        return {"status": "ok"}


@pytest.fixture
def fake_store():
    """Store fake por test, aislado entre casos."""
    return FakeStore(
        initial=[
            DummyTodo(id=1, title="Primera tarea", done=False),
            DummyTodo(id=2, title="Segunda tarea", done=True),
        ]
    )


@pytest.fixture
def client(fake_store):
    """Client de FastAPI con override del get_store para usar FakeStore."""

    def override_get_store():
        return fake_store

    app.dependency_overrides[get_store] = override_get_store
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_healthz_ok():
    """/healthz debe responder 200 y status ok."""
    with TestClient(app) as c:
        resp = c.get("/healthz")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_list_todos_uses_store(client, fake_store):
    """/api/todos debe devolver lo que le entrega el Store."""
    resp = client.get("/api/todos")

    assert resp.status_code == 200
    data = resp.json()

    assert isinstance(data, list)
    assert len(data) == 2

    assert data[0]["id"] == 1
    assert data[0]["title"] == "Primera tarea"
    assert data[0]["done"] is False

    assert data[1]["id"] == 2
    assert data[1]["title"] == "Segunda tarea"
    assert data[1]["done"] is True


def test_create_todo_adds_to_store(client, fake_store):
    """Caso feliz de creación: debe delegar en Store.add y devolver el nuevo TODO."""
    payload = {"title": "Nueva tarea desde test"}

    resp = client.post("/api/todos", json=payload)

    assert resp.status_code == 201
    body = resp.json()

    # venía con 2 iniciales
    assert body["id"] == 3
    assert body["title"] == payload["title"]
    assert body["done"] is False

    # Verificamos que el store fue llamado correctamente
    assert len(fake_store.add_calls) == 1
    assert fake_store.add_calls[0]["title"] == payload["title"]


def test_create_todo_rejects_empty_title(client, fake_store):
    """Regla de negocio: el título no puede ser vacío ni solo espacios."""
    payload = {"title": "   ", "description": "cualquier cosa"}

    resp = client.post("/api/todos", json=payload)

    assert resp.status_code == 400
    body = resp.json()
    assert body["detail"] == "title must not be empty"

    # No debe intentar crear nada en el store
    assert fake_store.add_calls == []


def test_create_todo_rejects_duplicate_title_case_insensitive(client, fake_store):
    """Regla de negocio: títulos únicos (case-insensitive)."""
    # En el fake store ya existe "Primera tarea"
    payload = {"title": "  primera TAREA  "}

    resp = client.post("/api/todos", json=payload)

    assert resp.status_code == 400
    body = resp.json()
    assert body["detail"] == "title must be unique"

    # No debe intentar crear nada nuevo
    assert fake_store.add_calls == []


def test_admin_seed_unauthorized():
    """/admin/seed debe rechazar si el token no coincide."""
    settings.SEED_TOKEN = "SECRET"

    with TestClient(app) as c:
        resp = c.post("/admin/seed", headers={"X-Seed-Token": "WRONG"})

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Unauthorized"


def test_admin_seed_ok(monkeypatch):
    """/admin/seed con token correcto debe llamar a seed_if_empty (mockeado)."""
    from app import main as main_module

    called = {}

    def fake_seed_if_empty(db):
        called["ok"] = True
        return {"inserted": 3, "skipped": False, "existing": 0}

    settings.SEED_TOKEN = "SECRET"
    # Importante: parcheamos el símbolo que usa run_seed
    monkeypatch.setattr(main_module, "seed_if_empty", fake_seed_if_empty)

    with TestClient(app) as c:
        resp = c.post("/admin/seed", headers={"X-Seed-Token": "SECRET"})

    assert resp.status_code == 200
    body = resp.json()

    assert body["ok"] is True
    assert body["inserted"] == 3
    # Verificamos que nuestro fake fue invocado
    assert called.get("ok") is True

