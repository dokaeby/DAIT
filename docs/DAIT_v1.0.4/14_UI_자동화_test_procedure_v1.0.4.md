# DAIT UI 자동화 테스트 절차서

## English Metadata

| 항목 | 값 |
|---|---|
| English Title | DAIT UI Automation Test Procedure |
| Search Keywords | DAIT, UI automation procedure, Playwright, pytest, seed data, viewport, browser, evidence rules, auth dialog, slow-auth-notice, regression, reproducibility |
| English Summary | Standardized procedure so any developer or QA can reproduce DAIT UI automation tests with identical seed data, viewport, browser, commands, and evidence rules. Covers Playwright setup across Windows/macOS/Linux, local and Render target URLs, verifying the immediate `#slow-auth-notice` popup, failure investigation, and evidence retention. |

| 항목 | 값 |
|---|---|
| 문서 버전 | 1.0.4 |
| 기준일 | 2026-11-13 |
| 대상 | DAIT 단계 1 MVP UI 회귀 |
| 환경 | Windows 10/11, macOS, Linux, Python 3.12+ |
| 자동화 | Playwright for Python, pytest |
| 기준 케이스 | `13_UI_자동화_test_cases_v1.0.4.md` |

## 문서 이력

| 버전 | 작성자 | 기준일 | 수정 내용 |
|---|---|---|---|
| 1.0.0 | seonghoon.yang | 2026-11-03 | 최초 작성 |
| 1.0.1 | seonghoon.yang | 2026-11-06 | 화면설계서 v1.0.1 반영 및 문서 세트 정합성 보강 |
| 1.0.2 | seonghoon.yang | 2026-11-10 | mockup 경로를 DAIT_v1.0.2로 수정, 문서 세트 버전 1.0.2로 갱신 |
| 1.0.3 | seonghoon.yang | 2026-11-12 | UI 자동화 절차를 현재 프론트엔드 구조와 Playwright 환경 기준으로 갱신 |
| 1.0.4 | seonghoon.yang | 2026-11-13 | v1.0.4 UI 요소 반영 — 지역/관심사 칩, member-only 게이팅, 출처 태그·기자명 |
| 1.0.4.1 | seonghoon.yang | 2026-11-13 | 상세보기 화면·설정 `노출·알림` 메뉴 UI 제거 반영 — 상세·노출·알림 UI 자동화 케이스 폐기/API 수준 전환 |

## 0.1 v1.0.3 UI 자동화 환경

- 대상 URL: 로컬 `http://127.0.0.1:8000` 또는 `https://dait.onrender.com`.
- Playwright MCP로 인증 다이얼로그·팝업·목록·설정 화면을 검증한다. (1.0.4.1: 상세 다이얼로그·`노출·알림` 섹션 제거)
- 로그인 팝업은 제출 즉시 `#slow-auth-notice`가 `open` 되고 응답 완료/실패 시 닫히는 것을 확인한다.

## 1. 목적

어떤 개발자나 QA 담당자도 동일한 seed, 뷰포트, 브라우저, 실행 명령과 증거 규칙으로 DAIT UI 자동화 테스트를 재현하도록 준비, 실행, 실패 조사, 증거 보관, 재검증 절차를 표준화한다.

## 2. 테스트 계층

| 계층 | 대상 | 실행 방식 | 판정 |
|---|---|---|---|
| Static UI | `mockup/index.html`, `settings.html` | 정적 서버 + Playwright | 메인·설정 레이아웃, 반응형, DOM, 접근성 계약 |
| Dynamic UI | 실제 DAIT Web + FastAPI | 격리 DB·Redis + Playwright | 조작, API, 저장, 재진입, 오류 복구 |

정적 목업의 버튼은 기능 PASS 근거로 사용하지 않는다. 검색, 저장, Clipboard, API 오류 시나리오는 Dynamic UI에서만 판정한다.

## 3. 사전 조건

