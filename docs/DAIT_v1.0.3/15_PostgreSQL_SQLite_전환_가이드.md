# DAIT SQLite → PostgreSQL 전환 가이드

| 항목 | 값 |
|---|---|
| 문서 버전 | 1.0.3 |
| 기준일 | 2026-11-10 |
| 목적 | 로컬 개발(SQLite)과 운영(Supabase PostgreSQL)에서 저장소 계층이 동일하게 동작하도록 SQL 차이를 정리한다 |
| 대상 | `src/backend/src/dait/repositories/`, Alembic 마이그레이션, `src/backend/app/repositories/` |

## 문서 이력

| 버전 | 작성자 | 기준일 | 수정 내용 |
|---|---|---|---|
| 1.0.0 | seonghoon.yang | 2026-11-03 | 최초 작성 |
| 1.0.1 | seonghoon.yang | 2026-11-06 | 화면설계서 v1.0.1 반영 및 문서 세트 정합성 보강 |
| 1.0.2 | seonghoon.yang | 2026-11-10 | PostgreSQL/SQLite 전환 가이드 신규 작성 |
| 1.0.2 | seonghoon.yang | 2026-11-10 | 9절을 이중 백엔드 구현 현황으로 갱신 |
| 1.0.3 | devin | 2026-11-12 | Supabase PostgreSQL + Render 실 배포 기준으로 전환 가이드 갱신 (pooler 접속, search_path 분리) |

## 1. 전환 원칙

- 두 DB에서 공통으로 쓸 수 있는 타입과 문법을 우선한다(DB 설계서 7.2절).
- DB별 분기가 필요하면 드라이버 추상화 계층 하나에만 모은다. 서비스·라우트 계층에 `if sqlite` 분기를 두지 않는다.
- 가능하면 raw SQL 대신 SQLAlchemy Core/ORM 표현을 사용해 방언 차이를 프레임워크에 위임한다.
- 모든 시각은 UTC timezone-aware로 저장·비교한다.

## 2. 플레이스홀더 차이

| DB | 플레이스홀더 | 예 |
|---|---|---|
| SQLite | `?` | `WHERE id = ?` |
| PostgreSQL | `%s` (psycopg) / `$1` (asyncpg) | `WHERE id = %s` |

권장: `text()` + SQLAlchemy 바인드 파라미터, 또는 ORM을 사용해 플레이스홀더를 직접 쓰지 않는다.
불가피하게 raw SQL을 쓸 경우 연결 드라이버에 맞는 변환 함수를 repository 베이스에 둔다.

```python
# 나쁜 예 — 서비스 계층에 분기
if dialect == "sqlite":
    sql = "SELECT * FROM news WHERE id = ?"

# 좋은 예 — repository 내부에서 방언 변환
from sqlalchemy.engine import make_url

def placeholder(sql: str, dialect: str) -> str:
    return sql.replace("?", "%s") if dialect == "postgresql" else sql
```

## 3. 타입 매핑

| 논리 타입 | SQLite | PostgreSQL | 비고 |
|---|---|---|---|
| 불린 | `INTEGER 0/1` | `BOOLEAN` | 반환값 정규화 필요(아래 3.1) |
| JSON | `TEXT` + `json.loads` | `JSONB` | PostgreSQL은 인덱싱·쿼리 가능 |
| 시간 | `TEXT` ISO-8601 | `TIMESTAMPTZ` | PostgreSQL은 timezone을 강제함 |
| 불투명 ID | `TEXT` (uuid str) | `UUID` 또는 `TEXT` | `UUID` 타입 사용 시 드라이버별 처리 차이 주의 |
| 정수 | `INTEGER` | `BIGINT` 권장 | `INTEGER`도 동작하나 큰 카운터는 BIGINT |

### 3.1 불린 정규화

SQLite는 `True`/`False`를 0/1로 반환할 수 있다. SELECT 결과를 Pydantic 모델에 넣기 전 정규화한다.

```python
# SQLite 드라이버 결과 정규화 예시
if dialect == "sqlite":
    row["enabled"] = bool(row["enabled"])
```

