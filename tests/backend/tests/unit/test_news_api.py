"""FR-HOME/SEARCH/DETAIL/SET 계약 HTTP 테스트. DB는 마이그레이션된 sqlite를 직접 채운다."""

import sqlite3
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import ClassVar

from dait.core.config import Settings
from dait.main import create_app
from support import HttpClient, as_client

PASSWORD = "Str0ng!Passw0rd-xyz"  # noqa: S105 - 테스트 전용 가짜 비밀번호
SIGNUP = {
    "email": "newsuser@example.com",
    "password": PASSWORD,
    "password_confirm": PASSWORD,
    "terms_accepted": True,
}
NOW = datetime(2026, 1, 1, tzinfo=UTC).isoformat()
SUMMARY_JSON = '["핵심 요약 한 줄", "둘째 줄", "셋째 줄"]'


def client_for(settings: Settings) -> HttpClient:
    """테스트 DB를 쓰는 앱의 클라이언트를 만든다."""
    return as_client(create_app(settings))


def bearer(token: str) -> Mapping[str, str]:
    """Authorization 헤더 값을 만든다."""
    return {"Authorization": f"Bearer {token}"}


def sign_up(client: HttpClient) -> str:
    """가입시키고 access token을 돌려준다."""
    response = client.request("POST", "/v1/auth/signup", json=SIGNUP)
    assert response.status_code == 201
    return str(response.json()["tokens"]["access_token"])


def _db_path(db_url: str) -> str:
    """sqlite:/// URL에서 파일 경로를 꺼낸다."""
    return db_url.removeprefix("sqlite:///")


def seed_news(db_url: str) -> None:
    """공개 가능한 출처·기사·요약 결과를 직접 넣는다."""
    conn = sqlite3.connect(_db_path(db_url))
    try:
        conn.execute(
            "INSERT INTO sources (id, name, kind, base_url, priority, enabled, "
            "created_at, updated_at) VALUES ('src1', '테스트통신', 'RSS', "
            "'https://example.com/feed', 10, 1, ?, ?)",
            (NOW, NOW),
        )
        for index in range(3):
            news_id = f"news{index:02d}"
            conn.execute(
                "INSERT INTO news (id, source_id, title, canonical_url, published_at, "
                "collected_at, category, original_language, created_at) "
                "VALUES (?, 'src1', ?, ?, ?, ?, 'AI', 'ko', ?)",
                (
                    news_id,
                    f"기사 {index} 제목",
                    f"https://example.com/a{index}",
                    f"2026-01-0{index + 1}T00:00:00+00:00",
                    NOW,
                    NOW,
                ),
            )
            conn.execute(
                "INSERT INTO content_results (news_id, extracted_text, "
                "translated_text, summary_lines, status, prompt_version, model_id, "
                "processed_at, updated_at) "
                "VALUES (?, '본문 텍스트', '번역 텍스트', ?, 'READY', 'pv1', 'm1', ?, ?)",
                (news_id, SUMMARY_JSON, NOW, NOW),
            )
        conn.execute(
            "INSERT INTO news (id, source_id, title, canonical_url, published_at, "
            "collected_at, category, original_language, created_at) "
            "VALUES ('news99', 'src1', '실패 기사', 'https://example.com/fail', ?, ?, "
            "'AI', 'ko', ?)",
            (NOW, NOW, NOW),
        )
        conn.execute(
            "INSERT INTO content_results (news_id, status, updated_at) "
            "VALUES ('news99', 'FAILED', ?)",
            (NOW,),
        )
        conn.commit()
    finally:
        conn.close()


