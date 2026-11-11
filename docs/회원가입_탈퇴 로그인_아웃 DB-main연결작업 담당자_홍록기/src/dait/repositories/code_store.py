"""2차 인증 코드 저장소. 인터페이스(CodeStore) 뒤에 두어 나중에 Redis(TTL) 구현으로 바꿀 수 있다."""

import sqlite3
from datetime import datetime
from typing import Protocol

from dait.repositories.db import transaction
from dait.schemas.two_factor import ChallengeRecord


class CodeStore(Protocol):
    """코드 저장소가 지켜야 할 동작. 서비스는 이 모양만 안다."""

    def replace_for_user(self, record: ChallengeRecord) -> None:
        """사용자의 기존 챌린지를 모두 지우고 새로 저장한다(사용자당 하나만 유효)."""
        ...

    def get(self, key: str) -> ChallengeRecord | None:
        """키로 챌린지를 찾는다. 없으면 None."""
        ...

    def add_attempt(self, key: str) -> int | None:
        """시도 횟수를 1 늘리고 늘어난 값을 돌려준다. 챌린지가 없으면 None."""
        ...

    def reissue(
        self,
        key: str,
        code_hash: str,
        expires_at: datetime,
        sent_at: datetime,
        sent_before: datetime,
        max_resends: int,
    ) -> bool:
        """쿨다운이 지났고 재발송 횟수가 남았을 때만 새 코드로 바꾼다. 바꿨으면 True."""
        ...

    def consume(self, key: str, code_hash: str) -> bool:
        """해시가 맞는 챌린지를 지운다. 이 호출에 성공한 쪽 하나만 True를 받는다."""
        ...

    def delete(self, key: str) -> None:
        """챌린지를 지운다. 없어도 오류가 아니다."""
        ...

    def delete_expired(self, now: datetime) -> int:
        """만료된 챌린지를 모두 지우고 지운 개수를 돌려준다."""
        ...


def _to_record(row: tuple[str, str, str, str, int, int, str, str]) -> ChallengeRecord:
    """DB 행을 챌린지 레코드로 바꾼다.

    입력: row (two_factor_challenges 컬럼 순서대로 읽은 행)
    출력: ChallengeRecord (검증된 모델)
    기능: 저장된 ISO 문자열을 UTC 시각으로 되돌린다.
    """
    return ChallengeRecord(
        key=row[0],
        user_id=row[1],
        code_hash=row[2],
        expires_at=datetime.fromisoformat(row[3]),
        attempts=row[4],
        resend_count=row[5],
        last_sent_at=datetime.fromisoformat(row[6]),
        created_at=datetime.fromisoformat(row[7]),
    )


