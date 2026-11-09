# DAIT 통합 테스트 케이스

| 항목 | 값 |
|---|---|
| 문서 버전 | 1.0.1 |
| 기준일 | 2026-11-06 |
| 대상 | 메인·상세보기·설정 + API + DB + Redis + Worker + Scheduler |
| 테스트 수준 | Integration / E2E-like Integration |
| 기준 | 화면설계서/API/DB/기능설계 v1.0.1 |

## 1. 목적

단위 테스트를 통과한 구성 요소들이 실제 연결 상태에서 계약대로 동작하는지 검증한다. 특히 단계 1 MVP의 핵심 경로인 **로그인 → 메인 → 검색/필터 → 상세 → 원문 → 설정 조회/저장/복원 → 예약 실행 → 알림 → 로그아웃** 흐름을 중심으로 한다.

## 2. 통합 범위

- Browser/Web ↔ FastAPI
- API ↔ PostgreSQL/SQLite
- API ↔ Redis cache
- Scheduler ↔ Redis queue/lock
- Worker ↔ Collector fixture server
- Worker ↔ Fake LLM server
- Worker ↔ DB ↔ cache invalidation
- Settings ↔ schedules ↔ notifications

실제 공개 인터넷 뉴스/LLM/SMTP는 기본 CI 통합 테스트에서는 fake server를 사용한다. 별도 수동 검증에서만 승인된 실제 서비스 smoke test를 수행할 수 있다.

## 3. 테스트 환경 데이터 기준

- 사용자 A/B 2명
- 승인 출처 2개 + 실패 출처 1개
- READY 기사 3건
- INSUFFICIENT 1건
- FAILED 1건
- USER-A 설정: 10개, AI, 인앱 on, 메일 off
- USER-A 예약: 08:30 Asia/Seoul

## 4. 인증→메인 통합

### IT-AUTH-HOME-001 가입 후 메인 진입
**선행조건** DB empty

**절차**
1. POST `/v1/auth/signup`
2. 생성된 session으로 GET `/v1/news`
3. users/refresh_sessions 확인

**기대**
- 201 signup
- 세션 존재
- GET news 200
- password 원문 DB 없음

### IT-AUTH-HOME-002 로그인 후 저장 뉴스 조회
1. 기존 user login
2. GET news
3. Redis miss
4. DB 조회
5. Redis cache 생성

기대: 응답과 DB 기사 일치, cache key 생성.

### IT-AUTH-003 로그아웃 후 보호 설정 API 접근
- logout 204
- GET `/v1/me/settings` → 401

## 5. 메인 화면 통합

### IT-HOME-001 메인 3건 표시
**DB** READY 3건
**기대** 화면/API items 3, rank 1~3, source/summary/status/actions 모두 표시 가능

### IT-HOME-002 최대 10건
- READY 12건 seed
- 기대 첫 화면 최대 10, cursor 정책 일치

### IT-HOME-003 랭킹순
- 품질/시각/source priority seed
- API 및 화면 순서 일치

### IT-HOME-004 최신순
- `sort=latest`
- published_at 역순

### IT-HOME-005 검색 제목
- q=OpenAI
- OpenAI 기사만

### IT-HOME-006 검색 요약
- 제목에는 없고 요약에만 있는 keyword
- 해당 기사 반환

### IT-HOME-007 검색 없음→초기화
- 0건 상태 표시
- 초기화 후 원 목록 복구

### IT-HOME-008 일부 출처 실패
- collector 한 출처 실패 seed
- 정상 카드 유지 + partial 안내

### IT-HOME-009 Redis 장애
- Redis stop/unavailable
- DB fallback으로 목록 200
- 캐시 장애가 사용자 요청 전체를 실패시키지 않음

### IT-HOME-010 캐시 무효화
1. 목록 호출하여 cache 생성
2. worker가 새 READY 기사 저장
3. 목록 cache invalidate
4. 재호출
- 새 기사 포함

## 6. 메인→상세 통합

### IT-DETAIL-001 카드 상세보기
1. GET news
2. 첫 item id 추출
3. GET `/v1/news/{id}`
- 목록 카드 title/source와 상세 article 일치

