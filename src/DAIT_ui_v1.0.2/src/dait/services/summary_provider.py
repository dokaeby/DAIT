"""요약 엔진 연결부. 작업자·DB·화면과 생성 엔진의 호출 방식을 분리합니다."""
from collections.abc import Mapping
from typing import Literal, Protocol

from dait.core.config import SUMMARY_MODEL as MODEL
Status = Literal["generated", "insufficient"]
Article = Mapping[str, str]


class SummaryProvider(Protocol):
    # 기능: 공급자의 국내 기사 요약 계약에 따라 상태와 문장을 제공한다.
    # 입력:
    #   self: 현재 인스턴스.
    #   article (Article): 기사 ID·제목·RSS 설명 등의 필드를 담은 사전.
    #   model (str): 사용할 모델 이름.
    #   timeout (int): 생성 요청 제한 시간(초).
    # 출력: (상태, 요약 문장 목록) 튜플. 생성 실패 시 예외.
    def summarize(self, article: Article, model: str, timeout: int) -> tuple[Status, list[str]]: ...

    # 기능: 공급자의 해외 기사 번역 계약에 따라 제목과 요약을 제공한다.
    # 입력:
    #   self: 현재 인스턴스.
    #   article (Article): 기사 ID·제목·RSS 설명 등의 필드를 담은 사전.
    #   model (str): 사용할 모델 이름.
    #   timeout (int): 생성 요청 제한 시간(초).
    # 출력: (상태, 한국어 제목, 요약 문장 목록) 튜플. 생성 실패 시 예외.
    def translate(self, article: Article, model: str, timeout: int) -> tuple[Status, str, list[str]]: ...


class OllamaProvider:
    """기존 프롬프트·생성 옵션·응답 검증을 그대로 재사용합니다."""

    # 기능: 공급자의 국내 기사 요약 계약에 따라 상태와 문장을 제공한다.
    # 입력:
    #   self: 현재 인스턴스.
    #   article (Article): 기사 ID·제목·RSS 설명 등의 필드를 담은 사전.
    #   model (str): 사용할 모델 이름.
    #   timeout (int): 생성 요청 제한 시간(초).
    # 출력: (상태, 요약 문장 목록) 튜플. 생성 실패 시 예외.
    def summarize(self, article: Article, model: str, timeout: int) -> tuple[Status, list[str]]:
        from dait.pipelines.summary_generation import generate as ollama_generate
        return ollama_generate(article, model, timeout)

    # 기능: 공급자의 해외 기사 번역 계약에 따라 제목과 요약을 제공한다.
    # 입력:
    #   self: 현재 인스턴스.
    #   article (Article): 기사 ID·제목·RSS 설명 등의 필드를 담은 사전.
    #   model (str): 사용할 모델 이름.
    #   timeout (int): 생성 요청 제한 시간(초).
    # 출력: (상태, 한국어 제목, 요약 문장 목록) 튜플. 생성 실패 시 예외.
    def translate(self, article: Article, model: str, timeout: int) -> tuple[Status, str, list[str]]:
        from dait.pipelines.translate_foreign import generate_translation as ollama_translate
        return ollama_translate(article, model, timeout)


_provider: SummaryProvider = OllamaProvider()


# 기능: 현재 설정된 요약 공급자를 가져온다.
# 입력: 없음.
# 출력: SummaryProvider 구현 객체.
def get_provider() -> SummaryProvider:
    """외부 API 도입 시 동일한 인터페이스의 어댑터를 이 경계에서 선택합니다."""
    return _provider


# 기능: 현재 공급자에 국내 기사 요약 생성을 요청한다.
# 입력:
#   article (Article): 기사 ID·제목·RSS 설명 등의 필드를 담은 사전.
#   model (str): 사용할 모델 이름.
#   timeout (int): 생성 요청 제한 시간(초).
# 출력: (상태, 요약 문장 목록) 튜플. 생성 실패 시 예외.
def generate(article: Article, model: str, timeout: int) -> tuple[Status, list[str]]:
    # 연결/검증 오류는 작업자로 전달해 기존 실패 기록 및 재시도 정책을 적용합니다.
    return get_provider().summarize(article, model, timeout)


# 기능: 현재 공급자에 해외 기사 번역·요약 생성을 요청한다.
# 입력:
#   article (Article): 기사 ID·제목·RSS 설명 등의 필드를 담은 사전.
#   model (str): 사용할 모델 이름.
#   timeout (int): 생성 요청 제한 시간(초).
# 출력: (상태, 한국어 제목, 요약 문장 목록) 튜플. 생성 실패 시 예외.
def generate_translation(article: Article, model: str, timeout: int) -> tuple[Status, str, list[str]]:
    return get_provider().translate(article, model, timeout)
