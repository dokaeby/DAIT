"""국내 한국어와 해외 외국어 번역 노출 조건."""

import pytest

from dait.core.article_language import needs_translation


@pytest.mark.parametrize(
    ("language", "source", "expected"),
    [
        ("ko", "전자신문", False),
        ("ko-KR", "TechCrunch", False),
        ("und", "전자신문", False),
        ("und", "TechCrunch", True),
        ("en", "TechCrunch", True),
        ("en", "전자신문", False),
        ("und", "미확인 출처", False),
    ],
)
def test_translation_policy(language: str, source: str, expected: bool) -> None:
    """한국어 번역은 생략하고 언어가 불명확한 신규 출처는 추측하지 않는다."""
    assert needs_translation(language, source) is expected