1. DAIT 소스 checkout 완료
2. Python 3.12 이상과 `uv` 설치
3. 테스트용 DB·Redis 또는 로컬 데모 DB 사용 가능
4. 운영 Supabase, Redis, SMTP, LLM 자격 증명 사용 금지
5. 시각·ID·뉴스 순서가 고정된 UI seed 준비
6. 테스트 대상 기본 URL 확인

## 4. 도구 설치

DAIT 루트에서 실행한다.

```powershell
uv sync --dev
uv run playwright install chromium
uv run playwright --version
uv run pytest --version
```

`pytest-playwright`를 사용하는 테스트 구조라면 개발 의존성에 명시적으로 추가한다.

```powershell
uv add --dev pytest-playwright
```

개인 전역 환경에만 설치하지 않고 프로젝트 lock 파일에 버전을 반영한다.

## 5. 권장 폴더 구조

```text
tests/
  ui/
    conftest.py
    pages/
      home_page.py
      settings_page.py
    test_common_ui.py
    test_home_ui.py
    test_settings_ui.py
    test_state_recovery_ui.py
    snapshots/
  fixtures/
    ui_seed.py
playwright-report/
test-results/
```

Page Object는 재사용되는 화면 행동이 2개 이상의 테스트에서 반복될 때만 도입한다. 한 번만 사용하는 locator를 별도 wrapper로 감추지 않는다.

## 6. 환경 설정

예시 `.env.ui`:

```text
APP_ENV=test
UI_BASE_URL=http://127.0.0.1:8000
DATABASE_URL=sqlite:///./.tmp/ui-test.db
REDIS_URL=redis://127.0.0.1:6379/15
UI_USER_EMAIL=ui-user-a@dait.test
UI_USER_PASSWORD=ui-test-only-password
```

- 실제 비밀값은 파일·trace·screenshot에 저장하지 않는다.
- CI에서는 secret store와 전용 테스트 계정을 사용한다.
- 실행 시간은 `Asia/Seoul`로 고정하고 애플리케이션 타임존과 브라우저 타임존을 동일하게 맞춘다.

## 7. 테스트 데이터 준비

### 7.1 초기화

현재 `test-demo` 로컬 UI는 다음과 같이 격리 DB를 초기화한다.

```powershell
Push-Location docs/demo/test-demo
$env:DAIT_DB_PATH = (Join-Path $PWD ".tmp/ui-test.db")
uv run python -c "from pathlib import Path; from app.database import initialize_database; initialize_database(Path('.tmp/ui-test.db'))"
Pop-Location
```

전체 통합 환경은 `11_통합_test_procedure_v1.0.4.md`의 migration·seed 절차를 사용하되 다음 결과를 보장해야 한다.

| 데이터 | 기대 |
|---|---|
| USER-A | 기본 노출 10, 인앱 ON, 메일 OFF |
| USER-B | 소유권 검증용, USER-A와 데이터 분리 |
| 예약 | USER-A, 08:30, Asia/Seoul, enabled |
| READY news | 3건 이상, 결정적 랭킹·발행 시각 |
| INSUFFICIENT news | 1건 |
| FAILED news | 1건, 기본 목록 미노출 |

### 7.2 데이터 검증

테스트 시작 전에 API 또는 DB 진단 명령으로 row 수와 ID를 확인한다. 필수 seed가 없으면 UI 테스트를 시작하지 않는다.

## 8. 서비스 기동과 준비 상태

실제 애플리케이션:

```powershell
Push-Location docs/demo/test-demo
$env:PYTHONPATH = "."
$env:DAIT_DB_PATH = (Join-Path $PWD ".tmp/ui-test.db")
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

서버 종료 후 `Pop-Location`으로 DAIT 루트에 복귀한다.

정적 목업 전용:

```powershell
uv run python -m http.server 4173 --directory docs/DAIT_v1.0.4/mockup
```

준비 상태 확인:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/healthz
Invoke-RestMethod http://127.0.0.1:8000/readyz
```

`readyz` 실패 시 UI 테스트를 시작하지 않고 의존성을 복구한다.

