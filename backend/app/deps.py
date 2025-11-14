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

    def health(self):
        # toca la DB para comprobar que responde
        self.db.execute("SELECT 1")
        return {"status": "ok"}


def get_store() -> Generator[Store, None, None]:
    db = SessionLocal()
    try:
        yield Store(db)
    finally:
        db.close()
