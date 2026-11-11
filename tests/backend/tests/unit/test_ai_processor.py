"""ai_processor 단위 테스트.

외부 Grok 네트워크 호출 없이 Fake 클라이언트와 httpx.MockTransport로 검증한다.
"""

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from dait.core.config import Settings
from dait.workers.ai_processor import (
    PROMPT_VERSION,
    AIProcessor,
    ArticleContent,
    ContentStatus,
    GrokClient,
    GrokSummaryCompletion,
    ProcessedContent,
    ProcessingError,
)
from pydantic import SecretStr, ValidationError

DOMESTIC_BODY = (
    "국내 증시가 외국인 매수세에 힘입어 강세를 보였다. "
    "코스피는 전 거래일 대비 1.8% 상승한 2,640을 기록했다. "
    "분석가들은 반도체 업황 개선과 환율 안정이 상승을 이끌었다고 분석했다. "
    "다만 단기 차익 실현 물량이 늘어나면서 변동성은 커질 수 있다는 전망도 나온다."
)
FOREIGN_BODY = (
    "Global chip demand pushed semiconductor stocks higher on Tuesday. "
    "Analysts said orders from AI data centers drove the rally. "
    "The trend is expected to continue through next quarter."
)
VALID_LINES = ["핵심 결론 한 문장.", "배경과 원인 한 문장.", "전망과 영향 한 문장."]


def _settings(*, api_key: str = "test-xai-key", groq_key: str = "") -> Settings:
    return Settings(
        xai_api_key=SecretStr(api_key),
        groq_api_key=SecretStr(groq_key),
        grok_model="grok-test",
    )


def _domestic_article() -> ArticleContent:
    return ArticleContent(title="국내 증시 강세", body_text=DOMESTIC_BODY)


def _foreign_article() -> ArticleContent:
    return ArticleContent(
        title="Chip stocks rally on AI demand", body_text=FOREIGN_BODY, is_foreign=True
    )


class FakeGrokClient:
    """네트워크 없이 호출을 기록하고 설정된 결과/예외를 반환하는 Fake."""

    def __init__(self, result: str | Exception | list[str | Exception]) -> None:
        self._queue = (
            list(result) if isinstance(result, list) else [result]
        )
        self.calls: list[dict[str, str]] = []

    async def complete(self, *, system_instruction: str, user_prompt: str) -> str:
        self.calls.append({"system": system_instruction, "user": user_prompt})
        result = self._queue.pop(0) if len(self._queue) > 1 else self._queue[0]
        if isinstance(result, Exception):
            raise result
        return result


def _completion_payload(**overrides: Any) -> str:
    payload: dict[str, Any] = {"summary_lines": list(VALID_LINES)}
    payload.update(overrides)
    return json.dumps(payload, ensure_ascii=False)


def test_domestic_article_returns_three_summary_lines() -> None:
    client = FakeGrokClient(_completion_payload())
    processor = AIProcessor(_settings(), client=client)

    result = asyncio.run(processor.process(_domestic_article()))

    assert result.status is ContentStatus.READY
    assert result.engine == "grok"
    assert result.summary_lines == tuple(VALID_LINES)
    assert result.translated_title is None
    assert result.model_id == "grok-test"
    assert result.prompt_version == PROMPT_VERSION
    assert len(result.content_hash) == 64
    assert len(client.calls) == 1
    assert "3문장" in client.calls[0]["user"]
    assert "기사 제목: 국내 증시 강세" in client.calls[0]["user"]


def test_foreign_article_translates_title_and_summarizes() -> None:
    client = FakeGrokClient(
        _completion_payload(translated_title="AI 수요에 반도체 주가 급등")
    )
    processor = AIProcessor(_settings(), client=client)

    result = asyncio.run(processor.process(_foreign_article()))

    assert result.status is ContentStatus.READY
    assert result.engine == "grok"
    assert result.translated_title == "AI 수요에 반도체 주가 급등"
    assert len(result.summary_lines) == 3
    assert "번역" in client.calls[0]["user"]


def test_insufficient_body_returns_insufficient_without_llm_call() -> None:
    client = FakeGrokClient(_completion_payload())
    processor = AIProcessor(_settings(), client=client)
    article = ArticleContent(title="짧은 기사", body_text="본문이 짧습니다.")

    result = asyncio.run(processor.process(article))

    assert result.status is ContentStatus.INSUFFICIENT
    assert result.summary_lines == ()
    assert result.engine == "none"
    assert client.calls == []


