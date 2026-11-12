# DAIT 통합 테스트 절차서

| 항목 | 값 |
|---|---|
| 문서 버전 | 1.0.3 |
| 환경 | Windows 10/11 + Docker Desktop + Python 3.12+ |
| 대상 | 단계 1 MVP 전체 스택 |
| 실행 방식 | Docker Compose + pytest integration + 브라우저 수동 QA |

## 문서 이력

| 버전 | 작성자 | 기준일 | 수정 내용 |
|---|---|---|---|
| 1.0.0 | seonghoon.yang | 2026-11-03 | 최초 작성 |
| 1.0.1 | seonghoon.yang | 2026-11-06 | 화면설계서 v1.0.1 반영 및 문서 세트 정합성 보강 |
| 1.0.2 | seonghoon.yang | 2026-11-10 | 문서 세트 버전 1.0.2로 갱신 |
| 1.0.3 | devin | 2026-11-12 | 통합 테스트 절차를 로컬+Render/Supabase 환경 기준으로 갱신 |

## 0.1 v1.0.3 통합 절차 환경

- 로컬: `DATABASE_URL=sqlite:///...`, `JWT_SECRET`, `APP_ENV=debug`.
- 운영 검증: Render `dait.onrender.com`(`/healthz`,`/readyz`,`/v1/*`)과
  `dait-pipeline.onrender.com`, Supabase PostgreSQL, Render Key Value `dait-redis`.
- 스케줄 E2E는 `SCHEDULER_TICK_SECRET` Bearer 인증으로 `POST /v1/internal/scheduler/tick`을 호출한다.

## 1. 목적

메인, 상세보기, 설정 화면과 API, DB, Redis, Worker, Scheduler가 함께 동작하는지 동일한 절차로 검증하고, 장애·복구·보안까지 재현 가능한 증거를 남긴다.

## 2. 권장 통합 테스트 토폴로지

```mermaid
flowchart LR
  B[Browser/Test Client] --> API[FastAPI]
  API --> DB[(PostgreSQL/SQLite)]
  API --> R[(Redis)]
  S[Scheduler] --> R
  R --> W[Worker]
  W --> FS[Fixture Source Server]
  W --> FL[Fake LLM Server]
  W --> DB
  W --> R
  W --> FM[Fake SMTP]
```

## 3. 사전 준비

### 3.1 필수 도구

```powershell
python --version
docker --version
docker compose version
git --version
```

### 3.2 환경 분리

통합 테스트는 운영 Supabase/Redis/SMTP/LLM과 분리한다.

예시 `.env.integration`:

```text
APP_ENV=test
DATABASE_URL=postgresql://dait_test:dait_test@localhost:55432/dait_test
REDIS_URL=redis://localhost:56379/0
LLM_BASE_URL=http://localhost:58001
SMTP_HOST=localhost
SMTP_PORT=51025
```

비밀값은 테스트용 더미만 사용한다.

## 4. 인프라 기동

```powershell
docker compose -f docker-compose.integration.yml up -d --build
```

상태 확인:

```powershell
docker compose -f docker-compose.integration.yml ps
```

기대 컨테이너:
- api
- worker
- scheduler
- postgres 또는 test-db
- redis
- fixture-source
- fake-llm
- fake-smtp

## 5. DB 초기화 및 seed

### 5.1 migration

```powershell
alembic upgrade head
```

### 5.2 seed

```powershell
python scripts/seed_integration.py
```

필수 seed:
- USER-A/B
- 승인 source 2개
- READY news 3개
- INSUFFICIENT 1개
- FAILED 1개
- user_settings
- schedule 1개

### 5.3 seed 검증

SQL 또는 repository diagnostic command로 row count 확인한다.

| Table | 최소 기대 |
|---|---:|
| users | 2 |
| sources | 2 이상 |
| news | 5 이상 |
| content_results | news와 대응 |
| user_settings | 2 |
| schedules | 1 이상 |

## 6. Health/Ready 확인

```powershell
Invoke-RestMethod http://localhost:8000/healthz
Invoke-RestMethod http://localhost:8000/readyz
```

정상 시 API 테스트를 시작한다.