## 9. 자동화 구현 규칙

### 9.1 Locator 우선순위

1. `get_by_role()` + 접근성 이름
2. `get_by_label()`
3. `get_by_placeholder()`
4. 의미 있는 `data-testid`

CSS class, DOM 순번, 텍스트의 부분 일치에 의존하지 않는다. `data-testid`가 필요하면 `<화면>-<영역>-<역할>` 규칙을 사용한다.

### 9.2 대기 규칙

- `wait_for_timeout()`과 고정 sleep을 사용하지 않는다.
- 화면 상태, API response, URL, locator visibility 중 사용자에게 보이는 완료 조건을 기다린다.
- 네트워크 idle 전체 대기는 장시간 connection으로 끝나지 않을 수 있으므로 핵심 API로 범위를 제한한다.

### 9.3 격리 규칙

- 테스트마다 새 browser context를 사용한다.
- 설정·예약 변경 테스트는 전용 사용자 또는 사전 초기화 fixture를 사용한다.
- 실행 순서와 직렬·병렬 실행 여부에 결과가 달라지지 않아야 한다.

### 9.4 Network 제어

- 외부 뉴스 URL은 route interception으로 방향만 확인하고 실제 인터넷으로 나가지 않는다.
- 오류·지연·partial 케이스는 결정적 fake response를 사용한다.
- 핵심 성공 흐름은 가능하면 실제 테스트 API·DB를 통과한다.

## 10. 실행 절차

### 10.1 정적 목업 smoke

```powershell
$env:UI_BASE_URL = "http://127.0.0.1:4173"
uv run pytest tests/ui/test_common_ui.py -m static -q
```

확인:

- 1440×900과 390×844에서 가로 넘침 없음
- 메인·설정 heading·navigation·button 이름 존재 (상세 패널은 1.0.4.1에서 제거)
- Desktop sidebar와 Mobile bottom navigation 전환

### 10.2 Dynamic UI P0 smoke

```powershell
$env:UI_BASE_URL = "http://127.0.0.1:8000"
uv run pytest tests/ui -m "ui and p0" -q
```

필수 흐름:

1. 인증 상태 준비
2. 메인 기본 목록·랭킹·검색
3. 첫 카드 원문 열기·`GET /v1/news/{id}` 상세 API 확인 (상세 화면 미제공 — 1.0.4.1)
4. 설정 조회·저장·재진입
5. 검증 오류와 API 오류 일반화

### 10.3 전체 Chromium 회귀

```powershell
uv run pytest tests/ui -m ui -q
```

### 10.4 화면을 보며 실행

```powershell
uv run pytest tests/ui/test_settings_ui.py -m ui --headed -vv
```

### 10.5 단일 케이스 재현

```powershell
uv run pytest tests/ui/test_home_ui.py -k "UI_HOME_005" --headed -vv -s
```

케이스 ID는 pytest test name 또는 marker에 그대로 남겨 문서와 보고서를 추적할 수 있게 한다.

## 11. 반응형·시각 검증

1. Desktop Chromium 1440×900을 실행한다.
2. Mobile Chromium 390×844을 실행한다.
3. 동적 시각, request ID, 랜덤 seed를 고정한다.
4. 화면 전체보다 핵심 component를 우선 캡처한다.
5. 베이스라인 갱신은 기능 변경 승인자의 확인 후에만 수행한다.

시각 비교 예외 허용치는 폰트 랜더링 환경을 고정한 후 최소로 유지한다. 차이를 높여 실제 레이아웃 회귀를 숨기지 않는다.

## 12. 접근성 검증

Playwright assertion으로 다음을 필수 확인한다.

- 페이지당 대표 `h1` 1개
- `main`, navigation, form landmark의 이름
- 모든 입력의 label 또는 접근성 이름
- icon-only button의 `aria-label`
- 키보드 포커스 순서와 focus-visible
- 오류 메시지와 입력의 연결
- 색상 외 텍스트로 처리 상태 표시
- Mobile에서 주요 터치 대상 44px 이상

