"""Local title correction must use article evidence and preserve academic titles."""

import pytest
from src.backend.app.core.title_translation import contextualize_title, repair_contextual_title


@pytest.mark.parametrize(
    ("title", "context", "expected"),
    [
        (
            "After the midterms ||| 중간고사 이후",
            "이번 중간선거에서 민주당이 승리했다.",
            "After the midterms ||| 중간선거 이후",
        ),
        (
            "After the midterm elections ||| 중간 고사 이후",
            "",
            "After the midterm elections ||| 중간선거 이후",
        ),
        (
            "Studying for midterms ||| 중간고사 공부",
            "대학 학생들의 수학 시험 준비.",
            "Studying for midterms ||| 중간고사 공부",
        ),
        (
            "After the midterms ||| 중간고사 이후",
            "Unrelated subject matter.",
            "After the midterms ||| 중간고사 이후",
        ),
        ("After the midterms", "Democrats win Congress.", "After the midterms"),
    ],
)
def test_stored_title_repair(title: str, context: str, expected: str) -> None:
    assert repair_contextual_title(title, context) == expected


def test_context_after_first_thirty_five_words_is_used_locally() -> None:
    context = "background " * 60 + "Congress voted after the elections."
    assert contextualize_title("After the midterms", context) == "After the midterm elections"
