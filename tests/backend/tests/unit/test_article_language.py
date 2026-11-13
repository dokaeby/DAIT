"""국내 한국어와 해외 외국어 번역 노출 조건."""

import pytest

from dait.core.article_language import is_korean_text, looks_foreign_text, needs_translation


@pytest.mark.parametrize(
    ("language", "source", "expected"),
    [
        ("ko", "전자신문", False),
        ("ko-KR", "TechCrunch", False),
        ("und", "전자신문", False),
        ("und", "TechCrunch", True),
        ("en", "TechCrunch", True),
        ("en", "전자신문", True),
        ("und", "미확인 출처", False),
    ],
)
def test_translation_policy(language: str, source: str, expected: bool) -> None:
    """한국어 번역은 생략하고 언어가 불명확한 신규 출처는 추측하지 않는다."""
    assert needs_translation(language, source) is expected


def test_text_language_heuristics_reject_latin_dominant_text() -> None:
    """한글이 섞여 있어도 라틴이 지배적이면 외국어/비한국어로 본다."""
    assert looks_foreign_text("Global chip demand pushed stocks higher.") is True
    assert looks_foreign_text("한국어 요약입니다. AI") is False
    assert is_korean_text("한국어로 번역된 문장입니다.") is True
    assert is_korean_text("Chip stocks rallied on AI demand.") is False
    assert (
        is_korean_text(
            "한국어로 번역된 문장입니다. Chip stocks rallied on AI demand and analysts "
            "expect further gains for data center suppliers."
        )
        is False
    )
