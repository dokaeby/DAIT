# DAIT Backend

FastAPI 기반 `/v1` JSON API. 회원 인증(가입·로그인·토큰 회전·탈퇴·관심사)과 상태 확인이 구현되어 있다.

## 구조

| 경로 | 책임 |
|---|---|
| `src/dait/api/` | HTTP 경계: `deps.py`(인증 의존성), `v1/` 라우터 |
| `src/dait/services/` | 유스케이스: 인증·계정·관심사·상태, 로그인 잠금 |
| `src/dait/repositories/` | sqlite 접근과 트랜잭션 경계 (`db.py` + 테이블별 모듈) |
| `src/dait/schemas/` | Pydantic v2 요청·응답·내부 모델 (`extra="forbid"`) |
| `src/dait/core/` | 설정(BaseSettings), 보안(해시·JWT), 로깅·마스킹, 오류·미들웨어 |
| `src/dait/workers/`, `src/dait/collectors/` | 수집·AI 처리 비동기 실행 (구현 예정) |
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

# 서버
PYTHONPATH=src ../../.venv/bin/python -m uvicorn dait.main:app --host 127.0.0.1 --port 8000
```

`APP_ENV` 기본값은 `release`이며 release에서는 `/docs`, `/redoc`, `/openapi.json`이 비활성화된다.

## 테스트·품질 게이트 (저장소 루트에서 실행)

```bash
.venv/bin/python -m pytest tests/backend -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pyright
```