## 7. 자동 통합 테스트 실행

```powershell
pytest tests/integration -vv
```

기능군별:

```powershell
pytest tests/integration/test_auth_flow.py -vv
pytest tests/integration/test_news_flow.py -vv
pytest tests/integration/test_settings_flow.py -vv
pytest tests/integration/test_pipeline_flow.py -vv
pytest tests/integration/test_failure_recovery.py -vv
```

## 8. 메인 화면 검증 절차

1. USER-A 로그인
2. 브라우저에서 메인 접속
3. Network 탭에서 `GET /v1/news` 확인
4. 화면 카드 수와 response items 수 비교
5. 각 카드의 title/source/time/category/summary/status 확인
6. `전체`, `AI·기술` 필터 확인
7. `랭킹순`/`최신순` 전환
8. `OpenAI` 검색
9. 결과 0 검색어 입력
10. 초기화

증거:
- screenshot desktop 1440×900
- screenshot mobile 390×844
- `/v1/news` response JSON
- DB query 결과

## 9. 상세보기 검증 절차

1. 메인 첫 카드 `상세 보기`
2. URL/news_id 확인
3. `GET /v1/news/{id}` response 저장
4. 화면 article header와 API 비교
5. 3줄 요약 정확히 3개
6. 한국어 번역
7. 처리 정보
8. 원본 정보 source/url/published
9. 관련 뉴스 목록
10. 원문 새 탭
11. 링크 복사 성공
12. Clipboard 차단 환경에서 대체 UI

## 10. 설정 화면 검증 절차

1. 설정 진입
2. `GET /v1/me/settings`, `GET /v1/me/schedules` 확인
3. 예약 시각 08:30→09:00 변경
4. timezone `Asia/Seoul`
5. 관심 키워드 추가/삭제
6. 승인 출처 선택
7. AI 카테고리 확인
8. default_count 10→5
9. 인앱 ON
10. 메일 ON
11. 설정 저장
12. PATCH/POST request payload 저장
13. DB row 확인
14. 페이지 refresh
15. 값 복원 확인
16. 로그아웃→로그인
17. 다시 설정 진입
18. 값 복원 확인

설정은 단계 1 MVP이므로 “목업만 보임”은 실패로 판정한다.

## 11. 예약 실행 검증 절차

1. test clock을 next_run_at 직전으로 설정
2. scheduler tick
3. tick 전에는 job 0
4. next_run 도달
5. scheduler 두 인스턴스를 동시에 실행
6. Redis lock 확인
7. jobs 1건 생성 확인
8. worker consume
9. job status SUCCEEDED/FAILED 정책 확인
10. next_run_at 갱신

## 12. Pipeline 검증 절차

### 정상
1. fixture source에 신규 article 준비
2. collect job 실행
3. news row 확인
4. fake LLM request 확인
5. content_results READY
6. summary_lines 3개
7. translated_text 확인
8. cache invalidation
9. 메인 새 기사 확인

### 중복
1. 동일 canonical_url 재수집
2. news count 불변
3. LLM call count 불필요 증가 없음

### 본문 부족
1. 짧은 fixture
2. LLM call 0
3. INSUFFICIENT 저장

## 13. 장애 주입 절차

### 13.1 Redis 중단

```powershell
docker compose -f docker-compose.integration.yml stop redis
```

확인:
- 기존 저장 뉴스 조회 가능
- 필요 시 cache miss → DB fallback

복구:

```powershell
docker compose -f docker-compose.integration.yml start redis
```

### 13.2 Fake LLM 500
- fake LLM mode를 500으로 변경
- 신규 AI 처리 실패 기록
- 기존 READY 상세/목록 조회 정상

### 13.3 Source 500
- 한 source만 500
- 다른 source 정상 처리
- partial 상태

### 13.4 DB 중단
- `/readyz` 실패 확인
- `/healthz`는 프로세스 생존 정책에 맞게 확인
- 사용자 오류는 내부 stack 없이 일반화

## 14. 보안 절차

### 14.1 IDOR
- USER-A 인증으로 USER-B schedule ID PATCH/DELETE
- 기대 404 또는 정책상 authorization failure

