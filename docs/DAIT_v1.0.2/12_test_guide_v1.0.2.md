# DAIT 테스트 실행 가이드

| 항목 | 값 |
|---|---|
| 문서 버전 | 1.0.2 |
| 대상 | DAIT 단계 1 MVP |
| 기준 문서 | 08 단위 테스트 케이스, 09 단위 테스트 절차서, 10 통합 테스트 케이스, 11 통합 테스트 절차서 |
| 기본 환경 | Windows 10/11, Python 3.12+, PowerShell |
| 통합 환경 | Docker Desktop, Docker Compose, PostgreSQL/SQLite, Redis |
| 테스트 러너 | pytest |

## 문서 이력

| 버전 | 작성자 | 기준일 | 수정 내용 |
|---|---|---|---|
| 1.0.0 | seonghoon.yang | 2026-11-03 | 최초 작성 |
| 1.0.1 | seonghoon.yang | 2026-11-06 | 화면설계서 v1.0.1 반영 및 문서 세트 정합성 보강 |
| 1.0.2 | seonghoon.yang | 2026-11-10 | 문서 세트 버전 1.0.2로 갱신 |

## 1. 목적

이 문서는 DAIT의 테스트 케이스를 실제로 실행하는 방법을 설명한다. 테스트 담당자는 이 문서만 따라가도 다음 작업을 수행할 수 있어야 한다.

1. 테스트 환경 준비
2. 단위 테스트 실행
3. API 테스트 실행
4. 메인 화면 수동 테스트
5. 상세보기 화면 수동 테스트
6. 설정 화면 수동 테스트
7. DB 저장값 확인
8. Redis 캐시·큐 확인
9. Worker/Scheduler 연동 확인
10. 오류와 장애 상황 재현
11. 테스트 결과와 증거 기록
12. 실패 케이스 재검증

---

## 2. 전체 테스트 순서

권장 순서는 아래와 같다.

```text
소스 준비
  ↓
가상환경 생성
  ↓
의존성 설치
  ↓
정적 검사
  ↓
단위 테스트
  ↓
테스트 DB/Redis 기동
  ↓
Migration / Seed
  ↓
API 통합 테스트
  ↓
메인 화면 테스트
  ↓
상세보기 테스트
  ↓
설정 화면 테스트
  ↓
Scheduler / Worker 테스트
  ↓
DB / Redis 검증
  ↓
장애·보안 테스트
  ↓
전체 E2E 시나리오
  ↓
결과 정리 및 결함 등록
```

단위 테스트가 실패한 상태에서 통합 테스트를 진행하지 않는 것을 원칙으로 한다.

---

## 3. 테스트 환경 준비

### 3.1 프로젝트 폴더 이동

PowerShell에서 DAIT 프로젝트 루트로 이동한다.

```powershell
cd C:\Users\Playdata\aio4\DAIT
```

현재 경로 확인:

```powershell
Get-Location
```

### 3.2 Python 확인

```powershell
py -3.12 --version
```

기대 결과:

```text
Python 3.12.x
```

### 3.3 가상환경 생성

처음 한 번만 실행한다.

```powershell
py -3.12 -m venv .venv
```

활성화:

```powershell
.\.venv\Scripts\Activate.ps1
```

활성화 후 확인:

```powershell
python --version
where.exe python
```

### 3.4 의존성 설치

프로젝트가 requirements 파일을 사용하면:

