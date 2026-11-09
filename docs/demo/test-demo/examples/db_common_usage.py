"""공용 SQLite 연결 모듈을 사용하는 실행 가능한 예제."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

from app.database import DEMO_USER_ID, initialize_database
from app.db_common import connect


# 입력: 초기화된 SQLite DB 파일 경로.
# 출력: 반환값 없음. 조회한 사용자 정보를 표준 출력에 표시한다.
# 동작: 파라미터 바인딩으로 데모 사용자를 조회하고 sqlite3.Row의 이름 기반 접근을 검증한다.
def read_user(db_path: Path) -> None:
    with closing(connect(db_path)) as connection:
        row = connection.execute(
            "SELECT id, email, status FROM users WHERE id = ?",
            (DEMO_USER_ID,),
        ).fetchone()

    assert row is not None
    assert row["id"] == DEMO_USER_ID
    assert row["status"] == "ACTIVE"
    print("1. 단건 조회:", dict(row))


# 입력: 초기화된 SQLite DB 파일 경로.
# 출력: 반환값 없음. 최대 2개의 뉴스 정보를 표준 출력에 표시한다.
# 동작: 카테고리와 조회 개수를 SQL placeholder로 전달해 JOIN 목록 조회를 검증한다.
def list_news_with_parameters(db_path: Path) -> None:
    category = "AI"
    page_size = 2
    with closing(connect(db_path)) as connection:
        rows = connection.execute(
            """
            SELECT n.id, n.title, s.name AS source_name
            FROM news AS n
            JOIN sources AS s ON s.id = n.source_id
            WHERE n.category = ?
            ORDER BY n.published_at DESC, n.id
            LIMIT ?
            """,
            (category, page_size),
        ).fetchall()

    assert len(rows) == page_size
    print("2. 파라미터 목록 조회:", [dict(row) for row in rows])


# 입력: 초기화된 SQLite DB 파일 경로.
# 출력: 반환값 없음. CRUD 트랜잭션 완료 메시지를 표시한다.
# 동작: 임시 예약을 생성, 조회, 수정, 삭제하고 하나의 트랜잭션으로 commit한다.
def run_schedule_crud_transaction(db_path: Path) -> None:
    schedule_id = "sch_common_example"
    criteria = json.dumps(
        {"keywords": ["공용 DB"], "source_ids": ["src_openai"], "categories": ["AI"]},
        ensure_ascii=False,
    )
    now = "2026-11-06T12:00:00Z"

    with closing(connect(db_path)) as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO schedules
                    (id, user_id, local_time, timezone, enabled, criteria_json,
                     next_run_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    schedule_id,
                    DEMO_USER_ID,
                    "10:30",
                    "Asia/Seoul",
                    1,
                    criteria,
                    "2026-11-07T01:30:00Z",
                    now,
                    now,
                ),
            )
            created = connection.execute(
                "SELECT local_time, enabled FROM schedules WHERE id = ?",
                (schedule_id,),
            ).fetchone()
            assert created is not None and created["local_time"] == "10:30"

            connection.execute(
                "UPDATE schedules SET enabled = 0, updated_at = ? WHERE id = ?",
                (now, schedule_id),
            )
            updated = connection.execute(
                "SELECT enabled FROM schedules WHERE id = ?",
                (schedule_id,),
            ).fetchone()
            assert updated is not None and updated["enabled"] == 0

            deleted = connection.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
            assert deleted.rowcount == 1

    print("3. CRUD 트랜잭션: 생성, 조회, 수정, 삭제 후 commit")


# 입력: 초기화된 SQLite DB 파일 경로.
# 출력: 반환값 없음. 발생한 제약 오류와 rollback 결과를 표시한다.
# 동작: 허용값 변경 뒤 CHECK 제약을 위반해 트랜잭션 전체가 rollback되는지 검증한다.
def verify_constraint_rollback(db_path: Path) -> None:
    with closing(connect(db_path)) as connection:
        original = connection.execute(
            "SELECT default_count FROM user_settings WHERE user_id = ?",
            (DEMO_USER_ID,),
        ).fetchone()
        assert original is not None

        try:
            with connection:
                connection.execute(
                    "UPDATE user_settings SET default_count = 5 WHERE user_id = ?",
                    (DEMO_USER_ID,),
                )
                connection.execute(
                    "UPDATE user_settings SET default_count = 7 WHERE user_id = ?",
                    (DEMO_USER_ID,),
                )
        except sqlite3.IntegrityError as error:
            print("4. 제약 오류:", error)
        else:
            raise AssertionError("CHECK 제약 오류가 발생해야 합니다.")

        restored = connection.execute(
            "SELECT default_count FROM user_settings WHERE user_id = ?",
            (DEMO_USER_ID,),
        ).fetchone()

    assert restored is not None
    assert restored["default_count"] == original["default_count"]
    print("   rollback 확인: default_count =", restored["default_count"])


# 입력: 초기화된 SQLite DB 파일 경로.
# 출력: 반환값 없음. 변환한 키워드와 출처 ID 목록을 표시한다.
# 동작: TEXT 컬럼의 JSON 배열을 json.loads로 변환하고 Python list인지 검증한다.
def decode_json_column(db_path: Path) -> None:
    with closing(connect(db_path)) as connection:
        row = connection.execute(
            "SELECT keywords, source_ids FROM user_settings WHERE user_id = ?",
            (DEMO_USER_ID,),
        ).fetchone()

    assert row is not None
    keywords = json.loads(row["keywords"])
    source_ids = json.loads(row["source_ids"])
    assert isinstance(keywords, list) and isinstance(source_ids, list)
    print("5. JSON 컬럼:", {"keywords": keywords, "source_ids": source_ids})


# 입력: 초기화된 SQLite DB 파일 경로.
# 출력: 반환값 없음. 다중 연결 검증 완료 메시지를 표시한다.
# 동작: writer가 commit한 설정 변경을 reader가 조회하는지 확인한 뒤 원래 값을 복원한다.
def verify_commit_between_connections(db_path: Path) -> None:
    with closing(connect(db_path)) as writer, closing(connect(db_path)) as reader:
        with writer:
            writer.execute(
                "UPDATE user_settings SET in_app_notice = 0 WHERE user_id = ?",
                (DEMO_USER_ID,),
            )

        visible = reader.execute(
            "SELECT in_app_notice FROM user_settings WHERE user_id = ?",
            (DEMO_USER_ID,),
        ).fetchone()
        assert visible is not None and visible["in_app_notice"] == 0

        with writer:
            writer.execute(
                "UPDATE user_settings SET in_app_notice = 1 WHERE user_id = ?",
                (DEMO_USER_ID,),
            )

    print("6. 다중 연결: commit된 변경을 다른 연결에서 확인")


# 입력: 없음.
# 출력: 반환값 없음. 각 예제 결과와 전체 통과 메시지를 표시한다.
# 동작: 임시 DB를 생성해 모든 공용 DB 호출 예제를 순서대로 실행하고 종료 시 삭제한다.
def main() -> None:
    with TemporaryDirectory(prefix="dait-db-common-") as directory:
        db_path = Path(directory) / "dait.db"
        initialize_database(db_path)

        read_user(db_path)
        list_news_with_parameters(db_path)
        run_schedule_crud_transaction(db_path)
        verify_constraint_rollback(db_path)
        decode_json_column(db_path)
        verify_commit_between_connections(db_path)

        print("모든 공용 DB 예제가 통과했습니다:", db_path)


if __name__ == "__main__":
    main()