### IT-DETAIL-002 상세 모든 패널
- 기사 헤더
- AI 3줄 요약 3개
- 한국어 번역
- 처리 정보
- 원본 정보
- 관련 뉴스
모두 response와 화면 매핑 일치

### IT-DETAIL-003 관련 뉴스 클릭
- related news id가 상세 API에서 유효
- 자기 자신 아님

### IT-DETAIL-004 404
- NEWS-404 조회
- 404 + 일반화 오류
- 내부 DB key/stack 미노출

### IT-DETAIL-005 INSUFFICIENT
- 내용 부족 기사 상세
- READY UI처럼 오인되지 않는 상태

### IT-DETAIL-006 원문 HTTPS
- 원문 버튼 URL이 DB canonical_url과 일치
- https만

### IT-DETAIL-007 링크 복사
- browser Clipboard 성공/거부 두 경로
- 거부 시 대체 URL 표시

## 7. 설정 조회/저장/복원 통합

### IT-SET-001 설정 화면 최초 조회
1. login USER-A
2. GET `/v1/me/settings`
3. DB user_settings 비교
- 화면 값 일치

### IT-SET-002 관심 키워드 저장
1. keywords 변경
2. PATCH settings
3. DB 확인
4. GET 재조회
5. 화면 재진입
- 정규화 값 동일하게 복원

### IT-SET-003 출처/카테고리 저장
- 승인 source만 허용
- 미승인 source는 422/도메인 오류
- DB 변경 없음

### IT-SET-004 기본 노출 수 5
- PATCH 5
- 메인 재진입 시 화면 기본 노출 정책에 적용

### IT-SET-005 기본 노출 수 10
- 동일

### IT-SET-006 인앱/메일 토글
- 4가지 조합 저장/재조회

### IT-SET-007 변경 취소
- UI 변경 후 취소
- PATCH 미호출
- DB 변화 없음

### IT-SET-008 사용자 격리
- USER-A token으로 USER-B 설정 접근/변경 불가

## 8. 예약 수집 통합

### IT-SCH-001 예약 생성
1. POST `/v1/me/schedules` 08:30 Asia/Seoul
2. DB schedules 확인
3. next_run_at 계산 확인
4. GET schedules 복원

### IT-SCH-002 예약 수정
- 09:00로 변경
- next_run_at 갱신

### IT-SCH-003 예약 비활성화
- enabled=false
- scheduler가 queue에 등록하지 않음

### IT-SCH-004 예약 삭제
- DELETE 204
- 재조회에서 없음

### IT-SCH-005 소유권
- USER-A가 SCHEDULE-B update/delete 불가

### IT-SCH-006 중복 실행 방지
1. 동일 실행 window로 scheduler 두 번 호출
2. Redis lock/dedupe
3. jobs row 수 확인
- 1건만

## 9. 수집→AI→DB→메인 통합

### IT-PIPE-001 정상 파이프라인
1. scheduler 또는 관리 명령 job 생성
2. worker가 승인 fixture source 수집
3. news 저장
4. fake LLM 번역/3줄 요약
5. content_results READY
6. ranking/relation 생성
7. cache invalidate
8. GET news
- 신규 카드 표시

### IT-PIPE-002 중복 기사
- 같은 canonical_url 두 번 수집
- news 1건 유지
- 불필요 AI 재호출 없음

### IT-PIPE-003 본문 부족
- LLM 호출 없음
- INSUFFICIENT 저장
- 메인 READY 목록에서 제외/정책대로 표시

### IT-PIPE-004 LLM JSON 오류
- attempt FAILED
- 다른 READY 기사 조회 계속 정상

### IT-PIPE-005 출처 하나 500
- 해당 source 실패 기록
- 다른 source 기사 처리 계속
- 메인 partial 상태

### IT-PIPE-006 SSRF redirect
- fixture server가 private IP로 redirect
- worker 차단
- DB에 위험 content 저장 없음

## 10. 설정→예약→알림 통합

### IT-NOTI-001 인앱 ON / 메일 OFF
1. settings 저장
2. schedule 실행
3. 뉴스 처리 성공
4. notification delivery 생성
- IN_APP 1건, EMAIL 0건

### IT-NOTI-002 인앱 ON / 메일 ON
- 채널별 1건

### IT-NOTI-003 중복 전달 방지
- 동일 결과 notify 두 번 호출
- 각 channel 1건 유지