```powershell
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

uv를 사용하는 프로젝트라면:

```powershell
uv sync --dev
```

### 3.5 테스트 환경변수

실제 운영 계정, Supabase 운영 DB, 실제 SMTP, 실제 LLM API 키를 테스트에 사용하지 않는다.

예시 `.env.test`:

```text
APP_ENV=test
DATABASE_URL=sqlite:///./test_dait.db
REDIS_URL=redis://localhost:6379/15
LLM_BASE_URL=http://localhost:58001
SMTP_HOST=localhost
SMTP_PORT=51025
```

통합 테스트는 별도의 `.env.integration`을 사용한다.

---

## 4. 테스트 전 기본 검증

### 4.1 코드 스타일

```powershell
ruff check .
```

기대 결과:

```text
All checks passed!
```

### 4.2 포맷 검사

```powershell
ruff format --check .
```

### 4.3 타입 검사

```powershell
pyright
```

단위 테스트 이전에 위 검사를 통과시키는 것을 권장한다.

---

# 5. 단위 테스트 실행 방법

## 5.1 전체 단위 테스트

```powershell
pytest tests/unit -v
```

빠른 실행:

```powershell
pytest tests/unit -q
```

실패 즉시 중지:

```powershell
pytest tests/unit -x -v
```

첫 실패만 상세히 보고 싶을 때 유용하다.

## 5.2 특정 기능만 실행

### 인증

```powershell
pytest tests/unit/services/test_auth_service.py -v
```

### 메인 뉴스 목록

```powershell
pytest tests/unit/services/test_news_service.py -v
```

### 검색

```powershell
pytest tests/unit -k "search" -v
```

### 설정

```powershell
pytest tests/unit/services/test_settings_service.py -v
```

### 예약

```powershell
pytest tests/unit/services/test_schedule_service.py -v
```

### AI 처리

```powershell
pytest tests/unit/workers/test_ai_processor.py -v
```

### 수집기

```powershell
pytest tests/unit/workers/test_collector.py -v
```

## 5.3 특정 테스트 케이스 한 개 실행

예:

```powershell
pytest tests/unit/services/test_news_service.py::test_ranked_news_returns_ready_items_only -v
```

테스트 케이스 ID를 pytest marker로 연결했다면:

```powershell
pytest -m UT_HOME_001 -v
```

## 5.4 Coverage 확인

```powershell
pytest tests/unit --cov=src --cov-report=term-missing
```

HTML 보고서:

```powershell
pytest tests/unit --cov=src --cov-report=html
start htmlcov\index.html
```

Coverage 숫자만 높이는 테스트보다 핵심 분기와 실패 경로를 검증하는 것이 우선이다.

---

# 6. API 테스트 방법

API 서버 실행:

```powershell
uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

프로젝트 구조에 따라 `src.api.main:app` 경로는 실제 앱 엔트리포인트로 변경한다.

## 6.1 Health 확인

```powershell
Invoke-RestMethod http://127.0.0.1:8000/healthz
```

## 6.2 Ready 확인

```powershell
Invoke-RestMethod http://127.0.0.1:8000/readyz
```

DB나 Redis가 필요한 구성이라면 준비 상태까지 확인한다.

## 6.3 뉴스 목록 API

```powershell
Invoke-RestMethod `
  "http://127.0.0.1:8000/v1/news?category=AI&sort=rank&page_size=10"
```

확인 항목:

- HTTP 200
- `items` 배열 존재
- rank 순서
- title
- source_name
- published_at
- summary_lines 3개
- processing_status
- original_url

## 6.4 검색 API

```powershell
Invoke-RestMethod `
  "http://127.0.0.1:8000/v1/news?q=OpenAI&category=AI&sort=rank&page_size=10"
```

기대:
- 제목 또는 검증 요약에 OpenAI가 포함된 결과만 반환
- 검색 결과가 없으면 빈 배열
- 500 오류가 아니어야 함

## 6.5 상세 API

먼저 목록에서 `id`를 확인한 뒤:

```powershell
Invoke-RestMethod `
  "http://127.0.0.1:8000/v1/news/NEWS_ID"
```

확인:
- 원본 메타데이터
- summary_lines 정확히 3개
- translated_text
- related_news
- 검증된 HTTPS URL

## 6.6 설정 API

로그인 세션 또는 테스트 인증 토큰을 준비한 상태에서 실행한다.

조회:

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/v1/me/settings" `
  -Method GET `
  -WebSession $session
```

수정 예시:

```powershell
$body = @{
    default_count = 10
    categories = @("AI")
    keywords = @("멀티모달", "AI 에이전트")
    source_ids = @("source-openai")
    in_app_notice = $true
    email_notice = $false
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/v1/me/settings" `
  -Method PATCH `
  -ContentType "application/json" `
  -Body $body `
  -WebSession $session
```

저장 후 GET을 다시 호출하여 동일 값이 복원되는지 확인한다.

---

# 7. 메인 화면 수동 테스트 방법

## 7.1 사전 조건

DB에 다음 데이터가 준비되어 있어야 한다.

- READY 기사 3건 이상
- PARTIAL 상태를 표시할 수 있는 기사 또는 출처 상태 1건
- AI 카테고리 기사
- 검색 가능한 `OpenAI` 키워드 포함 기사

## 7.2 정상 화면 확인

1. 브라우저에서 DAIT 접속
2. 로그인
3. 메인 화면 진입
4. `오늘의 AI 뉴스` 제목 확인
5. 검색창 확인
6. `전체`, `AI·기술` 필터 확인
7. 정렬 컨트롤 확인
8. 뉴스 카드 1~3 확인
9. 순위, 제목, 출처, 시각, 카테고리 확인
10. AI 3줄 요약 확인
11. 처리 상태 확인
12. `상세 보기`, `원문 열기` 확인

### 기대 결과

- 카드가 겹치지 않는다.
- 각 카드의 제목과 출처가 표시된다.
- 3줄 요약이 정확히 3개다.
- READY 상태는 텍스트와 색으로 구분된다.
- 실제 데이터 수보다 많은 가짜 카드가 생기지 않는다.

## 7.3 검색 테스트

1. 검색창에 `OpenAI` 입력
2. 검색 실행
3. 결과 개수 확인
4. 제목/요약의 일치 여부 확인
5. 검색어 삭제 또는 초기화
6. 전체 목록 복원 확인

### 실패 케이스

- 존재하지 않는 문자열 입력
- 공백만 입력
- 매우 긴 검색어
- 특수문자 입력

기대:
- 서버 오류 없이 처리
- 빈 검색은 전체 목록으로 복귀
- 결과 없음은 오류 화면과 구분

## 7.4 필터/정렬 테스트

1. `AI·기술` 선택
2. AI 카테고리만 표시되는지 확인
3. `랭킹순` 확인
4. `최신순` 변경
5. 발행 시각 기준 순서 변경 확인

---

# 8. 상세보기 화면 테스트 방법

## 8.1 진입

1. 메인 화면에서 첫 번째 뉴스의 `상세 보기` 클릭
2. 상세 화면 URL 또는 route 변경 확인

## 8.2 화면 검증

확인 순서:

1. breadcrumb
2. AI·기술 태그
3. 처리 완료 상태
4. 기사 제목
5. 출처
6. 발행 시각
7. 원문 새 탭 버튼
8. 링크 복사 버튼
9. AI 3줄 요약
10. 한국어 번역
11. 처리 정보
12. 원본 정보
13. 관련 뉴스

### 기대 결과

- 요약은 정확히 3개
- 번역이 있는 경우 한국어 텍스트 표시
- 원본 정보와 서비스 요약이 섞이지 않음
- 관련 뉴스에 현재 기사 자신이 나오지 않음
- 위험한 `javascript:` 또는 `http:` URL을 원문 버튼에서 사용하지 않음

## 8.3 원문 새 탭 테스트

1. 원문 새 탭 클릭
2. 새 탭 열림 확인
3. 주소가 HTTPS인지 확인
4. 원 사이트 도메인 확인

## 8.4 링크 복사 테스트

1. 링크 복사 클릭
2. 성공 안내 확인
3. 메모장에 붙여넣기
4. 원문 URL과 동일한지 확인

Clipboard 권한 거부도 테스트한다.

---

# 9. 설정 화면 테스트 방법

메인·상세·설정은 모두 단계 1 MVP 구현 범위다.

## 9.1 설정 화면 진입

1. 헤더의 설정 버튼 클릭
2. 설정 화면 표시 확인
3. 현재 저장값 조회 확인

