from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    Integer,
    String,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarativa para todos los modelos."""
    pass


class TodoStatus(str, Enum):
    """Estado de la tarea, usado por advanced_stats y los tests."""
    pending = "pending"
    in_progress = "in_progress"
    done = "done"


class TodoPriority(str, Enum):
    """Prioridad de la tarea, usada por advanced_stats y los tests."""
    low = "low"
    medium = "medium"
    high = "high"


class Todo(Base):
    __tablename__ = "todos"

    # Campos originales
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    done = Column(Boolean, default=False)

    # Campos nuevos para estadísticas avanzadas
    priority = Column(
        SAEnum(TodoPriority, name="todo_priority"),
        nullable=False,
        default=TodoPriority.medium,
    )
    status = Column(
        SAEnum(TodoStatus, name="todo_status"),
        nullable=False,
        default=TodoStatus.pending,
    )
    due_date = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # opcional, sólo para debug lindo
        return (
            f"Todo(id={self.id!r}, title={self.title!r}, "
            f"done={self.done!r}, priority={self.priority!r}, "
            f"status={self.status!r}, due_date={self.due_date!r})"
        )