### IT-NOTI-004 SMTP 실패
- email delivery FAILED
- news READY 유지
- 인앱 성공 유지

## 11. DB 관계/무결성 통합 테스트

### IT-DB-001 user 삭제 정책
- 사용자 설정/예약/세션 정리
- shared news 유지

### IT-DB-002 source 삭제/비활성 정책
- 운영 정책대로 FK/비활성화 처리
- orphan news 금지

### IT-DB-003 content_results 1:1
- 동일 news 두 결과 중복 삽입 거부

### IT-DB-004 news_relation 자기 관계 차단
- 서비스/constraint 정책 검증

### IT-DB-005 notification dedupe unique
- 중복 insert 방지

## 12. 오류/복구 통합 테스트

### IT-ERR-001 API validation 422
- extra field 포함 request
- 422 + fields

### IT-ERR-002 DB down
- `/readyz` 실패
- `/healthz`는 process 살아있으면 성공 정책

### IT-ERR-003 Redis down
- 저장 결과 조회는 계속 제공

### IT-ERR-004 LLM down
- 기존 READY 뉴스 조회 정상
- 신규 processing 실패만 기록

### IT-ERR-005 Collector down
- 기존 뉴스 조회 정상

### IT-ERR-006 retry→success
- 첫 시도 실패, 두 번째 성공
- attempt history 2건

### IT-ERR-007 max retry→DEAD_LETTER
- 무한 재시도 없음

## 13. 반응형/화면 통합 테스트

### IT-UI-001 Desktop 1440×900 메인
- sidebar, header, search, chips, sort, cards 겹침 없음

### IT-UI-002 Mobile 390×844 메인
- sidebar 숨김
- bottom tabs 표시
- card single column
- horizontal overflow 0

### IT-UI-003 Desktop 상세
- content + side panel 2열

### IT-UI-004 Mobile 상세
- 한 열 적층

### IT-UI-005 Desktop 설정
- settings menu + cards 정상

### IT-UI-006 Mobile 설정
- 설정 메뉴 horizontal
- form fields 한 열

### IT-UI-007 키보드 흐름
- 로그인→검색→카드→상세→원문→설정→저장→로그아웃
- mouse 없이 수행

### IT-UI-008 접근성 이름
- icon button, search, toggle, mobile tabs accessible name

## 14. 보안 통합 테스트

### IT-SEC-001 IDOR settings
### IT-SEC-002 IDOR schedules
### IT-SEC-003 SQL injection-like search
### IT-SEC-004 XSS-like title/source fixture output escape
### IT-SEC-005 SSRF private IP
### IT-SEC-006 token reuse
### IT-SEC-007 rate limit login/signup
### IT-SEC-008 release docs/openapi 비노출
### IT-SEC-009 오류 응답 stack trace 비노출
### IT-SEC-010 로그 token/password/email 원문 비노출

## 15. 핵심 시연 시나리오 통합 테스트

### IT-DEMO-001 전체 MVP 정상 시나리오
1. 회원가입 또는 로그인
2. 메인 진입
3. 랭킹 카드 3건 확인
4. `OpenAI` 검색
5. 검색 초기화
6. `랭킹순 → 최신순` 전환
7. 기사 상세 진입
8. 3줄 요약 확인
9. 한국어 번역 확인
10. 원본 정보/관련 뉴스 확인
11. 원문 새 탭
12. 링크 복사
13. 설정 진입
14. 예약 08:30→09:00 변경
15. 관심 키워드 추가
16. 기본 노출 5 변경
17. 인앱 ON / 메일 ON
18. 설정 저장
19. 화면 재진입 후 값 복원 확인
20. 로그아웃

**최종 기대**: 사용자에게 보이는 모든 값이 API/DB 상태와 일치하고 오류 없음.

## 16. 통합 테스트 완료 기준

- IT-DEMO-001 PASS
- P0/P1 integration 실패 0
- 메인/상세/설정 desktop/mobile PASS
- DB/Redis 장애 복구 정책 PASS
- 중복 작업/중복 알림 0
- IDOR/SSRF/token reuse 차단 PASS
- 기존 READY 기사 조회는 외부 LLM/collector 장애 시 유지
- 설정 저장 후 재로그인/재진입 복원 PASS