def test_cache_hit_makes_zero_api_calls() -> None:
    client = FakeGrokClient(_completion_payload())
    processor = AIProcessor(_settings(), client=client)
    article = _domestic_article()

    first = asyncio.run(processor.process(article))
    second = asyncio.run(processor.process(article))

    assert first.cached is False
    assert second.cached is True
    assert second == first.model_copy(update={"cached": True})
    assert len(client.calls) == 1


def test_different_content_hash_bypasses_cache() -> None:
    client = FakeGrokClient(_completion_payload())
    processor = AIProcessor(_settings(), client=client)

    asyncio.run(processor.process(_domestic_article()))
    other = ArticleContent(title="다른 기사", body_text=DOMESTIC_BODY + " 추가 문장.")
    asyncio.run(processor.process(other))

    assert len(client.calls) == 2


def test_missing_api_key_uses_regex_fallback() -> None:
    processor = AIProcessor(_settings(api_key=""))

    result = asyncio.run(processor.process(_domestic_article()))

    assert result.status is ContentStatus.READY
    assert result.engine == "regex-fallback"
    assert len(result.summary_lines) == 3
    assert all(line for line in result.summary_lines)


def test_api_error_falls_back_to_regex_summary() -> None:
    client = FakeGrokClient(httpx.ConnectError("network down"))
    processor = AIProcessor(_settings(), client=client)

    result = asyncio.run(processor.process(_domestic_article()))

    assert result.status is ContentStatus.READY
    assert result.engine == "regex-fallback"
    assert len(result.summary_lines) == 3


def test_malformed_json_falls_back() -> None:
    client = FakeGrokClient("여기는 JSON이 아닙니다")
    processor = AIProcessor(_settings(), client=client)

    result = asyncio.run(processor.process(_domestic_article()))

    assert result.engine == "regex-fallback"


def test_wrong_summary_line_count_falls_back() -> None:
    client = FakeGrokClient(_completion_payload(summary_lines=["하나", "둘"]))
    processor = AIProcessor(_settings(), client=client)

    result = asyncio.run(processor.process(_domestic_article()))

    assert result.engine == "regex-fallback"


def test_extra_field_in_completion_falls_back() -> None:
    client = FakeGrokClient(_completion_payload(unexpected_field="x"))
    processor = AIProcessor(_settings(), client=client)

    result = asyncio.run(processor.process(_domestic_article()))

    assert result.engine == "regex-fallback"


def test_regex_fallback_always_returns_three_lines() -> None:
    processor = AIProcessor(_settings(api_key=""), client=FakeGrokClient(""))
    article = ArticleContent(title="t", body_text="가" * 100)

    result = asyncio.run(processor.process(article))

    assert len(result.summary_lines) == 3


def test_completion_schema_rejects_empty_line() -> None:
    with pytest.raises(ValidationError):
        GrokSummaryCompletion.model_validate(
            {"summary_lines": ["가", "", "다"], "translated_title": None}
        )


def test_processed_content_is_immutable() -> None:
    content = ProcessedContent(
        status=ContentStatus.READY,
        summary_lines=("a", "b", "c"),
        content_hash="0" * 64,
        model_id="m",
    )
    with pytest.raises(ValidationError):
        content.status = ContentStatus.INSUFFICIENT  # type: ignore[misc]


def test_grok_enabled_reflects_api_key_presence() -> None:
    assert _settings(api_key="real-key").grok_enabled is True
    assert _settings(api_key="").grok_enabled is False
    assert _settings(api_key="   ").grok_enabled is False


def test_whitespace_api_key_uses_regex_fallback() -> None:
    processor = AIProcessor(_settings(api_key="   "))

    result = asyncio.run(processor.process(_domestic_article()))

    assert result.engine == "regex-fallback"


def test_settings_keeps_secret_out_of_repr() -> None:
    settings = _settings(api_key="super-secret-value")

    assert "super-secret-value" not in repr(settings)
    assert settings.xai_api_key.get_secret_value() == "super-secret-value"
    assert settings.grok_model == "grok-test"


def test_httpx_client_sends_openai_compatible_request() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers.get("authorization")
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": _completion_payload()}}
                ]
            },
        )

    async def run() -> str:
        client = GrokClient.from_settings(
            _settings(), transport=httpx.MockTransport(handler)
        )
        assert client is not None
        try:
            return await client.complete(system_instruction="sys", user_prompt="usr")
        finally:
            await client.aclose()

    content = asyncio.run(run())

    assert json.loads(content)["summary_lines"] == VALID_LINES
    assert captured["url"] == "https://api.x.ai/v1/chat/completions"
    assert captured["authorization"] == "Bearer test-xai-key"
    payload = captured["payload"]
    assert payload["model"] == "grok-test"
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["messages"][0] == {"role": "system", "content": "sys"}
    assert payload["messages"][1] == {"role": "user", "content": "usr"}


