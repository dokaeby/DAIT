# DAIT 단위 테스트 절차서

## English Metadata

| 항목 | 값 |
|---|---|
| English Title | DAIT Unit Test Procedure |
| Search Keywords | DAIT, unit test procedure, pytest, Windows, PowerShell, uv run, tests/backend, SQLite temp DB, test runner, quality gate |
| English Summary | Step-by-step procedure for running DAIT unit tests on Windows with Python 3.12+ and pytest. Documents `uv run pytest tests/backend -q`, the 608-test passing gate, per-module test file conventions, v1.0.4 additions (interest matching, pipeline sync, regional activity, URL pinning, keepalive), and separation of SQLite temp-DB tests from Supabase/PostgreSQL integration verification. |

| 항목 | 값 |
|---|---|
| 문서 버전 | 1.0.4 |
| 환경 | Windows 10/11, Python 3.12+ |
| 기본 명령 | PowerShell |
| 테스트 러너 | pytest |
| 대상 | DAIT 단계 1 MVP |

## 문서 이력

| 버전 | 작성자 | 기준일 | 수정 내용 |
|---|---|---|---|
| 1.0.0 | seonghoon.yang | 2026-11-03 | 최초 작성 |
| 1.0.1 | seonghoon.yang | 2026-11-06 | 화면설계서 v1.0.1 반영 및 문서 세트 정합성 보강 |
| 1.0.2 | seonghoon.yang | 2026-11-10 | 문서 세트 버전 1.0.2로 갱신 |
| 1.0.3 | seonghoon.yang | 2026-11-12 | pytest 실행 절차와 1.0.3 추가 테스트 파일 기준으로 절차 갱신 |
| 1.0.4 | seonghoon.yang | 2026-11-13 | 테스트 수 608건·v1.0.4 신규 테스트 파일(관심사 매칭, pipeline 동기화, 지역/관심사 활성, URL 안전성) 반영 |
| 1.0.4.1 | seonghoon.yang | 2026-11-13 | 상세보기 화면·설정 `노출·알림` 메뉴 UI 제거 반영 — 상세·설정 관련 UI 단위 테스트 기대값을 API 수준으로 전환 |

## 0.1 v1.0.3 실행 기준

```bash
cd src/backend
uv run pytest ../tests/backend -q   # 또는 저장소 루트에서 uv run pytest tests/backend -q
```

- 전체 608건 통과가 게이트다(develop 기준 수집 수). 신규 기능은 해당 모듈 테스트 파일에 케이스를 추가한다.
- DB 의존 테스트는 SQLite 임시 DB를 사용하고, Supabase/PostgreSQL은 통합·수동 검증으로 분리한다.
- v1.0.4 신규 테스트 파일: `test_interest_news_matching.py`, `test_pipeline_sync.py`,
  `test_regional_interest_activity.py` 및 `test_url_safety.py`·`test_password_policy_and_throttle.py`·
  `test_news_api.py`·`test_ai_processor.py`·`test_app_http.py`의 추가 케이스.

## 1. 목적

단위 테스트를 누구나 동일한 절차로 준비, 실행, 증거 수집, 결함 등록, 재검증할 수 있도록 실행 절차를 표준화한다.

## 2. 사전 조건

1. 프로젝트 소스 checkout 완료
2. Python 3.12 이상 설치
3. 테스트 dependency 설치 가능
4. `.env.test` 또는 test settings 준비
5. 실제 운영 DB/Redis/SMTP/LLM 자격 증명 사용 금지
6. 테스트 DB는 SQLite 또는 격리된 임시 PostgreSQL schema 사용
7. 시스템 시간이 테스트 결과에 직접 영향을 주지 않도록 clock fixture 사용

## 3. 권장 테스트 구조

```text
tests/
  unit/
    api/
      test_auth_schemas.py
      test_news_schemas.py
      test_settings_schemas.py
    services/
      test_auth_service.py
      test_news_service.py
      test_settings_service.py
      test_schedule_service.py
      test_ranking_service.py
    repositories/
      test_user_repository.py
      test_news_repository.py
      test_settings_repository.py
    workers/
      test_collector.py
      test_ai_processor.py
      test_retry.py
    ui/
      test_view_models.py
  fixtures/
    users.py
    news.py
    settings.py
    fake_clock.py
```

## 4. Windows PowerShell 환경 준비

