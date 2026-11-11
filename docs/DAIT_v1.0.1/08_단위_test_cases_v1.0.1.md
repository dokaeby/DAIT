# DAIT 단위 테스트 케이스

| 항목 | 값 |
|---|---|
| 문서 버전 | 1.0.1 |
| 기준일 | 2026-11-06 |
| 대상 | 단계 1 MVP 전체 기능 |
| 기준 화면 | 메인 / 상세보기 / 설정 |
| 기준 문서 | 01~07 v1.0.1 문서, 화면설계서 v1.0.1 |
| 테스트 수준 | Unit Test |
| 기본 도구 | pytest, pytest-asyncio, FastAPI TestClient/httpx, unittest.mock |

## 1. 목적

이 문서는 DAIT 단계 1 MVP를 구성하는 화면 로직, API 경계 검증, 서비스 규칙, 저장소, 인증, 뉴스 수집, AI 번역·3줄 요약, 랭킹·관련 뉴스, 설정·예약, 캐시·재처리 로직을 독립적으로 검증하기 위한 단위 테스트 케이스를 정의한다.

단위 테스트는 외부 네트워크, 실제 SMTP, 실제 LLM, 실제 뉴스 사이트에 의존하지 않는다. DB·Redis·LLM·수집기는 fake 또는 mock으로 대체하고, 한 테스트가 하나의 규칙만 명확히 검증하도록 한다.

## 2. 공통 판정 규칙

- 모든 테스트는 독립 실행 가능해야 한다.
- 테스트 순서에 의존하지 않는다.
- 시간 의존 로직은 고정 시각 또는 fake clock을 사용한다.
- UUID/opaque ID는 고정 fixture를 사용한다.
- 실패 응답에 stack trace, password, token, email 원문, 내부 SQL이 포함되면 실패다.
- API 모델은 `extra="forbid"` 정책을 검증한다.
- 화면 상태는 색상만이 아니라 텍스트/아이콘 의미가 함께 존재해야 한다.
- 설정 화면은 단계 1 MVP이며 저장 후 재조회 시 동일 값이 복원되어야 한다.

## 3. 공통 테스트 데이터

| 데이터 ID | 값 | 용도 |
|---|---|---|
| USER-A | `usr_test_a` / `usera@example.com` | 정상 사용자 |
| USER-B | `usr_test_b` / `userb@example.com` | 소유권 차단 검증 |
| NEWS-1 | `news_openai_001` | READY 영문 기사 |
| NEWS-2 | `news_anthropic_002` | READY 영문 기사 |
| NEWS-3 | `news_github_003` | PARTIAL 표기 예시 |
| NEWS-404 | `news_missing_999` | 존재하지 않는 기사 |
| SOURCE-1 | `src_openai` | 승인 출처 |
| SOURCE-BLOCKED | `src_unknown` | 미승인 출처 |
| SCHEDULE-A | `sch_usera_0830` | USER-A 예약 |
| SCHEDULE-B | `sch_userb_0900` | USER-B 예약 |

## 4. 인증 단위 테스트

### UT-AUTH-001 회원가입 정상
- 관련 기능: FR-AUTH-01
- 대상: signup service/schema
- 입력: 유효 이메일, 강한 비밀번호, confirm 일치, 약관 true
- Mock: user repository `email_exists=False`
- 절차:
  1. request model 생성
  2. signup service 호출
  3. repository 호출 인자 캡처
- 기대결과:
  - 사용자 1건 생성
  - 비밀번호 평문 저장 없음
  - `password_hash != password`
  - status `ACTIVE`
  - 최초 세션 생성 1회
- 실패 조건: 평문 비밀번호가 repository/log 인자에 남음

### UT-AUTH-002 이메일 형식 오류
- 입력: `abc`, `@example.com`, 255자 초과
- 기대: Pydantic validation error / 422 매핑 가능 형태

### UT-AUTH-003 비밀번호 확인 불일치
- 입력: password와 password_confirm 상이
- 기대: 사용자 생성 호출 0회

