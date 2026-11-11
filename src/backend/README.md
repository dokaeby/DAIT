# DAIT Backend

FastAPI 기반 `/v1` JSON API. 두 개의 패키지가 공존한다.

- `src/dait/` — 문서 계약 기반 구현: 회원 인증·관심사·뉴스/설정/예약 API, SSRF·robots·dedupe·캐시 안전장치, Alembic 마이그레이션
- `app/` — KAN-10 수집·AI 파이프라인: RSS 수집, 본문 추출(trafilatura), 제목 번역, 3줄 요약, 랭킹, 수집 worker (실행 코드는 `app/`에 모음)

## 구조

| 경로 | 역할 |
|---|---|
| `src/dait/api/` | HTTP 경계: `deps.py`(인증 의존성), `v1/` 라우터 |
| `src/dait/services/` | 유스케이스: 인증·계정·관심사·뉴스·설정·예약·수집 안전장치 |
| `src/dait/repositories/` | DB 접근과 트랜잭션 경계. `db.py`가 `DATABASE_URL` 스킴으로 `db_sqlite.py`(로컬)/`db_postgres.py`(서버, psycopg3)를 선택하고 테이블별 모듈은 공통 SQL만 사용 |
| `src/dait/schemas/` | Pydantic v2 요청·응답·내부 모델 (`extra="forbid"`) |
| `src/dait/core/` | 설정(BaseSettings), 보안(해시·JWT), SSRF 방어, 로깅·마스킹, 오류·미들웨어 |
| `src/dait/workers/`, `src/dait/collectors/` | 수집·AI 처리 비동기 실행 (가이드 스텁) |
| `app/api/main.py` | KAN-10 앱 생성·환경설정·생명주기·화면 제공 |
| `app/api/v1/news.py` | KAN-10 뉴스 목록·상세 API |
| `app/collectors/` | RSS 수집·본문 추출 |
| `app/core/` | 뉴스 분류·제목 번역 규칙 |
| `app/repositories/` | KAN-10 DB 접근 |
| `app/schemas/` | KAN-10 데이터 계약 |
| `app/services/` | KAN-10 뉴스 조회·캐시·랭킹 |
| `app/workers/` | KAN-10 수집·번역·요약 파이프라인 |
| `migrations/` | Alembic 변경 이력 (SQLite/PostgreSQL 공통 문법) |
| `config/.env.example` | 환경변수 이름 명세 (비밀값 없음) |

## 실행

저장소 루트 `.venv`를 사용한다.

```bash
# 의존성은 루트 uv.lock으로 관리
uv sync

# 환경변수 (JWT_SECRET은 32자 이상 필수)
export APP_ENV=debug
export DATABASE_URL="sqlite:///./dait.db"
export JWT_SECRET="<32자 이상 무작위 문자열>"

# 마이그레이션
cd src/backend
PYTHONPATH=src ../../.venv/bin/python -m alembic upgrade head

# 서버 (문서 계약 구현)
PYTHONPATH=src ../../.venv/bin/python -m uvicorn dait.main:app --host 127.0.0.1 --port 8000

# 서버 (KAN-10 파이프라인 앱)
python -m uvicorn src.backend.app.api.main:app --reload
```

`APP_ENV` 기본값은 `release`이며 release에서는 `/docs`, `/redoc`, `/openapi.json`이 비활성화된다.
화면은 `src/frontend/public/`, 테스트는 `tests/backend/tests/`에 있다.

## 테스트·품질 게이트 (저장소 루트에서 실행)

```bash
.venv/bin/python -m pytest tests/backend -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pyright
```
