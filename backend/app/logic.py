from __future__ import annotations

from typing import Sequence, Protocol


class HasTodoShape(Protocol):
    """Interfaz mínima que nos interesa de un "todo" para estas funciones.

    No requerimos que sea exactamente app.models.Todo; cualquier objeto que
    tenga al menos `title`, `done` y `description` es suficiente.
    """

    title: str
    done: bool
    description: str | None


def normalize_title(title: str) -> str:
    """Normaliza un título.

    - Elimina espacios al inicio y al final.
    - Colapsa múltiples espacios internos en uno solo.

    Ejemplo:
        "   Hola   mundo  " -> "Hola mundo"
    """
    # split() sin argumentos ya hace trim + colapsa espacios en blanco
    parts = title.split()
    return " ".join(parts)


def is_empty_title(title: str) -> bool:
    """Indica si un título se considera vacío bajo nuestras reglas.

    Cualquier string que, una vez normalizado, quede vacío, se considera vacío.
    """
    return normalize_title(title) == ""


def is_duplicate_title(title: str, existing: Sequence[HasTodoShape]) -> bool:
    """Chequea si `title` ya existe en `existing`.

    - Comparamos de forma case-insensitive.
    - Usamos el título normalizado tanto para el nuevo como para los existentes.
    """
    norm_new = normalize_title(title).lower()
    if not norm_new:
        # Si ya es vacío, no lo consideramos duplicado aquí; esa es otra regla.
        return False

    for item in existing:
        existing_norm = normalize_title(getattr(item, "title", "")).lower()
        if existing_norm == norm_new:
            return True
    return False


def validate_new_todo(title: str, existing: Sequence[HasTodoShape]) -> None:
    """Valida las reglas de dominio para crear un TODO nuevo.

    Levanta ValueError con códigos específicos:
    - "empty"     -> título vacío
    - "duplicate" -> ya existe un TODO con ese título
    """
    if is_empty_title(title):
        raise ValueError("empty")

    if is_duplicate_title(title, existing):
        raise ValueError("duplicate")


def compute_stats(todos: Sequence[HasTodoShape]) -> dict[str, int]:
    """Devuelve estadísticas simples sobre la lista de TODOs."""
    total = len(todos)
    done = sum(1 for t in todos if bool(getattr(t, "done", False)))
    pending = total - done
    return {"total": total, "done": done, "pending": pending}


def filter_todos(
    todos: Sequence[HasTodoShape],
    *,
    done: bool | None = None,
    text: str | None = None,
) -> list[HasTodoShape]:
    """Filtra TODOs en memoria por estado `done` y/o texto.

    - done: si es True, sólo completados; si es False, sólo pendientes;
      si es None, no filtra por estado.
    - text: se busca (case-insensitive) en título y descripción.
    """
    result: list[HasTodoShape] = list(todos)

    if done is not None:
        result = [t for t in result if bool(getattr(t, "done", False)) is done]

    if text:
        needle = text.lower()
        filtered: list[HasTodoShape] = []
        for t in result:
            title = str(getattr(t, "title", "")).lower()
            desc = str(getattr(t, "description", "") or "").lower()
            if needle in title or needle in desc:
                filtered.append(t)
        result = filtered

    return result
