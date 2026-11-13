"""언어 메타데이터가 없는 기존 기사의 번역 노출 정책."""

import re

# app/core/taxonomy.py의 OFFICIAL_MEDIA_SOURCES에서 오는 출처 분류를 dait 계층에 맞게 둔다.
# 파이프라인(app/)을 import하면 배포 경로에서 모듈을 찾지 못하므로 이름만 여기 둔다.
_HANGUL = re.compile(r"[가-힣]")
_LATIN = re.compile(r"[A-Za-z]")
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


def needs_translation(language: str, source_name: str) -> bool:
    """국내 한국어는 제외하며 명시된 비한국어 원문은 출처와 무관하게 번역한다."""
    primary = language.lower().split("-")[0]
    if primary == "ko":
        return False
    if primary == "und":
        return source_name in _GLOBAL_SOURCE_NAMES
    return True