확인 영역:

- 예약 수집
- 관심 설정
- 노출·알림
- 계정·정책

## 9.2 예약 수집 테스트

1. 예약 시각을 `08:30`으로 설정
2. 시간대 `Asia/Seoul` 확인
3. 활성 상태 확인
4. 저장
5. 화면 재진입
6. 동일 값 복원 확인

DB 확인:

```sql
SELECT user_id, local_time, timezone, enabled, next_run_at
FROM schedules
ORDER BY id DESC;
```

## 9.3 관심 설정 테스트

1. 관심 키워드에 `멀티모달` 입력
2. `AI 에이전트` 추가
3. 승인 출처 선택
4. 카테고리 `AI` 선택
5. 저장
6. 페이지 새로고침
7. 저장값 복원 확인

## 9.4 노출 수 테스트

허용값:

- 5
- 10

테스트:

1. 5 저장 → 성공
2. 10 저장 → 성공
3. 7 전송 → 422 또는 명시적 validation 실패

## 9.5 알림 테스트

1. 인앱 알림 ON
2. 이메일 알림 OFF
3. 저장
4. 재조회
5. 동일 상태 확인

이후 반대로 설정해 재검증한다.

## 9.6 변경 취소 테스트

1. 저장된 값과 다른 값을 입력
2. `변경 취소` 클릭
3. 서버 저장값으로 복구되는지 확인
4. DB 값이 변경되지 않았는지 확인

---

# 10. DB 검증 방법

## 10.1 사용자 설정

```sql
SELECT *
FROM user_settings
WHERE user_id = 'TEST_USER_ID';
```

확인:
- default_count
- categories
- keywords
- source_ids
- in_app_notice
- email_notice

## 10.2 뉴스와 콘텐츠 결과

```sql
SELECT
    n.id,
    n.title,
    n.published_at,
    c.status,
    c.summary_lines
FROM news n
JOIN content_results c ON c.news_id = n.id
ORDER BY n.published_at DESC;
```

## 10.3 중복 기사 검사

```sql
SELECT canonical_url, COUNT(*)
FROM news
GROUP BY canonical_url
HAVING COUNT(*) > 1;
```

기대: 0행.

## 10.4 관련 뉴스 자기참조 검사

```sql
SELECT *
FROM news_relations
WHERE news_id = related_news_id;
```

기대: 0행.

## 10.5 알림 중복 검사

```sql
SELECT user_id, schedule_id, news_id, channel, COUNT(*)
FROM notification_deliveries
GROUP BY user_id, schedule_id, news_id, channel
HAVING COUNT(*) > 1;
```

기대: 0행.

---

# 11. Redis 확인 방법

Redis CLI 사용 가능 환경에서:

```powershell
redis-cli -h localhost -p 6379
```

테스트 DB 선택:

```text
SELECT 15
```

캐시 키 확인:

```text
SCAN 0 MATCH cache:news:*
```

작업 잠금:

```text
SCAN 0 MATCH lock:*
```

큐 확인:

```text
LLEN queue:jobs
```

주의: 테스트 목적이라도 운영 Redis에 `KEYS *`를 사용하지 않는다.

---

# 12. Scheduler / Worker 테스트 방법

## 12.1 예약 생성

설정 화면 또는 API로 1~2분 뒤 실행되는 예약을 만든다.

## 12.2 Scheduler 로그 확인

```powershell
docker compose logs -f scheduler
```

확인:
- 예약 시각 평가
- dedupe key 생성
- 동일 작업 중복 등록 없음

## 12.3 Worker 로그 확인

```powershell
docker compose logs -f worker
```

확인:

```text
QUEUED
 → RUNNING
 → COLLECT
 → NORMALIZE
 → AI PROCESS
 → VALIDATE
 → DB SAVE
 → CACHE INVALIDATE
 → SUCCEEDED
```

## 12.4 DB 상태 확인

```sql
SELECT id, kind, status, scheduled_at, started_at, finished_at
FROM jobs
ORDER BY scheduled_at DESC;
```

