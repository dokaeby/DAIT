# 구조 전환 1단계: 현재 동작 기준 (2026-11-09)

작업 기준은 C:/DAIT_test/DAIT_ui입니다. C:/DAIT/src/backend/src/dait와 frontend/src는 목표 구조 참고 자료이며 이번 단계에서 수정하지 않았습니다.

## 보호할 범위

- 기사·회원·세션·관심사·저장 요약·번역·임베딩 색인·대기열 데이터를 보존합니다.
- 현재 로그인 방식·카테고리 정책·RSS 기반 요약·검색 유사도 표시·재시도 정책을 구조 이동과 함께 바꾸지 않습니다.
- 기존 URL은 아래 계약 목록으로 남깁니다. /v1 도입은 후속 단계이며 기존 URL의 제거를 이번 작업에 포함하지 않습니다.
- 이메일 인증 5단계와 외부 API 연결은 계속 보류합니다.

## 코드·데이터 기준

소스 52개 파일의 SHA-256, 라우트 19개, DB 6개의 해시·크기·테이블 건수와 기존 실패 테스트 ID를 로컬 .tmp/migration-baseline/baseline.json에 기록했습니다. 회원 값·세션 토큰·기사 본문 등 실제 행 내용은 기록하지 않았습니다.

이 기록은 비교용 메타데이터이며 DB 복구용 백업이 아닙니다. 데이터 수집·요약·로그인 후에는 DB 해시와 건수가 정상적으로 달라질 수 있습니다. DB별 읽기 트랜잭션 시점의 건수이며 여러 DB를 하나의 시점으로 동결한 기록도 아닙니다. 실제 DB 이동 직전에는 서버·작업자를 종료하고 별도 백업을 확보해야 합니다.

| DB | 기록 시점 테이블 건수 |
|---|---|
| data/real_articles.db | articles: 50, article_categories: 71 |
| data/users.db | users: 3, sessions: 0, interest_profiles: 3, interest_categories: 13 |
| data/summary_tests.db | summary_tests: 109 |
| data/foreign_translations.db | foreign_translations: 1 |
| data/search_index.db | embeddings: 106 |
| data/summary_queue.db | jobs: 115 |

## 기존 자동 테스트 기준

이전 실행 결과: 118개 중 106개 통과, 12개 실패. 이번 단계에서 다시 실행하지 않았습니다. [상세 결과](../testing/UNIT_TEST_RESULTS.md)를 참고합니다. 구조 이동 후 기존 통과 케이스의 새 실패와 기존 문서 차이 12개를 구분해야 합니다. 기존 실패를 추가 실패의 허용 기준으로 사용하지 않습니다.

## 보존할 URL

- POST /signup
- POST /login
- POST /logout
- GET /api/auth/me
- GET /assets/{filename}
- GET /
- GET /article/{article_id}
- GET /api/search-lab/info
- GET /api/search-lab/jobs/{job_id}
- POST /api/search-lab/jobs
- GET /api/summary/batch-status
- GET /api/summary/jobs/{job_id}
- POST /api/summary/batch
- POST /api/summary/jobs
- GET /interests
- GET /api/interests
- PUT /api/interests
- POST /api/interests/skip
- GET /settings

## 사용자가 직접 확인할 체크리스트

서버를 평소 명령으로 실행하고 브라우저에서 Ctrl+F5로 새로고침합니다. 성공하지 않은 항목은 실패 또는 미실행으로 남깁니다.

| ID | 확인 항목 | 기대 | 사용자 결과 |
|---|---|---|---|
| B01 | 비로그인 메인 | 최신 기사·저장 요약 표시 | 대기 |
| B02 | 기존 회원 로그인 | 로그인 유지, 기존 회원·관심사 보존 | 대기 |
| B03 | 동일 계정 재로그인 | 이미 로그인 안내, 팝업 유지 | 대기 |
| B04 | 계정 전환·로그아웃 | 계정별 관심사·목록 정상, 타 계정과 혼합 없음 | 대기 |
| B05 | 미설정 관심사 화면 | 로그인 직후 안내, 메뉴·다음에 하기로 자유 이동 | 대기 |
| B06 | 관심사 저장 | 저장 후 맞춤 목록 반영, 재로그인 후 유지 | 대기 |
| B07 | 검색·필터·정렬 | 기존 검색 결과·실제 유사도 표시, 초기화 정상 | 대기 |
| B08 | 상세 팝업 | 메인과 같은 요약, 원문 링크·복사·닫기·Esc | 대기 |
| B09 | 팝업 스크롤 | 팝업 끝에서 배경 화면 스크롤로 이어지지 않음 | 대기 |
| B10 | 미완료 팝업 | 대기·처리 상태와 생성 결과 자동 갱신 | 대기 |
| B11 | 최종 실패 국내 기사 | 다시 시도 후 정상 생성 시 메인·팝업 일치 | 대기 |
| B12 | 새 기사 수집 | 필요한 기사만 자동 처리, 정상 저장 결과 재사용 | 대기 |
| B13 | 설정 접근 | 게스트 비노출·접근 제한, 로그인 후 /settings 이동 | 대기 |
| B14 | 서버 재시작 | 회원·관심사·저장 요약 유지 | 대기 |

새 기사가 없거나 실패 기사가 없으면 B10~B12 일부는 미실행으로 기록해도 됩니다. 테스트 때문에 기존 정상 요약을 삭제하거나 DB를 초기화하지 않습니다. B13은 화면 접근만 검증하며 아직 연결되지 않은 설정 저장·예약·알림을 성공으로 기록하지 않습니다.

## 단계 완료 조건

사용자 확인 결과와 남은 미실행 항목을 기록한 뒤, 명시적인 다음 단계 요청을 받아 패키지·설정·저장소 이동을 시작합니다. 이번 단계에서는 업무 코드·DB·기존 실행 명령을 변경하지 않았고 서버·브라우저·테스트를 실행하지 않았습니다.
