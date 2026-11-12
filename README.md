# DAIT

AI 뉴스 수집·번역·요약 큐레이션 서비스.

## 통합 서버 — DAIT_UI_v1.0.3 1단계

저장소 루트 `C:\DAIT`에서 실행합니다. 공용 진입점은 `src.server:create_app`입니다.
회원·관심사·설정·예약·뉴스 목록/상세와 `src/frontend/public/` 화면을 같은 서버에서 제공합니다.
뉴스 API는 `src/backend/src/dait/api/v1/news_routes.py` 한 벌만 등록합니다.

### 환경 준비 (Windows PowerShell)

동작하는 Python 3.12 이상과 프로젝트 의존성이 필요합니다.
복사한 가상환경이 이전 PC의 Python 경로를 참조한다면 해당 가상환경을 재생성해야 합니다.
아래 명령은 정상적인 Python 환경에서 실행합니다.

```powershell
python -m pip install -r requirements.txt
```

루트 `.env` 또는 셸 환경변수로 `JWT_SECRET`(32자 이상 무작위 값), `DATABASE_URL`을 설정합니다.
문자열 예제 값을 실제 서명 키로 쓰지 마세요. 아래 키 생성 명령은 서버 재시작마다 반복하지 않습니다.

```powershell
$env:JWT_SECRET = python -c "import secrets; print(secrets.token_urlsafe(48))"
$env:APP_ENV = 'debug'
$env:DATABASE_URL = 'sqlite:///./dait_integrated.db'
python -m src.server migrate
python -m uvicorn src.server:create_app --factory --reload
```

접속: http://127.0.0.1:8000/ (debug API 문서: `/docs`).
`migrate`는 설정된 DB에 Alembic 변경 이력을 적용합니다. 서버 시작 시 DB 초기화·삭제·자동 마이그레이션을 하지 않습니다.
기본 통합 DB는 `dait_integrated.db`입니다. 기존 뉴스 서버의 `dait.db`와 v1.0.2의 DB는 덮어쓰지 않습니다.
이미 `DATABASE_URL`을 설정한 경우 그 값이 우선하므로, 마이그레이션 전에 대상 DB를 확인하세요.
운영에서는 고정된 JWT_SECRET과 DATABASE_URL을 공급하고 배포 준비 단계에서 마이그레이션을 실행합니다.
Procfile은 통합 서버를 실행하며 DB 마이그레이션은 자동 실행하지 않습니다.

## 현재 적용 범위

- 회원가입·로그인·토큰 갱신·로그아웃, 관심사 저장, 설정·예약 CRUD API 연결.
- 뉴스 목록·상세는 같은 DATABASE_URL에서 저장된 결과를 조회.
- 새 통합 DB에는 기사가 없으므로 뉴스 목록이 비어 있는 것이 정상입니다.
- 기존 수집·Cloud LLM 파이프라인은 `src/backend/app/`에 보존하며 통합 서버에 아직 연결하지 않았습니다.
- 2단계: v1.0.2 스타일을 적용한 메인·뉴스 카드·상세 팝업을 현재 뉴스 API에 연결했습니다.
- 맞춤 뉴스, E5 의미 검색, 요약 재시도·자동 갱신 이식은 후속 단계입니다.
- 예약 CRUD 연결은 예약 실행·알림 발송의 완료를 의미하지 않습니다.

## 코드 위치

| 경로 | 역할 |
|---|---|
| `src/server.py` | 공용 서버 factory 및 명시적 DB 마이그레이션 명령 |
| `src/backend/src/dait/` | 통합 API·서비스·인증·DB 접근 |
| `src/backend/migrations/` | 통합 DB 변경 이력 |
| `src/backend/app/` | 별도 뉴스 수집·번역·요약 파이프라인 |
| `src/frontend/public/` | 현재 제공되는 HTML·CSS·JavaScript |
| `tests/backend/tests/` | 백엔드 단위·통합 테스트 |
| `tests/frontend/tests/` | 프론트엔드 테스트 자료 |
| `docs/` | 기획·목업·과거 작업 자료 |

기존 `src.backend.app.api.main:app`은 별도 뉴스 서버입니다. 통합 UI 작업에는 공용 진입점을 사용합니다.
`dait.main`이라는 이름의 로컬 v1.0.2 패키지와 혼동하지 않도록 서버는 루트에서 위 명령으로 실행합니다.
