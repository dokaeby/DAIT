"""요약 엔진 연결부. 작업자·DB·화면과 생성 엔진의 호출 방식을 분리합니다."""
from collections.abc import Mapping
from typing import Literal, Protocol

from dait.core.config import SUMMARY_MODEL as MODEL
Status = Literal["generated", "insufficient"]
Article = Mapping[str, str]


class SummaryProvider(Protocol):
    def summarize(self, article: Article, model: str, timeout: int) -> tuple[Status, list[str]]: ...

    def translate(self, article: Article, model: str, timeout: int) -> tuple[Status, str, list[str]]: ...


class OllamaProvider:
    """기존 프롬프트·생성 옵션·응답 검증을 그대로 재사용합니다."""

    def summarize(self, article: Article, model: str, timeout: int) -> tuple[Status, list[str]]:
        from dait.pipelines.summary_generation import generate as ollama_generate
        return ollama_generate(article, model, timeout)

    def translate(self, article: Article, model: str, timeout: int) -> tuple[Status, str, list[str]]:
        from dait.pipelines.translate_foreign import generate_translation as ollama_translate
        return ollama_translate(article, model, timeout)


_provider: SummaryProvider = OllamaProvider()


def get_provider() -> SummaryProvider:
    """외부 API 도입 시 동일한 인터페이스의 어댑터를 이 경계에서 선택합니다."""
    return _provider


def generate(article: Article, model: str, timeout: int) -> tuple[Status, list[str]]:
    # 연결/검증 오류는 작업자로 전달해 기존 실패 기록 및 재시도 정책을 적용합니다.
    return get_provider().summarize(article, model, timeout)


def generate_translation(article: Article, model: str, timeout: int) -> tuple[Status, str, list[str]]:
    return get_provider().translate(article, model, timeout)
