import io
import json
from unittest.mock import Mock

import pytest

from backend.pipelines import summary_generation as generation
from backend.services import foreign_content


@pytest.fixture
def llm(monkeypatch):
    def arrange(data, **extra):
        envelope = dict(done=True, done_reason="stop", response=json.dumps(data), **extra)
        body = io.BytesIO(json.dumps(envelope).encode())
        mock = Mock(return_value=body)
        monkeypatch.setattr(generation.urllib.request, "urlopen", mock)
        return mock

    return arrange


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


@pytest.mark.ut("UT-AI-004")
def test_malformed_json_fails(monkeypatch):
    monkeypatch.setattr(
        generation.urllib.request,
        "urlopen",
        lambda *a, **kw: io.BytesIO(b'{"done":true,"response":"broken"}'),
    )
    with pytest.raises(ValueError):
        generation.generate(dict(title="기사", summary="설명"), "fake", 1)


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


@pytest.mark.ut("UT-DETAIL-009")
def test_insufficient_is_not_three_line_success(llm):
    llm(dict(status="insufficient", lines=[]))
    assert generation.generate(dict(title="기사", summary="짧음"), "fake", 1) == (
        "insufficient",
        [],
    )


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
