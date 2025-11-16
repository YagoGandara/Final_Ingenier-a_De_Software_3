from typing import List

from fastapi.testclient import TestClient

from app.main import app
from app.deps import get_store


class DummyTodo:
  def __init__(self, id: int, title: str, done: bool = False, description: str | None = None):
      self.id = id
      self.title = title
      self.done = done
      self.description = description


class FakeStore:
    """Store en memoria para probar las rutas nuevas sin tocar la DB real."""

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

    def toggle(self, todo_id: int) -> DummyTodo | None:
        for t in self._todos:
            if t.id == todo_id:
                t.done = not t.done
                return t
        return None

    def health(self) -> dict:
        return {"status": "ok"}


def _override_store(store: FakeStore):
    def override_get_store():
        return store

    app.dependency_overrides[get_store] = override_get_store


def _clear_overrides():
    app.dependency_overrides.clear()


def test_todos_stats_on_empty_store_returns_zeros():
    store = FakeStore(initial=[])
    _override_store(store)
    try:
        with TestClient(app) as client:
            resp = client.get("/api/todos/stats")
        assert resp.status_code == 200
        body = resp.json()
        assert body == {"total": 0, "done": 0, "pending": 0}
    finally:
        _clear_overrides()


def test_todos_stats_counts_done_and_pending():
    store = FakeStore(
        initial=[
            DummyTodo(id=1, title="A", done=False),
            DummyTodo(id=2, title="B", done=True),
            DummyTodo(id=3, title="C", done=True),
        ]
    )
    _override_store(store)
    try:
        with TestClient(app) as client:
            resp = client.get("/api/todos/stats")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert body["done"] == 2
        assert body["pending"] == 1
    finally:
        _clear_overrides()


def test_search_todos_without_filters_returns_all():
    store = FakeStore(
        initial=[
            DummyTodo(id=1, title="Primero", done=False),
            DummyTodo(id=2, title="Segundo", done=True),
        ]
    )
    _override_store(store)
    try:
        with TestClient(app) as client:
            resp = client.get("/api/todos/search")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 2
        titles = {t["title"] for t in body}
        assert titles == {"Primero", "Segundo"}
    finally:
        _clear_overrides()


def test_search_todos_filter_by_done_true():
    store = FakeStore(
        initial=[
            DummyTodo(id=1, title="Pendiente", done=False),
            DummyTodo(id=2, title="Hecho", done=True),
        ]
    )
    _override_store(store)
    try:
        with TestClient(app) as client:
            resp = client.get("/api/todos/search", params={"done": True})
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["title"] == "Hecho"
    finally:
        _clear_overrides()


def test_search_todos_filter_by_text_in_title_or_description():
    store = FakeStore(
        initial=[
            DummyTodo(id=1, title="Comprar pan", done=False),
            DummyTodo(id=2, title="Otra cosa", done=False, description="algo de pan"),
            DummyTodo(id=3, title="Nada que ver", done=False),
        ]
    )
    _override_store(store)
    try:
        with TestClient(app) as client:
            resp = client.get("/api/todos/search", params={"q": "pan"})
        assert resp.status_code == 200
        body = resp.json()
        titles = {t["title"] for t in body}
        assert titles == {"Comprar pan", "Otra cosa"}
    finally:
        _clear_overrides()


def test_search_todos_filter_by_done_and_text_combined():
    store = FakeStore(
        initial=[
            DummyTodo(id=1, title="Pendiente pan", done=False),
            DummyTodo(id=2, title="Hecho pan", done=True),
            DummyTodo(id=3, title="Hecho otra cosa", done=True),
        ]
    )
    _override_store(store)
    try:
        with TestClient(app) as client:
            resp = client.get("/api/todos/search", params={"q": "pan", "done": True})
        assert resp.status_code == 200
        body = resp.json()
        titles = [t["title"] for t in body]
        assert titles == ["Hecho pan"]
    finally:
        _clear_overrides()


def test_create_todo_uses_normalized_title_before_saving():
    store = FakeStore(initial=[])
    _override_store(store)
    try:
        with TestClient(app) as client:
            resp = client.post("/api/todos", json={"title": "  Comprar   pan  "})
        assert resp.status_code == 201
        assert len(store.add_calls) == 1
        assert store.add_calls[0]["title"] == "Comprar pan"
    finally:
        _clear_overrides()


def test_toggle_todo_flips_done_flag_and_returns_updated_todo():
    store = FakeStore(
        initial=[
            DummyTodo(id=1, title="Pendiente", done=False),
        ]
    )
    _override_store(store)
    try:
        with TestClient(app) as client:
            resp = client.patch("/api/todos/1/toggle")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == 1
        assert body["done"] is True
    finally:
        _clear_overrides()


def test_toggle_todo_returns_404_when_not_found():
    store = FakeStore(initial=[])
    _override_store(store)
    try:
        with TestClient(app) as client:
            resp = client.patch("/api/todos/999/toggle")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "todo not found"
    finally:
        _clear_overrides()
