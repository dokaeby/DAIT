"""audit_logs 테이블 접근. 비밀번호·토큰·검색어 원문은 기록하지 않는다."""

import uuid
from datetime import datetime

from dait.repositories.db import DbConnection


def insert_audit(
    conn: DbConnection,
    actor_user_id: str | None,
    event: str,
    target_type: str,
    target_id: str | None,
    request_id: str | None,
    created_at: datetime,
) -> None:
    """감사 로그 한 줄을 남긴다.

    입력: conn (트랜잭션 연결), actor_user_id (수행자, 시스템 작업은 None),
          event (예: SETTINGS_UPDATED), target_type·target_id (대상),
          request_id (API 추적 ID), created_at (UTC 시각)
    출력: 없음
    기능: 호출하는 쪽의 트랜잭션 안에서 실행돼 업무 변경과 함께 커밋·롤백된다.
    """
    conn.execute(
        "INSERT INTO audit_logs (id, actor_user_id, event, target_type, target_id, "
        "request_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            uuid.uuid4().hex,
            actor_user_id,
            event,
            target_type,
            target_id,
            request_id,
            created_at.isoformat(),
        ),
    )
