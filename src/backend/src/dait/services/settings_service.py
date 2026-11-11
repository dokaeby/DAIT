"""FR-SET-02/03 사용자 설정 조회·저장. 저장·정규화 결과를 그대로 응답한다."""

from datetime import UTC, datetime

from dait.core.config import Settings
from dait.core.errors import ValidationFailedError
from dait.repositories import news_repository, settings_repository
from dait.repositories.audit_repository import insert_audit
from dait.repositories.db import DbConnection, transaction
from dait.schemas.news import ACTIVE_CATEGORIES, NewsCategory
from dait.schemas.settings import (
    SettingsResponse,
    SettingsUpdateRequest,
    normalize_keywords,
)
from dait.schemas.user import UserRecord

_DEFAULT_COUNT = 10


def _parse_categories(raw: str) -> list[NewsCategory]:
    """저장된 카테고리 목록을 Enum으로 되돌린다.

    입력: raw (JSON TEXT)
    출력: NewsCategory 목록
    기능: 비활성·알 수 없는 값은 응답에서 제외해 계약을 지킨다.
    """
    result: list[NewsCategory] = []
    for item in settings_repository.loads_list(raw):
        try:
            category = NewsCategory(item)
        except ValueError:
            continue
        if category in ACTIVE_CATEGORIES and category not in result:
            result.append(category)
    return result


def _to_response(row: settings_repository.SettingsRow) -> SettingsResponse:
    """저장 행을 API 응답으로 변환한다.

    입력: row (user_settings 행)
    출력: SettingsResponse
    기능: DB 경계 값을 계약 모델이 요구하는 형태로만 변환한다.
    """
    return SettingsResponse(
        default_count=10 if row.default_count == 10 else 5,  # CHECK 제약상 5/10뿐
        keywords=settings_repository.loads_list(row.keywords),
        source_ids=settings_repository.loads_list(row.source_ids),
        categories=_parse_categories(row.categories),
        in_app_notice=row.in_app_notice,
        email_notice=row.email_notice,
        updated_at=row.updated_at,
    )


def _ensure_row(
    conn: DbConnection, user: UserRecord, now: datetime
) -> settings_repository.SettingsRow:
    """설정 행을 읽고 없으면 기본값으로 만든다.

    입력: conn (연결), user (본인), now (UTC 시각)
    출력: SettingsRow
    기능: 첫 조회에서도 같은 응답이 나오도록 기본값을 즉시 저장한다.
    """
    row = settings_repository.get_row(conn, user.id)
    if row is not None:
        return row
    row = settings_repository.SettingsRow(
        user_id=user.id,
        default_count=_DEFAULT_COUNT,
        categories=settings_repository.dumps_list([NewsCategory.AI.value]),
        keywords="[]",
        source_ids="[]",
        in_app_notice=True,
        email_notice=False,
        created_at=now,
        updated_at=now,
    )
    settings_repository.save_row(conn, row)
    return row


def get_settings(settings: Settings, user: UserRecord) -> SettingsResponse:
    """현재 사용자의 설정을 조회한다(없으면 기본값 생성).

    입력: settings (앱 설정), user (인증된 본인)
    출력: SettingsResponse
    기능: user_id는 토큰에서 온 본인 것만 사용한다(IDOR 방지).
    """
    with transaction(settings.database_url) as conn:
        row = _ensure_row(conn, user, datetime.now(UTC))
    return _to_response(row)


def _validate_source_ids(conn: DbConnection, source_ids: list[str]) -> list[str]:
    """출처 ID가 활성 승인 출처인지 확인한다.

    입력: conn (연결), source_ids (사용자가 고른 ID 목록)
    출력: 같은 목록(순서 유지, 중복 제거)
    기능: 중복은 제거하고, 승인되지 않은 ID가 하나라도 있으면 422.
    """
    deduped = list(dict.fromkeys(source_ids))
    allowed = set(news_repository.list_enabled_source_ids(conn))
    if any(source_id not in allowed for source_id in deduped):
        raise ValidationFailedError
    return deduped


def update_settings(
    settings: Settings,
    user: UserRecord,
    request: SettingsUpdateRequest,
    request_id: str | None,
    now: datetime,
) -> SettingsResponse:
    """설정을 부분 수정하고 정규화된 결과를 돌려준다.

    입력: settings, user (본인), request (보낸 필드만 변경),
          request_id (감사 추적용), now (UTC 시각)
    출력: SettingsResponse (실제 저장된 값)
    기능: 사용자·예약 생성과 같은 트랜잭션에서 감사 로그를 남긴다.
          검색어 원문 등 불필요한 개인정보는 기록하지 않는다.
    """
    try:
        keywords = normalize_keywords(request.keywords) if request.keywords is not None else None
    except ValueError as exc:
        raise ValidationFailedError from exc

    with transaction(settings.database_url) as conn:
        row = _ensure_row(conn, user, now)
        merged_keywords = (
            keywords if keywords is not None else settings_repository.loads_list(row.keywords)
        )
        merged_source_ids = (
            _validate_source_ids(conn, request.source_ids)
            if request.source_ids is not None
            else settings_repository.loads_list(row.source_ids)
        )
        merged_categories = (
            list(dict.fromkeys(c.value for c in request.categories))
            if request.categories is not None
            else [c.value for c in _parse_categories(row.categories)]
        )
        new_row = settings_repository.SettingsRow(
            user_id=user.id,
            default_count=(
                request.default_count if request.default_count is not None else row.default_count
            ),
            categories=settings_repository.dumps_list(merged_categories),
            keywords=settings_repository.dumps_list(merged_keywords),
            source_ids=settings_repository.dumps_list(merged_source_ids),
            in_app_notice=(
                request.in_app_notice if request.in_app_notice is not None else row.in_app_notice
            ),
            email_notice=(
                request.email_notice if request.email_notice is not None else row.email_notice
            ),
            created_at=row.created_at,
            updated_at=now,
        )
        settings_repository.save_row(conn, new_row)
        insert_audit(
            conn,
            user.id,
            "SETTINGS_UPDATED",
            "SETTINGS",
            user.id,
            request_id,
            now,
        )
    return _to_response(new_row)
