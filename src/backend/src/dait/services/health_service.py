"""서비스 준비 상태를 판단한다. HTTP 응답 형식은 api 계층이 맡는다."""

import logging
import sqlite3

from dait.core.errors import NotReadyError
from dait.repositories.db import ping

logger = logging.getLogger(__name__)


def ensure_database_ready(database_url: str) -> None:
    """DB가 응답하는지 확인하고 아니면 NotReadyError를 낸다.

    입력: database_url (sqlite:///경로 형식 문자열)
    출력: 없음(정상이면 그냥 반환)
    기능: 실패 원인(경로, 오류 문구)은 응답에 쓰지 않고 예외 클래스 이름만 WARNING 로그로 남긴다.
    """
    try:
        ping(database_url)
    except sqlite3.Error as exc:
        logger.warning("DB 준비 확인 실패: %s", type(exc).__name__)
        raise NotReadyError from exc
