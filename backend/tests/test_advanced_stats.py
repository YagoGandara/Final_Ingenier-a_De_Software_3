from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.advanced_stats import classify_title_length, compute_advanced_stats
from app.models import Todo, TodoPriority, TodoStatus


def make_todo(
    *,
    title: str = "Tarea",
    description: str | None = None,
    priority: TodoPriority = TodoPriority.medium,
    status: TodoStatus = TodoStatus.pending,
    due_date: datetime | None = None,
) -> Todo:
    """
    Helper para crear instancias de Todo sin pegarle a la DB.
    SQLAlchemy permite instanciar el modelo directamente.
    """
    return Todo(
        title=title,
        description=description,
        priority=priority,
        status=status,
        due_date=due_date,
    )


@pytest.mark.parametrize(
    "title,expected",
    [
        ("", "short"),
        ("abcd", "short"),
        ("abcdefghij", "short"),  # 10
        ("abcdefghijk", "medium"),  # 11
        ("a" * 25, "medium"),
        ("a" * 26, "long"),
        ("   con espacios   ", "short"),
    ],
)
def test_classify_title_length(title: str, expected: str) -> None:
    assert classify_title_length(title) == expected


def test_compute_advanced_stats_empty_list() -> None:
    stats = compute_advanced_stats([])
    assert stats["total"] == 0
    assert stats["pending"] == 0
    assert stats["in_progress"] == 0
    assert stats["done"] == 0
    assert stats["with_description"] == 0
    assert stats["without_description"] == 0
    assert stats["title_short"] == 0
    assert stats["title_medium"] == 0
    assert stats["title_long"] == 0
    assert stats["high_priority"] == 0
    assert stats["overdue"] == 0


def test_compute_advanced_stats_basic_counts() -> None:
    todos = [
        make_todo(title="A", status=TodoStatus.pending),
        make_todo(title="B", status=TodoStatus.in_progress),
        make_todo(title="C", status=TodoStatus.done),
    ]
    stats = compute_advanced_stats(todos)

    assert stats["total"] == 3
    assert stats["pending"] == 1
    assert stats["in_progress"] == 1
    assert stats["done"] == 1


def test_compute_advanced_stats_description_counts() -> None:
    todos = [
        make_todo(title="A", description=None),
        make_todo(title="B", description=" "),
        make_todo(title="C", description="algo"),
    ]
    stats = compute_advanced_stats(todos)

    # Solo el último tiene descripción "real"
    assert stats["with_description"] == 1
    assert stats["without_description"] == 2


def test_compute_advanced_stats_title_lengths() -> None:
    todos = [
        make_todo(title="short"),
        make_todo(title="a" * 15),
        make_todo(title="a" * 30),
    ]
    stats = compute_advanced_stats(todos)

    assert stats["title_short"] == 1
    assert stats["title_medium"] == 1
    assert stats["title_long"] == 1


def test_compute_advanced_stats_high_priority() -> None:
    todos = [
        make_todo(title="A", priority=TodoPriority.low),
        make_todo(title="B", priority=TodoPriority.medium),
        make_todo(title="C", priority=TodoPriority.high),
        make_todo(title="D", priority=TodoPriority.high),
    ]
    stats = compute_advanced_stats(todos)

    assert stats["high_priority"] == 2


def test_compute_advanced_stats_overdue_ignores_done() -> None:
    now = datetime.now(timezone.utc)
    past = now - timedelta(days=1)
    future = now + timedelta(days=1)

    todos = [
        # overdue (pending + past)
        make_todo(
            title="overdue1",
            status=TodoStatus.pending,
            due_date=past,
        ),
        # overdue (in_progress + past)
        make_todo(
            title="overdue2",
            status=TodoStatus.in_progress,
            due_date=past,
        ),
        # NO overdue porque está done
        make_todo(
            title="done_past",
            status=TodoStatus.done,
            due_date=past,
        ),
        # NO overdue por ser futuro
        make_todo(
            title="future",
            status=TodoStatus.pending,
            due_date=future,
        ),
        # NO overdue porque no tiene due_date
        make_todo(
            title="noduedate",
            status=TodoStatus.pending,
            due_date=None,
        ),
    ]

    stats = compute_advanced_stats(todos)

    assert stats["overdue"] == 2


def test_compute_advanced_stats_mixed_everything() -> None:
    """Smoke test más grande que mezcla todos los contadores."""
    now = datetime.now(timezone.utc)
    past = now - timedelta(days=2)

    todos = [
        make_todo(
            title="short 1",
            description="desc",
            priority=TodoPriority.high,
            status=TodoStatus.pending,
            due_date=past,
        ),
        make_todo(
            title="short 2",
            description=None,
            priority=TodoPriority.low,
            status=TodoStatus.in_progress,
            due_date=past,
        ),
        make_todo(
            title="medium title 123",
            description="algo",
            priority=TodoPriority.medium,
            status=TodoStatus.done,
            due_date=past,
        ),
        make_todo(
            title="this is a very very long title for a todo",
            description=None,
            priority=TodoPriority.high,
            status=TodoStatus.pending,
            due_date=None,
        ),
    ]

    stats = compute_advanced_stats(todos)

    assert stats["total"] == 4
    assert stats["pending"] == 2
    assert stats["in_progress"] == 1
    assert stats["done"] == 1

    assert stats["with_description"] == 2
    assert stats["without_description"] == 2

    assert stats["title_short"] == 2
    assert stats["title_medium"] == 1
    assert stats["title_long"] == 1

    assert stats["high_priority"] == 2
    # overdue: los dos primeros (no done y due_date pasada)
    assert stats["overdue"] == 2
