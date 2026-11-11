import io
import json
from unittest.mock import Mock

import pytest

from backend.pipelines import summary_generation as generation
from backend.services import foreign_content


# 기능: Ollama HTTP 호출을 대체할 모의 응답 설정 함수를 준비한다.
# 입력:
#   monkeypatch: 속성·환경을 임시 대체하는 pytest fixture.
# 출력: 모의 응답을 배치하는 arrange 함수.
@pytest.fixture
def llm(monkeypatch):
    # 기능: 지정 JSON과 추가 필드로 Ollama 응답을 대체한다.
    # 입력:
    #   data: 처리할 요청 또는 결과 데이터.
    #   extra: 모의 응답에 덧붙일 필드.
    # 출력: HTTP 호출 인자와 호출 횟수를 기록하는 Mock 객체.
    def arrange(data, **extra):
        envelope = dict(done=True, done_reason="stop", response=json.dumps(data), **extra)
        body = io.BytesIO(json.dumps(envelope).encode())
        mock = Mock(return_value=body)
        monkeypatch.setattr(generation.urllib.request, "urlopen", mock)
        return mock

    return arrange


# 기능: 잘못된 요약을 준비 완료로 처리하지 않는지 동작을 검증한다.
# 입력:
#   lines: 요약 문장 목록.
#   llm: 모의 LLM 응답을 설정하는 fixture.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-DETAIL-002", "UT-AI-005", "UT-AI-006")
@pytest.mark.parametrize(
    "lines",
    [
        ["a", "b"],
        ["a", "b", "c", "d"],
        ["a", "a", "b"],
        ["a", "b", ""],
        ["a\nb", "b", "c"],
    ],
)
def test_invalid_summary_not_ready(lines, llm):
    llm(dict(status="generated", lines=lines))
    with pytest.raises(ValueError):
        generation.generate(dict(title="기사", summary="설명"), "fake", 1)


# 기능: 잘못된 생성 JSON 거부 동작을 검증한다.
# 입력:
#   monkeypatch: 속성·환경을 임시 대체하는 pytest fixture.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-AI-004")
def test_malformed_json_fails(monkeypatch):
    monkeypatch.setattr(
        generation.urllib.request,
        "urlopen",
        lambda *a, **kw: io.BytesIO(b'{"done":true,"response":"broken"}'),
    )
    with pytest.raises(ValueError):
        generation.generate(dict(title="기사", summary="설명"), "fake", 1)


# 기능: 기사 필드만 LLM에 전달 동작을 검증한다.
# 입력:
#   llm: 모의 LLM 응답을 설정하는 fixture.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-AI-010")
def test_only_article_fields_sent_to_llm(llm):
    mock = llm(dict(status="generated", lines=["하나", "둘", "셋"]))
    result = generation.generate(
        dict(
            title="기사",
            summary="설명",
            email="private@example.com",
            token="private-token",
        ),
        "fake",
        1,
    )
    assert result == ("generated", ["하나", "둘", "셋"])
    body = mock.call_args.args[0].data.decode()
    assert "private@example.com" not in body and "private-token" not in body
    assert set(json.loads(json.loads(body)["prompt"])) == {"title", "rss_description"}


# 기능: 정보 부족 상태와 정상 세 문장 요약의 구분 동작을 검증한다.
# 입력:
#   llm: 모의 LLM 응답을 설정하는 fixture.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-DETAIL-009")
def test_insufficient_is_not_three_line_success(llm):
    llm(dict(status="insufficient", lines=[]))
    assert generation.generate(dict(title="기사", summary="짧음"), "fake", 1) == (
        "insufficient",
        [],
    )


# 기능: 해외 번역 결과 형식 동작을 검증한다.
# 입력: 없음.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-AI-001")
def test_foreign_result_contract():
    result = foreign_content.validate_result(
        dict(
            status="generated",
            title_ko="한국어 제목",
            lines=["첫 문장", "둘째 문장", "셋째 문장"],
        )
    )
    assert result == ("generated", "한국어 제목", ["첫 문장", "둘째 문장", "셋째 문장"])


# 기능: 숫자가 변경된 생성 결과의 준비 완료 방지 요구사항 동작을 검증한다.
# 입력:
#   llm: 모의 LLM 응답을 설정하는 fixture.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-AI-007")
@pytest.mark.spec_gap
def test_document_changed_number_must_not_be_ready(llm):
    llm(
        dict(
            status="generated",
            lines=["성능이 24% 개선됐다.", "새 모델이 나왔다.", "기업이 발표했다."],
        )
    )
    with pytest.raises(ValueError):
        generation.generate(dict(title="기업 발표", summary="성능이 42% 개선됐다."), "fake", 1)
