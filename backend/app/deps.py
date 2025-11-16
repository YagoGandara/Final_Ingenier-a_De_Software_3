from __future__ import annotations

from typing import Generator
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import Todo


class Store:
    def __init__(self, db: Session):
        self.db = db

    def list(self):
        return self.db.query(Todo).order_by(Todo.id).all()

    def add(self, title: str, description: str | None = None):
        todo = Todo(title=title, description=description)
        self.db.add(todo)
        self.db.commit()
        self.db.refresh(todo)
        return todo

    def toggle(self, todo_id: int):
        """Invierte el estado done de un TODO. Devuelve el TODO actualizado o None si no existe."""
        todo = self.db.query(Todo).filter(Todo.id == todo_id).first()
        if not todo:
            return None
        todo.done = not bool(todo.done)
        self.db.add(todo)
        self.db.commit()
        self.db.refresh(todo)
        return todo

    def health(self):
        self.db.execute("SELECT 1")
        return {"status": "ok"}


def get_store() -> Generator[Store, None, None]:
    db = SessionLocal()
    try:
        yield Store(db)
    finally:
        db.close()