PostgreSQL `BOOLEAN`은 그대로 `bool`을 반환하므로 정규화 함수는 양쪽에서 안전하게 동작해야 한다.

## 4. 쓰기 문법 차이

### 4.1 UPSERT

| DB | 문법 |
|---|---|
| SQLite | `INSERT ... ON CONFLICT(col) DO UPDATE SET ...` (3.24+) |
| PostgreSQL | 동일 문법 지원 |

두 DB 모두 `ON CONFLICT`를 지원하므로 그대로 사용 가능하다. 단, SQLite는 `ON CONFLICT DO NOTHING`의 `RETURNING`을 지원하지 않으므로 삽입 여부 확인이 필요하면 커서 `rowcount`를 사용한다.

```sql
-- 공통 사용 가능
INSERT INTO news (id, canonical_url, title, ...) VALUES (?, ?, ?, ...)
ON CONFLICT(canonical_url) DO NOTHING;
```

### 4.2 RETURNING

| DB | 지원 |
|---|---|
| SQLite | 3.35+ `RETURNING` 지원. 이전 버전은 미지원 |
| PostgreSQL | 완전 지원 |

`RETURNING`에 의존하는 코드는 SQLite 버전을 확인하거나 `cursor.lastrowid`/`rowcount` 폴백을 둔다.

### 4.3 AUTOINCREMENT

| DB | 문법 |
|---|---|
| SQLite | `INTEGER PRIMARY KEY AUTOINCREMENT` |
| PostgreSQL | `BIGSERIAL`/`GENERATED ... AS IDENTITY` |

DAIT는 외부 노출 ID를 불투명 문자열로 쓰므로 정수 자동증가 PK에 의존하지 않는 것을 권장한다.

## 5. 조회·조건 차이

### 5.1 LIKE 대소문자

- SQLite `LIKE`는 ASCII 범위에서 대소문자를 구분하지 않는다.
- PostgreSQL `LIKE`는 대소문자를 구분하고, `ILIKE`가 대소문자 무시다.

검색 동작을 맞추려면 PostgreSQL에서 `ILIKE`를 사용하거나 `lower(col) LIKE lower(?)`로 통일한다.
키워드 검색(`news.title`, `content_results` 요약 대상)에서 차이가 발생한다.

### 5.2 문자열 연결

| DB | 연결 연산자 |
|---|---|
| SQLite | `||` |
| PostgreSQL | `||` (동일) |

`dedupe_key` 해시는 애플리케이션에서 계산해 문자열로 저장하므로 DB 연결 연산자 의존은 피한다.

### 5.3 날짜·시간 함수

| 용도 | SQLite | PostgreSQL |
|---|---|---|
| 현재 시각 | `datetime('now')` | `now()` |
| UTC 변환 | `datetime(col, 'utc')` | `col AT TIME ZONE 'UTC'` |
| 다음 실행 시각 계산 | 애플리케이션(Python `zoneinfo`)에서 수행 권장 | 동일 |

`next_run_at` 같은 스케줄 계산은 DB 함수 대신 애플리케이션 계층에서 `zoneinfo`로 계산해 UTC `timestamptz`로 저장한다. DST 정책을 DB 방언에 의존시키지 않기 위함이다.

### 5.4 FOR UPDATE SKIP LOCKED

| DB | 지원 |
|---|---|
| SQLite | 미지원 (쓰기 잠금 모델이 다름) |
| PostgreSQL | 지원 |

tick 처리의 동시성 제어는 PostgreSQL에서 `SELECT ... FOR UPDATE SKIP LOCKED`를 사용하고,
SQLite 개발 환경에서는 단일 프로세스 전제 + `dedupe_key` unique로 대체한다.
방언 분기는 repository의 schedule 조회 메서드에만 국한한다.

## 6. 트랜잭션·동시성

