# backend/tests/test_seed_behavior.py
from app.seed import seed_if_empty, DEFAULT_TODOS
from app.models import Todo


class DummyDb:
    """
    DB fake muy simple para testear la lógica de seed_if_empty
    sin usar SQLAlchemy real.
    """
    def __init__(self, count: int):
        self._count = count
        self.queried = False
        self.added: list[Todo] = []
        self.committed = False

    def query(self, model):
        assert model is Todo

        class Q:
            def __init__(self, n: int):
                self._n = n

            def count(self) -> int:
                return self._n

        self.queried = True
        return Q(self._count)

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True


def test_seed_if_empty_skips_when_table_not_empty():
    db = DummyDb(count=3)

    result = seed_if_empty(db)

    # debería consultar la cantidad
    assert db.queried

    # no inserta nada ni hace commit
    assert result == {"inserted": 0, "skipped": True, "existing": 3}
    assert db.added == []
    assert not db.committed


def test_seed_if_empty_inserts_when_table_empty():
    db = DummyDb(count=0)

    result = seed_if_empty(db)

    # inserta todos los DEFAULT_TODOS
    assert result["inserted"] == len(DEFAULT_TODOS)
    assert result["skipped"] is False
    assert result["existing"] == 0

    assert len(db.added) == len(DEFAULT_TODOS)
    assert all(isinstance(t, Todo) for t in db.added)
    assert db.committed