### UT-AUTH-004 약관 미동의
- 입력: `terms_accepted=false`
- 기대: validation error, 세션 생성 0회

### UT-AUTH-005 중복 이메일 일반화
- Mock: unique violation 또는 email_exists true
- 기대: 외부 메시지에서 계정 존재 여부를 과도하게 노출하지 않음

### UT-AUTH-006 로그인 정상
- 관련 기능: FR-AUTH-03
- 기대: 비밀번호 검증 성공, access/refresh 생성, refresh 원문 DB 저장 금지

### UT-AUTH-007 로그인 실패 메시지 동일성
- Case A: 없는 이메일
- Case B: 잘못된 비밀번호
- 기대: 사용자 노출 메시지/코드가 동일 정책

### UT-AUTH-008 refresh 회전
- 기존 refresh hash 존재
- 기대: 기존 세션 revoked, 새 token hash 저장, family 유지

### UT-AUTH-009 폐기 refresh 재사용
- 기대: family 전체 revoke

### UT-AUTH-010 로그아웃
- 기대: 현재 세션 revoke 1회, 재호출 시 멱등 처리

### UT-AUTH-011 회원탈퇴 정상
- 관련 기능: FR-AUTH-04
- 기대: 사용자 소유 설정·예약·세션 정리, 공유 뉴스 유지

### UT-AUTH-012 회원탈퇴 재인증 실패
- 기대: 사용자 상태/데이터 변경 0건

## 5. 메인 화면 / 뉴스 목록 단위 테스트

### UT-HOME-001 READY 기사 랭킹 최대 10건
- 관련: FR-HOME-01
- 입력 fixture: READY 12건
- 기대: 10건 이하, rank 1..N, 실패 기사 제외

### UT-HOME-002 실제 기사 3건만 존재
- 기대: 3건만 반환, 더미 기사 생성 금지

### UT-HOME-003 카드 필수 필드 매핑
- 기대 각 item:
  - `id`, `rank`, `title`, `source_name`, `published_at`, `category`
  - 정확히 3개의 `summary_lines`
  - `processing_status`, `original_url`

### UT-HOME-004 긴 제목 처리용 데이터 보존
- service 결과에서 원문 제목 전체가 유지되어야 함
- UI truncation은 화면 계층 책임

### UT-HOME-005 랭킹 결정성
- 동일 입력을 10회 호출
- 기대 순서 항상 동일

### UT-HOME-006 최신순 정렬
- `sort=latest`
- 기대 `published_at DESC`

### UT-HOME-007 랭킹순 정렬
- `sort=rank`
- 기대 품질 > 최신성 > source priority > stable id 순

### UT-HOME-008 카테고리 AI 허용
- `category=AI` 정상

### UT-HOME-009 미지원 카테고리 거부
- 예: `POLITICS`
- 기대 validation error

### UT-HOME-010 page_size 경계
- 1, 10, 50 정상
- 0, 51 거부

### UT-HOME-011 cursor 정상/오류
- 정상 opaque cursor는 다음 페이지
- 변조/잘못된 cursor는 일반화 validation error

### UT-HOME-012 부분 출처 실패
- 정상 기사 + source error fixture
- 기대 정상 기사 유지, `meta.partial=true`

## 6. 검색·필터 단위 테스트

### UT-SEARCH-001 제목 검색
- q=`OpenAI`
- 기대 제목 일치 기사 반환

### UT-SEARCH-002 요약 검색
- q가 summary_lines에만 존재
- 기대 기사 반환

### UT-SEARCH-003 대소문자 비구분
- `openai`, `OpenAI` 결과 동일

### UT-SEARCH-004 앞뒤 공백 제거
- `  OpenAI  ` 결과가 `OpenAI`와 동일

### UT-SEARCH-005 빈 문자열은 전체 목록
- q=`   `
- 기대 검색 미적용

### UT-SEARCH-006 불일치
- 기대 items=[]이며 오류 코드 아님

### UT-SEARCH-007 과도한 검색어 길이
- 100자 정책 초과
- 기대 validation error

