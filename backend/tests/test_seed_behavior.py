# backend/tests/test_seed_behavior.py
from app import seed
from app.models import Todo

class DummyDb:
    def __init__(self, count):
        self._count = count
        self.committed = False
        self.added = []

    def query(self, model):
        class Q:
            def __init__(self, n):
                self._n = n
            def count(self):
                return self._n
        return Q(self._count)

    def add_all(self, items):
        self.added.extend(items)

    def commit(self):
        self.committed = True


def test_seed_if_needed_does_nothing_when_table_not_empty():
    db = DummyDb(count=3)
    inserted = seed.seed_if_needed(db)
    assert inserted == 0
    assert db.added == []
    assert not db.committed