axe 기반 검사를 추가하더라도 키보드 실제 조작과 상태 메시지 검증을 대체하지 않는다.

## 13. 오류·복구 검증

| 조건 | 제어 방법 | 필수 확인 |
|---|---|---|
| API 500 | route fulfill 또는 fake API | 일반화 오류, 재시도, 내부 stack 미노출 |
| 응답 지연 | route handler에서 제어된 지연 | loading 표시, 중복 요청 방지 |
| 0건 | 빈 `items` 응답 | 빈 상태, 초기화 |
| partial | `meta.partial=true` | 정상 카드 유지, 안내 표시 |
| offline | browser context offline | 네트워크 안내, 온라인 복구 |
| Clipboard 차단 | permissions 제거 | 대체 안내, 콘텐츠 유지 |
| 세션 만료 | storage state 제거·401 | 재인증, 민감 화면 숨김 |

## 14. 증거 수집

실패 시 다음을 `test-results/<case-id>/`에 저장한다.

| 증거 | 규칙 |
|---|---|
| screenshot | 실패 지점과 기대 상태 캡처 |
| trace | 네트워크·DOM·콘솔·조작 재현 |
| video | 상태 전환·재시도·반응형 실패에만 필수 |
| console | `error`, unhandled rejection 저장 |
| network | 핵심 API method, URL, status, 비민감 request body |

토큰, cookie, 비밀번호, 개인정보, 운영 URL은 저장 전에 제거한다.

## 15. 실패 조사 절차

1. 실패한 UI 케이스 ID와 환경을 기록한다.
2. trace에서 첫 실패 assertion 이전의 request·response·console을 확인한다.
3. 실패가 테스트 데이터 오염, locator 오류, 동기화 오류, 제품 결함 중 어디에 속하는지 분류한다.
4. 고정 sleep이나 무조건 재시도로 실패를 숨기지 않는다.
5. 해당 케이스를 단독·반복 10회 실행해 비결정성을 확인한다.
6. 수정 후 단일 케이스, 기능군, 전체 P0, 전체 UI 순으로 재검증한다.

## 16. 결함 기록 양식

| 항목 | 기록 예 |
|---|---|
| UI Case ID | UI-SET-006 |
| Commit | full SHA |
| 브라우저·뷰포트 | Chromium 1440×900 |
| 실행 명령 | `uv run pytest ... -vv` |
| seed | ui-seed-2026-11-06 |
| 기대 | 예약·관심·계정 설정값을 저장 후 복원한다. 설정 화면에 알림·노출 항목은 없다(1.0.4.1). |
| 실제 | 새로고침 후 API 값 그대로 복원 (노출·알림은 UI 없음) |
| 증거 | screenshot, trace, request body |
| 심각도 | P0/P1/P2 |
| 관련 FR·API | FR-SET-03, PATCH `/v1/me/settings` |

## 17. CI 실행 순서

```text
uv sync --frozen --dev
  → ruff check / format check / pyright
  → unit tests
  → integration infra + migration + seed
  → API integration tests
  → Playwright Chromium install
  → UI P0 smoke
  → UI full regression
  → artifact upload
  → environment teardown
```

UI 테스트는 동일 commit의 정적 검사, 단위, 통합 테스트가 PASS한 후 실행한다.

## 18. 종료 조건

- `13_UI_자동화_test_cases_v1.0.4.md`의 P0 100% PASS
- 미승인 P1 실패 0건
- 재시도에서만 PASS한 flaky 케이스 0건
- 콘솔 error·unhandled rejection 0건
- Desktop·Mobile 가로 넘침 0건
- trace·screenshot에 비밀값·개인정보 노출 0건
- 실패 증거와 결함 ID가 모두 추적 가능

## 19. 정리

```powershell
docker compose -f docker-compose.integration.yml down -v
Remove-Item -Recurse -Force .tmp\ui-test -ErrorAction SilentlyContinue
```

공유 환경이나 운영 데이터를 정리 대상으로 지정하지 않는다.
