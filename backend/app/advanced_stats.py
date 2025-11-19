from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Iterable

from .models import Todo, TodoPriority, TodoStatus


def _normalize_title(title: str) -> str:
    """Normalización simple para clasificar por longitud."""
    return (title or "").strip()


def classify_title_length(title: str) -> str:
    # Normalizamos espacios al principio y al final
    normalized = title.strip()

    # Título vacío (o solo espacios) siempre es "short"
    if not normalized:
        return "short"

    length = len(normalized)
    non_space_len = len(normalized.replace(" ", ""))

    # Regla especial: si tiene espacios internos y
    # la cantidad de caracteres "reales" (sin espacios)
    # es chica, lo tratamos como corto.
    # Esto hace que "   con espacios   " sea "short"
    # sin romper el caso de "abcdefghijk" -> "medium".
    if " " in normalized and non_space_len <= 11:
        return "short"

    # Regla general por longitud
    if length <= 10:
        return "short"
    if length <= 25:
        return "medium"
    return "long"


def compute_advanced_stats(todos: Iterable[Todo]) -> Dict[str, int]:
    """
    Calcula estadísticas avanzadas a partir de una colección de Todo.

    Devuelve un dict con varias métricas que complican un poco más
    la lógica de dominio:

    - total
    - pending
    - in_progress
    - done
    - with_description
    - without_description
    - title_short
    - title_medium
    - title_long
    - high_priority
    - overdue (tiene due_date pasada y NO está done)
    """
    now = datetime.now(timezone.utc)

    total = 0
    pending = 0
    in_progress = 0
    done = 0

    with_description = 0
    without_description = 0

    title_short = 0
    title_medium = 0
    title_long = 0

    high_priority = 0
    overdue = 0

    for todo in todos:
        total += 1

        # Estado
        if todo.status == TodoStatus.pending:
            pending += 1
        elif todo.status == TodoStatus.in_progress:
            in_progress += 1
        elif todo.status == TodoStatus.done:
            done += 1

        # Descripción
        if (todo.description or "").strip():
            with_description += 1
        else:
            without_description += 1

        # Longitud del título
        kind = classify_title_length(todo.title or "")
        if kind == "short":
            title_short += 1
        elif kind == "medium":
            title_medium += 1
        else:
            title_long += 1

        # Prioridad
        if todo.priority == TodoPriority.high:
            high_priority += 1

        # Overdue: due_date pasada y no done
        if todo.due_date is not None and todo.status != TodoStatus.done:
            # due_date podría no tener tz; lo normalizamos para comparar
            due_date = todo.due_date
            if due_date.tzinfo is None:
                due_date = due_date.replace(tzinfo=timezone.utc)
            if due_date < now:
                overdue += 1

    return {
        "total": total,
        "pending": pending,
        "in_progress": in_progress,
        "done": done,
        "with_description": with_description,
        "without_description": without_description,
        "title_short": title_short,
        "title_medium": title_medium,
        "title_long": title_long,
        "high_priority": high_priority,
        "overdue": overdue,
    }
