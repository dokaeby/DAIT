"""Fake-only ranking tests: no database, network, LLM, clocks or random shuffles."""

import socket
from datetime import UTC, datetime, timedelta, timezone
from itertools import permutations
from uuid import UUID

import pytest
from pydantic import ValidationError
from src.backend.app.schemas.content import InsufficientContent, SuccessContent
from src.backend.app.services.ranking_service import (
    RankedNews,
    RankingCandidate,
    RankingRequest,
    RankingService,
)

TIME = datetime(2026, 11, 8, 3, tzinfo=UTC)
LINES = ("AI 뉴스가 발표됐다.", "새 모델을 소개했다.", "연구 결과를 공개했다.")


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def deny(*args: object, **kwargs: object) -> None:
        pytest.fail("Ranking unit tests must not access real network services")

    monkeypatch.setattr(socket, "getaddrinfo", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket.socket, "connect_ex", deny)


def candidate(
    identifier: int = 1,
    *,
    ready: bool = True,
    published_at: datetime = TIME,
    source_priority: int = 0,
) -> RankingCandidate:
    content = (
        SuccessContent(
            content_hash="a" * 64,
            summary_lines=LINES,
            translated_text="AI 뉴스와 새 모델의 연구 결과를 소개했다.",
        )
        if ready
        else InsufficientContent(content_hash="b" * 64)
    )
    return RankingCandidate(
        id=UUID(int=identifier),
        published_at=published_at,
        source_priority=source_priority,
        content=content,
    )


def ranked_ids(items: tuple[RankedNews, ...]) -> tuple[int, ...]:
    return tuple(item.news.id.int for item in items)


def test_ready_overrides_recency_source_priority_and_id() -> None:
    missing = candidate(1, ready=False, published_at=TIME + timedelta(days=100), source_priority=0)
    ready = candidate(20, published_at=TIME - timedelta(days=100), source_priority=100)
    result = RankingService.rank(RankingRequest(candidates=(missing, ready)))
    assert ranked_ids(result) == (20, 1)
    assert result[0].news.ready is True
    assert result[1].news.ready is False


def test_newer_publication_overrides_source_priority_and_id() -> None:
    older = candidate(1, source_priority=0)
    newer = candidate(20, published_at=TIME + timedelta(microseconds=1), source_priority=100)
    assert ranked_ids(RankingService.rank(RankingRequest(candidates=(older, newer)))) == (20, 1)


def test_source_priority_overrides_id_when_quality_and_time_tie() -> None:
    result = RankingService.rank(
        RankingRequest(
            candidates=(
                candidate(1, source_priority=10),
                candidate(20, source_priority=0),
            )
        )
    )
    assert ranked_ids(result) == (20, 1)


def test_uuid_breaks_complete_tie() -> None:
    result = RankingService.rank(
        RankingRequest(candidates=(candidate(20), candidate(2), candidate(1)))
    )
    assert ranked_ids(result) == (1, 2, 20)


def test_all_input_permutations_produce_identical_output() -> None:
    items = (
        candidate(1, ready=False, published_at=TIME + timedelta(days=1)),
        candidate(5, published_at=TIME + timedelta(microseconds=1), source_priority=10),
        candidate(4, source_priority=1),
        candidate(3),
        candidate(2),
    )
    expected = (5, 2, 3, 4, 1)
    baseline = RankingService.rank(RankingRequest(candidates=items))
    for arrangement in permutations(items):
        ranked = RankingService.rank(RankingRequest(candidates=arrangement))
        assert ranked_ids(ranked) == expected
        assert ranked == baseline


@pytest.mark.parametrize("limit", [5, 10])
def test_entire_batch_is_sorted_before_slicing(limit: int) -> None:
    # The best candidate is at the end of an input larger than either limit.
    items = tuple(
        candidate(index, published_at=TIME + timedelta(minutes=index)) for index in range(1, 16)
    )
    request = RankingRequest.model_validate_json(
        '{"candidates":['
        + ",".join(item.model_dump_json() for item in items)
        + '],"limit":'
        + str(limit)
        + "}"
    )
    result = RankingService.rank(request)
    assert len(result) == limit
    assert ranked_ids(result) == tuple(range(15, 15 - limit, -1))
    assert tuple(item.rank for item in result) == tuple(range(1, limit + 1))


@pytest.mark.parametrize("size", [0, 1, 4])
def test_short_input_is_returned_without_padding(size: int) -> None:
    items = tuple(candidate(index) for index in range(1, size + 1))
    result = RankingService.rank(RankingRequest(candidates=items, limit=10))
    assert len(result) == size
    assert ranked_ids(result) == tuple(range(1, size + 1))


def test_default_limit_is_five() -> None:
    items = tuple(candidate(index) for index in range(1, 13))
    assert len(RankingService.rank(RankingRequest(candidates=items))) == 5


@pytest.mark.parametrize(
    "json_value", ["true", "false", "5.0", '"5"', "null", "0", "6", "11", "-5"]
)
def test_invalid_display_limits_are_rejected(json_value: str) -> None:
    with pytest.raises(ValidationError):
        RankingRequest.model_validate_json('{"candidates":[],"limit":' + json_value + "}")