- SQLite는 파일 단위 쓰기 잠금이라 동시 writer 처리량이 낮다. 로컬 개발·테스트 용도로만 사용한다.
- `BEGIN IMMEDIATE`(SQLite)와 `SELECT ... FOR UPDATE`(PostgreSQL)는 의미가 다르므로 공통 추상화가 필요하면 repository에서 `with_for_update()` 플래그를 받는 메서드로 통일한다.
- 멱등성은 DB unique 제약(`dedupe_key`, `canonical_url`)으로 양쪽에서 동일하게 보장한다.

## 7. 마이그레이션(Alembic) 처리

- `env.py`에서 `DATABASE_URL` 스킴을 감지해 `postgresql+psycopg`/`sqlite` 드라이버를 선택한다.
- 타입은 `sa.JSON` 대신 PostgreSQL에서 `JSONB`를 쓰려면 `postgresql.JSONB`를 dialect 조건으로 선택한다.

```python
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def json_type():
    # 마이그레이션 컨텍스트에 따라 분기
    return postgresql.JSONB().with_variant(sa.JSON(), "sqlite")
```

- `server_default`의 `now()`/`CURRENT_TIMESTAMP`는 양쪽 모두 지원되므로 그대로 사용 가능하다.
- SQLite는 `ALTER TABLE DROP COLUMN` 등 제약 변경이 제한적이므로 컬럼 삭제·타입 변경 마이그레이션은 운영 PostgreSQL 기준으로 작성하고, SQLite는 테스트용 재생성(`create_all`)으로 대응한다.

## 8. 점검 체크리스트

전환 시 repository별로 아래를 확인한다.

- [ ] `?` 플레이스홀더가 PostgreSQL 드라이버에서 동작하는가
- [ ] 불린 컬럼이 `bool`로 정규화되는가
- [ ] `LIKE` 검색 결과가 양쪽에서 동일한가(대소문자)
- [ ] `ON CONFLICT` UPSERT가 양쪽에서 동작하는가
- [ ] `RETURNING` 사용 시 SQLite 버전/폴백이 있는가
- [ ] `next_run_at` 계산이 애플리케이션 계층에서 이뤄지는가
- [ ] `FOR UPDATE SKIP LOCKED` 사용부가 방언 분기 안에 있는가
- [ ] `DATABASE_URL` 변경만으로 SQLite/PostgreSQL을 전환할 수 있는가
- [ ] 마이그레이션이 양쪽 dialect에서 `upgrade`/`downgrade` 모두 성공하는가

## 9. 참고: DB 이중 백엔드 구현 현황

`DATABASE_URL` 스킴으로 시작 시 백엔드가 자동 선택된다(`repositories/db.py` 디스패처).

| 계층 | 파일 | 역할 |
|---|---|---|
| 디스패처 | `repositories/db.py` | `db_dialect()` 스킴 판별, `connect`/`transaction`/`ping` 위임, `DB_ERRORS`/`DB_INTEGRITY_ERRORS` 공통 예외 계약 |
| SQLite 백엔드 | `repositories/db_sqlite.py` | 로컬 개발용. `PRAGMA foreign_keys`, `sqlite3` 동기 연결 |
| PostgreSQL 백엔드 | `repositories/db_postgres.py` | 서버 운영용. psycopg3, `?`→`%s` 변환(`translate_sql`), datetime→ISO 정규화, `lock_timeout` |

- 저장소·서비스 SQL은 두 백엔드 공통으로 유지한다. `?` 플레이스홀더는 postgres 백엔드가 `%s`로 변환한다.
- bool 파라미터는 `bool` 그대로 바인딩하고, `WHERE enabled = 1` 같은 방언 종속 조건은 `WHERE enabled`로 통일했다.
- `ON CONFLICT ... DO UPDATE/DO NOTHING`은 양쪽 DB가 네이티브 지원해 그대로 사용한다.
- Alembic `env.py`는 `postgresql://`→`postgresql+psycopg://` 변환과 `render_as_batch` sqlite 조건 분기를 처리한다.
- 남은 차이(LIKE 대소문자, `FOR UPDATE SKIP LOCKED`)는 필요 시 `db_dialect()` 분기로 처리한다(5.5절).
