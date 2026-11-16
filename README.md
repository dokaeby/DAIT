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
- 구글 로그인과 같은 이메일 계정 연결 선택(아래 "구글 로그인" 절).
- 뉴스 목록·상세는 같은 DATABASE_URL에서 저장된 결과를 조회.
- 새 통합 DB에는 기사가 없으므로 뉴스 목록이 비어 있는 것이 정상입니다.
- 기존 수집·Cloud LLM 파이프라인은 `src/backend/app/`에 보존하며 통합 서버에 아직 연결하지 않았습니다.
- 2단계: v1.0.2 스타일을 적용한 메인·뉴스 카드·상세 팝업을 현재 뉴스 API에 연결했습니다.
- 맞춤 뉴스, E5 의미 검색, 요약 재시도·자동 갱신 이식은 후속 단계입니다.
- 예약 CRUD 연결은 예약 실행·알림 발송의 완료를 의미하지 않습니다.

## 구글 로그인 (2단계 일부 선적용)

### 변경점
- 구글 로그인(OIDC Authorization Code + PKCE): `GET /v1/auth/google/login`, `GET /v1/auth/google/callback`,
  `POST /v1/auth/google/exchange`.
- 같은 이메일의 이메일 가입 계정이 있으면 사용자가 **"연결하기"/"연결하지 않기"**를 고르는
  연결 창을 띄운다. `POST /v1/auth/google/link`는 기존 비밀번호를 맞게 입력할 때만 연결한다.
- 구글 전용 계정(비밀번호 없음)의 탈퇴는 로그인한 지 5분 이내 + `탈퇴` 입력으로 확인한다
  (비밀번호 칸은 한글 조합이 안 되어 일반 글자칸을 쓴다).
- 마이그레이션: `0008_social_identities`(연결 표, `users.password_hash` NULL 허용),
  `0009_merge_social_topics`(`develop`의 `0008_news_topics`와 이력 합침).

### 구현 방식
- 시작 시 state·nonce·PKCE verifier를 만들어 1회용 저장소(Redis, 없으면 메모리)에 해시 키로 10분 보관하고,
  state는 HttpOnly·SameSite=Lax 쿠키에도 둬서 콜백에서 상수 시간 비교한다.
- 콜백은 구글 token 엔드포인트에서 id_token을 받아 `iss`·`aud`·`exp`·`nonce`·`email_verified`를 검사한다.
- 토큰은 주소 쿼리가 아니라 `#` 뒤의 **60초 1회용 교환 코드**로만 전달하고, 화면이 `exchange`로 토큰을 받는다.
- 토큰 발급은 이메일 로그인과 같은 경로(`open_session`)라 refresh 회전·재사용 감지가 똑같이 적용된다.
- 구글 통신은 `GoogleClient` 인터페이스 뒤에 두어 테스트가 가짜 구글로 대체한다(네트워크 없음).

### 판단 근거
- **이메일 자동 병합 금지:** 이메일 가입은 이메일 소유를 확인하지 않아, 남의 이메일로 먼저 가입한 공격자가
  피해자의 구글 로그인을 가로챌 수 있다. 연결은 구글의 이메일 확인과 계정 비밀번호를 **둘 다** 요구한다.
  비밀번호 시도는 로그인과 같은 잠금(계정+IP, 계정 전체, IP)을 쓴다.
- **id_token 서명 검증 생략:** 구글 token 엔드포인트와 TLS로 직접 받은 토큰은 OIDC Core 3.1.3.7이 TLS 검증으로
  대신하도록 허용한다. 새 라이브러리가 필요 없다(`httpx`, `PyJWT`는 기존 사용).
- 자세한 결정 기록은 `docs/decisions.md`의 2026-11-13 항목을 본다.

### 설정(환경변수)
`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`. 세 값이 모두 비면 기능이 꺼지고(404),
일부만 있으면 서버가 시작을 거부한다. release에서는 `https` 주소만 허용하고 debug에서만 `http://localhost`를 허용한다.
구글 콘솔의 "승인된 리디렉션 URI"와 `GOOGLE_REDIRECT_URI`는 한 글자도 다르면 안 된다.
로컬에서는 쿠키 때문에 주소창에 `127.0.0.1`이 아니라 `http://localhost:8000`으로 접속해야 한다.

### 자체 테스트 결과 (docs/DAIT_v1.0.3/08·09 기준)
- 단위 케이스 `UT-AUTH-013`~`UT-AUTH-029`(08 문서), 실행 절차는 09 문서 7.1.
- `uv run pytest tests/backend/tests/unit/test_google_login.py tests/backend/tests/unit/test_social_migration.py -q`
  → **33건 통과**(구글 로그인 30건 + 마이그레이션 3건).
- 전체: `uv run pytest -q` → **646건 통과**, `ruff check .` 통과, `pyright` 38건 오류(모두 `develop`에서 온
  기존 파일 `interest_matching.py`, `test_pipeline_sync.py`, `test_password_policy_and_throttle.py`이며 이번 변경 파일은 0건).
- 로컬에서 실제 구글 계정으로 가입·재로그인·연결·구글 전용 계정 탈퇴를 직접 확인했다.
- 아직 하지 않은 것: 운영 서버(Render)에서의 실제 구글 로그인, 구글 콘솔 앱 게시(현재 "테스트" 상태라 등록된 계정만 로그인).

### 푸시 후 작업 (배포 서버 반영 체크리스트)
코드는 `develop`에 반영되었지만, 배포 서버에서 구글 로그인이 동작하려면 아래 작업이 필요하다.
`.env`는 깃에 올리지 않으므로 서버마다 환경변수를 직접 넣어야 한다.
작업을 마치면 체크하고 날짜를 적는다. (현재: 모두 미완료)

- **최종(팀 운영 서버) 배포는 배포 담당자가 진행한다.** 아래 체크리스트는 담당자에게 넘기는 인수 항목이며,
  운영 서버의 구글 콘솔 리디렉션 URI 추가와 클라이언트 보안 비밀번호 전달은 담당자와 안전한 방법으로 협의한다.
- **개인 테스트 서버**(예: `https://project-dait.onrender.com`)는 푸시한 변경을 개인적으로 먼저 확인한 용도이며,
  팀 배포와는 별개다.

배포 담당자용 상세 절차(구글 콘솔 설정, 환경변수, 마이그레이션 순서, 확인·문제 해결)는
`docs/DAIT_v1.0.3/18_구글_로그인_운영_적용_가이드.md`를 본다.

서버마다 다음을 한다.
- [ ] 1. 서버 환경변수에 `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` 등록
      (`GOOGLE_REDIRECT_URI`는 `https://<서버 주소>/v1/auth/google/callback`이며 구글 콘솔의
      "승인된 리디렉션 URI"에 같은 주소가 등록되어 있어야 한다)
- [ ] 2. 해당 서버 DB에 마이그레이션 적용(`python -m src.server migrate`): `0008_social_identities`, `0009_merge_social_topics`
- [ ] 3. 구글 콘솔 "테스트 사용자"에 시험할 팀원 지메일 추가(앱 게시 전에는 등록된 계정만 로그인)
- [ ] 4. 서버 주소에서 실제 구글 로그인 확인: 신규 가입, 재로그인, 같은 이메일 계정 연결 창, 구글 전용 계정 탈퇴
- [ ] 5. 서버가 배포하는 브랜치(`develop` 또는 `main`)에 이 변경이 반영되었는지 확인

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