class TestNewsList:
    """GET /v1/news 목록·검색·정렬."""

    def test_lists_only_ready_articles(self, settings: Settings, db_url: str) -> None:
        """FAILED 기사는 목록에 나오지 않고 READY만 순위와 함께 반환된다."""
        seed_news(db_url)
        client = client_for(settings)
        response = client.request("GET", "/v1/news", params={"category": "AI"})
        assert response.status_code == 200
        body = response.json()
        titles = [item["title"] for item in body["items"]]
        assert titles == ["기사 2 제목", "기사 1 제목", "기사 0 제목"]  # 최신 발행순
        assert "실패 기사" not in titles
        assert [item["rank"] for item in body["items"]] == [1, 2, 3]
        assert all(len(item["summary_lines"]) == 3 for item in body["items"])
        assert body["meta"]["total_visible"] == 3
        assert body["page"]["has_more"] is False

    def test_search_matches_summary_and_title(self, settings: Settings, db_url: str) -> None:
        """제목 또는 저장된 요약에 검색어가 있는 기사만 반환된다."""
        seed_news(db_url)
        client = client_for(settings)
        token = sign_up(client)
        headers = bearer(token)
        by_summary = client.request("GET", "/v1/news", params={"q": "핵심 요약"}, headers=headers)
        by_title = client.request("GET", "/v1/news", params={"q": "기사 1"}, headers=headers)
        none = client.request("GET", "/v1/news", params={"q": "없는검색어xyz"}, headers=headers)
        assert len(by_summary.json()["items"]) == 3
        assert len(by_title.json()["items"]) == 1
        assert none.json()["items"] == []
        assert none.json()["meta"]["total_visible"] == 0

    def test_query_over_100_chars_is_422(self, settings: Settings) -> None:
        """검색어는 100자까지 허용한다(계약 상한)."""
        client = client_for(settings)
        response = client.request("GET", "/v1/news", params={"q": "가" * 101})
        assert response.status_code == 422

    def test_inactive_category_is_422(self, settings: Settings) -> None:
        """활성 카테고리는 AI·ECONOMY·POLITICS이고 WEATHER는 비활성이다."""
        client = client_for(settings)
        for code in ("AI", "ECONOMY", "POLITICS"):
            assert client.request("GET", "/v1/news", params={"category": code}).status_code == 200
        assert client.request("GET", "/v1/news", params={"category": "WEATHER"}).status_code == 422

    def test_all_categories_guest_limit_and_member_filters(
        self, settings: Settings, db_url: str
    ) -> None:
        """Guests see the global latest ten; members can filter and paginate all categories."""
        seed_news(db_url)
        with sqlite3.connect(_db_path(db_url)) as conn:
            for index in range(15):
                category = ("AI", "ECONOMY", "POLITICS")[index % 3]
                news_id = f"mixed{index:02d}"
                published = f"2026-02-{index + 1:02d}T00:00:00+00:00"
                conn.execute(
                    "INSERT INTO news (id, source_id, title, canonical_url, published_at, "
                    "collected_at, category, original_language, created_at) "
                    "VALUES (?, 'src1', ?, ?, ?, ?, ?, 'ko', ?)",
                    (
                        news_id,
                        news_id,
                        f"https://example.com/{news_id}",
                        published,
                        NOW,
                        category,
                        NOW,
                    ),
                )
                conn.execute(
                    "INSERT INTO content_results (news_id, summary_lines, status, updated_at) "
                    "VALUES (?, ?, 'READY', ?)",
                    (news_id, SUMMARY_JSON, NOW),
                )
            conn.execute("UPDATE news SET category = 'WEATHER' WHERE id = 'news00'")
        client = client_for(settings)
        guest = client.request(
            "GET",
            "/v1/news",
            params={"category": "AI", "q": "no-match", "page_size": "50", "sort": "rank"},
        )
        assert guest.status_code == 200
        body = guest.json()
        assert [item["id"] for item in body["items"]] == [
            f"mixed{index:02d}" for index in range(14, 4, -1)
        ]
        assert body["page"] == {"has_more": False, "next_cursor": None}
        assert body["meta"]["total_visible"] == 10
        headers = bearer(sign_up(client))
        member = client.request("GET", "/v1/news", headers=headers, params={"sort": "latest"})
        assert member.status_code == 200
        assert member.json()["meta"]["total_visible"] == 17
        cursor = member.json()["page"]["next_cursor"]
        assert client.request("GET", "/v1/news", params={"cursor": cursor}).status_code == 422
        second = client.request(
            "GET", "/v1/news", headers=headers, params={"cursor": cursor, "sort": "latest"}
        )
        assert len(second.json()["items"]) == 7
        filtered = client.request(
            "GET", "/v1/news", headers=headers, params={"category": "ECONOMY"}
        )
        assert len(filtered.json()["items"]) == 5
        assert all(item["category"] == "ECONOMY" for item in filtered.json()["items"])
        for news_id in ("mixed01", "mixed02"):
            detail = client.request("GET", f"/v1/news/{news_id}")
            assert detail.status_code == 200
            assert detail.json()["article"]["id"] == news_id
        assert client.request("GET", "/v1/news/news00").status_code == 404


