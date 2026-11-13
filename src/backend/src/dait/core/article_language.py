"""언어 메타데이터가 없는 기존 기사의 번역 노출 정책."""

import re

# app/core/taxonomy.py의 OFFICIAL_MEDIA_SOURCES에서 오는 출처 분류를 dait 계층에 맞게 둔다.
# 파이프라인(app/)을 import하면 배포 경로에서 모듈을 찾지 못하므로 이름만 여기 둔다.
_HANGUL = re.compile(r"[가-힣]")
_LATIN = re.compile(r"[A-Za-z]")
_KANA = re.compile(r"[ぁ-んァ-ヶー]")
_IDEOGRAPH = re.compile(r"[一-鿿々]")
_DOMESTIC_SOURCE_NAMES = frozenset(
    {
        "AI타임스",
        "IT조선",
        "뉴시스",
        "디지털데일리",
        "디지털투데이",
        "매일경제",
        "바이라인네트워크",
        "블로터",
        "서울경제",
        "연합뉴스",
        "전자신문",
        "지디넷코리아",
        "테크M",
        "한국경제",
    }
)
_GLOBAL_SOURCE_NAMES = frozenset({"MIT Tech Review", "TechCrunch", "The Verge"})


def looks_foreign_text(text: str) -> bool:
    """Return True when Latin letters dominate the supplied article text."""
    hangul = len(_HANGUL.findall(text))
    latin = len(_LATIN.findall(text))
    return latin > 0 and (hangul == 0 or hangul * 4 < latin)


def is_korean_text(text: str) -> bool:
    """Return True only for Hangul-containing, non-Latin-dominant text."""
    return bool(_HANGUL.search(text)) and not looks_foreign_text(text)


def is_korean_or_english_text(text: str) -> bool:
    """한글 또는 영어(라틴 문자) 위주 문장인지 판별한다.

    일본어 가나·한자만 섞인 문장은 영어로 보지 않기 위해 라틴 문자가
    다른 표의 문자보다 충분히 많을 때만 영어로 인정한다.
    """
    if is_korean_text(text):
        return True
    latin = len(_LATIN.findall(text))
    if latin == 0:
        return False
    hangul = len(_HANGUL.findall(text))
    if hangul and hangul * 4 >= latin:
        return False
    other = len(_KANA.findall(text)) + len(_IDEOGRAPH.findall(text))
    return latin > other * 4


def allowed_summary_lines(lines: list[str]) -> list[str]:
    """공개 요약으로 쓸 수 있는 1~3줄 한국어/영어 문장만 남긴다."""
    cleaned = [line.strip() for line in lines if line.strip() and is_korean_or_english_text(line)]
    return cleaned[:3]


def needs_translation(language: str, source_name: str) -> bool:
    """국내 한국어는 제외하며 명시된 비한국어 원문은 출처와 무관하게 번역한다."""
    primary = language.lower().split("-")[0]
    if primary == "ko":
        return False
    if primary == "und":
        return source_name in _GLOBAL_SOURCE_NAMES
    return True