```sql
SELECT job_id, step, attempt_no, error_code
FROM job_attempts
ORDER BY created_at DESC;
```

---

# 13. 장애 테스트 방법

## 13.1 Redis 중단

```powershell
docker compose stop redis
```

확인:
- 저장된 뉴스 조회가 가능한지
- API 전체가 종료되지 않는지
- 캐시 오류가 내부 오류 그대로 화면에 노출되지 않는지

복구:

```powershell
docker compose start redis
```

## 13.2 Fake LLM 오류

Fake LLM을 500 응답 모드로 전환한다.

기대:
- 해당 작업은 실패 상태 기록
- 기존 READY 기사 조회 가능
- 화면 요청이 LLM 응답을 기다리지 않음

## 13.3 출처 서버 장애

Fixture source server를 중지한다.

```powershell
docker compose stop fixture-source
```

기대:
- 출처 실패 기록
- 다른 출처의 정상 결과 유지
- 메인 화면에 저장된 기사 표시 가능

## 13.4 SMTP 장애

Fake SMTP를 중지하고 알림 작업 실행.

기대:
- notification delivery FAILED 기록
- 뉴스 처리 성공은 유지

---

# 14. 브라우저 반응형 테스트

## 14.1 Desktop

Chrome DevTools에서:

```text
1440 × 900
```

확인:
- 좌측 sidebar
- 카드 가로 레이아웃
- 상세 2열
- 설정 메뉴 + 설정 본문

## 14.2 Mobile

DevTools Device Toolbar:

```text
390 × 844
```

확인:
- sidebar 숨김
- 하단 navigation 표시
- 뉴스 카드 한 열
- 상세 패널 한 열
- 설정 입력 한 열
- 가로 scroll 없음

브라우저 Console:

```javascript
document.documentElement.scrollWidth <= document.documentElement.clientWidth
```

기대: `true`.

---

# 15. 접근성 테스트 방법

키보드만 사용한다.

1. 페이지 새로고침
2. `Tab` 반복
3. 검색 입력 이동
4. 검색 실행
5. 카드 상세 보기 이동
6. 상세 화면 버튼 이동
7. 설정 이동
8. 모든 입력과 버튼 접근 확인

검증 항목:

- 포커스가 보인다.
- 버튼 이름이 의미 있다.
- 아이콘만 있는 버튼도 접근 가능한 이름이 있다.
- 상태를 색상만으로 표현하지 않는다.
- Enter 또는 Space로 동작한다.
- modal이 있다면 포커스가 빠져나가지 않는다.

---

# 16. 보안 테스트 방법

## 16.1 IDOR

USER-A로 로그인 후 USER-B의 schedule ID를 요청한다.

기대:
- 403 또는 정보 은닉 404
- USER-B 데이터 노출 없음

## 16.2 위험 URL

수집 테스트 fixture에 다음 URL을 넣는다.

```text
http://127.0.0.1/admin
http://169.254.169.254/
file:///etc/passwd
javascript:alert(1)
```

기대:
- 수집/노출 거부

## 16.3 과도한 입력

검색·키워드·설정 입력에 길이 제한 이상의 값을 전송한다.

기대:
- 422
- 서버 500 없음

## 16.4 SQL/XSS 유사 입력

```text
' OR 1=1 --
<script>alert(1)</script>
```

기대:
- 데이터로 처리
- SQL 실행 또는 script 실행 없음

---

# 17. 전체 통합 시나리오 실행

최종 통합 테스트에서는 다음 순서로 실행한다.

```text
1. 회원가입 또는 로그인
2. 메인 화면 진입
3. 랭킹 카드 표시 확인
4. OpenAI 검색
5. 검색 초기화
6. 최신순 변경
7. 상세보기 진입
8. AI 3줄 요약 확인
9. 한국어 번역 확인
10. 원본 정보 확인
11. 관련 뉴스 확인
12. 원문 새 탭 열기
13. 링크 복사
14. 설정 화면 이동
15. 예약 시각 변경
16. 관심 키워드 변경
17. 기본 노출 수 5 또는 10 선택
18. 인앱/메일 알림 변경
19. 설정 저장
20. 페이지 새로고침
21. 저장값 복원 확인
22. DB에서 설정값 확인
23. Scheduler 작업 확인
24. Worker 처리 확인
25. 신규 READY 뉴스가 메인에 반영되는지 확인
26. 로그아웃
27. 보호 API 접근 차단 확인
```