class TestNewsDetail:
    def test_counts_and_private_read_history(self, settings: Settings, db_url: str) -> None:
        """Counts are fresh; read receipts are idempotent and owned by the token."""
        seed_news(db_url)
        client = client_for(settings)
        assert client.request("GET", "/v1/news/activity").status_code == 401
        headers = bearer(sign_up(client))
        first = client.request("GET", "/v1/news/activity", headers=headers)
        assert first.status_code == 200
        assert first.json()["total"] == 3
        assert first.json()["counts"]["AI"] == 3
        assert first.json()["read_ids"] == []
        for _ in range(2):
            assert client.request("PUT", "/v1/news/news00/read", headers=headers).status_code == 204
        marked = client.request(
            "GET", "/v1/news/activity", headers=headers, params={"ids": "news00"}
        )
        assert marked.json()["read_ids"] == ["news00"]
        other = client.request(
            "POST", "/v1/auth/signup", json={**SIGNUP, "email": "other@example.com"}
        )
        other_headers = bearer(str(other.json()["tokens"]["access_token"]))
        private = client.request(
            "GET", "/v1/news/activity", headers=other_headers, params={"ids": "news00"}
        )
        assert private.json()["read_ids"] == []
        assert client.request("PUT", "/v1/news/news99/read", headers=headers).status_code == 404
        with sqlite3.connect(_db_path(db_url)) as conn:
            conn.execute("UPDATE content_results SET status = 'FAILED' WHERE news_id = 'news02'")
        assert client.request("GET", "/v1/news/activity", headers=headers).json()["total"] == 2

    """GET /v1/news/{id} 상세."""

    def test_detail_returns_full_contract(self, settings: Settings, db_url: str) -> None:
        """상세는 기사·콘텐츠·출처·관련 뉴스·처리 정보를 모두 담는다."""
        seed_news(db_url)
        client = client_for(settings)
        response = client.request("GET", "/v1/news/news00")
        assert response.status_code == 200
        body = response.json()
        assert body["article"]["title"] == "기사 0 제목"
        assert body["content"]["content_status"] == "READY"
        assert len(body["content"]["summary_lines"]) == 3
        assert body["source"]["original_url"] == "https://example.com/a0"
        assert body["processing"]["summary_status"] == "SUCCEEDED"
        assert isinstance(body["related_news"], list)

    def test_missing_or_failed_is_news_not_found(self, settings: Settings, db_url: str) -> None:
        """없는 ID와 FAILED 기사는 같은 404 NEWS_NOT_FOUND를 돌려준다."""
        seed_news(db_url)
        client = client_for(settings)
        for news_id in ("nope", "news99"):
            response = client.request("GET", f"/v1/news/{news_id}")
            assert response.status_code == 404
            assert response.json()["code"] == "NEWS_NOT_FOUND"


class TestSettings:
    """GET/PATCH /v1/me/settings."""

    def test_get_creates_default_then_patch_normalizes(self, settings: Settings) -> None:
        """첫 조회는 기본값을 만들고, PATCH는 정규화된 값을 저장·반환한다."""
        client = client_for(settings)
        token = sign_up(client)
        headers = bearer(token)
        first = client.request("GET", "/v1/me/settings", headers=headers)
        assert first.status_code == 200
        assert first.json()["default_count"] == 10
        patched = client.request(
            "PATCH",
            "/v1/me/settings",
            headers=headers,
            json={
                "default_count": 5,
                "keywords": ["  AI  ", "AI", "로봇"],
                "source_ids": [],
                "categories": ["AI"],
                "email_notice": True,
            },
        )
        assert patched.status_code == 200
        body = patched.json()
        assert body["default_count"] == 5
        assert body["keywords"] == ["AI", "로봇"]
        assert body["email_notice"] is True
        again = client.request("GET", "/v1/me/settings", headers=headers)
        assert again.json()["keywords"] == ["AI", "로봇"]

    def test_patch_rejects_invalid_values(self, settings: Settings, db_url: str) -> None:
        """default_count 7, 미승인 출처, 비활성 카테고리, 모르는 필드는 422."""
        seed_news(db_url)
        client = client_for(settings)
        token = sign_up(client)
        headers = bearer(token)
        bad = [
            {"default_count": 7},
            {"source_ids": ["not-approved"]},
            {"categories": ["ECON"]},
            {"unknown_field": 1},
        ]
        for body in bad:
            response = client.request("PATCH", "/v1/me/settings", headers=headers, json=body)
            assert response.status_code == 422, body
        ok = client.request(
            "PATCH",
            "/v1/me/settings",
            headers=headers,
            json={"source_ids": ["src1"], "categories": ["AI"]},
        )
        assert ok.status_code == 200
        assert ok.json()["source_ids"] == ["src1"]

    def test_settings_requires_auth(self, settings: Settings) -> None:
        """토큰 없이는 401."""
        client = client_for(settings)
        assert client.request("GET", "/v1/me/settings").status_code == 401
        assert client.request("PATCH", "/v1/me/settings", json={}).status_code == 401


