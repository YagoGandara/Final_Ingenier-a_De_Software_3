import pytest

from app.logic import (
    normalize_title,
    is_empty_title,
    is_duplicate_title,
    validate_new_todo,
    compute_stats,
    filter_todos,
)


class Obj:
    """Objeto simple para usar en los tests en lugar del modelo real."""

    def __init__(self, title: str, done: bool = False, description: str | None = None):
        self.title = title
        self.done = done
        self.description = description


# --- Tests para normalize_title / is_empty_title ---


def test_normalize_title_trim_and_collapse_spaces():
    assert normalize_title("  hola   mundo   ") == "hola mundo"


def test_normalize_title_of_empty_string_is_empty():
    assert normalize_title("") == ""


def test_is_empty_title_true_for_whitespace_only():
    assert is_empty_title("   \t  \n  ") is True


def test_is_empty_title_false_for_non_empty():
    assert is_empty_title(" algo ") is False


# --- Tests para duplicados ---


def test_is_duplicate_title_false_when_list_empty():
    assert is_duplicate_title("Task", []) is False


def test_is_duplicate_title_true_case_insensitive_and_normalized():
    existing = [
        Obj("  Comprar   pan  "),
        Obj("Pagar servicios"),
    ]
    assert is_duplicate_title(" comprar pan", existing) is True
    assert is_duplicate_title("COMPRAR PAN", existing) is True


def test_is_duplicate_title_false_when_different_titles():
    existing = [Obj("A"), Obj("B")]
    assert is_duplicate_title("C", existing) is False


def test_validate_new_todo_raises_empty_for_whitespace():
    with pytest.raises(ValueError) as exc:
        validate_new_todo("   ", [])
    assert str(exc.value) == "empty"


def test_validate_new_todo_raises_duplicate_for_existing_title():
    existing = [Obj("Comprar pan")]
    with pytest.raises(ValueError) as exc:
        validate_new_todo("comprar   pan", existing)
    assert str(exc.value) == "duplicate"


def test_validate_new_todo_ok_for_new_title():
    existing = [Obj("Comprar pan")]
    # No debería levantar excepción
    validate_new_todo("Pagar luz", existing)


# --- Tests para compute_stats ---


def test_compute_stats_on_empty_list():
    stats = compute_stats([])
    assert stats == {"total": 0, "done": 0, "pending": 0}


def test_compute_stats_mixed_done_and_pending():
    todos = [
        Obj("A", done=False),
        Obj("B", done=True),
        Obj("C", done=True),
    ]
    stats = compute_stats(todos)
    assert stats["total"] == 3
    assert stats["done"] == 2
    assert stats["pending"] == 1


# --- Tests para filter_todos ---


def test_filter_todos_by_done_true():
    todos = [Obj("A", done=False), Obj("B", done=True)]
    result = filter_todos(todos, done=True)
    assert len(result) == 1
    assert result[0].title == "B"


def test_filter_todos_by_done_false():
    todos = [Obj("A", done=False), Obj("B", done=True)]
    result = filter_todos(todos, done=False)
    assert len(result) == 1
    assert result[0].title == "A"


def test_filter_todos_by_text_in_title():
    todos = [Obj("Comprar pan"), Obj("Pagar luz")]
    result = filter_todos(todos, text="pan")
    assert [t.title for t in result] == ["Comprar pan"]


def test_filter_todos_by_text_in_description():
    todos = [
        Obj("A", description="algo de pan"),
        Obj("B", description="otra cosa"),
    ]
    result = filter_todos(todos, text="pan")
    assert len(result) == 1
    assert result[0].title == "A"


def test_filter_todos_by_done_and_text_combined():
    todos = [
        Obj("A", done=False, description="algo de pan"),
        Obj("B", done=True, description="pan terminado"),
        Obj("C", done=True, description="otra cosa"),
    ]
    result = filter_todos(todos, done=True, text="pan")
    titles = {t.title for t in result}
    assert titles == {"B"}