이 흐름이 모두 통과하면 단계 1 핵심 사용자 흐름은 통합 관점에서 합격으로 판단할 수 있다.

---

# 18. 테스트 결과 기록 방법

모든 테스트는 다음 형식으로 결과를 남긴다.

| 항목 | 예시 |
|---|---|
| Test ID | IT-HOME-001 |
| 실행일 | 2026-11-06 |
| 실행자 | 홍길동 |
| 환경 | Windows 11 / Chrome / test |
| Build/Commit | abc1234 |
| 결과 | PASS / FAIL / BLOCKED |
| 실제 결과 | READY 뉴스 3건 정상 표시 |
| 기대 결과 | 랭킹 카드 정상 표시 |
| 증거 | screenshot, pytest log, DB query |
| Defect ID | BUG-014 |
| 비고 | Redis 중단 후 DB fallback 확인 |

---

# 19. 실패 시 처리 절차

테스트가 실패하면 다음 순서로 처리한다.

```text
실패 발견
  ↓
테스트 데이터 문제인지 확인
  ↓
재현 가능 여부 확인
  ↓
로그/스크린샷/응답/DB 상태 수집
  ↓
결함 등록
  ↓
개발 수정
  ↓
실패 케이스 단독 재실행
  ↓
연관 회귀 테스트 실행
  ↓
PASS 확인 후 종료
```

결함 기록 시 최소 포함 정보:

- 테스트 ID
- 재현 단계
- 기대 결과
- 실제 결과
- HTTP request/response
- request_id
- 관련 DB row
- 관련 로그 시각
- 스크린샷
- 발생 빈도

---

# 20. 최종 합격 기준

단계 1 테스트 완료 조건은 다음과 같다.

- 단위 테스트 전체 PASS
- API 계약 테스트 PASS
- 메인 화면 정상/검색/빈/부분 실패/오류 상태 PASS
- 상세보기 정상/원문/복사/관련 뉴스 PASS
- 설정 조회/저장/취소/복원 PASS
- 예약/Worker/AI 처리 흐름 PASS
- DB 무결성 검사 PASS
- 중복 캐시/작업/알림 방지 PASS
- 모바일/데스크톱 PASS
- 키보드 접근성 PASS
- IDOR/SSRF/위험 URL/과도 입력 차단 PASS
- 외부 의존성 장애 시 저장 결과 열람 유지
- P0/P1 미해결 결함 0건

---

# 21. 테스트 실행 체크리스트

## 자동 테스트

- [ ] ruff check 통과
- [ ] ruff format --check 통과
- [ ] pyright 통과
- [ ] unit test 통과
- [ ] integration test 통과
- [ ] API contract test 통과

## 화면

- [ ] 메인 화면
- [ ] 검색
- [ ] 필터
- [ ] 정렬
- [ ] 상세보기
- [ ] 원문 새 탭
- [ ] 링크 복사
- [ ] 설정
- [ ] 예약
- [ ] 관심 키워드
- [ ] 노출 수
- [ ] 알림
- [ ] 계정 정책

## 데이터/인프라

- [ ] DB 저장값
- [ ] FK/Unique 제약
- [ ] Redis cache
- [ ] Redis lock
- [ ] Scheduler
- [ ] Worker
- [ ] notification delivery

## 장애/보안

- [ ] Redis 장애
- [ ] Source 장애
- [ ] LLM 장애
- [ ] SMTP 장애
- [ ] IDOR
- [ ] SSRF
- [ ] XSS 유사 입력
- [ ] SQL injection 유사 입력
- [ ] 과도 입력