SCHEDULE_CRITERIA: dict[str, object] = {
    "keywords": [" AI "],
    "source_ids": [],
    "categories": ["AI"],
}


class TestSchedules:
    """/v1/me/schedules CRUD와 소유권."""

    SCHEDULE: ClassVar[dict[str, object]] = {
        "local_time": "07:30",
        "timezone": "Asia/Seoul",
        "enabled": True,
        "criteria": SCHEDULE_CRITERIA,
    }

    def test_crud_and_next_run(self, settings: Settings) -> None:
        """생성→목록→수정→삭제가 되고 다음 실행 시각은 UTC로 저장된다."""
        client = client_for(settings)
        token = sign_up(client)
        headers = bearer(token)
        created = client.request("POST", "/v1/me/schedules", headers=headers, json=self.SCHEDULE)
        assert created.status_code == 201
        body = created.json()
        assert body["criteria"]["keywords"] == ["AI"]
        assert body["next_run_at"].endswith(("Z", "+00:00"))
        schedule_id = body["id"]

        listed = client.request("GET", "/v1/me/schedules", headers=headers)
        assert [item["id"] for item in listed.json()["items"]] == [schedule_id]

        patched = client.request(
            "PATCH",
            f"/v1/me/schedules/{schedule_id}",
            headers=headers,
            json={"enabled": False},
        )
        assert patched.status_code == 200
        assert patched.json()["enabled"] is False
        assert patched.json()["next_run_at"] is None

        deleted = client.request("DELETE", f"/v1/me/schedules/{schedule_id}", headers=headers)
        assert deleted.status_code == 204
        assert client.request("GET", "/v1/me/schedules", headers=headers).json()["items"] == []

    def test_other_users_schedule_is_404(self, settings: Settings) -> None:
        """다른 사용자의 예약 ID로는 수정·삭제가 404다(IDOR 방지)."""
        client = client_for(settings)
        owner = sign_up(client)
        other_body = dict(SIGNUP, email="other@example.com")
        intruder = client.request("POST", "/v1/auth/signup", json=other_body).json()["tokens"][
            "access_token"
        ]
        created = client.request(
            "POST", "/v1/me/schedules", headers=bearer(owner), json=self.SCHEDULE
        ).json()
        schedule_id = created["id"]
        for method in ("PATCH", "DELETE"):
            response = client.request(
                method,
                f"/v1/me/schedules/{schedule_id}",
                headers=bearer(intruder),
                json={"enabled": True} if method == "PATCH" else None,
            )
            assert response.status_code == 404, method
            assert response.json()["code"] == "SCHEDULE_NOT_FOUND"

    def test_invalid_timezone_and_sources_are_422(self, settings: Settings, db_url: str) -> None:
        """IANA가 아닌 시간대와 미승인 출처는 422."""
        seed_news(db_url)
        client = client_for(settings)
        token = sign_up(client)
        headers = bearer(token)
        bad_tz = dict(self.SCHEDULE, timezone="Mars/Olympus")
        bad_src = {
            **self.SCHEDULE,
            "criteria": {**SCHEDULE_CRITERIA, "source_ids": ["nope"]},
        }
        assert (
            client.request("POST", "/v1/me/schedules", headers=headers, json=bad_tz).status_code
            == 422
        )
        assert (
            client.request("POST", "/v1/me/schedules", headers=headers, json=bad_src).status_code
            == 422
        )
        assert (
            client.request(
                "POST",
                "/v1/me/schedules",
                headers=headers,
                json={"local_time": "25:00", "timezone": "UTC", "criteria": {}},
            ).status_code
            == 422
        )
