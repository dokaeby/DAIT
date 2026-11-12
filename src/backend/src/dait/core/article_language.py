"""언어 메타데이터가 없는 기존 기사의 번역 노출 정책."""

from src.backend.app.core.taxonomy import DOMESTIC_SOURCE_NAMES, GLOBAL_SOURCE_NAMES


def needs_translation(language: str, source_name: str) -> bool:
    """국내 한국어는 제외하며 기존 해외 출처 결과만 제한적으로 복원한다."""
    primary = language.lower().split("-")[0]
    if primary == "ko":
        return False
    if primary == "und":
        return source_name in GLOBAL_SOURCE_NAMES
    return source_name not in DOMESTIC_SOURCE_NAMES