def test_grok_client_from_settings_returns_none_without_api_key() -> None:
    assert GrokClient.from_settings(_settings(api_key="")) is None
    assert GrokClient.from_settings(_settings(api_key="   ")) is None


def test_grok_client_from_settings_returns_client_with_api_key() -> None:
    client = GrokClient.from_settings(_settings())

    assert isinstance(client, GrokClient)


def test_grok_disabled_without_api_key_falls_back() -> None:
    processor = AIProcessor(_settings(api_key=""))

    result = asyncio.run(processor.process(_domestic_article()))

    assert result.status is ContentStatus.READY
    assert result.engine == "regex-fallback"
    assert len(result.summary_lines) == 3


def test_httpx_client_raises_processing_error_on_bad_payload() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": True})

    async def run() -> None:
        client = GrokClient.from_settings(
            _settings(), transport=httpx.MockTransport(handler)
        )
        assert client is not None
        try:
            await client.complete(system_instruction="s", user_prompt="u")
        finally:
            await client.aclose()

    with pytest.raises(ProcessingError):
        asyncio.run(run())


def _groq_settings() -> Settings:
    return Settings(
        groq_api_key=SecretStr("test-groq-key"),
        groq_model="gpt-oss-test",
    )


def test_groq_key_preferred_over_xai() -> None:
    client = GrokClient.from_settings(_groq_settings())

    assert client is not None
    assert client._model == "gpt-oss-test"
    assert client._base_url == "https://api.groq.com/openai/v1"


def test_groq_disabled_and_no_xai_returns_none() -> None:
    blank = Settings(xai_api_key=SecretStr(""), groq_api_key=SecretStr(""))
    assert GrokClient.from_settings(blank) is None


def test_grok_client_retries_on_429_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, json={"error": "rate limited"})
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": _completion_payload()}}
                ]
            },
        )

    async def run() -> str:
        client = GrokClient.from_settings(
            _settings(), transport=httpx.MockTransport(handler)
        )
        assert client is not None
        try:
            return await client.complete(system_instruction="s", user_prompt="u")
        finally:
            await client.aclose()

    with patch("dait.workers.ai_processor.asyncio.sleep", new=AsyncMock()):
        out = asyncio.run(run())

    assert calls["n"] == 2
    assert json.loads(out)["summary_lines"] == VALID_LINES


def test_batch_coalesces_calls_into_single_request() -> None:
    articles = [_domestic_article() for _ in range(3)]
    payload = {
        "results": [
            {"summary_lines": list(VALID_LINES), "translated_title": None}
            for _ in range(3)
        ]
    }
    client = FakeGrokClient(json.dumps(payload, ensure_ascii=False))
    processor = AIProcessor(_settings(), client=client, batch_size=4)

    async def run() -> list:
        return await asyncio.gather(
            *(processor.process(article) for article in articles)
        )

    results = asyncio.run(run())

    assert len(client.calls) == 1
    assert "results" in client.calls[0]["user"]
    assert all(r.engine == "grok" for r in results)
    stats = processor.stats_snapshot()
    assert stats["grok_calls"] == 1
    assert stats["grok_success"] == 3


def test_batch_result_count_mismatch_retries_individually() -> None:
    client = FakeGrokClient(
        [
            json.dumps({"results": []}, ensure_ascii=False),
            _completion_payload(),
            _completion_payload(),
        ]
    )
    processor = AIProcessor(_settings(), client=client, batch_size=4)

    async def run():
        return await asyncio.gather(
            processor.process(_domestic_article()),
            processor.process(_domestic_article()),
        )

    results = asyncio.run(run())

    assert len(client.calls) == 3
    assert all(r.engine == "grok" for r in results)
    stats = processor.stats_snapshot()
    assert stats["grok_calls"] == 3
    assert stats["grok_success"] == 2


def test_numeric_guard_rejects_invented_numbers() -> None:
    client = FakeGrokClient(
        _completion_payload(summary_lines=[
            "주가가 99% 급등했다.", "배경 설명.", "전망 설명.",
        ])
    )
    processor = AIProcessor(_settings(), client=client)

    result = asyncio.run(processor.process(_domestic_article()))

    assert result.engine == "regex-fallback"
    assert processor.stats_snapshot()["grok_fallback"] == 1


def test_batch_size_bounds_enforced() -> None:
    with pytest.raises(ValueError):
        AIProcessor(_settings(), client=FakeGrokClient("{}"), batch_size=9)