@pytest.mark.parametrize("json_value", ["true", "false", "1.5", "1.0", '"1"', "-1", "null"])
def test_source_priority_requires_nonnegative_strict_integer(json_value: str) -> None:
    serialized = (
        candidate()
        .model_dump_json()
        .replace('"source_priority":0', '"source_priority":' + json_value)
    )
    with pytest.raises(ValidationError):
        RankingCandidate.model_validate_json(serialized)


def test_missing_source_priority_is_rejected() -> None:
    serialized = candidate().model_dump_json().replace('"source_priority":0,', "")
    with pytest.raises(ValidationError):
        RankingCandidate.model_validate_json(serialized)


def test_naive_datetime_is_rejected() -> None:
    naive = TIME.replace(tzinfo=None)
    with pytest.raises(ValidationError):
        candidate(published_at=naive)


def test_equal_instants_in_different_timezones_use_id_tie_break() -> None:
    local = TIME.astimezone(timezone(timedelta(hours=9)))
    result = RankingService.rank(
        RankingRequest(
            candidates=(
                candidate(20, published_at=local),
                candidate(1, published_at=TIME),
            )
        )
    )
    assert ranked_ids(result) == (1, 20)
    assert all(item.news.published_at.tzinfo is UTC for item in result)


def test_extreme_dates_preserve_microsecond_precision() -> None:
    distant = datetime(9999, 1, 1, tzinfo=UTC)
    result = RankingService.rank(
        RankingRequest(
            candidates=(
                candidate(1, published_at=distant),
                candidate(20, published_at=distant + timedelta(microseconds=1)),
                candidate(2, published_at=datetime(1, 1, 1, tzinfo=UTC)),
            )
        )
    )
    assert ranked_ids(result) == (20, 1, 2)


def test_duplicate_id_is_rejected_even_with_different_content() -> None:
    with pytest.raises(ValidationError, match="unique IDs"):
        RankingRequest(candidates=(candidate(1), candidate(1, ready=False)))


def test_uuid_text_is_normalized_and_equivalent_ids_are_duplicates() -> None:
    uuid = UUID("abcdef00-0000-0000-0000-000000000001")
    serialized = candidate().model_dump_json().replace(str(UUID(int=1)), str(uuid).upper())
    parsed = RankingCandidate.model_validate_json(serialized)
    assert str(parsed.id) == str(uuid)
    with pytest.raises(ValidationError, match="unique IDs"):
        RankingRequest(
            candidates=(
                parsed,
                RankingCandidate.model_validate_json(
                    serialized.replace(str(uuid).upper(), str(uuid))
                ),
            )
        )


def test_invalid_uuid_category_and_extra_ready_flag_are_rejected() -> None:
    original = candidate().model_dump_json()
    for payload in (
        original.replace(str(UUID(int=1)), "not-a-uuid"),
        original.replace('"category":"AI"', '"category":"OTHER"'),
        original[:-1] + ',"ready":true}',
    ):
        with pytest.raises(ValidationError):
            RankingCandidate.model_validate_json(payload)


def test_forged_success_cannot_be_used_as_ready() -> None:
    forged = SuccessContent.model_construct(
        content_hash="a" * 64, summary_lines=("One.",), translated_text="translation"
    )
    with pytest.raises(ValidationError):
        RankingCandidate(id=UUID(int=1), published_at=TIME, source_priority=0, content=forged)


def test_constructed_request_is_revalidated_at_service_boundary() -> None:
    first = candidate()
    forged = RankingRequest.model_construct(candidates=(first, first), limit=5)
    with pytest.raises(ValidationError, match="unique IDs"):
        RankingService.rank(forged)
    invalid_candidate = RankingCandidate.model_construct(
        id=UUID(int=2), published_at=TIME, source_priority=-1, content=first.content
    )
    invalid_request = RankingRequest.model_construct(candidates=(invalid_candidate,), limit=5)
    with pytest.raises(ValidationError):
        RankingService.rank(invalid_request)


def test_input_is_not_mutated_and_output_is_immutable() -> None:
    items = (candidate(20), candidate(1), candidate(2, ready=False))
    request = RankingRequest(candidates=items)
    before = request.model_dump_json()
    result = RankingService.rank(request)
    assert request.model_dump_json() == before
    assert tuple(item.id.int for item in items) == (20, 1, 2)
    assert isinstance(result, tuple)
    with pytest.raises(ValidationError):
        result[0].rank = 10
    with pytest.raises(ValidationError):
        result[0].news.source_priority = 20


def test_ranking_key_exposes_only_supplied_facts() -> None:
    item = candidate(20, source_priority=7)
    assert item.ranking_key == (True, TIME, 7, str(UUID(int=20)))
    assert not hasattr(item, "views")
    assert not hasattr(item, "comments")
    assert not hasattr(item, "growth_rate")
    assert not hasattr(item, "score")


def test_rank_does_not_depend_on_wall_clock_or_randomness(caplog: pytest.LogCaptureFixture) -> None:
    request = RankingRequest(candidates=(candidate(20), candidate(1)))
    baseline = RankingService.rank(request)
    assert all(RankingService.rank(request) == baseline for _ in range(10))
    assert caplog.text == ""