### UT-SEARCH-008 HTML/script 입력
- 입력 `<script>alert(1)</script>`
- 기대 서버가 텍스트로 취급하고 SQL/HTML 실행 없음

### UT-SEARCH-009 초기화 상태 reducer/UI 함수
- 검색어, 강조, 결과, cursor를 초기값으로 복원

### UT-SEARCH-010 필터/정렬 상태 유지
- 전체/AI·기술 필터 + rank/latest 조합
- 기대 허용된 query만 생성

## 7. 메인 화면 상태 단위 테스트

### UT-STATE-001 Loading
- 기대 skeleton + `뉴스를 불러오는 중` 의미 상태

### UT-STATE-002 Empty-Search
- 검색 결과 0
- 기대 `검색 결과 없음` + 초기화 행동

### UT-STATE-003 Empty-NoData
- 저장 기사 0
- 기대 `아직 수집된 기사 없음`으로 검색 Empty와 구분

### UT-STATE-004 Partial
- 정상 카드 유지 + 일부 출처 지연/실패 비차단 안내

### UT-STATE-005 Error 500
- 일반화 메시지 + request_id + 재시도

### UT-STATE-006 Offline
- 저장된 화면 유지 + 연결 확인 안내

### UT-STATE-007 Retry lock
- 재시도 진행 중 중복 클릭 시 두 번째 요청 미발행

## 8. 상세보기 단위 테스트

### UT-DETAIL-001 READY 상세 응답 매핑
- 관련: FR-DETAIL-01
- 기대 원본 정보 → 3줄 요약 → 한국어 번역 → 관련 뉴스 데이터 모두 존재

### UT-DETAIL-002 정확히 3줄 요약
- 2줄/4줄이면 READY로 취급 금지

### UT-DETAIL-003 영문 원문 번역 표시
- translated_text 존재

### UT-DETAIL-004 한국어 원문
- 불필요 번역을 생성하지 않거나 정책에 맞게 원문 사용

### UT-DETAIL-005 관련 뉴스 0건
- 기대 빈 배열, 상세 자체는 정상

### UT-DETAIL-006 자기 자신 관계 제외
- `news_id == related_news_id` 제거

### UT-DETAIL-007 실패/비공개 관련 뉴스 제외

### UT-DETAIL-008 존재하지 않는 ID
- 기대 NEWS_NOT_FOUND

### UT-DETAIL-009 INSUFFICIENT 상태
- 기대 요약/번역을 정상 READY처럼 표시하지 않음

### UT-DETAIL-010 FAILED 상태
- 공개 가능한 일반화 오류만 응답

## 9. 원문 열기·링크 복사 단위 테스트

### UT-LINK-001 HTTPS URL 허용
- `https://openai.com/...` 허용

### UT-LINK-002 HTTP/JS/file 위험 scheme 거부
- `http://`, `javascript:`, `file:` 거부 또는 미노출

### UT-LINK-003 새 탭 속성 생성
- 기대 `noopener noreferrer`

### UT-LINK-004 Clipboard 성공 상태
- 기대 `복사 완료` 텍스트

### UT-LINK-005 Clipboard 거부
- 기대 선택 가능한 URL 대체 UI

## 10. 설정 화면 단위 테스트

### UT-SET-001 설정 기본 조회
- 관련: FR-SET-02/03
- 기대 `default_count`, categories, keywords, source_ids, in_app_notice, email_notice 반환

### UT-SET-002 default_count 허용값
- 5, 10 허용
- 0, 1, 20 거부

### UT-SET-003 관심 키워드 정상화
- 앞뒤 공백 제거, 중복 제거, 제어문자 거부

### UT-SET-004 미승인 출처 거부
- source_ids에 SOURCE-BLOCKED
- 기대 validation/domain error

### UT-SET-005 미지원 카테고리 거부
- MVP에서 `AI` 외 거부

### UT-SET-006 인앱 알림 독립 토글
- true/false 모두 저장 가능

