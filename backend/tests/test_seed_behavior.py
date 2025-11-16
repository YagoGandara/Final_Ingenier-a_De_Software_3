# backend/tests/test_seed_behavior.py
from app import seed


class DummyDb:
    def __init__(self, count: int):
        self._count = count
        self.committed = False
        self.added = []

    def query(self, model):
        class Q:
            def __init__(self, n: int):
                self._n = n

            def count(self) -> int:
                return self._n

        return Q(self._count)

    def add_all(self, items):
        self.added.extend(items)

    def commit(self):
        self.committed = True


def test_seed_if_needed_does_nothing_when_table_not_empty():
    db = DummyDb(count=3)

    inserted = seed.seed_if_needed(db)

    # no debería tocar nada
    assert inserted == 0
    assert db.added == []
    assert not db.committed


def test_seed_if_needed_inserts_when_table_empty():
    db = DummyDb(count=0)

    inserted = seed.seed_if_needed(db)

    # cuando está vacía tiene que insertar algo
    assert inserted > 0
    assert len(db.added) == inserted
    assert db.committed