class SqliteCodeStore:
    """sqlite(two_factor_challenges 테이블)에 코드 해시를 저장하는 CodeStore 구현."""

    def __init__(self, database_url: str) -> None:
        """저장소를 만든다.

        입력: database_url (sqlite:///경로 형식)
        출력: 없음
        기능: 연결은 호출마다 열고 닫아 스레드 사이에 연결을 공유하지 않는다.
        """
        self._url = database_url

    def replace_for_user(self, record: ChallengeRecord) -> None:
        """사용자의 기존 챌린지를 지우고 새 챌린지를 한 트랜잭션으로 저장한다.

        입력: record (저장할 챌린지)
        출력: 없음
        기능: 코드 재요청이 쌓이지 않게 사용자당 하나만 남긴다.
        """
        with transaction(self._url) as conn:
            conn.execute("DELETE FROM two_factor_challenges WHERE user_id = ?", (record.user_id,))
            conn.execute(
                "INSERT INTO two_factor_challenges (key, user_id, code_hash, expires_at, "
                "attempts, resend_count, last_sent_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record.key,
                    record.user_id,
                    record.code_hash,
                    record.expires_at.isoformat(),
                    record.attempts,
                    record.resend_count,
                    record.last_sent_at.isoformat(),
                    record.created_at.isoformat(),
                ),
            )

    def get(self, key: str) -> ChallengeRecord | None:
        """키로 챌린지를 찾는다.

        입력: key (challenge_id의 SHA-256)
        출력: ChallengeRecord 또는 None
        기능: 읽기만 한다.
        """
        with transaction(self._url) as conn:
            row = conn.execute(
                "SELECT key, user_id, code_hash, expires_at, attempts, resend_count, "
                "last_sent_at, created_at FROM two_factor_challenges WHERE key = ?",
                (key,),
            ).fetchone()
        return None if row is None else _to_record(row)

    def add_attempt(self, key: str) -> int | None:
        """시도 횟수를 1 늘리고 늘어난 값을 돌려준다.

        입력: key (챌린지 키)
        출력: int (늘어난 시도 횟수) 또는 None (챌린지 없음)
        기능: 읽고 쓰는 대신 한 UPDATE로 늘려, 동시에 들어온 요청도 서로 다른 번호를 받는다.
        """
        with transaction(self._url) as conn:
            updated = conn.execute(
                "UPDATE two_factor_challenges SET attempts = attempts + 1 WHERE key = ?", (key,)
            )
            if updated.rowcount != 1:
                return None
            return _read_attempts(conn, key)

    def reissue(
        self,
        key: str,
        code_hash: str,
        expires_at: datetime,
        sent_at: datetime,
        sent_before: datetime,
        max_resends: int,
    ) -> bool:
        """쿨다운이 지났고 재발송 횟수가 남았을 때만 새 코드로 바꾼다.

        입력: key, code_hash (새 코드의 해시), expires_at (새 만료), sent_at (지금),
              sent_before (이 시각 이전에 보냈어야 함 = 지금 - 쿨다운), max_resends (상한)
        출력: bool (바꿨으면 True)
        기능: 조건 검사와 갱신을 한 UPDATE로 해서 동시 재발송 요청 중 하나만 통과시킨다.
              새 코드는 시도 횟수를 0으로 되돌린다.
        """
        with transaction(self._url) as conn:
            updated = conn.execute(
                "UPDATE two_factor_challenges SET code_hash = ?, expires_at = ?, "
                "last_sent_at = ?, attempts = 0, resend_count = resend_count + 1 "
                "WHERE key = ? AND last_sent_at <= ? AND resend_count < ?",
                (
                    code_hash,
                    expires_at.isoformat(),
                    sent_at.isoformat(),
                    key,
                    sent_before.isoformat(),
                    max_resends,
                ),
            )
            return updated.rowcount == 1

    def consume(self, key: str, code_hash: str) -> bool:
        """해시가 맞는 챌린지를 지운다.

        입력: key (챌린지 키), code_hash (확인된 코드의 해시)
        출력: bool (이 호출이 지웠으면 True)
        기능: 같은 코드를 동시에 두 번 보내도 DELETE는 한 번만 성공한다.
        """
        with transaction(self._url) as conn:
            deleted = conn.execute(
                "DELETE FROM two_factor_challenges WHERE key = ? AND code_hash = ?",
                (key, code_hash),
            )
            return deleted.rowcount == 1

    def delete(self, key: str) -> None:
        """챌린지를 지운다.

        입력: key (챌린지 키)
        출력: 없음
        기능: 없는 키여도 오류 없이 끝난다.
        """
        with transaction(self._url) as conn:
            conn.execute("DELETE FROM two_factor_challenges WHERE key = ?", (key,))

    def delete_expired(self, now: datetime) -> int:
        """만료된 챌린지를 지운다.

        입력: now (UTC 시각)
        출력: int (지운 개수)
        기능: 시각을 ISO 문자열로 비교한다. 모두 UTC로 저장하므로 문자열 순서가 시간 순서다.
        """
        with transaction(self._url) as conn:
            deleted = conn.execute(
                "DELETE FROM two_factor_challenges WHERE expires_at <= ?", (now.isoformat(),)
            )
            return deleted.rowcount


def _read_attempts(conn: sqlite3.Connection, key: str) -> int | None:
    """같은 트랜잭션 안에서 시도 횟수를 읽는다.

    입력: conn (열려 있는 연결), key (챌린지 키)
    출력: int 또는 None
    기능: add_attempt가 늘린 값을 그대로 돌려주려고 쓴다.
    """
    row = conn.execute(
        "SELECT attempts FROM two_factor_challenges WHERE key = ?", (key,)
    ).fetchone()
    return None if row is None else int(row[0])