### UT-SET-007 이메일 알림 독립 토글
- true/false 모두 저장 가능

### UT-SET-008 설정 저장 후 정규화 응답
- repository 저장 값과 response 동일

### UT-SET-009 변경 취소 UI 상태
- 서버 PATCH 호출 없이 마지막 저장값으로 복원

### UT-SET-010 계정 정책 진입
- 개인정보 안내/회원탈퇴 행동 연결 정보 존재

## 11. 예약 수집 단위 테스트

### UT-SCH-001 예약 생성 정상
- 관련: FR-SET-01
- local_time `08:30`, timezone `Asia/Seoul`, enabled true
- 기대 next_run_at UTC 계산

### UT-SCH-002 잘못된 timezone
- `Asia/Seooul` 거부

### UT-SCH-003 예약 비활성화
- enabled false 저장, scheduler 대상 제외

### UT-SCH-004 사용자 소유권
- USER-A가 SCHEDULE-B 수정 시 not found/authorization 정책

### UT-SCH-005 DST 경계
- DST 사용 timezone fixture로 중복/누락 시각 정책 검증

### UT-SCH-006 dedupe key 결정성
- 같은 user/schedule/window에서 동일 key

### UT-SCH-007 중복 작업 등록 방지
- lock 획득 실패 시 queue push 0회

### UT-SCH-008 다음 실행 갱신
- 실행 완료 후 다음 next_run_at 계산

## 12. 알림 단위 테스트

### UT-NOTI-001 인앱 켜짐/메일 꺼짐
- 기대 인앱 전달 1건, SMTP 0회

### UT-NOTI-002 인앱/메일 모두 켜짐
- 각 채널 1회

### UT-NOTI-003 dedupe
- 동일 `(user,schedule,news,channel)` 재호출 시 2차 전달 생략

### UT-NOTI-004 SMTP 실패
- 뉴스 처리 성공 상태 rollback 금지
- notification status FAILED 기록

## 13. 뉴스 수집 단위 테스트

### UT-COL-001 승인 출처 수집
- 관련: FR-PIPE-01
- HTTPS 승인 host만 요청

### UT-COL-002 미승인 출처 차단

### UT-COL-003 사설 IP 차단
- 127.0.0.1, 10/8, 192.168/16 등

### UT-COL-004 redirect 후 재검증
- public → private redirect 차단

### UT-COL-005 MIME 제한
- HTML/RSS/API 정책 외 MIME 거부

### UT-COL-006 응답 크기 제한
- 상한 초과 즉시 실패

### UT-COL-007 canonical URL 중복
- 신규 저장 0건, 기존 기사 재사용

### UT-COL-008 한 출처 실패가 전체 실패로 전파되지 않음

## 14. AI 번역·3줄 요약 단위 테스트

### UT-AI-001 영문 정상 처리
- 관련: FR-PIPE-02
- LLM fake가 translated_text + 3 summary_lines 반환
- 기대 READY

### UT-AI-002 한국어 기사 번역 생략

### UT-AI-003 본문 부족
- LLM 호출 0회, INSUFFICIENT

### UT-AI-004 malformed JSON
- FAILED, attempt 기록

### UT-AI-005 summary 2줄
- 검증 실패

### UT-AI-006 summary 4줄
- 검증 실패

### UT-AI-007 수치 변형
- 원문 `42%`, 요약 `24%`
- READY 금지

### UT-AI-008 고유명사 변형
- 검증 정책에 따라 실패

### UT-AI-009 동일 content_hash/version/model
- LLM 재호출 0회

### UT-AI-010 개인정보 미전송
- LLM mock 호출 payload에 user email/settings/token 없음

## 15. 랭킹·관련 뉴스 단위 테스트

### UT-RANK-001 READY 우선
### UT-RANK-002 최신성 우선
### UT-RANK-003 source priority 동률 처리
### UT-RANK-004 stable ID 최종 tie-breaker
### UT-RANK-005 없는 조회수/급등률 사용 금지
### UT-REL-001 같은 카테고리 후보만
### UT-REL-002 자기 자신 제외
### UT-REL-003 중복 pair 제외
### UT-REL-004 실패 기사 제외
### UT-REL-005 reason/score 저장

