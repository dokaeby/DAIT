"""서비스 준비 상태를 판단한다. HTTP 응답 형식은 api 계층이 맡는다."""

import logging

from dait.core.config import Settings
from dait.core.errors import NotReadyError
from dait.repositories import redis_repository
from dait.repositories.db import DB_ERRORS, ping

logger = logging.getLogger(__name__)


# 입력: DATABASE_URL 문자열.
# 출력: 반환값 없음.
# 동작: DB 질의가 실패하면 내부 원인을 숨긴 준비 실패 오류로 변환한다.
def ensure_database_ready(database_url: str) -> None:
    """DB가 응답하는지 확인하고 아니면 NotReadyError를 낸다.

    입력: database_url (sqlite:///경로 형식 문자열)
    출력: 없음(정상이면 그냥 반환)
    기능: 실패 원인(경로, 오류 문구)은 응답에 쓰지 않고 예외 클래스 이름만 WARNING 로그로 남긴다.
    """
    try:
        ping(database_url)
    except DB_ERRORS as exc:
        logger.warning("DB 준비 확인 실패: %s", type(exc).__name__)
        raise NotReadyError from exc


# 입력: 선택적 Redis URL이 포함된 앱 설정.
# 출력: 반환값 없음.
# 동작: Redis가 설정된 경우 연결을 확인하고 실패하면 준비 실패 오류를 낸다.
def ensure_redis_ready(settings: Settings) -> None:
    """Redis가 설정돼 있으면 연결을 확인하고, 아니면 NotReadyError를 낸다.

    입력: settings (앱 설정, redis_url 포함)
    출력: 없음(정상이면 그냥 반환)
    기능: redis_url이 없으면 메모리 fallback으로 동작하므로 준비로 본다(설계서 12.1절).
          설정됐는데 ping이 실패하면 준비 실패로 본다. 실패 원인은 로그에만 남긴다.
    """
    if not settings.redis_url:
        return
    if redis_repository.connect(settings.redis_url) is None:
        logger.warning("Redis 준비 확인 실패: 연결 불가")
        raise NotReadyError