### 14.2 SSRF
fixture redirect:

```text
https://fixture.test/redirect -> http://127.0.0.1:8080/private
```

기대 worker 차단.

### 14.3 SQL/XSS 유사 입력
검색 q:

```text
' OR 1=1 --
<script>alert(1)</script>
```

기대 SQL 실행/HTML 실행 없음.

### 14.4 token reuse
- refresh rotate 후 old token 재사용
- family revoke

### 14.5 release 노출
- release 구성에서 `/docs`, `/redoc`, OpenAPI 비활성 정책 확인
- 500 response stack trace 없음

## 15. 반응형/접근성 수동 검증

### Desktop
- 1440×900

### Mobile
- 390×844

각 화면 공통:
- horizontal scrollbar 없음
- focus visible
- tab 순서 논리적
- Enter/Space로 버튼 가능
- 아이콘 accessible name
- 상태는 색상 외 텍스트 포함

메인:
- 좌측 sidebar desktop
- mobile bottom tabs

상세:
- desktop 2열
- mobile 1열

설정:
- desktop menu + content
- mobile settings menu horizontal + fields 1열

## 16. 데이터 정합성 검증 SQL 예시

### 뉴스/결과 orphan

```sql
SELECT n.id
FROM news n
LEFT JOIN content_results c ON c.news_id = n.id
WHERE c.news_id IS NULL;
```

### 잘못된 default_count

```sql
SELECT user_id, default_count
FROM user_settings
WHERE default_count NOT IN (5,10);
```

### 중복 알림

```sql
SELECT user_id, schedule_id, news_id, channel, COUNT(*)
FROM notification_deliveries
GROUP BY user_id, schedule_id, news_id, channel
HAVING COUNT(*) > 1;
```

### 중복 canonical URL

```sql
SELECT canonical_url, COUNT(*)
FROM news
GROUP BY canonical_url
HAVING COUNT(*) > 1;
```

## 17. 결함 분류

| 등급 | 정의 | 예 |
|---|---|---|
| P0 | 시연/핵심 서비스 불가, 보안 치명 | 로그인 불가, IDOR, DB 손상 |
| P1 | MVP 핵심 기능 오동작 | 설정 저장 안 됨, 상세 500 |
| P2 | 우회 가능한 기능 오류 | 특정 빈 상태 문구 오류 |
| P3 | 시각/문구 경미 | spacing, 미세 문구 |

MVP 발표 전 P0/P1은 0이어야 한다.

## 18. 테스트 결과 기록 양식

| 항목 | 값 |
|---|---|
| Test ID | IT-SET-002 |
| Build/Commit | |
| 환경 | Windows / Docker Compose |
| 시작/종료 시각 | |
| 선행조건 | |
| 입력/조작 | |
| 기대결과 | |
| 실제결과 | |
| API evidence | |
| DB evidence | |
| Screenshot | |
| 판정 | PASS/FAIL/BLOCKED |
| Defect ID | |
| 재검증 결과 | |

## 19. 전체 회귀 실행 순서

1. `ruff check .`
2. `ruff format --check .`
3. `pyright`
4. `pytest tests/unit -q`
5. integration infra clean start
6. migration
7. seed
8. `pytest tests/integration -q`
9. desktop UI smoke
10. mobile UI smoke
11. 장애 주입 3종
12. 보안 P0/P1
13. IT-DEMO-001
14. 테스트 데이터/컨테이너 정리

## 20. 종료/정리

```powershell
docker compose -f docker-compose.integration.yml down -v
```

테스트용 DB volume과 fake 서비스 데이터만 삭제하며 운영 리소스에 영향을 주면 안 된다.

## 21. 통합 테스트 최종 승인 조건

- Unit 전체 PASS
- Integration P0/P1 전체 PASS
- IT-DEMO-001 PASS
- 메인/상세/설정 desktop/mobile PASS
- 설정 실제 저장/복원 PASS
- 중복 작업/알림 0
- 외부 제공자 장애 시 기존 뉴스 조회 유지
- 보안 차단 케이스 PASS
- release 민감정보 노출 0
- 증거 링크/로그/스크린샷이 Test ID에 연결됨