## 16. 캐시·재처리 단위 테스트

### UT-CACHE-001 목록 cache hit
- DB 조회 0회

### UT-CACHE-002 목록 cache miss
- DB 조회 후 TTL 5분 저장

### UT-CACHE-003 상세 TTL 30분

### UT-CACHE-004 READY 저장 후 관련 목록 캐시 선택 무효화

### UT-CACHE-005 Redis 장애 fallback DB
- 요청 전체 실패 금지

### UT-RETRY-001 실패 단계 기록
### UT-RETRY-002 실패 단계부터 재개
### UT-RETRY-003 최대 시도 후 DEAD_LETTER
### UT-RETRY-004 같은 dedupe key 동시 실행 1건만

## 17. Repository/DB 단위 테스트

### UT-DB-001 users email unique
### UT-DB-002 news canonical_url unique
### UT-DB-003 user_settings user_id 1:1
### UT-DB-004 default_count CHECK 5/10
### UT-DB-005 content_results news_id 1:1
### UT-DB-006 schedule user scope query
### UT-DB-007 related pair unique
### UT-DB-008 notification dedupe unique
### UT-DB-009 탈퇴 시 사용자 소유 데이터 정책 적용
### UT-DB-010 공유 news는 사용자 탈퇴로 삭제되지 않음

## 18. 화면 컴포넌트/접근성 단위 테스트

### UT-UI-001 메인 헤더 로고/서비스명
### UT-UI-002 메인 검색 input accessible name
### UT-UI-003 전체/AI·기술 필터 selected 상태
### UT-UI-004 rank/latest select 상태
### UT-UI-005 뉴스 카드 상세보기 링크
### UT-UI-006 처리 상태가 텍스트로도 노출
### UT-UI-007 상세 breadcrumb
### UT-UI-008 상세 3줄 번호 목록
### UT-UI-009 설정 메뉴 4개 구역
### UT-UI-010 설정 저장/취소 버튼 accessible name
### UT-UI-011 토글 상태 accessible label
### UT-UI-012 모바일 하단 3탭 active 상태
### UT-UI-013 focus-visible 유지
### UT-UI-014 44px 이상 주요 모바일 터치 영역

## 19. 단위 테스트 추적 매트릭스

| 기능 | 대표 UT |
|---|---|
| FR-AUTH-01 | UT-AUTH-001~005 |
| FR-AUTH-03 | UT-AUTH-006~010 |
| FR-AUTH-04 | UT-AUTH-011~012 |
| FR-HOME-01 | UT-HOME-001~012 |
| FR-SEARCH-01 | UT-SEARCH-001~010 |
| FR-HOME-02 | UT-STATE-001~007 |
| FR-DETAIL-01 | UT-DETAIL-001~010 |
| FR-DETAIL-02 | UT-LINK-001~005 |
| FR-SET-01 | UT-SCH-001~008 |
| FR-SET-02 | UT-SET-001,003~005,008~009 |
| FR-SET-03 | UT-SET-002,006~010 + UT-NOTI-* |
| FR-PIPE-01 | UT-COL-* |
| FR-PIPE-02 | UT-AI-* |
| FR-PIPE-03 | UT-RANK-*, UT-REL-* |
| FR-PIPE-04 | UT-CACHE-*, UT-RETRY-* |

## 20. 단위 테스트 완료 기준

- 모든 P0/P1 단위 테스트 PASS
- flaky test 0건
- 외부 네트워크 호출 0건
- 실제 LLM/SMTP 호출 0건
- 테스트 실행 순서 의존 0건
- 실패 테스트를 skip/xfailed로 숨기지 않음
- 핵심 도메인 규칙 branch가 정상/경계/실패 사례를 보유
- 테스트 실패 시 어떤 FR/API/DB 규칙이 깨졌는지 ID로 추적 가능