### 4.1 가상환경

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
```

기대: Python 3.12.x 이상.

### 4.2 의존성 설치

프로젝트 lock 방식에 맞춰 실행한다.

```powershell
pip install -r requirements-dev.txt
```

또는 uv 사용 시:

```powershell
uv sync --dev
```

### 4.3 테스트 환경 변수

```powershell
$env:APP_ENV = "test"
$env:DATABASE_URL = "sqlite:///./.tmp/test.db"
$env:REDIS_URL = "redis://fake.invalid/0"
```

실제 API key를 넣지 않는다.

## 5. 실행 전 정적 검사

```powershell
ruff check .
ruff format --check .
pyright
```

세 명령 중 하나라도 실패하면 단위 테스트 결과와 별개로 품질 게이트 실패로 기록한다.

## 6. 전체 단위 테스트 실행

```powershell
pytest tests/unit -q
```

상세 출력:

```powershell
pytest tests/unit -vv
```

fail-fast 조사:

```powershell
pytest tests/unit -x -vv
```

## 7. 기능별 실행 절차

### 7.1 인증

```powershell
pytest tests/unit/services/test_auth_service.py -vv
pytest tests/unit/api/test_auth_schemas.py -vv
```

확인:
- 중복 이메일 일반화
- hash 저장
- refresh rotation
- logout/revoke
- 탈퇴 데이터 정리

### 7.2 메인/검색

```powershell
pytest tests/unit/services/test_news_service.py -k "home or search or rank" -vv
```

확인:
- 최대 10건
- 3건이면 3건만
- rank/latest
- 검색 trim/empty
- partial 상태

### 7.3 상세

```powershell
pytest tests/unit/services/test_news_service.py -k "detail or related or original" -vv
```

### 7.4 설정/예약

```powershell
pytest tests/unit/services/test_settings_service.py -vv
pytest tests/unit/services/test_schedule_service.py -vv
```

반드시 설정 저장 후 동일 fixture 재조회 테스트를 포함한다.

### 7.5 수집/AI/worker

```powershell
pytest tests/unit/workers -vv
```

실제 외부 HTTP/LLM이 호출되면 테스트 설계 실패다.

## 8. Mock/Fake 적용 원칙

| 의존성 | 단위 테스트 대체 |
|---|---|
| PostgreSQL | fake repository 또는 SQLite transaction fixture |
| Redis | fake cache/lock/queue |
| LLM | 고정 JSON fake |
| SMTP | fake sender |
| 뉴스 사이트 | fixture HTML/JSON |
| 시간 | fake clock |
| UUID | deterministic ID factory |
| Clipboard/browser | UI adapter mock |

## 9. 테스트 데이터 초기화

각 테스트는 arrange 단계에서 자체 데이터를 준비하고 종료 시 rollback 또는 임시 파일 삭제를 수행한다.

권장 pytest fixture:

```python
@pytest.fixture
def user_a(): ...


@pytest.fixture
def ready_news(): ...


@pytest.fixture
def fake_clock(): ...
```

세션 범위 fixture가 상태를 공유해 테스트 순서 의존성을 만들지 않게 한다.

## 10. 실패 조사 절차

1. 실패한 UT ID 확인
2. `pytest <file>::<test_name> -vv -s`로 단일 재현
3. 실제값/기대값 diff 확인
4. Mock call count와 인자 확인
5. DB mutation이 있으면 transaction 전후 상태 확인
6. 캐시 테스트면 key/TTL 확인
7. 보안 테스트면 응답/로그에 민감정보 존재 여부 확인
8. 결함 수정 후 해당 테스트 먼저 PASS
9. 기능군 전체 회귀
10. 전체 `tests/unit` 회귀

## 11. 실패 증거 기록 양식

| 항목 | 기록 예 |
|---|---|
| Test ID | UT-SET-002 |
| Commit | abc1234 |
| 실행 명령 | `pytest ... -vv` |
| 입력 | default_count=20 |
| 기대 | validation error |
| 실제 | 200 저장됨 |
| 관련 FR | FR-SET-03 |
| 관련 API | PATCH /v1/me/settings |
| 관련 DB | user_settings.default_count |
| 로그/캡처 | artifact 경로 |
| 원인 | CHECK/schema 누락 |
| 수정 | schema Literal[5,10] 적용 |
| 재검증 | PASS |

## 12. Coverage 사용

Coverage는 합격 기준 자체가 아니라 누락 탐지 보조 지표로 사용한다.

```powershell
pytest tests/unit --cov=src --cov-report=term-missing --cov-report=html
```

우선 확인 대상:
- 인증 분기
- settings validation
- scheduler DST/dedupe
- ranking tie-break
- AI validation
- retry/dead-letter

## 13. Mutation/경계 검토 체크

코드를 일부러 바꿨다고 가정하고 테스트가 잡는지 검토한다.

- `page_size<=50`을 `<100`으로 바꿔도 테스트가 실패하는가?
- default_count 5/10 제약을 제거하면 실패하는가?
- summary 3줄 제약을 제거하면 실패하는가?
- `https` 검증을 제거하면 실패하는가?
- user_id scope를 제거하면 실패하는가?
- dedupe unique를 제거하면 실패하는가?

## 14. 단위 테스트 종료 조건

다음 명령이 모두 성공해야 한다.

```powershell
ruff check .
ruff format --check .
pyright
pytest tests/unit -q
```

추가 조건:
- P0/P1 실패 0
- skip 사유 없는 skip 0
- flaky 0
- 외부 네트워크 0
- 테스트 로그 민감정보 0
- 관련 문서/기능 ID 최신 상태
